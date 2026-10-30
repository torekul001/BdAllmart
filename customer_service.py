from datetime import datetime
from pathlib import Path

from werkzeug.utils import secure_filename

from config import Config
from db import execute, fetch_all, fetch_one, get_connection
from security import password_for_storage, verify_password


CUSTOMER_MENU = [
    ("Customer Dashboard", "/customer/orders"),
    ("Ecommerce Orders", "/customer/orders"),
    ("Order Tracking", "/customer/order-tracking"),
    ("Add Product", "/customer/products"),
    ("Profile Products", "/customer/profile-products"),
    ("Post Design Job", "/customer/post-job"),
    ("My Jobs", "/customer/jobs"),
    ("Submitted Designs", "/customer/submissions"),
    ("Messages", "/customer/messages"),
    ("Profile", "/customer/profile"),
]


DESIGN_TYPES = [
    "Logo Design",
    "Business Card",
    "Banner Design",
    "Flyer Design",
    "Web Design",
    "Graphic Design",
    "Data Entry",
    "Other",
]


LOGO_STYLE_FIELDS = {
    "fSerif": "~\\LogoStyle\\Serif Font.jpg",
    "fSensSerif": "~\\LogoStyle\\Sens Serif Font.jpg",
    "fDecorative": "~\\LogoStyle\\Decorative Font.jpg",
    "fScript": "~\\LogoStyle\\Script Font.jpg",
    "Wordmark": "~\\LogoStyle\\Wordmark logo.jpg",
    "Lettermark": "~\\LogoStyle\\Lettermark-logo.jpg",
    "Emblem": "~\\LogoStyle\\Emblem Logo.jpg",
    "Pictorial": "~\\LogoStyle\\Pictorial logo.jpg",
    "charecter": "~\\LogoStyle\\Character Logo.jpg",
    "abastract": "~\\LogoStyle\\abstract-logo.jpg",
}


def _count(query, params=None):
    row = fetch_one(query, params or [])
    return int((row or {}).get("Total") or 0)


def _safe_int(value):
    try:
        return int(str(value or "").strip())
    except (TypeError, ValueError):
        return None


def _safe_float(value):
    try:
        return float(str(value or "0").strip())
    except (TypeError, ValueError):
        return 0.0


def _save_sample_image(file_storage, job_id):
    if not file_storage or not file_storage.filename:
        return ""
    target_dir = Path(Config.PROJECT_ROOT) / "SampleImages"
    target_dir.mkdir(parents=True, exist_ok=True)
    original_name = secure_filename(file_storage.filename)
    if not original_name:
        original_name = "sample"
    filename = "{0}_{1}_{2}".format(job_id, datetime.now().strftime("%Y%m%d%H%M%S%f"), original_name)
    file_storage.save(str(target_dir / filename))
    return filename


def _save_product_image(file_storage, product_id, product_name, index):
    if not file_storage or not file_storage.filename:
        return ""
    target_dir = Path(__file__).resolve().parent / "static" / "ProductImage" / str(product_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(file_storage.filename).suffix or ".jpg"
    image_base = "{0}{1:02d}".format(secure_filename(product_name)[:80] or "Product", index)
    file_storage.save(str(target_dir / (image_base + extension)))
    return image_base, extension


def get_product_form_options():
    return {
        "categories": fetch_all("SELECT id, CategoryName FROM Category ORDER BY CategoryName"),
        "subcategories": fetch_all("SELECT id, Catid, SubcatName FROM SubCategory ORDER BY SubcatName"),
        "brands": fetch_all("SELECT BrandID, Name FROM tblBrands ORDER BY Name"),
        "genders": fetch_all("SELECT GenderID, GenderName FROM tblGender ORDER BY GenderName"),
        "sizes": fetch_all("SELECT SizeID, SizeName FROM OnlySize ORDER BY SizeID"),
    }


def create_customer_product(user_id, username, form, images):
    name = (form.get("product_name") or "").strip()
    if not name:
        raise ValueError("Product name is required.")

    price = _safe_float(form.get("price"))
    sale_price = _safe_float(form.get("sale_price")) or price
    quantity = _safe_int(form.get("quantity")) or 1
    commission = _safe_float(form.get("commission"))
    commission_amount = (price * commission) / 100 if price else 0

    with get_connection() as conn:
        cursor = conn.cursor()
        next_row = cursor.execute("SELECT COALESCE(MAX(PID), 0) + 1 FROM tblProducts").fetchone()
        next_order = int(next_row[0] or 1)
        voucher_no = "VN/{0}/{1}".format(datetime.now().year, next_order)
        product_code = (form.get("product_code") or "").strip() or str(next_order)

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
                _safe_int(form.get("brand_id")) or 0,
                _safe_int(form.get("category_id")) or 0,
                _safe_int(form.get("subcategory_id")) or 0,
                _safe_int(form.get("gender_id")) or 0,
                form.get("description") or "",
                form.get("details") or "",
                form.get("material_care") or "",
                1 if form.get("free_delivery") else 0,
                1 if form.get("return_30") else 0,
                1 if form.get("cod") else 0,
                product_code,
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
        product_id = int(cursor.fetchone()[0])

        selected_sizes = form.getlist("sizes") if hasattr(form, "getlist") else []
        if not selected_sizes:
            selected_sizes = [form.get("size_id") or "1"]
        for size_id in selected_sizes:
            cursor.execute(
                "INSERT INTO tblProductSizeQuantity (PID, SizeID, Quantity) VALUES (?, ?, ?)",
                [product_id, _safe_int(size_id) or 1, quantity],
            )

        image_count = 0
        for image in images or []:
            if image and image.filename:
                image_count += 1
                image_name, extension = _save_product_image(image, product_id, name, image_count)
                cursor.execute(
                    "INSERT INTO tblProductImages (PID, Name, Extention) VALUES (?, ?, ?)",
                    [product_id, image_name, extension],
                )

    return product_id


def get_customer_products(username):
    return fetch_all(
        """
        SELECT TOP 120
            P.PID, P.PName, P.PPrice, P.PSelPrice, P.Status, P.MainItemSellerName,
            P.VoucherNo, P.ProductID, I.Name, I.Extention
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


def get_customer_profile(user_id):
    return fetch_one(
        """
        SELECT TOP 1 UserId, Username, Email, Phone, FirstName, LastName, Address,
            City, State, PostalCode, Country, UserCatagory, Active, Status, AdminStatus, picture, AboutMe
        FROM Users
        WHERE UserId = ?
        """,
        [user_id],
    )


def update_customer_profile(user_id, data, picture_file=None):
    username = str(data.get("username") or "").strip()
    if not username:
        raise ValueError("Username is required.")
    picture = None
    if picture_file and picture_file.filename:
        picture = picture_file.read(5 * 1024 * 1024 + 1)
        if len(picture) > 5 * 1024 * 1024:
            raise ValueError("Profile picture must be smaller than 5 MB.")
        if not (picture.startswith(b'\x89PNG\r\n\x1a\n') or picture.startswith(b'\xff\xd8\xff') or picture.startswith((b'GIF87a', b'GIF89a')) or (picture.startswith(b'RIFF') and picture[8:12] == b'WEBP')):
            raise ValueError("Use a PNG, JPEG, GIF, or WebP profile picture.")
    execute(
        """
        UPDATE Users
        SET Username = ?, FirstName = ?, LastName = ?, Phone = ?, Address = ?,
            City = ?, State = ?, PostalCode = ?, Country = ?, AboutMe = ?
        """ + (", picture = ?" if picture is not None else "") + """
        WHERE UserId = ?
        """,
        [
            username,
            data.get("first_name", ""),
            data.get("last_name", ""),
            data.get("phone", ""),
            data.get("address", ""),
            data.get("city", ""),
            data.get("state", ""),
            _safe_int(data.get("postal_code")),
            data.get("country", ""),
            data.get("about_me", ""),
        ] + ([picture] if picture is not None else []) + [user_id],
    )


def update_customer_password(user_id, password, old_password=""):
    if not password:
        raise ValueError("New password is required.")
    current = fetch_one("SELECT TOP 1 Password FROM Users WHERE UserId = ?", [user_id])
    if not old_password or not current or not verify_password(old_password, str(current.get("Password") or "")):
        raise ValueError("Old password is not correct.")
    execute("UPDATE Users SET Password = ? WHERE UserId = ?", [password_for_storage(password), user_id])


def get_customer_summary(user_id, username="", email="", phone=""):
    return {
        "orders": _count(
            """
            SELECT COUNT(1) AS Total
            FROM TblOrder
            WHERE UserName IN (?, ?, ?) OR Customerid IN (?, ?, ?)
            """,
            [username, email, phone, username, email, phone],
        ),
        "jobs": _count("SELECT COUNT(1) AS Total FROM JobsList WHERE Customerid = ?", [user_id]),
        "submissions": _count(
            """
            SELECT COUNT(1) AS Total
            FROM Submission S
            INNER JOIN JobsList J ON S.jobid = J.Jobid
            WHERE J.Customerid = ?
            """,
            [user_id],
        ),
        "messages": _count(
            "SELECT COUNT(1) AS Total FROM Message WHERE sender_id = ? OR receiver_id = ?",
            [str(user_id), str(user_id)],
        ),
    }


def get_ecommerce_orders(user_id, username="", email="", phone=""):
    new_orders = fetch_all(
        """
        SELECT TOP 120
            id, orderid, Customerid, Pid, Pname, Quantity, Price, Status, Date,
            MainItemSellerName, UserName
        FROM TblOrder
        WHERE UserName IN (?, ?, ?) OR Customerid IN (?, ?, ?)
        ORDER BY Date DESC
        """,
        [username, email, phone, username, email, phone],
    )
    old_orders = fetch_all(
        """
        SELECT TOP 80
            Id, email, OrderDetails, Image1, FileName1, FileType, Comment
        FROM OrderNow
        WHERE email = ?
        ORDER BY Id DESC
        """,
        [email],
    ) if email else []
    return new_orders, old_orders


def _customer_order_where():
    return """
        (
            O.UserName IN (?, ?, ?)
            OR O.Customerid IN (?, ?, ?, ?)
            OR O.Customerid = ('C' + ?)
        )
    """


def get_tracking_orders(username="", email="", phone="", status="", date_from="", date_to=""):
    params = [username, email, phone, username, email, phone, "C{0}".format(phone or ""), phone]
    filters = [_customer_order_where()]
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
            MAX(ISNULL(CI.name, ?)) AS CustomerName,
            MAX(ISNULL(CI.contactno, ?)) AS CustomerMobile,
            MAX(ISNULL(CI.address, '')) AS CustomerAddress,
            COUNT(1) AS LineCount,
            SUM(ISNULL(O.Quantity, 0)) AS TotalQty,
            SUM(ISNULL(O.Quantity, 0) * ISNULL(O.Price, 0)) AS TotalAmount
        FROM TblOrder O
        LEFT JOIN CustomerInformation CI
            ON CI.CustomerId = O.Customerid
            OR CI.contactno = O.Customerid
            OR ('C' + CI.contactno) = O.Customerid
        WHERE
        """ + " AND ".join(filters) + """
        GROUP BY O.orderid
        ORDER BY MAX(O.Date) DESC
        """,
        [username or email or phone or "Customer", phone] + params,
    )


def get_tracking_order_details(order_id, username="", email="", phone=""):
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
            AND """ + _customer_order_where() + """
        ORDER BY O.id
        """,
        [order_id, username, email, phone, username, email, phone, "C{0}".format(phone or ""), phone],
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
    statuses = {str(row.get("Status") or "Pending").strip().lower() for row in order_rows}
    current_status = str(first.get("Status") or "Pending").strip() or "Pending"
    has_delivery = bool(delivery_rows)
    is_paid = current_status.lower() in {"complete", "sold", "delivered"}
    timeline = [
        {"title": "Order Placed", "text": "Your order has been received.", "done": True, "date": first.get("Date")},
        {"title": "Processing", "text": "We are checking and confirming your order.", "done": True, "date": first.get("Date")},
        {"title": "Confirmed", "text": "Your order is confirmed.", "done": current_status.lower() not in {"pending", ""}, "date": first.get("Date")},
        {"title": "Delivery Assigned", "text": "Delivery team has received this order.", "done": has_delivery or "todeliveryman" in statuses, "date": delivery_rows[0].get("Date") if delivery_rows else first.get("Date")},
        {"title": "Delivering", "text": "Your order is on the way.", "done": current_status.lower() in {"picked up", "complete", "sold", "delivered"}, "date": delivery_rows[0].get("Date") if delivery_rows else first.get("Date")},
        {"title": "Payment", "text": "Payment will be updated after confirmation.", "done": is_paid, "date": first.get("Date")},
        {"title": "Delivered", "text": "You have received your order.", "done": current_status.lower() in {"complete", "sold", "delivered"}, "date": first.get("Date")},
    ]
    subtotal = sum(_safe_float(row.get("Price")) * (_safe_int(row.get("Quantity")) or 0) for row in order_rows)
    return {
        "order_id": order_id,
        "customer_name": first.get("CustomerName") or username or "Customer",
        "customer_mobile": first.get("CustomerMobile") or phone or "",
        "customer_address": first.get("CustomerAddress") or "",
        "status": current_status,
        "date": first.get("Date"),
        "items": order_rows,
        "timeline": timeline,
        "delivery": delivery_rows[0] if delivery_rows else {},
        "subtotal": subtotal,
        "total_qty": sum((_safe_int(row.get("Quantity")) or 0) for row in order_rows),
        "line_count": len(order_rows),
    }


def get_customer_jobs(user_id):
    return fetch_all(
        """
        SELECT
            J.Jobid, J.Title, J.Type, J.Description, J.Deadline, J.Price, J.Status,
            J.designlink, J.Color, J.Logotext, J.MustFollow, J.DontAdd, J.PriceFixing,
            J.Location, J.BitOrContest,
            (SELECT COUNT(1) FROM Submission S WHERE S.jobid = J.Jobid) AS TotalSubmissions
        FROM JobsList J
        WHERE J.Customerid = ?
        ORDER BY J.Jobid DESC
        """,
        [user_id],
    )


def get_customer_job(job_id, user_id):
    return fetch_one(
        """
        SELECT TOP 1
            Jobid, Title, Type, Description, Deadline, Price, Status, designlink,
            Logotext, MustFollow, DontAdd, Color, PriceFixing, Location, BitOrContest,
            fSerif, fSensSerif, fDecorative, fScript, Wordmark, Lettermark,
            Emblem, Pictorial, charecter, abastract
        FROM JobsList
        WHERE Jobid = ? AND Customerid = ?
        """,
        [job_id, user_id],
    )


def get_job_sample_images(job_id):
    return fetch_all("SELECT Id, JobId, Images FROM SampleImage WHERE JobId = ? ORDER BY Id DESC", [job_id])


def create_customer_job(user_id, data, files):
    from job_permissions import can_post
    account = fetch_one("SELECT UserCatagory FROM Users WHERE UserId=?", [user_id])
    if not account or not can_post(account["UserCatagory"]):
        raise ValueError("Only Customer / Buyer accounts can post jobs.")
    title = (data.get("title") or "").strip()
    deadline = (data.get("deadline") or "").strip()
    if not title:
        raise ValueError("Job title is required.")
    if not deadline:
        raise ValueError("Deadline is required.")

    selected_styles = set(data.getlist("styles")) if hasattr(data, "getlist") else set()
    style_values = {field: path if field in selected_styles else "" for field, path in LOGO_STYLE_FIELDS.items()}

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO JobsList
                (Title, Type, Description, Deadline, Customerid, Price, Status, Logotext,
                 MustFollow, DontAdd, designlink, Color, fSerif, fSensSerif, fDecorative,
                 fScript, Wordmark, Lettermark, Emblem, Pictorial, charecter, abastract,
                 PriceFixing, Location, BitOrContest)
            OUTPUT INSERTED.Jobid
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                title,
                data.get("type") or "Other",
                data.get("description") or "",
                deadline,
                user_id,
                _safe_float(data.get("price")),
                "True",
                data.get("logo_text") or "",
                data.get("must_follow") or "",
                data.get("dont_add") or "",
                "",
                data.get("color") or "",
                style_values["fSerif"],
                style_values["fSensSerif"],
                style_values["fDecorative"],
                style_values["fScript"],
                style_values["Wordmark"],
                style_values["Lettermark"],
                style_values["Emblem"],
                style_values["Pictorial"],
                style_values["charecter"],
                style_values["abastract"],
                data.get("price_fixing") or "Fixed",
                data.get("location") or "",
                data.get("bit_or_contest") or "Contest",
            ],
        )
        job_id = int(cursor.fetchone()[0])
        design_link = "{0}{1}".format(user_id, job_id)
        cursor.execute("UPDATE JobsList SET designlink = ? WHERE Jobid = ?", [design_link, job_id])

        for file_storage in files:
            filename = _save_sample_image(file_storage, job_id)
            if filename:
                cursor.execute("INSERT INTO SampleImage (JobId, Images) VALUES (?, ?)", [job_id, filename])
    return job_id


def update_customer_job(user_id, job_id, data, files):
    from job_permissions import can_post
    account = fetch_one("SELECT UserCatagory FROM Users WHERE UserId=?", [user_id])
    if not account or not can_post(account["UserCatagory"]):
        raise ValueError("Only Customer / Buyer accounts can update jobs.")
    job_id = _safe_int(job_id)
    if not job_id:
        raise ValueError("Job was not selected.")

    existing = get_customer_job(job_id, user_id)
    if not existing:
        raise ValueError("Job was not found for this customer.")

    contract = fetch_one("SELECT O.Id FROM MarketLegacyContract C JOIN MarketOrder O ON O.Id=C.OrderId WHERE C.Id=? AND O.Status NOT IN ('cancelled','refunded')", [str(job_id)])
    if contract:
        raise ValueError("This job has an active contract. Manage delivery and completion in Orders & Contracts.")

    title = (data.get("title") or "").strip()
    deadline = (data.get("deadline") or "").strip()
    if not title:
        raise ValueError("Job title is required.")
    if not deadline:
        raise ValueError("Deadline is required.")

    selected_styles = set(data.getlist("styles")) if hasattr(data, "getlist") else set()
    style_values = {field: path if field in selected_styles else "" for field, path in LOGO_STYLE_FIELDS.items()}

    execute(
        """
        UPDATE JobsList
        SET Title = ?, Type = ?, Description = ?, Deadline = ?, Price = ?, Logotext = ?,
            MustFollow = ?, DontAdd = ?, Color = ?, fSerif = ?, fSensSerif = ?,
            fDecorative = ?, fScript = ?, Wordmark = ?, Lettermark = ?, Emblem = ?,
            Pictorial = ?, charecter = ?, abastract = ?, PriceFixing = ?, Location = ?,
            BitOrContest = ?
        WHERE Jobid = ? AND Customerid = ?
        """,
        [
            title,
            data.get("type") or "Other",
            data.get("description") or "",
            deadline,
            _safe_float(data.get("price")),
            data.get("logo_text") or "",
            data.get("must_follow") or "",
            data.get("dont_add") or "",
            data.get("color") or "",
            style_values["fSerif"],
            style_values["fSensSerif"],
            style_values["fDecorative"],
            style_values["fScript"],
            style_values["Wordmark"],
            style_values["Lettermark"],
            style_values["Emblem"],
            style_values["Pictorial"],
            style_values["charecter"],
            style_values["abastract"],
            data.get("price_fixing") or "Fixed",
            data.get("location") or "",
            data.get("bit_or_contest") or "Contest",
            job_id,
            user_id,
        ],
    )

    clean_files = [file_storage for file_storage in (files or []) if file_storage and file_storage.filename]
    for file_storage in clean_files:
        filename = _save_sample_image(file_storage, job_id)
        if filename:
            execute("INSERT INTO SampleImage (JobId, Images) VALUES (?, ?)", [job_id, filename])
    return job_id


def get_customer_submissions(user_id, job_id=None):
    params = [user_id]
    clause = ""
    if job_id:
        clause = " AND J.Jobid = ?"
        params.append(job_id)
    return fetch_all(
        """
        SELECT
            U.UserId, U.Username, J.Jobid, J.Title, J.Type, J.designlink,
            S.subid, S.jpgfile, S.aifile, S.zipfile, S.date,
            S.AdminStatus, S.status, S.feedback, S.Price
        FROM JobsList J
        INNER JOIN Submission S ON J.Jobid = S.jobid
        INNER JOIN Users U ON U.UserId = S.userid
        WHERE J.Customerid = ? {0}
        ORDER BY S.date DESC
        """.format(clause),
        params,
    )


def update_submission_review(user_id, subid, status="", feedback=""):
    submission = fetch_one(
        """
        SELECT TOP 1 S.subid
        FROM Submission S
        INNER JOIN JobsList J ON S.jobid = J.Jobid
        WHERE S.subid = ? AND J.Customerid = ?
        """,
        [subid, user_id],
    )
    if not submission:
        raise ValueError("Submission was not found for this customer.")

    execute(
        """
        UPDATE Submission
        SET status = ?, feedback = ?
        WHERE subid = ?
        """,
        [status or "", feedback or "", subid],
    )


def get_customer_messages(user_id, username):
    return fetch_all(
        """
        SELECT TOP 120
            id, sender_id, receiver_id, msg_sub, msg_details, sending_date,
            status, Permission, SubmissionId, Jobid
        FROM Message
        WHERE sender_id IN (?, ?) OR receiver_id IN (?, ?)
        ORDER BY sending_date DESC
        """,
        [str(user_id), username, str(user_id), username],
    )


def send_customer_message(sender_id, receiver_id, subject, details, job_id="", submission_id=""):
    if not receiver_id:
        raise ValueError("Receiver is required.")
    if not details:
        raise ValueError("Message details are required.")
    execute(
        """
        INSERT INTO Message
            (sender_id, receiver_id, msg_sub, msg_details, sending_date, Jobid, SubmissionId)
        VALUES
            (?, ?, ?, ?, GETDATE(), ?, ?)
        """,
        [str(sender_id), str(receiver_id), subject or "", details, str(job_id or ""), str(submission_id or "")],
    )
