import argparse
import html
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urljoin
from urllib.request import Request, urlopen

from db import fetch_all, fetch_one, get_connection


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCE_CATEGORIES = {
    "Medicine": "https://www.arogga.com/category-home/medicines",
    "Herbal": "https://www.arogga.com/category-home/herbal",
    "Sexual Wellness": "https://www.arogga.com/category-home/sexual-wellness",
    "Supplement": "https://www.arogga.com/category-home/supplement",
}

HEALTH_CARE_CATEGORY = "Health Care"
SOURCE_BRAND = "Arogga"
SELLER = "admin"
DEFAULT_QUANTITY = 20
DEFAULT_SIZE_ID = 1
DEFAULT_GENDER_ID = 4
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)


def clean_text(value):
    text = html.unescape(str(value or ""))
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_name(value, limit=80):
    value = clean_text(value)
    value = re.sub(r"[\\/:*?\"<>|]+", "", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value[:limit].strip() or "AroggaProduct")


def money(value):
    text = clean_text(value).replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else 0.0


def fetch_url(url):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read()


def extract_image_url(block):
    src = ""
    match = re.search(r'\bsrc="([^"]+)"', block)
    if match:
        src = html.unescape(match.group(1))
    if not src:
        match = re.search(r'\bsrcSet="([^"]+)"', block)
        if match:
            first = html.unescape(match.group(1)).split(" ")[0]
            src = first.strip()
    if not src:
        return ""
    return urljoin("https://www.arogga.com", src)


def parse_products(category_name, url):
    page = fetch_url(url).decode("utf-8", errors="ignore")
    products = {}
    pattern = re.compile(
        r'<a\b(?=[^>]*href="/product/(\d+)/([^"]+)")[^>]*>(.*?)</a></li>',
        re.S,
    )
    for match in pattern.finditer(page):
        source_id, slug, block = match.groups()
        name_match = re.search(r'<img\b[^>]*\balt="([^"]+)"', block)
        h4_match = re.search(r"<h4\b[^>]*>(.*?)</h4>", block, re.S)
        name = clean_text(name_match.group(1) if name_match else "")
        if not name and h4_match:
            name = clean_text(h4_match.group(1))
        if not name:
            name = clean_text(slug.replace("-", " "))

        price_match = re.search(r'product_single_price_generate[^>]*>(.*?)</div>', block, re.S)
        mrp_match = re.search(r'product_single_mrp_generate[^>]*>(.*?)</del>', block, re.S)
        sale_price = money(price_match.group(1) if price_match else "")
        mrp = money(mrp_match.group(1) if mrp_match else "") or sale_price
        if not sale_price:
            sale_price = mrp

        source_url = urljoin("https://www.arogga.com", "/product/{0}/{1}".format(source_id, slug))
        products[source_id] = {
            "source_id": source_id,
            "source_category": category_name,
            "source_url": source_url,
            "name": name[:550],
            "mrp": mrp,
            "sale_price": sale_price,
            "image_url": extract_image_url(block),
        }
    return list(products.values())


def ensure_brand(cursor):
    row = cursor.execute("SELECT TOP 1 BrandID FROM tblBrands WHERE Name = ?", [SOURCE_BRAND]).fetchone()
    if row:
        return int(row[0])
    cursor.execute("INSERT INTO tblBrands (Name) OUTPUT INSERTED.BrandID VALUES (?)", [SOURCE_BRAND])
    return int(cursor.fetchone()[0])


def ensure_subcategory(cursor, category_id, name):
    row = cursor.execute(
        "SELECT TOP 1 id FROM SubCategory WHERE Catid = ? AND SubcatName = ?",
        [category_id, name],
    ).fetchone()
    if row:
        return int(row[0])
    cursor.execute(
        """
        INSERT INTO SubCategory (Catid, SubcatName, Description, Image)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?)
        """,
        [category_id, name, "Imported Arogga {0} products.".format(name), ""],
    )
    return int(cursor.fetchone()[0])


def product_exists(cursor, source_id):
    code = "AROGGA-{0}".format(source_id)
    return cursor.execute("SELECT TOP 1 PID FROM tblProducts WHERE ProductID = ?", [code]).fetchone()


def save_image(product_id, product):
    image_url = product.get("image_url")
    if not image_url:
        return None
    product_dir = Path(__file__).resolve().parent / "static" / "ProductImage" / str(product_id)
    product_dir.mkdir(parents=True, exist_ok=True)
    image_base = safe_name("Arogga-{0}".format(product["source_id"]), 70) + "01"
    extension = ".jpg"
    try:
        path_part = unquote(image_url.split("?", 1)[0]).lower()
        suffix = Path(path_part).suffix
        if suffix in (".jpg", ".jpeg", ".png", ".webp"):
            extension = suffix
    except Exception:
        pass
    target = product_dir / (image_base + extension)
    if target.exists():
        return image_base, extension
    try:
        data = fetch_url(image_url)
        if data:
            target.write_bytes(data)
            return image_base, extension
    except Exception as exc:
        print("image download failed {0}: {1}".format(product["source_id"], exc))
    return None


def insert_product(cursor, product, category_id, subcategory_id, brand_id):
    next_row = cursor.execute("SELECT COALESCE(MAX(PID), 0) + 1 FROM tblProducts").fetchone()
    product_id = int(next_row[0] or 1)
    order_by = product_id
    voucher_no = "VN/{0}/{1}".format(datetime.now().year, order_by)
    price = product["mrp"] or product["sale_price"] or 0
    sale_price = product["sale_price"] or price
    source_code = "AROGGA-{0}".format(product["source_id"])
    description = "Imported from Arogga {0}. Source: {1}".format(
        product["source_category"],
        product["source_url"],
    )
    data = {
        "VoucherNo": voucher_no,
        "PName": product["name"],
        "PPrice": price,
        "PSelPrice": sale_price,
        "PBrandID": brand_id,
        "PCategoryID": category_id,
        "PSubCatID": subcategory_id,
        "PGender": DEFAULT_GENDER_ID,
        "PDescription": description,
        "PProductDetails": description,
        "PMaterialCare": "",
        "FreeDelivery": 0,
        "30DayRet": 0,
        "COD": 1,
        "ProductID": source_code,
        "Unit": "pcs",
        "MadeBy": SOURCE_BRAND,
        "Status": "BarcodeOk",
        "MainItemSellerName": SELLER,
        "Comission": 0,
        "MainItemSellerwillget": price,
        "UserComission": 0,
        "Marketplaecomission": 0,
        "ReferenceComission": 0,
        "OrderBy": order_by,
    }
    columns = list(data.keys())
    cursor.execute(
        """
        INSERT INTO tblProducts ({0})
        VALUES ({1})
        """.format(
            ", ".join("[{0}]".format(column) for column in columns),
            ", ".join("?" for _ in columns),
        ),
        [data[column] for column in columns],
    )
    cursor.execute(
        "INSERT INTO tblProductSizeQuantity (PID, SizeID, Quantity) VALUES (?, ?, ?)",
        [product_id, DEFAULT_SIZE_ID, DEFAULT_QUANTITY],
    )
    saved = save_image(product_id, product)
    if saved:
        image_name, extension = saved
        cursor.execute(
            "INSERT INTO tblProductImages (PID, Name, Extention) VALUES (?, ?, ?)",
            [product_id, image_name, extension],
        )
    cursor.execute(
        """
        INSERT INTO Productbarcode
            (Item_Id, CREATE_BY, VoucherNo, CREATE_DATE, PRICE, barcode, star, Status, Productid)
        VALUES
            (?, ?, ?, GETDATE(), ?, ?, ?, ?, ?)
        """,
        [
            str(product_id),
            SELLER,
            voucher_no,
            price,
            "{0}{1}{2}".format(product_id, DEFAULT_QUANTITY, order_by),
            "*",
            "OK",
            source_code,
        ],
    )
    return product_id


def collect_products():
    products = {}
    for category_name, url in SOURCE_CATEGORIES.items():
        for product in parse_products(category_name, url):
            products[product["source_id"]] = product
        time.sleep(0.5)
    return list(products.values())


def import_products(dry_run=True, limit=0):
    products = collect_products()
    if limit:
        products = products[:limit]
    print("Extracted {0} unique products.".format(len(products)))
    for product in products[:10]:
        print("{source_id} | {source_category} | {name} | {sale_price}".format(**product))
    if dry_run:
        return

    health = fetch_one("SELECT TOP 1 id FROM Category WHERE CategoryName = ?", [HEALTH_CARE_CATEGORY])
    if not health:
        raise RuntimeError("Health Care category was not found.")
    category_id = int(health["id"])

    inserted = 0
    skipped = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        brand_id = ensure_brand(cursor)
        subcategories = {
            name: ensure_subcategory(cursor, category_id, name)
            for name in SOURCE_CATEGORIES
        }
        for product in products:
            if product_exists(cursor, product["source_id"]):
                skipped += 1
                continue
            insert_product(cursor, product, category_id, subcategories[product["source_category"]], brand_id)
            inserted += 1
            print("inserted {0}: {1}".format(product["source_id"], product["name"]))
    print("Done. Inserted: {0}. Skipped duplicates: {1}.".format(inserted, skipped))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Insert products into the database.")
    parser.add_argument("--limit", type=int, default=0, help="Limit products for a small test import.")
    args = parser.parse_args()
    import_products(dry_run=not args.apply, limit=args.limit)


if __name__ == "__main__":
    main()
