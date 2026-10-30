from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4

from db import execute, fetch_one, get_connection


SMS_API_URL = "http://bulksmsbd.net/api/smsapi"
SMS_API_KEY = "VOIcht1ruPGGs88Vy5SU"
SMS_SENDER_ID = "8809617623792"
ADMIN_SMS_NUMBERS = "8801677802233"


def truncate_status(value, limit=48):
    text = str(value or "")
    return text[:limit]


def send_sms(mobile, message):
    params = {
        "api_key": SMS_API_KEY,
        "type": "text",
        "number": mobile,
        "senderid": SMS_SENDER_ID,
        "message": message,
    }
    url = "{0}?{1}".format(SMS_API_URL, urlencode(params))
    try:
        with urlopen(url, timeout=8) as response:
            result = response.read().decode("utf-8", errors="replace")
        return True, result
    except Exception as exc:
        return False, str(exc)


def log_sms_status(mobile, status):
    try:
        execute(
            """
            INSERT INTO SMS_COUNT (MOBILE_NO, STATUS, INSERT_TIME, TotalSms)
            VALUES (?, ?, GETDATE(), ?)
            """,
            [str(mobile or "")[:50], truncate_status(status), 1],
        )
    except Exception:
        # SMS log must not break order placement.
        pass


def find_customer_by_mobile(mobile):
    return fetch_one(
        """
        SELECT TOP 1 id, name, email, address, contactno, CustomerId
        FROM CustomerInformation
        WHERE contactno = ?
        ORDER BY id DESC
        """,
        [mobile],
    )


def create_or_update_customer(data):
    mobile = data["mobile"]
    customer = find_customer_by_mobile(mobile)
    if customer:
        execute(
            """
            UPDATE CustomerInformation
            SET name = ?, email = ?, address = ?
            WHERE id = ?
            """,
            [data["name"], data.get("email", ""), data["address"], customer["id"]],
        )
        return str(customer.get("CustomerId") or mobile)

    customer_id = "C{0}".format(mobile)
    execute(
        """
        INSERT INTO CustomerInformation (name, address, contactno, email, CustomerId, comments)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [data["name"], data["address"], mobile, data.get("email", ""), customer_id, "Created from Python checkout"],
    )
    return customer_id


def build_order_id():
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:5].upper()
    return "AS{0}{1}".format(stamp, suffix)


def _to_float(value, default=0):
    try:
        return float(str(value or default).strip())
    except (TypeError, ValueError):
        return default


def save_checkout_order(customer_id, customer, items, payment_type, payment_method, total):
    order_id = build_order_id()
    pay_method = payment_method if payment_type == "Mobile Payment" else payment_type

    with get_connection() as conn:
        cursor = conn.cursor()
        for item in items:
            quantity = int(item.get("quantity", 1))
            unit_price = _to_float(item.get("price"), 0)
            line_total = unit_price * quantity
            commission_percent = _to_float(item.get("affiliate_commission_percent") or item.get("commission"), 0)
            commission_amount = (line_total * commission_percent) / 100 if commission_percent else 0
            marketplace_commission = (commission_amount * 40) / 100
            user_commission = (commission_amount * 50) / 100
            reference_commission = (commission_amount * 10) / 100
            price_to_main_seller = line_total - commission_amount
            affiliate_username = str(item.get("affiliate_username") or customer["mobile"])
            cursor.execute(
                """
                INSERT INTO TblOrder
                    (orderid, Customerid, Barcode, Pid, Pname, Quantity, Price, Status, Date, MainItemSellerName,
                     UserName, UserComission, Marketplaecomission, ReferenceComission, PricetoMainsailer)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?, ?, ?, ?, ?)
                """,
                [
                    order_id,
                    customer_id,
                    "",
                    str(item.get("id", "")),
                    str(item.get("name", "")),
                    quantity,
                    unit_price,
                    "Pending",
                    str(item.get("seller", "")),
                    affiliate_username,
                    user_commission,
                    marketplace_commission,
                    reference_commission,
                    price_to_main_seller,
                ],
            )
            if item.get("affiliate_username"):
                cursor.execute(
                    """
                    INSERT INTO SoldItembyUser
                        (UserName, UserId, ProductId, ProductName, Price, MainItemSellerName,
                         PricetoMainsailer, UserComission, Marketplaecomission, ReferenceComission)
                    VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        affiliate_username,
                        str(item.get("affiliate_user_id") or ""),
                        str(item.get("id", "")),
                        str(item.get("name", "")),
                        line_total,
                        str(item.get("seller", "")),
                        price_to_main_seller,
                        user_commission,
                        marketplace_commission,
                        reference_commission,
                    ],
                )

        cursor.execute(
            """
            INSERT INTO OrderPayment
                (Pay_method, Pay_by, Pay_to, Pay_amount, Sending_account, Transition_No, Pay_date)
            VALUES
                (?, ?, ?, ?, ?, ?, GETDATE())
            """,
            [
                pay_method,
                customer["mobile"],
                "bdallmart.com",
                "{0:.2f}".format(float(total)),
                customer["mobile"] if payment_type == "Mobile Payment" else "",
                "",
            ],
        )

    customer_message = (
        "Your order {0} has been submitted to bdallmart.com. "
        "Please wait for delivery confirmation. User ID: {1}"
    ).format(order_id, customer["mobile"])
    admin_message = "You have received an order {0} from {1}. Please confirm delivery. bdallmart.com".format(
        order_id,
        customer["mobile"],
    )

    customer_sms_ok, customer_sms_result = send_sms(customer["mobile"], customer_message)
    admin_sms_ok, admin_sms_result = send_sms(ADMIN_SMS_NUMBERS, admin_message)

    log_sms_status(
        customer["mobile"],
        "Sent: {0}".format(customer_sms_result) if customer_sms_ok else "Failed: {0}".format(customer_sms_result),
    )
    log_sms_status(
        ADMIN_SMS_NUMBERS,
        "Sent: {0}".format(admin_sms_result) if admin_sms_ok else "Failed: {0}".format(admin_sms_result),
    )
    return order_id
