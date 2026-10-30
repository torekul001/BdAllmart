from db import fetch_all, fetch_one, get_connection


DELIVERY_MENU = [
    ("Delivery Dashboard", "/dashboards/delivery"),
    ("Assigned Orders", "/dashboards/delivery"),
]


DELIVERY_STATUSES = [
    "To DeliveryMan",
    "Picked Up",
    "Complete",
    "Return",
    "Sold",
]


def get_delivery_profile(user_id):
    return fetch_one(
        """
        SELECT TOP 1 UserId, Username, Email, Phone, FirstName, LastName, UserCatagory,
            Active, Status, AdminStatus, picture
        FROM Users
        WHERE UserId = ?
        """,
        [user_id],
    )


def get_delivery_summary(username):
    row = fetch_one(
        """
        SELECT
            SUM(CASE WHEN ISNULL(O.Status, '') = 'To DeliveryMan' THEN 1 ELSE 0 END) AS Assigned,
            SUM(CASE WHEN ISNULL(O.Status, '') = 'Picked Up' THEN 1 ELSE 0 END) AS PickedUp,
            SUM(CASE WHEN ISNULL(O.Status, '') = 'Complete' THEN 1 ELSE 0 END) AS Complete,
            SUM(CASE WHEN ISNULL(O.Status, '') IN ('Return', 'Sold') THEN 1 ELSE 0 END) AS Closed
        FROM SendToDelivery D
        LEFT JOIN TblOrder O ON O.orderid = D.orderid AND O.Pname = D.Pname
        WHERE D.DeliveryManName = ?
        """,
        [username],
    ) or {}
    return {
        "assigned": int(row.get("Assigned") or 0),
        "picked_up": int(row.get("PickedUp") or 0),
        "complete": int(row.get("Complete") or 0),
        "closed": int(row.get("Closed") or 0),
    }


def get_delivery_orders(username, date_from="", date_to="", status=""):
    return fetch_all(
        """
        SELECT TOP 200
            D.Id AS AssignId,
            O.id AS OrderRowId,
            D.orderid AS OrderId,
            D.Customerid,
            D.Barcode,
            D.Pname,
            D.Quantity,
            D.Price,
            D.Date,
            O.Status,
            O.UserName
        FROM SendToDelivery D
        LEFT JOIN TblOrder O ON O.orderid = D.orderid AND O.Pname = D.Pname
        WHERE D.DeliveryManName = ?
            AND (? = '' OR CAST(D.Date AS date) >= CAST(? AS date))
            AND (? = '' OR CAST(D.Date AS date) <= CAST(? AS date))
            AND (? = '' OR ISNULL(O.Status, '') = ?)
        ORDER BY D.Id DESC
        """,
        [username, date_from, date_from, date_to, date_to, status, status],
    )


def update_delivery_order_status(username, assign_id, status):
    assign_id = str(assign_id or "").strip()
    status = str(status or "").strip()
    if not assign_id:
        raise ValueError("Order assignment was not selected.")
    if status not in DELIVERY_STATUSES:
        raise ValueError("Please select a valid delivery status.")

    assignment = fetch_one(
        """
        SELECT TOP 1 Id, DeliveryManName, orderid, Pname
        FROM SendToDelivery
        WHERE Id = ? AND DeliveryManName = ?
        """,
        [assign_id, username],
    )
    if not assignment:
        raise ValueError("This order is not assigned to your account.")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE TblOrder
            SET Status = ?
            WHERE orderid = ? AND Pname = ?
            """,
            [status, assignment.get("orderid"), assignment.get("Pname")],
        )
