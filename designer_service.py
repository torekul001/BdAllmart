import base64
import html
from datetime import datetime
from pathlib import Path

from werkzeug.utils import secure_filename

from config import Config
from db import execute, fetch_all, fetch_one, get_connection
from security import password_for_storage, verify_password


DESIGNER_MENU = [
    ("Designer Dashboard", "/designer/dashboard"),
    ("Offer Place", "/designer/offers"),
    ("My Profile", "/designer/profile"),
    ("Own Products", "/designer/products"),
    ("Affiliate Products", "/designer/affiliate"),
    ("Work Order List", "/designer/jobs"),
    ("Design Submit", "/designer/submit"),
    ("My Design", "/designer/submissions"),
    ("Design Status", "/designer/status"),
    ("All Design", "/designer/designs"),
    ("My Orders", "/designer/orders"),
    ("Order Tracking", "/designer/order-tracking"),
    ("Messages", "/designer/messages"),
]

OFFER_CATEGORIES = [
    "Graphic Design",
    "Web Design",
    "Image Editing",
    "Mobile Apps",
    "Health Product",
    "Data Entry",
    "Email Marketing",
    "Search Engine Optimization(SEO)",
    "Logo Design",
    "Software Develop",
]

PACKAGE_FEATURES = [
    ("High Resolution(JPG)", "high_resolution"),
    ("Logo Transparency(PNG)", "logo_transparency"),
    ("3D Mockup", "mockup"),
    ("Vector File(EPS)", "vector_file"),
    ("PDF File", "pdf_file"),
    ("Source File", "source_file"),
    ("PSD File", "PSD_File"),
]


def _count(query, params=None):
    row = fetch_one(query, params or [])
    if not row:
        return 0
    return int(row.get("Total") or 0)


def _money(value):
    try:
        return "Tk {0:,.0f}".format(float(value or 0))
    except (TypeError, ValueError):
        return "Tk 0"


def _legacy_file_path(folder, filename):
    return "~\\{0}\\{1}".format(folder, filename)


def _save_upload(file_storage, folder, prefix):
    if not file_storage or not file_storage.filename:
        return ""

    target_dir = Path(Config.PROJECT_ROOT) / folder
    target_dir.mkdir(parents=True, exist_ok=True)

    original_name = secure_filename(file_storage.filename)
    if not original_name:
        original_name = "upload"
    filename = "{0}_{1}_{2}".format(prefix, datetime.now().strftime("%Y%m%d%H%M%S%f"), original_name)
    file_storage.save(str(target_dir / filename))
    return _legacy_file_path(folder, filename)


def _save_plain_upload(file_storage, folder, filename):
    if not file_storage or not file_storage.filename:
        return ""
    target_dir = Path(Config.PROJECT_ROOT) / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    file_storage.save(str(target_dir / filename))
    return filename


def _compact_filename(prefix, original_name, limit=50):
    safe_name = secure_filename(original_name or "upload")
    suffix = Path(safe_name).suffix[:10]
    stem = Path(safe_name).stem
    reserved = len(prefix) + len(suffix)
    available = max(6, limit - reserved)
    return "{0}{1}{2}".format(prefix, stem[:available], suffix)


def _to_int(value, default=0):
    try:
        return int(float(str(value or default).replace("$", "").strip()))
    except (TypeError, ValueError):
        return default


def _to_float(value, default=0):
    try:
        return float(str(value or default).strip())
    except (TypeError, ValueError):
        return default


def ensure_affiliate_table():
    execute(
        """
        IF OBJECT_ID('dbo.DesignerAffiliateProducts', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.DesignerAffiliateProducts (
                Id INT IDENTITY(1,1) PRIMARY KEY,
                DesignerUserId VARCHAR(50) NOT NULL,
                ProductId VARCHAR(100) NOT NULL,
                AffiliatePrice DECIMAL(18,2) NULL,
                CommissionPercent DECIMAL(18,2) NULL,
                Note VARCHAR(500) NULL,
                Status VARCHAR(50) NULL,
                CreatedAt DATETIME NOT NULL DEFAULT(GETDATE())
            )
        END
        """
    )


def get_designer_profile(user_id):
    return fetch_one(
        """
        SELECT TOP 1 UserId, Username, FirstName, LastName, Email, Phone, UserCatagory,
            Active, Status, Team, SubTeam, Reting, Lavel, AboutMe, Address, City,
            State, PostalCode, Country, picture
        FROM Users
        WHERE UserId = ?
        """,
        [user_id],
    )


def get_designer_expertise(user_id, username=""):
    keys = [str(user_id or ""), str(username or "")]
    return {
        str(row.get("ExpName") or "").strip()
        for row in fetch_all(
            """
            SELECT ExpName
            FROM UserExperties
            WHERE UserId IN (?, ?)
            """,
            keys,
        )
        if str(row.get("ExpName") or "").strip()
    }


def get_service_types():
    return fetch_all(
        """
        SELECT Services
        FROM ServicesType
        WHERE ISNULL(Services, '') <> ''
        ORDER BY Services
        """
    )


def update_designer_profile(user_id, data, picture_file=None):
    values = [
        data.get("username", "").strip(),
        data.get("first_name", "").strip(),
        data.get("last_name", "").strip(),
        data.get("phone", "").strip(),
        data.get("address", "").strip(),
        data.get("city", "").strip(),
        data.get("state", "").strip(),
        data.get("postal_code", "").strip() or None,
        data.get("about_me", "").strip(),
        user_id,
    ]
    if picture_file and picture_file.filename:
        execute(
            """
            UPDATE Users
            SET Username = ?, FirstName = ?, LastName = ?, Phone = ?, Address = ?,
                City = ?, State = ?, PostalCode = ?, AboutMe = ?, picture = ?
            WHERE UserId = ?
            """,
            values[:-1] + [picture_file.read(), user_id],
        )
        return

    execute(
        """
        UPDATE Users
        SET Username = ?, FirstName = ?, LastName = ?, Phone = ?, Address = ?,
            City = ?, State = ?, PostalCode = ?, AboutMe = ?
        WHERE UserId = ?
        """,
        values,
    )


def update_designer_expertise(user_id, username, expertise, previous_username=""):
    keys = [str(user_id or ""), str(username or ""), str(previous_username or "")]
    execute("DELETE FROM UserExperties WHERE UserId IN (?, ?, ?)", keys)
    for item in expertise or []:
        service = str(item or "").strip()
        if service:
            execute(
                "INSERT INTO UserExperties (ExpName, UserId) VALUES (?, ?)",
                [service, str(username or user_id)],
            )


def update_designer_password(user_id, password, old_password=""):
    if not password:
        raise ValueError("New password is required.")
    current = fetch_one("SELECT TOP 1 Password FROM Users WHERE UserId = ?", [user_id])
    if old_password and current and not verify_password(old_password, str(current.get("Password") or "")):
        raise ValueError("Old password is not correct.")
    execute("UPDATE Users SET Password = ? WHERE UserId = ?", [password_for_storage(password), user_id])


def user_picture_data_url(profile):
    picture = (profile or {}).get("picture")
    if not picture:
        return ""
    try:
        return "data:image/png;base64,{0}".format(base64.b64encode(bytes(picture)).decode("ascii"))
    except Exception:
        return ""


def get_designer_public_profile(username_or_id):
    lookup = str(username_or_id or "").strip()
    user_id = int(lookup) if lookup.isdigit() else -1
    return fetch_one(
        """
        SELECT TOP 1 UserId, Username, FirstName, LastName, Email, Phone, Country,
            UserCatagory, Lavel, Reting, AboutMe, Team, SubTeam, picture
        FROM Users
        WHERE Username = ? OR UserId = ?
        """,
        [lookup, user_id],
    )


def get_designer_summary(user_id, username=""):
    selected_total = fetch_one(
        """
        SELECT COALESCE(SUM(CAST(J.Price AS float)), 0) AS Total
        FROM Submission S
        INNER JOIN JobsList J ON S.jobid = J.Jobid
        WHERE S.userid = ? AND COALESCE(S.status, '') = 'Selected'
        """,
        [user_id],
    )
    return {
        "open_jobs": _count("SELECT COUNT(1) AS Total FROM JobsList WHERE Deadline >= GETDATE() AND LOWER(COALESCE(BitOrContest,'contest')) IN ('bit','bid','contest') AND LTRIM(RTRIM(COALESCE(Status,''))) IN ('True','1','Active')"),
        "submissions": _count("SELECT COUNT(1) AS Total FROM Submission WHERE userid = ?", [user_id]),
        "selected": _count("SELECT COUNT(1) AS Total FROM Submission WHERE userid = ? AND COALESCE(status, '') = 'Selected'", [user_id]),
        "orders": _count(
            """
            SELECT SUM(Total) AS Total
            FROM (
                SELECT COUNT(1) AS Total
                FROM Order_List O
                LEFT JOIN OfferDetails OD ON O.Offer_id = OD.id
                WHERE O.DesignerId IN (?, ?)
                    OR OD.userid IN (?, ?)
                UNION ALL
                SELECT COUNT(DISTINCT O.orderid) AS Total
                FROM TblOrder O
                WHERE O.MainItemSellerName = ? OR O.UserName = ?
            ) X
            """,
            [user_id, str(username or ""), str(user_id), str(username or ""), str(username or ""), str(username or "")],
        ),
        "offers": _count("SELECT COUNT(1) AS Total FROM OfferDetails WHERE userid = ?", [str(user_id)]),
        "earnings": _money((selected_total or {}).get("Total")),
    }


def get_offer_categories():
    return OFFER_CATEGORIES


def get_designer_offers(user_id):
    return fetch_all(
        """
        SELECT
            O.*,
            I.image_path,
            I.NofImage
        FROM OfferDetails O
        LEFT JOIN (
            SELECT Offerid, COUNT(*) AS NofImage, MIN(image_path) AS image_path
            FROM OfferImage
            GROUP BY Offerid
        ) I ON I.Offerid = O.id
        WHERE O.userid = ?
        ORDER BY O.id DESC
        """,
        [str(user_id)],
    )


def get_offer_images(offer_id):
    return fetch_all(
        "SELECT id, userid, image_path, Offerid FROM OfferImage WHERE Offerid = ? ORDER BY id DESC",
        [offer_id],
    )


def get_public_offer(offer_id):
    return fetch_one(
        """
        SELECT TOP 1
            O.*,
            U.Username,
            U.FirstName,
            U.LastName,
            I.image_path
        FROM OfferDetails O
        LEFT JOIN Users U ON CONVERT(varchar(50), U.UserId) = O.userid
        LEFT JOIN (
            SELECT Offerid, MIN(image_path) AS image_path
            FROM OfferImage
            GROUP BY Offerid
        ) I ON I.Offerid = O.id
        WHERE O.id = ?
        """,
        [offer_id],
    )


def offer_package_amount(offer, package_id):
    package_id = str(package_id or "3")
    if package_id == "1":
        return _to_float((offer or {}).get("offer_amount1"), 0)
    if package_id == "2":
        return _to_float((offer or {}).get("offer_amount2"), 0)
    return _to_float((offer or {}).get("offer_amount3"), 0)


def create_service_order(offer, customer_id, package_id, amount):
    if not offer:
        raise ValueError("Offer was not found.")
    execute(
        """
        INSERT INTO Order_List
            (Offer_id, Order_date, CustomerId, DesignerId, pakageId, status, OfferAmount)
        VALUES
            (?, GETDATE(), ?, ?, ?, ?, ?)
        """,
        [
            str(offer.get("id") or ""),
            str(customer_id or "0"),
            str(offer.get("userid") or "0"),
            str(package_id or "3"),
            "Pending",
            amount,
        ],
    )


def save_designer_offer(user_id, username, form, images, zip_file=None):
    offer_id = str(form.get("offer_id") or "").strip()
    values = {
        "offer_title": form.get("offer_title", "").strip(),
        "OfferType": form.get("offer_category", "").strip() or "Graphic Design",
        "offer_type1": form.get("package1_name", "").strip() or "Premium",
        "offer_type2": form.get("package2_name", "").strip() or "Standard",
        "offer_type3": form.get("package3_name", "").strip() or "Basic",
        "offer_amount1": _to_int(form.get("package1_amount"), 0),
        "offer_amount2": _to_int(form.get("package2_amount"), 0),
        "offer_amount3": _to_int(form.get("package3_amount"), 0),
        "description1": form.get("package1_description", "").strip(),
        "description2": form.get("package2_description", "").strip(),
        "description3": form.get("package3_description", "").strip(),
        "initial_concepts1": form.get("initial_concepts1", "").strip(),
        "initial_concepts2": form.get("initial_concepts2", "").strip(),
        "initial_concepts3": form.get("initial_concepts3", "").strip(),
        "revisions1": form.get("revisions1", "").strip(),
        "revisions2": form.get("revisions2", "").strip(),
        "revisions3": form.get("revisions3", "").strip(),
        "delivery_time1_1day": form.get("delivery1", "").strip(),
        "delivery_time2": form.get("delivery2", "").strip(),
        "delivery_time3": form.get("delivery3", "").strip(),
        "about_this_offer1": form.get("about_offer1", "").strip(),
        "about_this_offer2": form.get("about_offer2", "").strip(),
        "QuickDelivery1": form.get("quick_delivery1", "").strip(),
        "QuickDelivery2": form.get("quick_delivery2", "").strip(),
        "QuickDelivery3": form.get("quick_delivery3", "").strip(),
        "QuickDelChare1": _to_int(form.get("quick_charge1"), 0),
        "QuickDelChare2": _to_int(form.get("quick_charge2"), 0),
        "QuickDelChare3": _to_int(form.get("quick_charge3"), 0),
    }
    if not values["offer_title"]:
        raise ValueError("Offer title is required.")

    selected_features = set(form.getlist("features")) if hasattr(form, "getlist") else set()
    for _, key in PACKAGE_FEATURES:
        for index in (1, 2, 3):
            values["{0}{1}".format(key, index)] = "1" if "{0}{1}".format(key, index) in selected_features else "0"

    zip_name = ""
    if zip_file and zip_file.filename:
        zip_name = "{0}_{1}".format(username, secure_filename(zip_file.filename))
        _save_plain_upload(zip_file, "ZipFiles", zip_name)

    with get_connection() as conn:
        cursor = conn.cursor()
        if offer_id:
            existing = cursor.execute("SELECT COUNT(1) FROM OfferDetails WHERE id = ? AND userid = ?", [offer_id, str(user_id)]).fetchone()[0]
            if not existing:
                raise ValueError("Offer was not found for this user.")
            cursor.execute(
                """
                UPDATE OfferDetails SET
                    offer_title=?, OfferType=?, offer_type1=?, offer_type2=?, offer_type3=?,
                    offer_amount1=?, offer_amount2=?, offer_amount3=?,
                    description1=?, description2=?, description3=?,
                    high_resolution1=?, high_resolution2=?, high_resolution3=?,
                    logo_transparency1=?, logo_transparency2=?, logo_transparency3=?,
                    mockup1=?, mockup2=?, mockup3=?,
                    vector_file1=?, vector_file2=?, vector_file3=?,
                    pdf_file1=?, pdf_file2=?, pdf_file3=?,
                    source_file1=?, source_file2=?, source_file3=?,
                    PSD_File1=?, PSD_File2=?, PSD_File3=?,
                    initial_concepts1=?, initial_concepts2=?, initial_concepts3=?,
                    revisions1=?, revisions2=?, revisions3=?,
                    delivery_time1_1day=?, delivery_time2=?, delivery_time3=?,
                    about_this_offer1=?, about_this_offer2=?,
                    QuickDelivery1=?, QuickDelivery2=?, QuickDelivery3=?,
                    QuickDelChare1=?, QuickDelChare2=?, QuickDelChare3=?,
                    zipfile=COALESCE(NULLIF(?, ''), zipfile)
                WHERE id=? AND userid=?
                """,
                _offer_params(values) + [zip_name, offer_id, str(user_id)],
            )
            saved_offer_id = int(offer_id)
        else:
            cursor.execute(
                """
                INSERT INTO OfferDetails
                    (offer_title, OfferType, offer_type1, offer_type2, offer_type3,
                     offer_amount1, offer_amount2, offer_amount3,
                     description1, description2, description3,
                     high_resolution1, high_resolution2, high_resolution3,
                     logo_transparency1, logo_transparency2, logo_transparency3,
                     mockup1, mockup2, mockup3,
                     vector_file1, vector_file2, vector_file3,
                     pdf_file1, pdf_file2, pdf_file3,
                     source_file1, source_file2, source_file3,
                     PSD_File1, PSD_File2, PSD_File3,
                     initial_concepts1, initial_concepts2, initial_concepts3,
                     revisions1, revisions2, revisions3,
                     delivery_time1_1day, delivery_time2, delivery_time3,
                     about_this_offer1, about_this_offer2,
                     QuickDelivery1, QuickDelivery2, QuickDelivery3,
                     QuickDelChare1, QuickDelChare2, QuickDelChare3,
                     userid, zipfile, order_date)
                OUTPUT INSERTED.id
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                """,
                _offer_params(values) + [str(user_id), zip_name],
            )
            saved_offer_id = int(cursor.fetchone()[0])

        clean_images = [image for image in (images or []) if image and image.filename][:3]
        if clean_images:
            cursor.execute("DELETE FROM OfferImage WHERE userid = ? AND Offerid = ?", [str(user_id), saved_offer_id])

        for image in clean_images:
            if image and image.filename:
                filename = _compact_filename("{0}{1}_".format(user_id, saved_offer_id), image.filename, 50)
                _save_plain_upload(image, "OfferImages", filename)
                cursor.execute(
                    "INSERT INTO OfferImage (userid, image_path, Offerid) VALUES (?, ?, ?)",
                    [str(user_id), filename, saved_offer_id],
                )
    return saved_offer_id


def _offer_params(values):
    return [
        values["offer_title"], values["OfferType"], values["offer_type1"], values["offer_type2"], values["offer_type3"],
        values["offer_amount1"], values["offer_amount2"], values["offer_amount3"],
        values["description1"], values["description2"], values["description3"],
        values["high_resolution1"], values["high_resolution2"], values["high_resolution3"],
        values["logo_transparency1"], values["logo_transparency2"], values["logo_transparency3"],
        values["mockup1"], values["mockup2"], values["mockup3"],
        values["vector_file1"], values["vector_file2"], values["vector_file3"],
        values["pdf_file1"], values["pdf_file2"], values["pdf_file3"],
        values["source_file1"], values["source_file2"], values["source_file3"],
        values["PSD_File1"], values["PSD_File2"], values["PSD_File3"],
        values["initial_concepts1"], values["initial_concepts2"], values["initial_concepts3"],
        values["revisions1"], values["revisions2"], values["revisions3"],
        values["delivery_time1_1day"], values["delivery_time2"], values["delivery_time3"],
        values["about_this_offer1"], values["about_this_offer2"],
        values["QuickDelivery1"], values["QuickDelivery2"], values["QuickDelivery3"],
        values["QuickDelChare1"], values["QuickDelChare2"], values["QuickDelChare3"],
    ]


def get_categories():
    return fetch_all("SELECT id, CategoryName FROM Category ORDER BY CategoryName")


def get_subcategories(category_id=None):
    if category_id:
        return fetch_all("SELECT id, Catid, SubcatName FROM SubCategory WHERE Catid = ? ORDER BY SubcatName", [category_id])
    return fetch_all("SELECT id, Catid, SubcatName FROM SubCategory ORDER BY SubcatName")


def create_designer_product(user_id, username, form, images):
    name = form.get("product_name", "").strip()
    if not name:
        raise ValueError("Product name is required.")
    price = _to_float(form.get("price"), 0)
    sale_price = _to_float(form.get("sale_price"), price)
    commission = _to_float(form.get("commission"), 0)
    commission_amount = (price * commission) / 100 if price else 0

    with get_connection() as conn:
        cursor = conn.cursor()
        max_row = cursor.execute("SELECT COALESCE(MAX(PID), 0) + 1 FROM tblProducts").fetchone()
        next_order = int(max_row[0] or 1)
        voucher_no = "VN/{0}/{1}".format(datetime.now().year, next_order)
        cursor.execute(
            """
            INSERT INTO tblProducts
                (VoucherNo, PName, PPrice, PSelPrice, PBrandID, PCategoryID, PSubCatID, PGender,
                 PDescription, PProductDetails, PMaterialCare, FreeDelivery, [30DayRet], COD,
                 ProductID, Unit, MadeBy, Status, MainItemSellerName, Comission,
                 MainItemSellerwillget, UserComission, Marketplaecomission, ReferenceComission, OrderBy)
            OUTPUT INSERTED.PID
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                voucher_no,
                name,
                price,
                sale_price,
                int(form.get("brand_id") or 0),
                int(form.get("category_id") or 0),
                int(form.get("subcategory_id") or 0),
                int(form.get("gender_id") or 0),
                form.get("description", ""),
                form.get("details", ""),
                form.get("material_care", ""),
                1 if form.get("free_delivery") else 0,
                1 if form.get("return_30") else 0,
                1 if form.get("cod") else 0,
                form.get("product_code") or "",
                form.get("unit") or "",
                form.get("made_by") or username,
                "Not Delivered",
                username,
                commission,
                price - commission_amount,
                (commission_amount * 50) / 100,
                (commission_amount * 40) / 100,
                (commission_amount * 10) / 100,
                next_order,
            ],
        )
        pid = int(cursor.fetchone()[0])
        cursor.execute(
            """
            INSERT INTO Productbarcode
                (Item_Id, CREATE_BY, VoucherNo, CREATE_DATE, PRICE, Qty, barcode, star, Status, Productid)
            VALUES
                (?, ?, ?, GETDATE(), ?, ?, ?, ?, ?, ?)
            """,
            [
                str(pid),
                username,
                voucher_no,
                sale_price,
                int(form.get("quantity") or 1),
                str(pid),
                "",
                "OK",
                form.get("product_code") or str(pid),
            ],
        )

        product_dir = Path(__file__).resolve().parent / "static" / "ProductImage" / str(pid)
        product_dir.mkdir(parents=True, exist_ok=True)
        image_count = 0
        for image in images or []:
            if image and image.filename:
                image_count += 1
                extension = Path(image.filename).suffix or ".jpg"
                image_base = "{0}{1:02d}".format(secure_filename(name)[:80] or "Product", image_count)
                image.save(str(product_dir / (image_base + extension)))
                cursor.execute(
                    "INSERT INTO tblProductImages (PID, Name, Extention) VALUES (?, ?, ?)",
                    [pid, image_base, extension],
                )
    return pid


def get_designer_products(username):
    return fetch_all(
        """
        SELECT TOP 120
            P.PID, P.PName, P.PPrice, P.PSelPrice, P.PCategoryID, P.PSubCatID,
            P.Status, P.MainItemSellerName, P.Comission, I.Name, I.Extention
        FROM tblProducts P
        LEFT JOIN (
            SELECT PID, MIN(Name) AS Name, MIN(Extention) AS Extention
            FROM tblProductImages
            GROUP BY PID
        ) I ON I.PID = P.PID
        WHERE P.MainItemSellerName = ?
        ORDER BY P.PID DESC
        """,
        [username],
    )


def search_products(query="", limit=1000):
    like = "%{0}%".format(query or "")
    return fetch_all(
        """
        SELECT TOP ({0})
            P.PID, P.PName, P.PPrice, P.PSelPrice, P.Comission, P.MainItemSellerName,
            I.Name, I.Extention
        FROM tblProducts P
        LEFT JOIN (
            SELECT PID, MIN(Name) AS Name, MIN(Extention) AS Extention
            FROM tblProductImages
            GROUP BY PID
        ) I ON I.PID = P.PID
        WHERE EXISTS (
                SELECT 1
                FROM Productbarcode PB
                WHERE PB.Item_Id = P.PID AND PB.Status = 'OK'
            )
            AND (? = '%%' OR P.PName LIKE ? OR P.MainItemSellerName LIKE ?)
        ORDER BY P.PID DESC
        """.format(int(limit)),
        [like, like, like],
    )


def add_affiliate_product(user_id, form):
    ensure_affiliate_table()
    product_id = str(form.get("product_id") or "").strip()
    if not product_id:
        raise ValueError("Please select a product for affiliate.")
    exists = fetch_one("SELECT TOP 1 PID, Comission, PSelPrice, PPrice FROM tblProducts WHERE PID = ?", [product_id])
    if not exists:
        raise ValueError("Selected product was not found.")
    duplicate = fetch_one(
        "SELECT TOP 1 Id FROM DesignerAffiliateProducts WHERE DesignerUserId = ? AND ProductId = ?",
        [str(user_id), product_id],
    )
    commission = _to_float(form.get("commission_percent"), None)
    if commission is None:
        commission = _to_float(exists.get("Comission"), 0)
    affiliate_price = _to_float(form.get("affiliate_price"), 0) or _to_float(exists.get("PSelPrice") or exists.get("PPrice"), 0)
    if duplicate:
        execute(
            """
            UPDATE DesignerAffiliateProducts
            SET AffiliatePrice = ?, CommissionPercent = ?, Note = ?, Status = ?
            WHERE Id = ?
            """,
            [affiliate_price, commission, form.get("note", ""), "Active", duplicate["Id"]],
        )
        return
    execute(
        """
        INSERT INTO DesignerAffiliateProducts
            (DesignerUserId, ProductId, AffiliatePrice, CommissionPercent, Note, Status, CreatedAt)
        VALUES
            (?, ?, ?, ?, ?, ?, GETDATE())
        """,
        [
            str(user_id),
            product_id,
            affiliate_price,
            commission,
            form.get("note", ""),
            "Active",
        ],
    )


def get_affiliate_products(user_id):
    ensure_affiliate_table()
    return fetch_all(
        """
        SELECT
            A.Id, A.DesignerUserId, A.ProductId, A.AffiliatePrice, A.CommissionPercent,
            A.Note, A.Status, A.CreatedAt,
            P.PName, P.PPrice, P.PSelPrice, P.Comission, P.MainItemSellerName,
            I.Name, I.Extention
        FROM DesignerAffiliateProducts A
        INNER JOIN tblProducts P ON CAST(P.PID AS varchar(100)) = A.ProductId
        LEFT JOIN (
            SELECT PID, MIN(Name) AS Name, MIN(Extention) AS Extention
            FROM tblProductImages
            GROUP BY PID
        ) I ON I.PID = P.PID
        WHERE A.DesignerUserId = ?
        ORDER BY A.CreatedAt DESC
        """,
        [str(user_id)],
    )


def product_image_path(row):
    pid = str(row.get("PID") or row.get("ProductId") or "").strip()
    name = str(row.get("Name") or "").strip()
    extension = str(row.get("Extention") or "").strip()
    if not pid or not name:
        return "ProductImage/download.jpg"
    if extension and not name.lower().endswith(extension.lower()):
        name += extension
    return "ProductImage/{0}/{1}".format(pid, name)


def get_open_jobs(limit=80):
    return fetch_all(
        """
        SELECT TOP ({0})
            Jobid, Title, Type, Description, Deadline, Price, Status, Designlink, Customerid,
            Location, BitOrContest
        FROM JobsList
        WHERE Deadline >= GETDATE() AND LOWER(COALESCE(BitOrContest,'contest')) IN ('bit','bid','contest') AND LTRIM(RTRIM(COALESCE(Status,''))) IN ('True','1','Active')
        ORDER BY Deadline ASC, Jobid DESC
        """.format(int(limit))
    )


def get_open_job_type_summary(limit=6):
    return fetch_all(
        """
        SELECT TOP ({0})
            ISNULL(NULLIF(Type, ''), 'General') AS Type,
            COUNT(1) AS Total,
            COALESCE(SUM(CAST(Price AS float)), 0) AS TotalValue,
            COALESCE(AVG(CAST(Price AS float)), 0) AS AveragePrice,
            MIN(Deadline) AS NextDeadline
        FROM JobsList
        WHERE Deadline >= GETDATE() AND LOWER(COALESCE(BitOrContest,'contest')) IN ('bit','bid','contest') AND LTRIM(RTRIM(COALESCE(Status,''))) IN ('True','1','Active')
        GROUP BY ISNULL(NULLIF(Type, ''), 'General')
        ORDER BY COUNT(1) DESC, MIN(Deadline) ASC
        """.format(int(limit))
    )


def get_job(job_id):
    return fetch_one(
        """
        SELECT TOP 1 Jobid, Title, Type, Description, Deadline, Price, Status, Designlink,
            Customerid, Logotext, LogoStyles, Color, MustFollow, DontAdd, Location, BitOrContest
        FROM JobsList
        WHERE Jobid = ?
        """,
        [job_id],
    )


def find_job_by_design_link(design_link):
    if not design_link:
        return None
    return fetch_one(
        "SELECT TOP 1 Jobid, Title, Type, Designlink FROM JobsList WHERE Designlink = ?",
        [design_link],
    )


def get_my_submissions(user_id, status=None):
    params = [user_id]
    status_clause = ""
    if status:
        status_clause = " AND COALESCE(S.status, '') = ?"
        params.append(status)
    return fetch_all(
        """
        SELECT
            S.subid, S.jobid, S.jpgfile, S.zipfile, S.aifile, S.title AS SubmissionTitle,
            S.date, S.feedback, S.status, S.AdminStatus, S.Price,
            J.Title, J.Type, J.Price AS JobPrice
        FROM Submission S
        LEFT JOIN JobsList J ON S.jobid = J.Jobid
        WHERE S.userid = ? {0}
        ORDER BY S.date DESC
        """.format(status_clause),
        params,
    )


def get_all_designs(user_id):
    return fetch_all(
        """
        SELECT TOP 120
            S.subid, S.userid, S.jobid, S.jpgfile, S.zipfile, S.aifile, S.title,
            S.date, S.feedback, S.status, S.AdminStatus, S.SubTeam, S.Price,
            J.Title AS JobTitle, J.Type, J.Price AS JobPrice
        FROM Submission S
        LEFT JOIN JobsList J ON S.jobid = J.Jobid
        WHERE S.userid = ? OR S.SubTeam = ?
        ORDER BY S.date DESC
        """,
        [user_id, user_id],
    )


def get_designer_orders(user_id, username=""):
    return fetch_all(
        """
        SELECT TOP 100 *
        FROM (
            SELECT
                CAST(O.Oder_id AS varchar(100)) AS Oder_id,
                CAST(O.Offer_id AS varchar(100)) AS Offer_id,
                O.Order_date,
                O.CustomerId,
                CAST(O.DesignerId AS varchar(100)) AS DesignerId,
                CAST(O.pakageId AS varchar(100)) AS pakageId,
                ISNULL(O.status, 'Pending') AS status,
                CAST(ISNULL(O.OfferAmount, 0) AS decimal(18,2)) AS OfferAmount,
                OD.offer_title,
                ISNULL(OD.OfferType, 'Service') AS OfferType
            FROM Order_List O
            LEFT JOIN OfferDetails OD ON O.Offer_id = OD.id
            WHERE O.DesignerId IN (?, ?)
                OR OD.userid IN (?, ?)

            UNION ALL

            SELECT
                CAST(O.orderid AS varchar(100)) AS Oder_id,
                CAST(MAX(O.Pid) AS varchar(100)) AS Offer_id,
                MAX(O.Date) AS Order_date,
                MAX(O.Customerid) AS CustomerId,
                MAX(ISNULL(O.MainItemSellerName, O.UserName)) AS DesignerId,
                CAST(COUNT(1) AS varchar(100)) AS pakageId,
                MAX(ISNULL(O.Status, 'Pending')) AS status,
                CAST(SUM(ISNULL(O.Quantity, 0) * ISNULL(O.Price, 0)) AS decimal(18,2)) AS OfferAmount,
                MAX(O.Pname) AS offer_title,
                'Product Order' AS OfferType
            FROM TblOrder O
            WHERE O.MainItemSellerName = ? OR O.UserName = ?
            GROUP BY O.orderid
        ) Orders
        ORDER BY Order_date DESC
        """,
        [user_id, str(username or ""), str(user_id), str(username or ""), str(username or ""), str(username or "")],
    )


def get_designer_tracking_orders(username="", status="", date_from="", date_to=""):
    params = [username, username]
    filters = ["(O.MainItemSellerName = ? OR O.UserName = ?)"]
    if status:
        filters.append("ISNULL(O.Status, '') = ?")
        params.append(status)
    if date_from:
        filters.append("CAST(O.Date AS date) >= CAST(? AS date)")
        params.append(date_from)
    if date_to:
        filters.append("CAST(O.Date AS date) <= CAST(? AS date)")
        params.append(date_to)

    return fetch_all(
        """
        SELECT TOP 120
            O.orderid,
            MAX(O.Customerid) AS Customerid,
            MAX(O.Date) AS OrderDate,
            MAX(ISNULL(O.Status, 'Pending')) AS Status,
            MAX(ISNULL(CI.name, O.Customerid)) AS CustomerName,
            MAX(ISNULL(CI.contactno, O.Customerid)) AS CustomerMobile,
            MAX(ISNULL(CI.address, '')) AS CustomerAddress,
            COUNT(1) AS LineCount,
            SUM(ISNULL(O.Quantity, 0)) AS TotalQty,
            SUM(ISNULL(O.Quantity, 0) * ISNULL(O.Price, 0)) AS TotalAmount
        FROM TblOrder O
        LEFT JOIN CustomerInformation CI
            ON CI.CustomerId = O.Customerid
            OR CI.contactno = O.Customerid
            OR ('C' + CI.contactno) = O.Customerid
        WHERE """ + " AND ".join(filters) + """
        GROUP BY O.orderid
        ORDER BY MAX(O.Date) DESC
        """,
        params,
    )


def get_designer_tracking_order_details(order_id, username=""):
    order_rows = fetch_all(
        """
        SELECT
            O.id, O.orderid, O.Customerid, O.Barcode, O.Pid, O.Pname, O.Quantity, O.Price,
            O.Status, O.Date, O.MainItemSellerName, O.UserName,
            CI.name AS CustomerName, CI.contactno AS CustomerMobile, CI.address AS CustomerAddress,
            IMG.Name AS ImageName, IMG.Extention AS ImageExtention
        FROM TblOrder O
        LEFT JOIN CustomerInformation CI
            ON CI.CustomerId = O.Customerid
            OR CI.contactno = O.Customerid
            OR ('C' + CI.contactno) = O.Customerid
        OUTER APPLY (
            SELECT TOP 1 Name, Extention
            FROM tblProductImages
            WHERE PID = O.Pid AND ISNULL(Extention, '') <> 'YouTube' AND ISNULL(Extention, '') <> '.mp4'
            ORDER BY Name
        ) IMG
        WHERE O.orderid = ?
            AND (O.MainItemSellerName = ? OR O.UserName = ?)
        ORDER BY O.id
        """,
        [order_id, username, username],
    )
    if not order_rows:
        return None

    delivery_rows = fetch_all(
        """
        SELECT DeliveryManName, orderid, Pname, Quantity, Price, Date
        FROM SendToDelivery
        WHERE orderid = ?
        ORDER BY Id DESC
        """,
        [order_id],
    )

    for row in order_rows:
        image_name = str(row.get("ImageName") or "").strip()
        image_extension = str(row.get("ImageExtention") or "").strip()
        if image_name and image_extension and not image_name.lower().endswith(image_extension.lower()):
            image_name += image_extension
        row["ImagePath"] = "ProductImage/{0}/{1}".format(row.get("Pid"), image_name) if row.get("Pid") and image_name else "ProductImage/download.jpg"

    first = order_rows[0]
    current_status = str(first.get("Status") or "Pending").strip() or "Pending"
    has_delivery = bool(delivery_rows)
    is_done = current_status.lower() in {"complete", "sold", "delivered"}
    timeline = [
        {"title": "Order Received", "text": "Customer placed this order.", "done": True, "date": first.get("Date")},
        {"title": "Processing", "text": "Order is waiting for seller confirmation.", "done": True, "date": first.get("Date")},
        {"title": "Confirmed", "text": "Seller confirmed this order.", "done": current_status.lower() not in {"pending", ""}, "date": first.get("Date")},
        {"title": "Delivery Assigned", "text": "Delivery team received this order.", "done": has_delivery, "date": delivery_rows[0].get("Date") if delivery_rows else first.get("Date")},
        {"title": "Delivering", "text": "Order is on the way to customer.", "done": current_status.lower() in {"picked up", "complete", "sold", "delivered"}, "date": delivery_rows[0].get("Date") if delivery_rows else first.get("Date")},
        {"title": "Payment", "text": "Payment status will update after confirmation.", "done": is_done, "date": first.get("Date")},
        {"title": "Delivered", "text": "Customer received the order.", "done": is_done, "date": first.get("Date")},
    ]
    subtotal = sum(_money_number(row.get("Price")) * (int(row.get("Quantity") or 0)) for row in order_rows)
    return {
        "order_id": order_id,
        "customer_name": first.get("CustomerName") or first.get("Customerid") or "Customer",
        "customer_mobile": first.get("CustomerMobile") or "",
        "customer_address": first.get("CustomerAddress") or "",
        "status": current_status,
        "date": first.get("Date"),
        "items": order_rows,
        "timeline": timeline,
        "delivery": delivery_rows[0] if delivery_rows else {},
        "subtotal": subtotal,
        "total_qty": sum(int(row.get("Quantity") or 0) for row in order_rows),
        "line_count": len(order_rows),
    }


def _money_number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def get_designer_messages(user_id, username=""):
    user_key = str(user_id or "")
    username_key = str(username or "")
    direct = fetch_all(
        """
        SELECT TOP 80
            id, sender_id, receiver_id, msg_sub AS Subject, msg_details AS Details,
            sending_date AS Date, status, Jobid, SubmissionId
        FROM Message
        WHERE CAST(sender_id AS varchar(100)) IN (?, ?)
            OR CAST(receiver_id AS varchar(100)) IN (?, ?)
        ORDER BY sending_date DESC
        """,
        [user_key, username_key, user_key, username_key],
    )
    customer = fetch_all(
        """
        SELECT TOP 80
            id, did AS sender_id, cid AS receiver_id, cat AS Subject, message AS Details,
            date AS Date, ReadUnRead AS status, Jobid, NULL AS SubmissionId
        FROM CustomerMessage
        WHERE CAST(did AS varchar(100)) IN (?, ?)
        ORDER BY date DESC
        """,
        [user_key, username_key],
    )
    rows = direct + customer
    rows.sort(key=lambda item: item.get("Date") or datetime.min, reverse=True)
    return rows[:100]


def create_submission(user_id, job_id=None, design_link="", title="", jpg_file=None, zip_file=None, ai_file=None):
    from job_permissions import can_apply
    account = get_designer_profile(user_id) or {}
    if not can_apply(account.get("UserCatagory")):
        raise ValueError("Only Designer / Freelancer accounts can submit work.")
    if not job_id and design_link:
        job = find_job_by_design_link(design_link.strip())
        if not job:
            raise ValueError("Design link diye kono job pawa jayni.")
        job_id = job["Jobid"]

    if not job_id:
        raise ValueError("Please select a job or enter a valid design link.")

    selected_job = get_job(job_id)
    if not selected_job:
        raise ValueError("Job not found.")
    if str(selected_job.get("Customerid")) == str(user_id):
        raise ValueError("You cannot apply to your own job.")
    job_type = str(selected_job.get("BitOrContest") or "Contest").strip().lower()
    if job_type in {"bit", "bid"}:
        raise ValueError("Use the Bid application form for this job.")
    if job_type != "contest":
        raise ValueError("Designers can apply to Bid / Contest jobs only.")
    from market_service import today
    if str(selected_job.get("Deadline") or "")[:10] < today().isoformat() or str(selected_job.get("Status") or "").strip().lower() not in {"true", "1", "active"}:
        raise ValueError("This contest is closed.")

    if not jpg_file or not jpg_file.filename:
        raise ValueError("Please select JPG/JPEG preview file.")

    ext = Path(jpg_file.filename).suffix.lower()
    if ext not in (".jpg", ".jpeg"):
        raise ValueError("Only JPG or JPEG preview file is allowed.")

    profile = get_designer_profile(user_id) or {}
    sub_team = str(profile.get("SubTeam") or "")
    prefix = str(user_id)

    jpg_path = _save_upload(jpg_file, "JPEGFiles", prefix)
    zip_path = ""
    if zip_file and zip_file.filename:
        zip_saved = _save_upload(zip_file, "ZipFiles", prefix)
        zip_path = Path(zip_saved).name
    ai_path = _save_upload(ai_file, "AIFiles", prefix) if ai_file and ai_file.filename else ""

    execute(
        """
        INSERT INTO Submission
            (userid, jobid, aifile, jpgfile, zipfile, title, date, SubTeam)
        VALUES
            (?, ?, ?, ?, ?, ?, GETDATE(), ?)
        """,
        [user_id, job_id, ai_path, jpg_path, zip_path, html.escape(html.unescape(title or ""), quote=True), sub_team],
    )
    execute(
        """
        INSERT INTO SubmissionHistory (userid, ownsubmission, Jobid, date)
        VALUES (?, ?, ?, GETDATE())
        """,
        [str(user_id), 1, str(job_id)],
    )
    return int(job_id)
