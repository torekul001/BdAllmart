from datetime import datetime
from pathlib import Path

from werkzeug.utils import secure_filename

from admin_service import approve_product_barcode
from config import Config
from db import execute, fetch_all, fetch_one, get_connection


LOOKUP_CONFIG = {
    "brand": {
        "title": "Add Brand",
        "table": "tblBrands",
        "id": "BrandID",
        "name": "Name",
        "order": "Name",
        "source": "EcommerceUI/AddBrand.aspx",
    },
    "category": {
        "title": "Add Category",
        "table": "Category",
        "id": "id",
        "name": "CategoryName",
        "serial": "CategorySerial",
        "description": "Description",
        "image": "Image",
        "image_dir": "CatagoryImage",
        "order": "CASE WHEN ISNULL(CategorySerial, 0) = 0 THEN 1 ELSE 0 END, CategorySerial, CategoryName",
        "source": "EcommerceUI/Addcategory.aspx",
    },
    "subcategory": {
        "title": "Add Sub-category",
        "table": "SubCategory",
        "id": "id",
        "name": "SubcatName",
        "parent": "Catid",
        "description": "Description",
        "image": "Image",
        "image_dir": "SubCatagoryImage",
        "order": "SubcatName",
        "source": "EcommerceUI/AddSubCategory.aspx",
    },
    "gender": {
        "title": "Add Gender",
        "table": "tblGender",
        "id": "GenderID",
        "name": "GenderName",
        "order": "GenderName",
        "source": "EcommerceUI/AddGender.aspx",
    },
    "size": {
        "title": "Add Sizes",
        "table": "OnlySize",
        "id": "SizeId",
        "name": "SizeName",
        "order": "SizeId",
        "source": "EcommerceUI/AddSize.aspx",
    },
}


def _safe_int(value, default=0):
    try:
        return int(str(value or "").strip())
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        return float(str(value or default).strip())
    except (TypeError, ValueError):
        return default


def _clean(value, limit=None):
    text = str(value or "").strip()
    if limit:
        return text[:limit]
    return text


def _sql_id(name):
    return "[{0}]".format(str(name).replace("]", "]]"))


def _save_lookup_image(file_storage, folder):
    if not file_storage or not file_storage.filename:
        return ""
    target_dir = Path(__file__).resolve().parent / "static" / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file_storage.filename)
    if not filename:
        return ""
    stem = Path(filename).stem[:70] or "image"
    suffix = Path(filename).suffix or ".jpg"
    final_name = "{0}_{1}{2}".format(stem, datetime.now().strftime("%Y%m%d%H%M%S%f"), suffix)
    file_storage.save(str(target_dir / final_name))
    return "{0}/{1}".format(folder, final_name)


def _save_product_image(file_storage, product_id, product_name, index):
    if not file_storage or not file_storage.filename:
        return None
    target_dir = Path(__file__).resolve().parent / "static" / "ProductImage" / str(product_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(file_storage.filename).suffix or ".jpg"
    image_base = "{0}{1:02d}".format(secure_filename(product_name)[:80] or "Product", index)
    file_storage.save(str(target_dir / (image_base + extension)))
    return image_base, extension


def ensure_category_serial_column():
    exists = fetch_one(
        """
        SELECT TOP 1 COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Category' AND COLUMN_NAME = 'CategorySerial'
        """
    )
    if exists:
        return
    execute("ALTER TABLE Category ADD CategorySerial int NULL")
    rows = fetch_all("SELECT id FROM Category ORDER BY CategoryName")
    for index, row in enumerate(rows, start=1):
        execute("UPDATE Category SET CategorySerial = ? WHERE id = ?", [index, row.get("id")])


def lookup_module(slug):
    if slug == "category":
        ensure_category_serial_column()
    return LOOKUP_CONFIG.get(slug)


def ecommerce_setup_links():
    return [
        ("Add Brand", "brand"),
        ("Add Category", "category"),
        ("Add Sub-category", "subcategory"),
        ("Add Gender", "gender"),
        ("Add Sizes", "size"),
        ("Add Product", "product"),
    ]


def get_lookup_rows(slug):
    config = lookup_module(slug)
    if not config:
        return []
    if slug == "subcategory":
        return fetch_all(
            """
            SELECT S.id, S.Catid, C.CategoryName, S.SubcatName, S.Image, S.Description
            FROM SubCategory S
            LEFT JOIN Category C ON C.id = S.Catid
            ORDER BY C.CategoryName, S.SubcatName
            """
        )
    columns = [config["id"], config["name"]]
    if config.get("serial"):
        columns.append(config["serial"])
    if config.get("image"):
        columns.append(config["image"])
    if config.get("description"):
        columns.append(config["description"])
    return fetch_all(
        "SELECT {0} FROM {1} ORDER BY {2}".format(
            ", ".join(columns),
            config["table"],
            config.get("order") or config["name"],
        )
    )


def get_lookup_row(slug, item_id):
    config = lookup_module(slug)
    if not config:
        return None
    return fetch_one(
        "SELECT * FROM {0} WHERE {1} = ?".format(config["table"], config["id"]),
        [_safe_int(item_id)],
    )


def save_lookup(slug, form, files):
    config = lookup_module(slug)
    if not config:
        raise ValueError("Selected setup module was not found.")
    item_id = _safe_int(form.get("item_id"))
    name = _clean(form.get("name"), 50)
    if not name:
        raise ValueError("Name is required.")

    fields = {config["name"]: name}
    if config.get("serial"):
        serial = _safe_int(form.get("serial"))
        fields[config["serial"]] = serial or None
    if config.get("description"):
        fields[config["description"]] = _clean(form.get("description"), 500 if slug == "category" else 100)
    if config.get("parent"):
        fields[config["parent"]] = _safe_int(form.get("category_id"))
        if not fields[config["parent"]]:
            raise ValueError("Please select a category.")
    if config.get("image"):
        image_path = _save_lookup_image(files.get("image") if files else None, config["image_dir"])
        if image_path:
            fields[config["image"]] = image_path

    if item_id:
        assignments = ", ".join("{0} = ?".format(field) for field in fields)
        execute(
            "UPDATE {0} SET {1} WHERE {2} = ?".format(config["table"], assignments, config["id"]),
            list(fields.values()) + [item_id],
        )
        return item_id

    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    row = fetch_one(
        """
        INSERT INTO {0} ({1})
        OUTPUT INSERTED.{2}
        VALUES ({3})
        """.format(config["table"], columns, config["id"], placeholders),
        list(fields.values()),
    )
    return row.get(config["id"]) if row else None


def delete_lookup(slug, item_id):
    config = lookup_module(slug)
    if not config:
        raise ValueError("Selected setup module was not found.")
    execute("DELETE FROM {0} WHERE {1} = ?".format(config["table"], config["id"]), [_safe_int(item_id)])


def get_product_options():
    return {
        "categories": fetch_all("SELECT id, CategoryName FROM Category ORDER BY CategoryName"),
        "subcategories": fetch_all("SELECT id, Catid, SubcatName FROM SubCategory ORDER BY SubcatName"),
        "brands": fetch_all("SELECT BrandID, Name FROM tblBrands ORDER BY Name"),
        "genders": fetch_all("SELECT GenderID, GenderName FROM tblGender ORDER BY GenderName"),
        "sizes": fetch_all("SELECT SizeId, SizeName FROM OnlySize ORDER BY SizeId"),
    }


def _admin_product_filter(search):
    search = _clean(search, 80)
    clause = ""
    params = []
    if search:
        clause = "WHERE P.PName LIKE ? OR P.ProductID LIKE ? OR P.MainItemSellerName LIKE ?"
        like = "%{0}%".format(search)
        params.extend([like, like, like])
    return clause, params


def get_admin_product_count(search=""):
    clause, params = _admin_product_filter(search)
    row = fetch_one(
        """
        SELECT COUNT(1) AS Total
        FROM tblProducts P
        {0}
        """.format(clause),
        params,
    )
    return int((row or {}).get("Total") or 0)


def get_admin_products(search="", page=1, per_page=20):
    clause, params = _admin_product_filter(search)
    page = max(1, _safe_int(page, 1))
    per_page = max(1, min(100, _safe_int(per_page, 20)))
    offset = (page - 1) * per_page
    return fetch_all(
        """
        SELECT
            P.PID, P.PName, P.PPrice, P.PSelPrice, P.ProductID, P.Unit, P.MadeBy,
            P.Status, P.MainItemSellerName, C.CategoryName, S.SubcatName, B.Name AS BrandName,
            I.Name AS ImageName, I.Extention
        FROM tblProducts P
        LEFT JOIN Category C ON C.id = P.PCategoryID
        LEFT JOIN SubCategory S ON S.id = P.PSubCatID
        LEFT JOIN tblBrands B ON B.BrandID = P.PBrandID
        OUTER APPLY (
            SELECT TOP 1 Name, Extention
            FROM tblProductImages
            WHERE PID = P.PID
            ORDER BY PIMGID
        ) I
        {0}
        ORDER BY P.PID DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """.format(clause),
        params + [offset, per_page],
    )


def get_admin_product(product_id):
    return fetch_one(
        """
        SELECT TOP 1 *
        FROM tblProducts
        WHERE PID = ?
        """,
        [_safe_int(product_id)],
    )


def get_product_sizes(product_id):
    return fetch_all(
        "SELECT SizeID, Quantity FROM tblProductSizeQuantity WHERE PID = ?",
        [_safe_int(product_id)],
    )


def get_product_images(product_id):
    return fetch_all(
        "SELECT PIMGID, PID, Name, Extention FROM tblProductImages WHERE PID = ? ORDER BY PIMGID",
        [_safe_int(product_id)],
    )


def save_admin_product(form, files, admin_username):
    product_id = _safe_int(form.get("product_id"))
    name = _clean(form.get("product_name"), 550)
    if not name:
        raise ValueError("Product name is required.")

    price = _safe_float(form.get("price"))
    sale_price = _safe_float(form.get("sale_price"), price) or price
    quantity = _safe_int(form.get("quantity"), 1) or 1
    commission = _safe_float(form.get("commission"))
    commission_amount = (price * commission) / 100 if price else 0
    status = _clean(form.get("status"), 50) or "Not Delivered"

    data = {
        "PName": name,
        "PPrice": price,
        "PSelPrice": sale_price,
        "PBrandID": _safe_int(form.get("brand_id")),
        "PCategoryID": _safe_int(form.get("category_id")),
        "PSubCatID": _safe_int(form.get("subcategory_id")),
        "PGender": _safe_int(form.get("gender_id")),
        "PDescription": form.get("description") or "",
        "PProductDetails": form.get("details") or "",
        "PMaterialCare": form.get("material_care") or "",
        "FreeDelivery": 1 if form.get("free_delivery") else 0,
        "30DayRet": 1 if form.get("return_30") else 0,
        "COD": 1 if form.get("cod") else 0,
        "ProductID": _clean(form.get("product_code"), 50),
        "Unit": _clean(form.get("unit"), 50),
        "MadeBy": _clean(form.get("made_by"), 50),
        "Status": status,
        "MainItemSellerName": _clean(form.get("seller"), 250) or admin_username or "admin",
        "Comission": commission,
        "MainItemSellerwillget": price - commission_amount,
        "UserComission": (commission_amount * 50) / 100,
        "Marketplaecomission": (commission_amount * 40) / 100,
        "ReferenceComission": (commission_amount * 10) / 100,
    }

    with get_connection() as conn:
        cursor = conn.cursor()
        if product_id:
            assignments = ", ".join("{0} = ?".format(_sql_id(field)) for field in data)
            cursor.execute(
                "UPDATE tblProducts SET {0} WHERE PID = ?".format(assignments),
                list(data.values()) + [product_id],
            )
            cursor.execute("DELETE FROM tblProductSizeQuantity WHERE PID = ?", [product_id])
        else:
            next_row = cursor.execute("SELECT COALESCE(MAX(PID), 0) + 1 FROM tblProducts").fetchone()
            next_order = int(next_row[0] or 1)
            if not data["ProductID"]:
                data["ProductID"] = str(next_order)
            data["VoucherNo"] = "VN/{0}/{1}".format(datetime.now().year, next_order)
            data["OrderBy"] = next_order
            columns = list(data.keys())
            cursor.execute(
                """
                INSERT INTO tblProducts ({0})
                OUTPUT INSERTED.PID
                VALUES ({1})
                """.format(", ".join(_sql_id(column) for column in columns), ", ".join("?" for _ in columns)),
                [data[column] for column in columns],
            )
            product_id = int(cursor.fetchone()[0])

        selected_sizes = form.getlist("sizes") if hasattr(form, "getlist") else []
        if not selected_sizes:
            selected_sizes = [form.get("size_id") or "1"]
        for size_id in selected_sizes:
            cursor.execute(
                "INSERT INTO tblProductSizeQuantity (PID, SizeID, Quantity) VALUES (?, ?, ?)",
                [product_id, _safe_int(size_id, 1), quantity],
            )

        image_files = files.getlist("images") if files and hasattr(files, "getlist") else []
        current_count = cursor.execute("SELECT COUNT(*) FROM tblProductImages WHERE PID = ?", [product_id]).fetchone()[0]
        for image in image_files:
            if image and image.filename:
                current_count += 1
                saved = _save_product_image(image, product_id, name, current_count)
                if saved:
                    image_name, extension = saved
                    cursor.execute(
                        "INSERT INTO tblProductImages (PID, Name, Extention) VALUES (?, ?, ?)",
                        [product_id, image_name, extension],
                    )

    if form.get("approve_now"):
        approve_product_barcode(product_id, admin_username)

    return product_id


def delete_admin_product(product_id):
    product_id = _safe_int(product_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tblProductSizeQuantity WHERE PID = ?", [product_id])
        cursor.execute("DELETE FROM tblProductImages WHERE PID = ?", [product_id])
        cursor.execute("DELETE FROM Productbarcode WHERE Item_Id = ?", [str(product_id)])
        cursor.execute("DELETE FROM tblProducts WHERE PID = ?", [product_id])
