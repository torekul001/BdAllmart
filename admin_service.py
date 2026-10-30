from db import execute, fetch_all, fetch_one, get_connection


ADMIN_MODULE_QUERIES = {
    "customer-order": {
        "title": "Customer Orders",
        "description": "Pending ecommerce orders from TblOrder.",
        "filters": ["date_from", "date_to"],
        "query": """
            SELECT TOP 200
                id AS [_row_id],
                Barcode AS [_barcode],
                orderid AS [Order ID],
                Customerid AS [Customer],
                Pname AS [Product],
                Quantity,
                Price,
                Status,
                Date
            FROM TblOrder
            WHERE ISNULL(Status, '') IN ('', 'Pending', 'pending')
                AND (? = '' OR CAST(Date AS date) >= CAST(? AS date))
                AND (? = '' OR CAST(Date AS date) <= CAST(? AS date))
            ORDER BY Date DESC, id DESC
        """,
    },
    "all-orders": {
        "title": "All Orders",
        "description": "All recent order rows grouped by order id in the existing order table.",
        "query": """
            SELECT TOP 50
                orderid AS [Order ID],
                Customerid AS [Customer],
                Pname AS [Product],
                Quantity,
                Price,
                Status,
                MainItemSellerName AS [Seller],
                Date
            FROM TblOrder
            ORDER BY Date DESC, id DESC
        """,
    },
    "order-approve": {
        "title": "Order Approve",
        "description": "Pending orders that need admin review.",
        "query": """
            SELECT TOP 50
                orderid AS [Order ID],
                Customerid AS [Customer],
                Pname AS [Product],
                Quantity,
                Price,
                Status,
                Date
            FROM TblOrder
            WHERE ISNULL(Status, '') IN ('', 'Pending', 'pending')
            ORDER BY Date DESC, id DESC
        """,
    },
    "customer-order-place": {
        "title": "Customer Order Place",
        "description": "Customer contact and order placement information.",
        "query": """
            SELECT TOP 50
                CustomerId AS [Customer ID],
                name AS [Name],
                contactno AS [Mobile],
                email AS [Email],
                address AS [Address]
            FROM CustomerInformation
            ORDER BY id DESC
        """,
    },
    "delivery-man": {
        "title": "Delivery Man Assigned Orders",
        "description": "Orders assigned to delivery men from SendToDelivery.",
        "filters": ["date_from", "date_to", "delivery_man"],
        "query": """
            SELECT TOP 100
                D.Id AS [Assign ID],
                D.DeliveryManName AS [Delivery Man],
                U.Phone AS [Delivery Phone],
                D.orderid AS [Order ID],
                D.Customerid AS [Customer],
                D.Pname AS [Product],
                D.Quantity,
                D.Price,
                O.Status,
                D.Date
            FROM SendToDelivery D
            LEFT JOIN TblOrder O ON O.orderid = D.orderid AND O.Pname = D.Pname
            LEFT JOIN Users U ON U.Username = D.DeliveryManName
            WHERE (? = '' OR CAST(D.Date AS date) >= CAST(? AS date))
                AND (? = '' OR CAST(D.Date AS date) <= CAST(? AS date))
                AND (? = '' OR D.DeliveryManName = ?)
            ORDER BY D.Id DESC
        """,
    },
    "product-list": {
        "title": "Product List",
        "description": "Latest products from tblProducts.",
        "query": """
            SELECT TOP 50
                PID,
                PName AS [Product],
                PPrice AS [Price],
                PSelPrice AS [Sale Price],
                MainItemSellerName AS [Seller],
                PCategoryID AS [Category],
                PSubCatID AS [Sub Category]
            FROM tblProducts
            ORDER BY PID DESC
        """,
    },
    "product-barcode": {
        "title": "Product Barcode Approval",
        "description": "Customer submitted products waiting for admin approval.",
        "query": """
            SELECT TOP 200
                B.PID AS [_product_id],
                B.PID AS [Product ID],
                B.VoucherNo AS [Voucher No],
                B.PName AS [Product],
                B.PPrice AS [Price],
                B.PSelPrice AS [Sale Price],
                B.ProductID AS [Product Code],
                SQ.Quantity,
                B.MainItemSellerName AS [Seller],
                B.Status
            FROM tblProducts B
            OUTER APPLY (
                SELECT TOP 1 Quantity
                FROM tblProductSizeQuantity
                WHERE PID = B.PID
                ORDER BY PID DESC
            ) SQ
            WHERE ISNULL(B.Status, '') = 'Not Delivered'
            ORDER BY B.PID DESC
        """,
    },
    "payment-details": {
        "title": "Payment Details",
        "description": "Latest payment records from OrderPayment.",
        "query": """
            SELECT TOP 50
                Pay_id AS [Payment ID],
                Pay_method AS [Method],
                Pay_by AS [Pay By],
                Pay_to AS [Pay To],
                Pay_amount AS [Amount],
                Sending_account AS [Sending Account],
                Transition_No AS [Transaction],
                Pay_date AS [Date]
            FROM OrderPayment
            ORDER BY Pay_date DESC, Pay_id DESC
        """,
    },
    "expend-amount": {
        "title": "Expend Amount",
        "description": "Payment and expense records from OrderPayment.",
        "query": """
            SELECT TOP 50
                Pay_id AS [Payment ID],
                Pay_method AS [Method],
                Pay_by AS [Pay By],
                Pay_amount AS [Amount],
                Pay_date AS [Date]
            FROM OrderPayment
            ORDER BY Pay_date DESC, Pay_id DESC
        """,
    },
    "payment-withdraw": {
        "title": "Payment Withdraw Request",
        "description": "Withdraw payment records.",
        "query": """
            SELECT TOP 50
                Pay_id AS [Payment ID],
                Pay_method AS [Method],
                Pay_by AS [Pay By],
                Pay_to AS [Pay To],
                Pay_amount AS [Amount],
                Pay_date AS [Date]
            FROM OrderPayment
            ORDER BY Pay_date DESC, Pay_id DESC
        """,
    },
    "message": {
        "title": "Messages",
        "description": "Latest messages from Message table.",
        "query": """
            SELECT TOP 50
                id,
                sender_id AS [Sender],
                receiver_id AS [Receiver],
                msg_sub AS [Subject],
                msg_details AS [Message],
                Permission,
                sending_date AS [Date]
            FROM Message
            ORDER BY sending_date DESC, id DESC
        """,
    },
    "message-approve": {
        "title": "Message Approve",
        "description": "Messages waiting for approval.",
        "query": """
            SELECT TOP 50
                id,
                sender_id AS [Sender],
                receiver_id AS [Receiver],
                msg_sub AS [Subject],
                msg_details AS [Message],
                Permission,
                sending_date AS [Date]
            FROM Message
            WHERE ISNULL(Permission, '') NOT IN ('Approved', 'approved')
            ORDER BY sending_date DESC, id DESC
        """,
    },
    "submitted-work": {
        "title": "Submitted Work",
        "description": "Recent customer/freelancer messages related to work submissions.",
        "query": """
            SELECT TOP 50
                id,
                sender_id AS [Sender],
                receiver_id AS [Receiver],
                Jobid AS [Job],
                SubmissionId AS [Submission],
                msg_details AS [Details],
                sending_date AS [Date]
            FROM Message
            WHERE ISNULL(SubmissionId, '') <> ''
            ORDER BY sending_date DESC, id DESC
        """,
    },
    "jobs-post": {
        "title": "Jobs Post",
        "description": "Customer orders and job requests.",
        "query": """
            SELECT TOP 50
                id,
                name AS [Name],
                email AS [Email],
                phone AS [Phone],
                type AS [Type],
                description AS [Description],
                Status,
                orderdate AS [Date]
            FROM CustomerOrder
            ORDER BY orderdate DESC, id DESC
        """,
    },
    "customer-earning": {
        "title": "All Customer Earning",
        "description": "Payment records by customer.",
        "query": """
            SELECT TOP 50
                Pay_by AS [Customer],
                Pay_method AS [Method],
                Pay_amount AS [Amount],
                Pay_date AS [Date]
            FROM OrderPayment
            ORDER BY Pay_date DESC, Pay_id DESC
        """,
    },
}


def get_delivery_men():
    return fetch_all(
        """
        SELECT UserId, Username, Phone
        FROM Users
        WHERE UserCatagory LIKE 'Del%'
        ORDER BY Username
        """
    )


def _safe_count(query, params=None):
    try:
        row = fetch_one(query, params or [])
        return int((row or {}).get("Total") or 0)
    except Exception:
        return 0


def _safe_money_total(query, params=None):
    try:
        row = fetch_one(query, params or [])
        return float((row or {}).get("Total") or 0)
    except Exception:
        return 0


def _format_money(value):
    try:
        return "Tk {0:,.0f}".format(float(value or 0))
    except (TypeError, ValueError):
        return "Tk 0"


def _safe_rows(query, params=None):
    try:
        return fetch_all(query, params or [])
    except Exception:
        return []


def get_admin_dashboard_summary():
    total_orders = _safe_count("SELECT COUNT(DISTINCT orderid) AS Total FROM TblOrder")
    in_delivery = _safe_count("SELECT COUNT(DISTINCT orderid) AS Total FROM SendToDelivery")
    delivered = _safe_count(
        """
        SELECT COUNT(DISTINCT orderid) AS Total
        FROM TblOrder
        WHERE LOWER(ISNULL(Status, '')) IN ('delivered', 'complete', 'completed', 'sold')
        """
    )
    returned = _safe_count(
        """
        SELECT COUNT(DISTINCT orderid) AS Total
        FROM TblOrder
        WHERE LOWER(ISNULL(Status, '')) LIKE '%return%'
        """
    )
    pending = _safe_count(
        """
        SELECT COUNT(DISTINCT orderid) AS Total
        FROM TblOrder
        WHERE ISNULL(Status, '') = '' OR LOWER(ISNULL(Status, '')) IN ('pending', 'new')
        """
    )
    cancelled = _safe_count(
        """
        SELECT COUNT(DISTINCT orderid) AS Total
        FROM TblOrder
        WHERE LOWER(ISNULL(Status, '')) LIKE '%cancel%'
        """
    )

    customers = _safe_count("SELECT COUNT(1) AS Total FROM Users WHERE UserCatagory LIKE 'Customer%'")
    designers = _safe_count(
        """
        SELECT COUNT(1) AS Total
        FROM Users
        WHERE UserCatagory LIKE 'Designer%' OR UserCatagory LIKE 'Freelancer%'
        """
    )
    delivery_men = _safe_count("SELECT COUNT(1) AS Total FROM Users WHERE UserCatagory LIKE 'Del%'")
    vendors = _safe_count(
        """
        SELECT COUNT(1) AS Total
        FROM Users
        WHERE UserCatagory LIKE 'Vendor%' OR UserCatagory LIKE 'Seller%'
        """
    )
    students = _safe_count("SELECT COUNT(1) AS Total FROM Users WHERE UserCatagory LIKE 'Student%'")
    total_users = _safe_count("SELECT COUNT(1) AS Total FROM Users")

    total_sales_amount = _safe_money_total(
        """
        SELECT COALESCE(SUM(CAST(Quantity AS float) * CAST(Price AS float)), 0) AS Total
        FROM TblOrder
        """
    )
    month_sales_amount = _safe_money_total(
        """
        SELECT COALESCE(SUM(CAST(Quantity AS float) * CAST(Price AS float)), 0) AS Total
        FROM TblOrder
        WHERE Date >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
            AND Date < DATEADD(MONTH, 1, DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1))
        """
    )
    today_sales_amount = _safe_money_total(
        """
        SELECT COALESCE(SUM(CAST(Quantity AS float) * CAST(Price AS float)), 0) AS Total
        FROM TblOrder
        WHERE CAST(Date AS date) = CAST(GETDATE() AS date)
        """
    )
    delivery_man_commission = _safe_money_total(
        """
        SELECT COALESCE(SUM(CAST(ISNULL(Quantity, 0) AS float) * CAST(ISNULL(Price, 0) AS float)), 0) AS Total
        FROM SendToDelivery
        """
    )
    top_selling_products = _safe_rows(
        """
        SELECT TOP 10
            ISNULL(NULLIF(Pname, ''), 'Unknown Product') AS Product,
            SUM(CAST(ISNULL(Quantity, 0) AS float)) AS QuantitySold,
            SUM(CAST(ISNULL(Quantity, 0) AS float) * CAST(ISNULL(Price, 0) AS float)) AS SalesAmount
        FROM TblOrder
        GROUP BY ISNULL(NULLIF(Pname, ''), 'Unknown Product')
        ORDER BY SUM(CAST(ISNULL(Quantity, 0) AS float)) DESC,
            SUM(CAST(ISNULL(Quantity, 0) AS float) * CAST(ISNULL(Price, 0) AS float)) DESC
        """
    )
    for product in top_selling_products:
        product["SalesAmountText"] = _format_money(product.get("SalesAmount"))

    return {
        "total_orders": total_orders,
        "in_delivery": in_delivery,
        "delivered": delivered,
        "returned": returned,
        "pending": pending,
        "cancelled": cancelled,
        "total_users": total_users,
        "customers": customers,
        "designers": designers,
        "delivery_men": delivery_men,
        "vendors": vendors,
        "students": students,
        "sales": _format_money(total_sales_amount),
        "month_sales": _format_money(month_sales_amount),
        "today_sales": _format_money(today_sales_amount),
        "delivery_man_commission": _format_money(delivery_man_commission),
        "top_selling_products": top_selling_products,
        "order_chart": [
            {"label": "Pending", "value": pending, "color": "#f59e0b"},
            {"label": "In Delivery", "value": in_delivery, "color": "#1d72c8"},
            {"label": "Delivered", "value": delivered, "color": "#078c2f"},
            {"label": "Returned", "value": returned, "color": "#ef4444"},
            {"label": "Cancelled", "value": cancelled, "color": "#64748b"},
        ],
        "user_chart": [
            {"label": "Customers", "value": customers, "color": "#078c2f"},
            {"label": "Designers", "value": designers, "color": "#7c3aed"},
            {"label": "Delivery Man", "value": delivery_men, "color": "#1d72c8"},
            {"label": "Vendors", "value": vendors, "color": "#f59e0b"},
            {"label": "Students", "value": students, "color": "#ef4444"},
        ],
    }


def assign_order_to_delivery_man(order_row_id, delivery_username):
    order_row_id = str(order_row_id or "").strip()
    delivery_username = str(delivery_username or "").strip()
    if not order_row_id:
        raise ValueError("Order row was not selected.")
    if not delivery_username:
        raise ValueError("Please select a delivery man.")

    delivery = fetch_one(
        """
        SELECT TOP 1 UserId, Username, Phone
        FROM Users
        WHERE UserCatagory LIKE 'Del%' AND Username = ?
        """,
        [delivery_username],
    )
    if not delivery:
        raise ValueError("Selected delivery man was not found.")

    order = fetch_one(
        """
        SELECT TOP 1 id, orderid, Customerid, Barcode, Pname, Quantity, Price, Date
        FROM TblOrder
        WHERE id = ?
        """,
        [order_row_id],
    )
    if not order:
        raise ValueError("Selected order was not found.")

    with get_connection() as conn:
        cursor = conn.cursor()
        existing = cursor.execute(
            """
            SELECT TOP 1 Id
            FROM SendToDelivery
            WHERE orderid = ? AND ISNULL(Pname, '') = ISNULL(?, '')
            """,
            [order.get("orderid"), order.get("Pname")],
        ).fetchone()
        if existing:
            cursor.execute(
                """
                UPDATE SendToDelivery
                SET DeliveryManName = ?, Customerid = ?, Barcode = ?, Quantity = ?,
                    Size = ?, Price = ?, Date = ?
                WHERE Id = ?
                """,
                [
                    delivery_username,
                    order.get("Customerid"),
                    order.get("Barcode") or "101",
                    order.get("Quantity") or 0,
                    "0",
                    order.get("Price") or 0,
                    order.get("Date"),
                    existing[0],
                ],
            )
        else:
            cursor.execute(
                """
                INSERT INTO SendToDelivery
                    (DeliveryManName, orderid, Customerid, Barcode, Pname, Quantity, Size, Price, Date)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    delivery_username,
                    order.get("orderid"),
                    order.get("Customerid"),
                    order.get("Barcode") or "101",
                    order.get("Pname"),
                    order.get("Quantity") or 0,
                    "0",
                    order.get("Price") or 0,
                    order.get("Date"),
                ],
            )
        cursor.execute("UPDATE TblOrder SET Status = ? WHERE id = ?", ["To DeliveryMan", order_row_id])


def approve_product_barcode(product_id, admin_username):
    product_id = str(product_id or "").strip()
    if not product_id:
        raise ValueError("Product was not selected.")

    product = fetch_one(
        """
        SELECT TOP 1
            P.PID, P.VoucherNo, P.PName, P.PPrice, P.PSelPrice, P.ProductID,
            SQ.Quantity
        FROM tblProducts P
        OUTER APPLY (
            SELECT TOP 1 Quantity
            FROM tblProductSizeQuantity
            WHERE PID = P.PID
            ORDER BY PID DESC
        ) SQ
        WHERE P.PID = ?
        """,
        [product_id],
    )
    if not product:
        raise ValueError("Product was not found.")

    voucher_no = str(product.get("VoucherNo") or "")
    barcode_suffix = ""
    parts = voucher_no.split("/")
    if len(parts) >= 3:
        barcode_suffix = parts[2]
    barcode = "{0}{1}{2}".format(product.get("PID"), product.get("Quantity") or 1, barcode_suffix)

    with get_connection() as conn:
        cursor = conn.cursor()
        existing = cursor.execute(
            "SELECT TOP 1 Item_Id FROM Productbarcode WHERE Item_Id = ? AND Status = 'OK'",
            [str(product.get("PID"))],
        ).fetchone()
        if not existing:
            cursor.execute(
                """
                INSERT INTO Productbarcode
                    (Item_Id, CREATE_BY, VoucherNo, CREATE_DATE, PRICE, barcode, star, Status, Productid)
                VALUES
                    (?, ?, ?, GETDATE(), ?, ?, ?, ?, ?)
                """,
                [
                    str(product.get("PID")),
                    admin_username or "admin",
                    voucher_no,
                    product.get("PPrice") or product.get("PSelPrice") or 0,
                    barcode,
                    "*",
                    "OK",
                    product.get("ProductID") or str(product.get("PID")),
                ],
            )
        cursor.execute("UPDATE tblProducts SET Status = ? WHERE PID = ?", ["BarcodeOk", product.get("PID")])


def delete_pending_product(product_id):
    product_id = str(product_id or "").strip()
    if not product_id:
        raise ValueError("Product was not selected.")
    execute("DELETE FROM tblProducts WHERE PID = ? AND ISNULL(Status, '') = 'Not Delivered'", [product_id])


def get_admin_module_data(slug, filters=None):
    config = ADMIN_MODULE_QUERIES.get(slug)
    filters = filters or {}
    if not config:
        return {
            "title": "Module Ready",
            "description": "Database function for this module will be connected in the next step.",
            "columns": [],
            "display_columns": [],
            "rows": [],
            "error": "",
            "filters": {},
            "delivery_men": [],
            "assignment_enabled": False,
            "product_approval_enabled": False,
        }

    try:
        params = []
        if "date_from" in config.get("filters", []):
            date_from = (filters.get("date_from") or "").strip()
            params.extend([date_from, date_from])
        if "date_to" in config.get("filters", []):
            date_to = (filters.get("date_to") or "").strip()
            params.extend([date_to, date_to])
        if "delivery_man" in config.get("filters", []):
            delivery_man = (filters.get("delivery_man") or "").strip()
            params.extend([delivery_man, delivery_man])
        rows = fetch_all(config["query"], params)
    except Exception as exc:
        return {
            "title": config["title"],
            "description": config["description"],
            "columns": [],
            "display_columns": [],
            "rows": [],
            "error": str(exc),
            "filters": {key: (filters.get(key) or "") for key in config.get("filters", [])},
            "delivery_men": get_delivery_men() if slug in ("customer-order", "delivery-man") else [],
            "assignment_enabled": slug == "customer-order",
            "product_approval_enabled": slug == "product-barcode",
        }

    columns = list(rows[0].keys()) if rows else []
    display_columns = [column for column in columns if not str(column).startswith("_")]
    return {
        "title": config["title"],
        "description": config["description"],
        "columns": columns,
        "display_columns": display_columns,
        "rows": rows,
        "error": "",
        "filters": {key: (filters.get(key) or "") for key in config.get("filters", [])},
        "delivery_men": get_delivery_men() if slug in ("customer-order", "delivery-man") else [],
        "assignment_enabled": slug == "customer-order",
        "product_approval_enabled": slug == "product-barcode",
    }
