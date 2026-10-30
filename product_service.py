from db import fetch_all, fetch_one


FALLBACK_PRODUCT_SECTIONS = [
    {
        "title": "Grocery Items",
        "tag": "Fresh market picks",
        "products": [
            {"name": "Pure Ghee 250gm", "image": "ProductImage/107/Pure Ghee  250gm01.jpg", "price": "390"},
            {"name": "Mustard Oil 490ml", "image": "ProductImage/108/Mustard Oil 490ml01.jpg", "price": "180"},
            {"name": "Sundarbans Honey", "image": "ProductImage/101/Sundarbans Honey01.jpg", "price": "450"},
            {"name": "Black Seed Oil", "image": "ProductImage/103/Black Seed Oil 250ml01.jpg", "price": "250"},
            {"name": "Remedy Juice", "image": "ProductImage/105/Remedy Juice 350ml01.jpg", "price": "320"},
            {"name": "Chaler Gura 1kg", "image": "ProductImage/109/Chaler Gura 1kg01.jpg", "price": "95"},
        ],
    },
    {
        "title": "Fashion & Beauty",
        "tag": "Style for everyday",
        "products": [
            {"name": "Yellow Panjabi", "image": "ProductImage/100/Yellow panjabi01.jpg", "price": "850"},
            {"name": "Denim Blue Shirt", "image": "ProductImage/102/Denim blue Shirt01.jpg", "price": "690"},
            {"name": "Panjabi Collection", "image": "ProductImage/104/pangabi01.jpg", "price": "990"},
            {"name": "Winter Jacket", "image": "ProductImage/105/jacket01.jpg", "price": "1450"},
            {"name": "Fantasy Makeup", "image": "ProductImage/103/Fantasy Makeup01.jpg", "price": "550"},
            {"name": "Ladies Watch", "image": "ProductImage/10/New Style Ladies Bracelet Watch Women's01.jpg", "price": "420"},
        ],
    },
    {
        "title": "Electronics & Services",
        "tag": "Products plus digital work",
        "products": [
            {"name": "Bluetooth Speaker", "image": "ProductImage/100/Original T2 Bluetooth Speaker01.jpg", "price": "1250"},
            {"name": "Web Design", "image": "ProductImage/10/Web Design01.jpg", "price": "5000"},
            {"name": "ARGI+ Energy Pack", "image": "ProductImage/1/ARGI+ Energy Savings01.jpg", "price": "2100"},
            {"name": "Laptop Package", "image": "ProductImage/download.jpg", "price": "28000"},
            {"name": "Office Setup", "image": "CatagoryImage/Office & home.jpg", "price": "3500"},
            {"name": "Creative Design", "image": "CatagoryImage/CPAOffer.JPG", "price": "1500"},
        ],
    },
]

FALLBACK_CATEGORY_SHORTCUTS = [
    {"name": "Grocery", "image": "CatagoryImage/forever-living-products.jpg"},
    {"name": "Cosmetics", "image": "CatagoryImage/Cosmatik.jpg"},
    {"name": "Fashion", "image": "CatagoryImage/Fashion & Beauty.jpg"},
    {"name": "Food", "image": "CatagoryImage/Honey.jpg"},
    {"name": "Electronics", "image": "CatagoryImage/48.png"},
    {"name": "Home", "image": "CatagoryImage/Office & home.jpg"},
    {"name": "Courses", "image": "CatagoryImage/CPAOffer.JPG"},
    {"name": "Services", "image": "CatagoryImage/Machinery.jpg"},
]


def get_home_product_sections():
    try:
        sections = get_products_by_category()
    except Exception:
        return FALLBACK_PRODUCT_SECTIONS

    if not sections:
        return FALLBACK_PRODUCT_SECTIONS

    return sections


def get_category_shortcuts():
    tree = get_category_tree()
    if tree:
        return tree

    try:
        rows = fetch_all(
            """
            SELECT id, CategoryName, Image
            FROM Category
            ORDER BY CASE WHEN ISNULL(CategorySerial, 0) = 0 THEN 1 ELSE 0 END, CategorySerial, CategoryName
            """
        )
    except Exception:
        return FALLBACK_CATEGORY_SHORTCUTS

    categories = []
    for row in rows:
        image = clean_image_path(row.get("Image"), "CatagoryImage/48.png")
        categories.append({
            "id": str(row.get("id") or ""),
            "name": str(row.get("CategoryName") or "Category").strip(),
            "image": image,
        })

    return categories or FALLBACK_CATEGORY_SHORTCUTS


def get_category_tree():
    try:
        rows = fetch_all(
            """
            SELECT
                C.id AS CategoryID,
                C.CategoryName,
                C.Image AS CategoryImage,
                S.id AS SubCategoryID,
                S.SubcatName,
                S.Image AS SubCategoryImage
            FROM Category C
            LEFT JOIN SubCategory S ON S.Catid = C.id
            ORDER BY CASE WHEN ISNULL(C.CategorySerial, 0) = 0 THEN 1 ELSE 0 END, C.CategorySerial, C.CategoryName, S.SubcatName
            """
        )
    except Exception:
        return []

    categories = {}
    for row in rows:
        category_id = str(row.get("CategoryID") or "")
        if category_id not in categories:
            categories[category_id] = {
                "id": category_id,
                "name": str(row.get("CategoryName") or "Category").strip(),
                "image": clean_image_path(row.get("CategoryImage"), "CatagoryImage/48.png"),
                "subcategories": [],
            }

        subcategory_id = row.get("SubCategoryID")
        if subcategory_id is not None:
            categories[category_id]["subcategories"].append({
                "id": str(subcategory_id),
                "name": str(row.get("SubcatName") or "Sub Category").strip(),
                "image": clean_image_path(row.get("SubCategoryImage"), "SubCatagoryImage/1.jpg"),
            })

    return list(categories.values())


def get_products_by_category():
    subcategories = get_subcategories_by_category()
    rows = fetch_all(
        """
        WITH RankedProducts AS (
            SELECT
                CAT.id AS CategoryID,
                CAT.CategoryName,
                CAT.CategorySerial,
                B.PID,
                B.PName,
                B.PPrice,
                B.PSelPrice,
                B.Comission,
                B.PSubCatID,
                B.MainItemSellerName,
                C.Name,
                C.Extention,
                ROW_NUMBER() OVER (
                    PARTITION BY CAT.id
                    ORDER BY B.OrderBy DESC, B.PID DESC
                ) AS ProductRank
            FROM Productbarcode A
            INNER JOIN tblProducts B ON A.Item_Id = B.PID
            INNER JOIN Category CAT ON CAT.id = B.PCategoryID
            CROSS APPLY (
                SELECT TOP 1 *
                FROM tblProductImages C
                WHERE C.PID = B.PID
                ORDER BY C.PID DESC
            ) C
            WHERE A.Status = 'OK'
        )
        SELECT
            CategoryID,
            CategoryName,
            CategorySerial,
            PID,
            PName,
            PPrice,
            PSelPrice,
            Comission,
            PSubCatID,
            MainItemSellerName,
            Name,
            Extention
        FROM RankedProducts
        WHERE ProductRank <= 24
        ORDER BY CASE WHEN ISNULL(CategorySerial, 0) = 0 THEN 1 ELSE 0 END, CategorySerial, CategoryName, ProductRank
        """
    )

    sections_by_id = {}
    for row in rows:
        category_id = str(row.get("CategoryID") or "")
        if category_id not in sections_by_id:
            category_name = str(row.get("CategoryName") or "Products").strip()
            sections_by_id[category_id] = {
                "id": category_id,
                "title": category_name,
                "tag": "Category wise products",
                "subcategories": subcategories.get(category_id, []),
                "products": [],
            }
        sections_by_id[category_id]["products"].append(map_product(row))

    return [section for section in sections_by_id.values() if section["products"]]


def get_category_details(category_id):
    rows = fetch_all(
        """
        SELECT TOP 1 id, CategoryName, Description, Image
        FROM Category
        WHERE id = ?
        """,
        [category_id],
    )
    if not rows:
        return None

    row = rows[0]
    return {
        "id": str(row.get("id") or ""),
        "name": str(row.get("CategoryName") or "Category").strip(),
        "description": str(row.get("Description") or "").strip(),
        "image": clean_image_path(row.get("Image"), "CatagoryImage/48.png"),
    }


def get_subcategory_details(subcategory_id):
    rows = fetch_all(
        """
        SELECT TOP 1 id, Catid, SubcatName, Description, Image
        FROM SubCategory
        WHERE id = ?
        """,
        [subcategory_id],
    )
    if not rows:
        return None

    row = rows[0]
    return {
        "id": str(row.get("id") or ""),
        "category_id": str(row.get("Catid") or ""),
        "name": str(row.get("SubcatName") or "Sub Category").strip(),
        "description": str(row.get("Description") or "").strip(),
        "image": clean_image_path(row.get("Image"), "SubCatagoryImage/1.jpg"),
    }


def get_category_products(category_id, subcategory_id=None):
    params = [category_id]
    subcategory_filter = ""
    if subcategory_id:
        subcategory_filter = " AND B.PSubCatID = ?"
        params.append(subcategory_id)

    rows = fetch_all(
        """
        SELECT
            B.PID,
            B.PName,
            B.PPrice,
            B.PSelPrice,
            B.Comission,
            B.PCategoryID,
            B.PSubCatID,
            B.MainItemSellerName,
            C.Name,
            C.Extention
        FROM Productbarcode A
        INNER JOIN tblProducts B ON A.Item_Id = B.PID
        CROSS APPLY (
            SELECT TOP 1 *
            FROM tblProductImages C
            WHERE C.PID = B.PID
            ORDER BY C.PID DESC
        ) C
        WHERE A.Status = 'OK' AND B.PCategoryID = ?
        """ + subcategory_filter + """
        ORDER BY B.OrderBy DESC, B.PID DESC
        """,
        params,
    )
    return [map_product(row) for row in rows]


def get_product_details(product_id):
    row = fetch_one(
        """
        SELECT TOP 1
            B.PID,
            B.PName,
            B.PPrice,
            B.PSelPrice,
            B.Comission,
            B.PCategoryID,
            B.PSubCatID,
            B.PDescription,
            B.PProductDetails,
            B.PMaterialCare,
            B.Unit,
            B.MadeBy,
            B.MainItemSellerName,
            CAT.CategoryName,
            SUB.SubcatName
        FROM tblProducts B
        LEFT JOIN Category CAT ON CAT.id = B.PCategoryID
        LEFT JOIN SubCategory SUB ON SUB.id = B.PSubCatID
        WHERE B.PID = ?
        """,
        [product_id],
    )
    if not row:
        return None

    product = map_product(row)
    product.update({
        "category_id": str(row.get("PCategoryID") or ""),
        "subcategory_id": str(row.get("PSubCatID") or ""),
        "category_name": str(row.get("CategoryName") or "").strip(),
        "subcategory_name": str(row.get("SubcatName") or "").strip(),
        "description": clean_html_text(row.get("PDescription")),
        "details": clean_html_text(row.get("PProductDetails")),
        "material_care": clean_html_text(row.get("PMaterialCare")),
        "unit": str(row.get("Unit") or "").strip(),
        "made_by": str(row.get("MadeBy") or "").strip(),
        "images": get_product_images(product_id),
    })

    if not product["images"]:
        product["images"] = [product["image"]]

    return product


def get_product_images(product_id):
    rows = fetch_all(
        """
        SELECT Name, Extention
        FROM tblProductImages
        WHERE PID = ? AND ISNULL(Extention, '') <> 'YouTube' AND ISNULL(Extention, '') <> '.mp4'
        ORDER BY Name
        """,
        [product_id],
    )

    images = []
    for row in rows:
        image_name = str(row.get("Name") or "").strip()
        extension = str(row.get("Extention") or "").strip()
        if image_name and extension and not image_name.lower().endswith(extension.lower()):
            image_name += extension
        if image_name:
            images.append("ProductImage/{0}/{1}".format(product_id, image_name))
    return images


def get_subcategories_by_category():
    rows = fetch_all(
        """
        SELECT id, Catid, SubcatName, Image
        FROM SubCategory
        ORDER BY Catid, SubcatName
        """
    )
    grouped = {}
    for row in rows:
        category_id = str(row.get("Catid") or "")
        grouped.setdefault(category_id, []).append({
            "id": str(row.get("id") or ""),
            "name": str(row.get("SubcatName") or "Sub Category").strip(),
            "image": clean_image_path(row.get("Image"), "SubCatagoryImage/1.jpg"),
        })
    return grouped


def get_latest_products():
    rows = fetch_all(
        """
        SELECT TOP 36
            B.PID,
            B.PName,
            B.PPrice,
            B.PSelPrice,
            B.Comission,
            B.PCategoryID,
            B.PSubCatID,
            B.MainItemSellerName,
            C.Name,
            C.Extention
        FROM Productbarcode A
        INNER JOIN tblProducts B ON A.Item_Id = B.PID
        CROSS APPLY (
            SELECT TOP 1 *
            FROM tblProductImages C
            WHERE C.PID = B.PID
            ORDER BY C.PID DESC
        ) C
        WHERE A.Status = 'OK'
        ORDER BY B.OrderBy DESC
        """
    )
    return [map_product(row) for row in rows]


def map_product(row):
    pid = str(row.get("PID") or "").strip()
    image_name = str(row.get("Name") or "").strip()
    extension = str(row.get("Extention") or "").strip()
    if image_name and extension and not image_name.lower().endswith(extension.lower()):
        image_name += extension

    image_path = "ProductImage/{0}/{1}".format(pid, image_name) if pid and image_name else "ProductImage/download.jpg"
    price = row.get("PSelPrice") or row.get("PPrice") or "0"

    return {
        "id": pid,
        "name": str(row.get("PName") or "Product").strip(),
        "price": str(price).strip(),
        "commission": str(row.get("Comission") or "0").strip(),
        "image": image_path,
        "seller": str(row.get("MainItemSellerName") or "").strip(),
    }


def clean_html_text(value):
    text = str(value or "").strip()
    return (
        text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("<br />", "\n")
        .replace("<br>", "\n")
    )


def clean_image_path(value, fallback):
    path = str(value or "").strip()
    if not path:
        return fallback

    path = path.replace("\\", "/")
    path = path.replace("~//", "").replace("~/", "").lstrip("/")
    while path.startswith("../"):
        path = path[3:]
    while "//" in path:
        path = path.replace("//", "/")
    return path or fallback
