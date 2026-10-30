import os
import secrets
import xml.etree.ElementTree as ET
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
WEB_CONFIG_PATH = PROJECT_ROOT / "web.config"


def session_secret():
    configured = os.environ.get("FLASK_SECRET_KEY")
    if configured and configured != "change-this-secret-before-production":
        return configured
    # Keep a random secret across restarts; never trust the previous public default.
    path = BASE_DIR / "instance" / "session_secret"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="ascii") as output:
            output.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    secret = path.read_text(encoding="ascii").strip()
    if len(secret) < 32:
        raise RuntimeError("Session secret is incomplete; set FLASK_SECRET_KEY before starting the app.")
    return secret
DEFAULT_DB_CONNECTION_STRING = (
    "Data Source=103.159.73.66;Initial Catalog=BdOnlinePlatform; "
    "User Id=sa; Password=Abc@#123ht;"
)


class Config:
    SECRET_KEY = session_secret()
    PASSWORD_STORAGE = os.environ.get("PASSWORD_STORAGE", "legacy_plaintext")
    SQLSERVER_ODBC_DRIVER = os.environ.get("SQLSERVER_ODBC_DRIVER", "ODBC Driver 17 for SQL Server")
    DB_CONNECTION_STRING = os.environ.get("ALLSERVICER_DB_CONN_STR") or ""
    PUBLIC_BASE_URL = os.environ.get("ALLSERVICER_PUBLIC_URL", "http://bdallmart.com").rstrip("/")
    MARKET_PAYMENT_INSTRUCTIONS = os.environ.get("MARKET_PAYMENT_INSTRUCTIONS", "")
    MARKET_PRIVATE_DIR = os.environ.get("MARKET_PRIVATE_DIR", "")
    PROJECT_ROOT = PROJECT_ROOT


def get_dotnet_connection_string(name="DBcon"):
    if Config.DB_CONNECTION_STRING:
        return Config.DB_CONNECTION_STRING

    if not WEB_CONFIG_PATH.exists():
        return DEFAULT_DB_CONNECTION_STRING

    tree = ET.parse(str(WEB_CONFIG_PATH))
    root = tree.getroot()
    for item in root.findall("./connectionStrings/add"):
        if item.attrib.get("name") == name:
            return item.attrib.get("connectionString", "")

    return DEFAULT_DB_CONNECTION_STRING


def parse_dotnet_connection_string(connection_string):
    values = {}
    for part in connection_string.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key.strip().lower()] = value.strip()
    return values


def get_pyodbc_connection_string():
    values = parse_dotnet_connection_string(get_dotnet_connection_string())
    server = values.get("data source") or values.get("server")
    database = values.get("initial catalog") or values.get("database")
    user = values.get("user id") or values.get("uid")
    password = values.get("password") or values.get("pwd")
    trusted = values.get("trusted_connection") or values.get("integrated security")

    parts = [
        "DRIVER={" + Config.SQLSERVER_ODBC_DRIVER + "}",
        "SERVER=" + server,
        "DATABASE=" + database,
        "TrustServerCertificate=yes",
        "Connection Timeout=3",
    ]

    if trusted and trusted.lower() in ("true", "yes", "sspi"):
        parts.append("Trusted_Connection=yes")
    else:
        parts.append("UID=" + user)
        parts.append("PWD=" + password)

    return ";".join(parts)
