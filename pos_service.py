from datetime import datetime
from uuid import uuid4

from db import get_connection


def build_pos_order_id():
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:5].upper()
    return "POS{0}{1}".format(stamp, suffix)


def _to_float(value, default=0):
    try:
        return float(str(value or default).strip())
    except (TypeError, ValueError):
        return default


def _to_int(value, default=1):
    try:
        return int(float(str(value or default).strip()))
    except (TypeError, ValueError):
        return default


def ensure_tbl_order_pos(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.TblOrderPOS', 'U') IS NULL
        BEGIN
            SELECT TOP 0 *
            INTO dbo.TblOrderPOS
            FROM dbo.TblOrder;
        END
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.TblOrderPOS', 'CustomerName') IS NULL
            ALTER TABLE dbo.TblOrderPOS ADD CustomerName nvarchar(150) NULL;
        IF COL_LENGTH('dbo.TblOrderPOS', 'CustomerMobile') IS NULL
            ALTER TABLE dbo.TblOrderPOS ADD CustomerMobile nvarchar(50) NULL;
        IF COL_LENGTH('dbo.TblOrderPOS', 'DeliveryAddress') IS NULL
            ALTER TABLE dbo.TblOrderPOS ADD DeliveryAddress nvarchar(500) NULL;
        """
    )


def save_pos_order(items, customer=None, sales_employee="", status="POS Sale"):
    clean_items = [item for item in items if str(item.get("id") or "").strip()]
    if not clean_items:
        raise ValueError("No POS item found.")

    customer = customer or {}
    customer_name = str(customer.get("full_name") or "").strip()
    customer_mobile = str(customer.get("mobile") or "").strip()
    delivery_address = str(customer.get("address") or "").strip()
    if not customer_mobile:
        raise ValueError("Mobile Number is required.")
    if not customer_name:
        raise ValueError("Full Name is required.")
    if not delivery_address:
        raise ValueError("Delivery Address is required.")

    order_id = build_pos_order_id()
    customer_id = "C{0}".format(customer_mobile)
    seller = str(sales_employee or "POS")

    with get_connection() as conn:
        cursor = conn.cursor()
        ensure_tbl_order_pos(cursor)
        for item in clean_items:
            quantity = max(1, _to_int(item.get("qty"), 1))
            unit_price = _to_float(item.get("price"), 0)
            discount = _to_float(item.get("discount"), 0)
            line_total = max(0, (unit_price * quantity) - discount)
            cursor.execute(
                """
                INSERT INTO TblOrderPOS
                    (orderid, Customerid, Barcode, Pid, Pname, Quantity, Price, Status, Date, MainItemSellerName,
                     UserName, UserComission, Marketplaecomission, ReferenceComission, PricetoMainsailer,
                     CustomerName, CustomerMobile, DeliveryAddress)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    order_id,
                    customer_id,
                    str(item.get("barcode") or item.get("id") or ""),
                    str(item.get("id") or ""),
                    str(item.get("name") or ""),
                    quantity,
                    unit_price,
                    status,
                    seller,
                    seller,
                    0,
                    0,
                    0,
                    line_total,
                    customer_name,
                    customer_mobile,
                    delivery_address,
                ],
            )

    return order_id


def get_pos_order(order_id):
    order_id = str(order_id or "").strip()
    if not order_id:
        return None

    with get_connection() as conn:
        cursor = conn.cursor()
        ensure_tbl_order_pos(cursor)
        cursor.execute(
            """
            SELECT
                O.orderid, O.Customerid, O.Barcode, O.Pid, O.Pname, O.Quantity, O.Price, O.Status, O.Date,
                O.MainItemSellerName, O.UserName, O.PricetoMainsailer,
                O.CustomerName, O.CustomerMobile, O.DeliveryAddress,
                IMG.Name AS ImageName, IMG.Extention AS ImageExtention
            FROM TblOrderPOS O
            OUTER APPLY (
                SELECT TOP 1 Name, Extention
                FROM tblProductImages
                WHERE PID = O.Pid AND ISNULL(Extention, '') <> 'YouTube' AND ISNULL(Extention, '') <> '.mp4'
                ORDER BY Name
            ) IMG
            WHERE O.orderid = ?
            ORDER BY O.id
            """,
            [order_id],
        )
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if not rows:
        return None

    for row in rows:
        image_name = str(row.get("ImageName") or "").strip()
        image_extension = str(row.get("ImageExtention") or "").strip()
        if image_name and image_extension and not image_name.lower().endswith(image_extension.lower()):
            image_name += image_extension
        row["ImagePath"] = "ProductImage/{0}/{1}".format(row.get("Pid"), image_name) if row.get("Pid") and image_name else "ProductImage/download.jpg"

    subtotal = sum(_to_float(row.get("Price"), 0) * _to_int(row.get("Quantity"), 1) for row in rows)
    total = sum(_to_float(row.get("PricetoMainsailer"), 0) for row in rows)
    if total <= 0:
        total = subtotal
    return {
        "order_id": order_id,
        "customer_id": rows[0].get("Customerid") or "",
        "customer_name": rows[0].get("CustomerName") or "",
        "customer_mobile": rows[0].get("CustomerMobile") or "",
        "delivery_address": rows[0].get("DeliveryAddress") or "",
        "sales_employee": rows[0].get("UserName") or rows[0].get("MainItemSellerName") or "",
        "date": rows[0].get("Date"),
        "status": rows[0].get("Status") or "",
        "items": rows,
        "subtotal": subtotal,
        "total": total,
        "item_count": sum(_to_int(row.get("Quantity"), 1) for row in rows),
    }


def _rows_to_dicts(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_pos_sales_report(date_from, date_to):
    params = [date_from, date_to]
    where_clause = "WHERE CAST(O.Date AS date) BETWEEN ? AND ?"

    with get_connection() as conn:
        cursor = conn.cursor()
        ensure_tbl_order_pos(cursor)

        cursor.execute(
            """
            SELECT
                COUNT(DISTINCT O.orderid) AS TotalOrders,
                COALESCE(SUM(O.Quantity), 0) AS TotalQty,
                COALESCE(SUM(O.PricetoMainsailer), 0) AS TotalSales,
                COALESCE(AVG(NULLIF(O.PricetoMainsailer, 0)), 0) AS AvgLineSale
            FROM TblOrderPOS O
            """ + where_clause,
            params,
        )
        summary = dict(zip([column[0] for column in cursor.description], cursor.fetchone()))

        cursor.execute(
            """
            SELECT
                COALESCE(C.CategoryName, 'Uncategorized') AS CategoryName,
                COALESCE(SUM(O.Quantity), 0) AS TotalQty,
                COALESCE(SUM(O.PricetoMainsailer), 0) AS TotalSales
            FROM TblOrderPOS O
            LEFT JOIN tblProducts P ON CONVERT(nvarchar(50), P.PID) = O.Pid
            LEFT JOIN Category C ON C.id = P.PCategoryID
            """ + where_clause + """
            GROUP BY COALESCE(C.CategoryName, 'Uncategorized')
            ORDER BY TotalSales DESC
            """,
            params,
        )
        category_rows = _rows_to_dicts(cursor)

        cursor.execute(
            """
            SELECT
                O.Pid,
                O.Pname,
                COALESCE(C.CategoryName, 'Uncategorized') AS CategoryName,
                COALESCE(SUM(O.Quantity), 0) AS TotalQty,
                COALESCE(SUM(O.PricetoMainsailer), 0) AS TotalSales
            FROM TblOrderPOS O
            LEFT JOIN tblProducts P ON CONVERT(nvarchar(50), P.PID) = O.Pid
            LEFT JOIN Category C ON C.id = P.PCategoryID
            """ + where_clause + """
            GROUP BY O.Pid, O.Pname, COALESCE(C.CategoryName, 'Uncategorized')
            ORDER BY TotalQty DESC, TotalSales DESC
            """,
            params,
        )
        product_rows = _rows_to_dicts(cursor)

        cursor.execute(
            """
            SELECT TOP 10
                O.Pname,
                COALESCE(SUM(O.Quantity), 0) AS TotalQty,
                COALESCE(SUM(O.PricetoMainsailer), 0) AS TotalSales
            FROM TblOrderPOS O
            """ + where_clause + """
            GROUP BY O.Pname
            ORDER BY TotalQty DESC, TotalSales DESC
            """,
            params,
        )
        top_products = _rows_to_dicts(cursor)

        cursor.execute(
            """
            SELECT
                CONVERT(varchar(10), CAST(O.Date AS date), 120) AS SaleDate,
                COUNT(DISTINCT O.orderid) AS TotalOrders,
                COALESCE(SUM(O.Quantity), 0) AS TotalQty,
                COALESCE(SUM(O.PricetoMainsailer), 0) AS TotalSales
            FROM TblOrderPOS O
            """ + where_clause + """
            GROUP BY CAST(O.Date AS date)
            ORDER BY CAST(O.Date AS date)
            """,
            params,
        )
        daily_rows = _rows_to_dicts(cursor)

    return {
        "summary": summary,
        "categories": category_rows,
        "products": product_rows,
        "top_products": top_products,
        "daily_sales": daily_rows,
    }
