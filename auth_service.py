from db import execute, fetch_one
from security import password_for_storage, verify_password


ROLE_DASHBOARDS = {
    "admin": "admin_dashboard",
    "customer": "customer_dashboard",
    "vendor": "vendor_dashboard",
    "seller": "vendor_dashboard",
    "buyer": "vendor_dashboard",
    "user": "customer_dashboard",
    "designer": "freelancer_dashboard",
    "freelancer": "freelancer_dashboard",
    "institute": "course_dashboard",
    "instructor": "course_dashboard",
    "student": "course_dashboard",
    "delivery": "delivery_dashboard",
    "deliveryman": "delivery_dashboard",
    "pos": "pos_dashboard",
    "posuser": "pos_dashboard",
}


def normalize_category(category):
    normalized = (category or "").replace(" ", "").replace("-", "").lower()
    aliases = {
        "consumer": "customer",
    }
    return aliases.get(normalized, normalized)


def dashboard_endpoint_for(category):
    normalized = normalize_category(category)
    return ROLE_DASHBOARDS.get(normalized, "customer_dashboard")


def find_user_by_login(login):
    return fetch_one(
        """
        SELECT TOP 1
            UserId, Username, Password, Email, Phone, UserCatagory, Active, Status,
            AdminStatus, FirstName, LastName, Address, City, Country
        FROM Users
        WHERE Email = ? OR Username = ? OR Phone = ?
        """,
        [login, login, login],
    )


def authenticate(login, password):
    login = str(login or "").strip()
    password = str(password or "").strip()
    user = find_user_by_login(login)
    if not user:
        return None, "Invalid email, username, or password."

    if not verify_password(password, str(user.get("Password") or "")):
        return None, "Invalid email, username, or password."

    active = str(user.get("Active") or "").strip()
    status = str(user.get("Status") or "").strip()
    active_ok = active == "1" or active.lower() == "true"
    status_ok = status == "" or status.lower() == "true"

    if not active_ok or not status_ok:
        return None, "Your account is not active. Please contact admin."

    return user, ""


def user_exists(username, email):
    row = fetch_one(
        "SELECT COUNT(1) AS Total FROM Users WHERE Username = ? OR Email = ?",
        [username, email],
    )
    return bool(row and int(row["Total"]) > 0)


def phone_exists(phone):
    if not phone:
        return False
    row = fetch_one(
        "SELECT COUNT(1) AS Total FROM Users WHERE Phone = ?",
        [phone],
    )
    return bool(row and int(row["Total"]) > 0)


def create_user(username, email, phone, password, category, reference):
    if category not in {"Customer", "Vendor", "Designer", "Student"}:
        raise ValueError("Please select a valid account category.")
    execute(
        """
        INSERT INTO Users
            (Username, Password, Email, Active, Status, Phone, Code, UserCatagory, referance, Lavel, Reting)
        VALUES
            (?, ?, ?, '1', 'True', ?, ?, ?, ?, ?, ?)
        """,
        [
            username,
            password_for_storage(password),
            email,
            phone,
            "00000",
            category,
            reference or "2",
            "5",
            "3",
        ],
    )
