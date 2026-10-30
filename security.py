import hashlib
import hmac
import os

from config import Config


def hash_password(password):
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return "pbkdf2_sha256${0}${1}".format(salt, digest)


def verify_password(password, stored_password):
    stored_password = stored_password or ""
    if stored_password.startswith("pbkdf2_sha256$"):
        _, salt, expected = stored_password.split("$", 2)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
        return hmac.compare_digest(digest, expected)
    return hmac.compare_digest(password, stored_password)


def password_for_storage(password):
    if Config.PASSWORD_STORAGE == "hashed":
        return hash_password(password)
    return password
