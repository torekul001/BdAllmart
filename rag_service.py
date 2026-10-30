import html
import json
import os
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from db import fetch_all


MAX_TERMS = 6
LOCAL_LLM_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
LOCAL_LLM_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
LOCAL_LLM_ENABLED = os.getenv("RAG_LOCAL_LLM", "1").lower() not in {"0", "false", "no"}

PRODUCT_WORDS = {"product", "products", "item", "items", "ponno", "panno"}
SERVICE_WORDS = {"service", "services", "offer", "offers", "package", "packages"}
JOB_WORDS = {"job", "jobs", "work", "order", "contest"}
COURSE_WORDS = {"course", "courses", "video", "videos", "lesson", "lessons"}


def _clean_text(value, limit=260):
    text = str(value or "").strip()
    for _ in range(3):
        text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def _terms(question):
    words = re.findall(r"[A-Za-z0-9\u0980-\u09FF]+", str(question or "").lower())
    ignored = {
        "the", "and", "for", "with", "this", "that", "ache", "ase", "koto", "ki",
        "ami", "amar", "show", "please", "price", "tk", "all", "your", "from",
        "product", "products", "item", "items", "ponno", "panno",
        "service", "services", "offer", "offers", "package", "packages",
        "course", "courses", "video", "videos", "lesson", "lessons", "job", "jobs",
        "how", "many", "much", "count", "total", "category", "catagory", "in", "of",
        "there", "is", "are", "have", "has", " koyta", "koita", "koyti",
        "taka", "takar", "tk", "amount", "budget", "under", "below", "within",
        "ar", "er", "vitor", "moddhe", "vitore", "inside",
        "list", "gulo", "gula", "ki", "ki ki", "dao", "dekhao",
        "related", "releted", "somprokito", "somporke", "show", "koro",
    }
    filtered = []
    for word in words:
        if len(word) < 2 or word in ignored:
            continue
        if word not in filtered:
            filtered.append(word)
    return filtered[:MAX_TERMS]


def _has_any(question, words):
    text = str(question or "").lower()
    return any(re.search(r"\b{0}\b".format(re.escape(word)), text) for word in words)


def _is_latest_question(question):
    text = str(question or "").lower()
    return any(word in text for word in ["latest", "new", "newest", "recent", "last", "notun", "newly"])


def _is_cheap_question(question):
    text = str(question or "").lower()
    return any(word in text for word in ["cheap", "low price", "lowest", "kom dam", "kom taka", "sosta", "affordable"])


def _is_expensive_question(question):
    text = str(question or "").lower()
    return any(word in text for word in ["expensive", "high price", "highest", "beshi dam", "premium"])


def _like_params(terms, field_count):
    params = []
    for term in terms:
        params.extend(["%{0}%".format(term)] * field_count)
    return params


def _and_like_clause(fields, terms):
    if not terms:
        return "", []
    parts = []
    for _ in terms:
        parts.append("(" + " OR ".join("{0} LIKE ?".format(field) for field in fields) + ")")
    return " AND " + " AND ".join(parts), _like_params(terms, len(fields))


def _or_like_clause(fields, terms):
    if not terms:
        return "", []
    parts = []
    for _ in terms:
        parts.extend("{0} LIKE ?".format(field) for field in fields)
    return " AND (" + " OR ".join(parts) + ")", _like_params(terms, len(fields))


def _safe_fetch(query, params=None):
    try:
        return fetch_all(query, params or [])
    except Exception:
        return []


def _product_image(row):
    pid = str((row or {}).get("PID") or "").strip()
    name = str((row or {}).get("Name") or "").strip()
    extension = str((row or {}).get("Extention") or "").strip()
    if not pid or not name:
        return "ProductImage/download.jpg"
    if extension and not name.lower().endswith(extension.lower()):
        name += extension
    return "ProductImage/{0}/{1}".format(pid, name)


def _is_count_question(question):
    text = str(question or "").lower()
    return any(
        token in text
        for token in [
            "how many",
            "total",
            "count",
            "koto",
            "koto ta",
            "koyta",
            "koita",
            "koto gula",
            "koto product",
            "কয়টা",
            "কত",
        ]
    )


def _single_count(query, params=None):
    rows = _safe_fetch(query, params or [])
    if not rows:
        return 0
    return int(rows[0].get("Total") or 0)


def _find_category(question):
    rows = _safe_fetch(
        """
        SELECT id, CategoryName
        FROM Category
        WHERE ISNULL(CategoryName, '') <> ''
        ORDER BY LEN(CategoryName) DESC
        """
    )
    text = str(question or "").lower()
    for row in rows:
        name = str(row.get("CategoryName") or "").strip()
        if name and name.lower() in text:
            return row
    terms = _terms(question)
    for row in rows:
        name = str(row.get("CategoryName") or "").lower()
        if any(term in name for term in terms):
            return row
    return None


def _find_subcategory(question):
    rows = _safe_fetch(
        """
        SELECT
            S.id,
            S.Catid,
            S.SubcatName,
            C.CategoryName
        FROM SubCategory S
        LEFT JOIN Category C ON C.id = S.Catid
        WHERE ISNULL(S.SubcatName, '') <> ''
        ORDER BY LEN(S.SubcatName) DESC
        """
    )
    text = str(question or "").lower()
    for row in rows:
        name = str(row.get("SubcatName") or "").strip()
        if name and name.lower() in text:
            return row
    return None


def aggregate_answer(question):
    text = str(question or "").lower()
    if any(token in text for token in ["category list", "catagory list", "all category", "categories", "category gulo"]):
        rows = _safe_fetch("SELECT id, CategoryName FROM Category WHERE ISNULL(CategoryName, '') <> '' ORDER BY CategoryName")
        results = [
            {
                "type": "Category",
                "title": _clean_text(row.get("CategoryName"), 90),
                "meta": "Product category",
                "text": "Open this category to view category wise products.",
                "url": "/category/{0}".format(row.get("id")),
            }
            for row in rows[:24]
        ]
        return {
            "answer": "Database e {0} ta category peyechi.".format(len(rows)),
            "results": results,
            "llm_enabled": LOCAL_LLM_ENABLED,
            "llm_model": LOCAL_LLM_MODEL,
            "llm_used": False,
        }

    if not _is_count_question(question):
        return None

    category = _find_category(question)
    subcategory = _find_subcategory(question)
    if subcategory:
        total = _single_count(
            """
            SELECT COUNT(DISTINCT P.PID) AS Total
            FROM tblProducts P
            INNER JOIN Productbarcode PB ON PB.Item_Id = P.PID AND PB.Status = 'OK'
            WHERE P.PSubCatID = ?
            """,
            [subcategory.get("id")],
        )
        name = _clean_text(subcategory.get("SubcatName"), 80)
        return {
            "answer": "{0} subcategory te {1} approved product ache.".format(name, total),
            "results": [{
                "type": "Summary",
                "title": "{0} product count".format(name),
                "meta": "{0} approved product".format(total),
                "text": "Count from tblProducts and Productbarcode where barcode status is OK.",
                "url": "/category/{0}?sub={1}".format(subcategory.get("Catid"), subcategory.get("id")),
            }],
            "llm_enabled": LOCAL_LLM_ENABLED,
            "llm_model": LOCAL_LLM_MODEL,
            "llm_used": False,
        }
    if category:
        total = _single_count(
            """
            SELECT COUNT(DISTINCT P.PID) AS Total
            FROM tblProducts P
            INNER JOIN Productbarcode PB ON PB.Item_Id = P.PID AND PB.Status = 'OK'
            WHERE P.PCategoryID = ?
            """,
            [category.get("id")],
        )
        name = _clean_text(category.get("CategoryName"), 80)
        return {
            "answer": "{0} category te {1} approved product ache.".format(name, total),
            "results": [{
                "type": "Summary",
                "title": "{0} product count".format(name),
                "meta": "{0} approved product".format(total),
                "text": "Count from tblProducts and Productbarcode where barcode status is OK.",
                "url": "/category/{0}".format(category.get("id")),
            }],
            "llm_enabled": LOCAL_LLM_ENABLED,
            "llm_model": LOCAL_LLM_MODEL,
            "llm_used": False,
        }

    if "product" in text or "পণ্য" in text:
        total = _single_count(
            """
            SELECT COUNT(DISTINCT P.PID) AS Total
            FROM tblProducts P
            INNER JOIN Productbarcode PB ON PB.Item_Id = P.PID AND PB.Status = 'OK'
            """
        )
        return {
            "answer": "Database e total {0} approved product ache.".format(total),
            "results": [{
                "type": "Summary",
                "title": "All approved products",
                "meta": "{0} approved product".format(total),
                "text": "Count from tblProducts and Productbarcode where barcode status is OK.",
                "url": "/login",
            }],
            "llm_enabled": LOCAL_LLM_ENABLED,
            "llm_model": LOCAL_LLM_MODEL,
            "llm_used": False,
        }

    if _has_any(question, SERVICE_WORDS):
        total = _single_count("SELECT COUNT(1) AS Total FROM OfferDetails")
        return {
            "answer": "Database e total {0} service offer ache.".format(total),
            "results": [{
                "type": "Summary",
                "title": "All service offers",
                "meta": "{0} service offer".format(total),
                "text": "Count from OfferDetails table.",
                "url": "/login",
            }],
            "llm_enabled": LOCAL_LLM_ENABLED,
            "llm_model": LOCAL_LLM_MODEL,
            "llm_used": False,
        }

    if _has_any(question, JOB_WORDS):
        total = _single_count("SELECT COUNT(1) AS Total FROM JobsList WHERE Deadline >= GETDATE()")
        return {
            "answer": "Database e {0} active job/work ache.".format(total),
            "results": [{
                "type": "Summary",
                "title": "Active jobs",
                "meta": "{0} active job".format(total),
                "text": "Count from JobsList where deadline is active.",
                "url": "/designer/jobs",
            }],
            "llm_enabled": LOCAL_LLM_ENABLED,
            "llm_model": LOCAL_LLM_MODEL,
            "llm_used": False,
        }

    if _has_any(question, COURSE_WORDS):
        total = _single_count("SELECT COUNT(1) AS Total FROM ClassVideo")
        return {
            "answer": "Database e total {0} course video ache.".format(total),
            "results": [{
                "type": "Summary",
                "title": "Course videos",
                "meta": "{0} video lesson".format(total),
                "text": "Count from ClassVideo table.",
                "url": "/courses/manage",
            }],
            "llm_enabled": LOCAL_LLM_ENABLED,
            "llm_model": LOCAL_LLM_MODEL,
            "llm_used": False,
        }

    return None


def _amount_from_question(question):
    text = str(question or "").replace(",", "")
    matches = re.findall(r"\d+(?:\.\d+)?", text)
    if not matches:
        return None
    try:
        return float(matches[0])
    except ValueError:
        return None


def _amount_range_from_question(question):
    text = str(question or "").replace(",", "")
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|to|theke|থেকে|–|—)\s*(\d+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    try:
        low = float(match.group(1))
        high = float(match.group(2))
    except ValueError:
        return None
    if low > high:
        low, high = high, low
    return low, high


def price_answer(question):
    text = str(question or "").lower()
    amount_range = _amount_range_from_question(question)
    if not amount_range and not any(token in text for token in ["taka", "takar", "tk", "price", "amount", "budget"]):
        return None
    amount = _amount_from_question(question)
    if amount_range is None and amount is None:
        return None

    wants_service = _has_any(question, SERVICE_WORDS)
    wants_job = _has_any(question, JOB_WORDS)
    if wants_service:
        return service_price_answer(question, amount, amount_range)
    if wants_job:
        return job_budget_answer(question, amount, amount_range)

    category = _find_category(question)
    subcategory = _find_subcategory(question)
    category_clause = ""
    if amount_range:
        low_amount, high_amount = amount_range
        price_clause = "COALESCE(P.PSelPrice, P.PPrice, 0) BETWEEN ? AND ?"
        params = [low_amount, high_amount]
    else:
        low_amount, high_amount = None, amount
        price_clause = "COALESCE(P.PSelPrice, P.PPrice, 0) <= ?"
        params = [amount]
    if category:
        category_clause = " AND P.PCategoryID = ?"
        params.append(category.get("id"))
    if subcategory:
        category_clause += " AND P.PSubCatID = ?"
        params.append(subcategory.get("id"))

    rows = _safe_fetch(
        """
        SELECT TOP 12
            P.PID,
            P.PName,
            P.PSelPrice,
            P.PPrice,
            P.MainItemSellerName,
            CAT.CategoryName,
            I.Name,
            I.Extention
        FROM tblProducts P
        INNER JOIN Productbarcode PB ON PB.Item_Id = P.PID AND PB.Status = 'OK'
        LEFT JOIN Category CAT ON CAT.id = P.PCategoryID
        LEFT JOIN (
            SELECT PID, MIN(Name) AS Name, MIN(Extention) AS Extention
            FROM tblProductImages
            GROUP BY PID
        ) I ON I.PID = P.PID
        WHERE {0}
        {1}
        ORDER BY COALESCE(P.PSelPrice, P.PPrice, 0) DESC, P.PID DESC
        """.format(price_clause, category_clause),
        params,
    )

    results = []
    for row in rows:
        price = row.get("PSelPrice") or row.get("PPrice") or 0
        results.append({
            "type": "Product",
            "id": row.get("PID"),
            "title": _clean_text(row.get("PName"), 90),
            "meta": "Tk {0} | {1}".format(price, _clean_text(row.get("CategoryName") or "Product", 60)),
            "text": "Seller: {0}.".format(_clean_text(row.get("MainItemSellerName") or "N/A", 60)),
            "url": "/product/{0}".format(row.get("PID")),
            "image": _product_image(row),
        })

    if not results:
        return None

    scope = "approved product"
    if subcategory:
        scope = "{0} subcategory product".format(_clean_text(subcategory.get("SubcatName"), 60))
    elif category:
        scope = "{0} category product".format(_clean_text(category.get("CategoryName"), 60))
    if amount_range:
        answer = "Tk {0:g} theke Tk {1:g} er moddhe {2} ta {3} peyechi.".format(
            low_amount, high_amount, len(results), scope
        )
    else:
        answer = "Tk {0:g} er moddhe {1} ta {2} peyechi.".format(amount, len(results), scope)
    return {
        "answer": answer,
        "results": results,
        "llm_enabled": LOCAL_LLM_ENABLED,
        "llm_model": LOCAL_LLM_MODEL,
        "llm_used": False,
    }


def service_price_answer(question, amount, amount_range=None):
    if amount_range:
        low_amount, high_amount = amount_range
        price_clause = """
            (
                O.offer_amount1 BETWEEN ? AND ?
             OR O.offer_amount2 BETWEEN ? AND ?
             OR O.offer_amount3 BETWEEN ? AND ?
            )
        """
        params = [low_amount, high_amount, low_amount, high_amount, low_amount, high_amount]
    else:
        low_amount, high_amount = None, amount
        price_clause = """
            (
                O.offer_amount1 <= ?
             OR O.offer_amount2 <= ?
             OR O.offer_amount3 <= ?
            )
        """
        params = [amount, amount, amount]

    rows = _safe_fetch(
        """
        SELECT TOP 12 O.id, O.offer_title, O.OfferType, O.offer_amount1, O.offer_amount2, O.offer_amount3, U.Username
        FROM OfferDetails O
        LEFT JOIN Users U ON CONVERT(varchar(50), U.UserId) = O.userid
        WHERE {0}
        ORDER BY O.id DESC
        """.format(price_clause),
        params,
    )
    results = []
    for row in rows:
        amounts = [row.get("offer_amount1"), row.get("offer_amount2"), row.get("offer_amount3")]
        amounts = [str(item) for item in amounts if item not in (None, "")]
        results.append({
            "type": "Service",
            "title": _clean_text(row.get("offer_title"), 90),
            "meta": "{0} | Package: {1}".format(_clean_text(row.get("OfferType") or "Service", 60), ", ".join(amounts) or "N/A"),
            "text": "Designer: {0}.".format(_clean_text(row.get("Username") or "N/A", 60)),
            "url": "/designer/offers?offer_id={0}".format(row.get("id")),
        })
    if not results:
        return None
    answer = "Tk {0:g} er moddhe {1} ta service peyechi.".format(amount, len(results))
    if amount_range:
        answer = "Tk {0:g} theke Tk {1:g} er moddhe {2} ta service peyechi.".format(low_amount, high_amount, len(results))
    return {
        "answer": answer,
        "results": results,
        "llm_enabled": LOCAL_LLM_ENABLED,
        "llm_model": LOCAL_LLM_MODEL,
        "llm_used": False,
    }


def job_budget_answer(question, amount, amount_range=None):
    if amount_range:
        low_amount, high_amount = amount_range
        price_clause = "CAST(Price AS float) BETWEEN ? AND ?"
        params = [low_amount, high_amount]
    else:
        low_amount, high_amount = None, amount
        price_clause = "CAST(Price AS float) <= ?"
        params = [amount]
    rows = _safe_fetch(
        """
        SELECT TOP 12 Jobid, Title, Type, Description, Price, Deadline, Status
        FROM JobsList
        WHERE {0}
        ORDER BY Jobid DESC
        """.format(price_clause),
        params,
    )
    results = []
    for row in rows:
        status = "Active" if str(row.get("Status")).lower() == "true" else _clean_text(row.get("Status") or "Open", 40)
        results.append({
            "type": "Job",
            "title": _clean_text(row.get("Title"), 90),
            "meta": "{0} | Tk {1} | {2}".format(_clean_text(row.get("Type") or "Job", 50), row.get("Price") or 0, status),
            "text": _clean_text(row.get("Description"), 180),
            "url": "/designer/submit?job_id={0}".format(row.get("Jobid")),
        })
    if not results:
        return None
    answer = "Tk {0:g} budget er moddhe {1} ta job/work peyechi.".format(amount, len(results))
    if amount_range:
        answer = "Tk {0:g} theke Tk {1:g} budget er moddhe {2} ta job/work peyechi.".format(low_amount, high_amount, len(results))
    return {
        "answer": answer,
        "results": results,
        "llm_enabled": LOCAL_LLM_ENABLED,
        "llm_model": LOCAL_LLM_MODEL,
        "llm_used": False,
    }


def listing_answer(question):
    category = _find_category(question)
    subcategory = _find_subcategory(question)
    if not any([_is_latest_question(question), _is_cheap_question(question), _is_expensive_question(question), category, subcategory]):
        return None
    if not _has_any(question, PRODUCT_WORDS) and not category and not subcategory:
        return None

    clauses = []
    params = []
    if category:
        clauses.append("P.PCategoryID = ?")
        params.append(category.get("id"))
    if subcategory:
        clauses.append("P.PSubCatID = ?")
        params.append(subcategory.get("id"))
    where = " AND " + " AND ".join(clauses) if clauses else ""
    order_by = "P.PID DESC"
    title = "latest approved product"
    if _is_cheap_question(question):
        order_by = "COALESCE(P.PSelPrice, P.PPrice, 0) ASC, P.PID DESC"
        title = "lowest price product"
    elif _is_expensive_question(question):
        order_by = "COALESCE(P.PSelPrice, P.PPrice, 0) DESC, P.PID DESC"
        title = "highest price product"

    rows = _safe_fetch(
        """
        SELECT TOP 12
            P.PID,
            P.PName,
            P.PSelPrice,
            P.PPrice,
            P.MainItemSellerName,
            CAT.CategoryName,
            SUB.SubcatName,
            I.Name,
            I.Extention
        FROM tblProducts P
        INNER JOIN Productbarcode PB ON PB.Item_Id = P.PID AND PB.Status = 'OK'
        LEFT JOIN Category CAT ON CAT.id = P.PCategoryID
        LEFT JOIN SubCategory SUB ON SUB.id = P.PSubCatID
        LEFT JOIN (
            SELECT PID, MIN(Name) AS Name, MIN(Extention) AS Extention
            FROM tblProductImages
            GROUP BY PID
        ) I ON I.PID = P.PID
        WHERE 1 = 1 {0}
        ORDER BY {1}
        """.format(where, order_by),
        params,
    )
    results = []
    for row in rows:
        price = row.get("PSelPrice") or row.get("PPrice") or 0
        results.append({
            "type": "Product",
            "id": row.get("PID"),
            "title": _clean_text(row.get("PName"), 90),
            "meta": "Tk {0} | {1}".format(price, _clean_text(row.get("CategoryName") or "Product", 60)),
            "text": "Seller: {0}. Subcategory: {1}.".format(
                _clean_text(row.get("MainItemSellerName") or "N/A", 60),
                _clean_text(row.get("SubcatName") or "N/A", 60),
            ),
            "url": "/product/{0}".format(row.get("PID")),
            "image": _product_image(row),
        })
    if not results:
        return None
    scope = "approved"
    if category:
        scope = _clean_text(category.get("CategoryName"), 60)
    if subcategory:
        scope = _clean_text(subcategory.get("SubcatName"), 60)
    return {
        "answer": "{0} er {1} list theke {2} ta result peyechi.".format(scope, title, len(results)),
        "results": results,
        "llm_enabled": LOCAL_LLM_ENABLED,
        "llm_model": LOCAL_LLM_MODEL,
        "llm_used": False,
    }


def search_products(question, terms):
    fields = ["P.PName", "P.MainItemSellerName", "CAT.CategoryName", "SUB.SubcatName"]

    def fetch_product_rows(clause, params):
        return _safe_fetch(
            """
            SELECT TOP 16
                P.PID,
                P.PName,
                P.PSelPrice,
                P.PPrice,
                P.MainItemSellerName,
                CAT.CategoryName,
                SUB.SubcatName,
                I.Name,
                I.Extention
            FROM tblProducts P
            INNER JOIN Productbarcode PB ON PB.Item_Id = P.PID AND PB.Status = 'OK'
            LEFT JOIN Category CAT ON CAT.id = P.PCategoryID
            LEFT JOIN SubCategory SUB ON SUB.id = P.PSubCatID
            LEFT JOIN (
                SELECT PID, MIN(Name) AS Name, MIN(Extention) AS Extention
                FROM tblProductImages
                GROUP BY PID
            ) I ON I.PID = P.PID
            WHERE 1 = 1 {0}
            ORDER BY P.PID DESC
            """.format(clause),
            params,
        )

    clause, params = _and_like_clause(fields, terms)
    rows = fetch_product_rows(clause, params)
    if not rows and terms:
        clause, params = _or_like_clause(fields, terms)
        rows = fetch_product_rows(clause, params)
    if not rows and _has_any(question, PRODUCT_WORDS):
        rows = fetch_product_rows("", [])
    results = []
    for row in rows:
        price = row.get("PSelPrice") or row.get("PPrice") or 0
        results.append({
            "type": "Product",
            "id": row.get("PID"),
            "title": _clean_text(row.get("PName"), 90),
            "meta": "Tk {0} | {1}".format(price, _clean_text(row.get("CategoryName") or "Product", 60)),
            "text": "Seller: {0}. Subcategory: {1}.".format(
                _clean_text(row.get("MainItemSellerName") or "N/A", 60),
                _clean_text(row.get("SubcatName") or "N/A", 60),
            ),
            "url": "/product/{0}".format(row.get("PID")),
            "image": _product_image(row),
        })
    return results


def search_services(question, terms):
    clause, params = _and_like_clause(
        ["O.offer_title", "O.OfferType", "O.about_this_offer1", "O.about_this_offer2"],
        terms,
    )
    rows = _safe_fetch(
        """
        SELECT TOP 8
            O.id,
            O.offer_title,
            O.OfferType,
            O.offer_amount1,
            O.offer_amount2,
            O.offer_amount3,
            O.about_this_offer1,
            U.Username
        FROM OfferDetails O
        LEFT JOIN Users U ON CONVERT(varchar(50), U.UserId) = O.userid
        WHERE 1 = 1 {0}
        ORDER BY O.id DESC
        """.format(clause),
        params,
    )
    results = []
    for row in rows:
        amounts = [row.get("offer_amount1"), row.get("offer_amount2"), row.get("offer_amount3")]
        amounts = [str(item) for item in amounts if item not in (None, "")]
        results.append({
            "type": "Service",
            "title": _clean_text(row.get("offer_title"), 90),
            "meta": "{0} | Package: {1}".format(_clean_text(row.get("OfferType") or "Service", 60), ", ".join(amounts) or "N/A"),
            "text": _clean_text(row.get("about_this_offer1") or "Designer service package.", 180),
            "url": "/designer/offers?offer_id={0}".format(row.get("id")),
        })
    return results


def search_jobs(question, terms):
    clause, params = _and_like_clause(["Title", "Type", "Description", "Location"], terms)
    rows = _safe_fetch(
        """
        SELECT TOP 8 Jobid, Title, Type, Description, Price, Deadline, Status
        FROM JobsList
        WHERE 1 = 1 {0}
        ORDER BY Jobid DESC
        """.format(clause),
        params,
    )
    results = []
    for row in rows:
        status = "Active" if str(row.get("Status")).lower() == "true" else _clean_text(row.get("Status") or "Open", 40)
        results.append({
            "type": "Job",
            "title": _clean_text(row.get("Title"), 90),
            "meta": "{0} | Tk {1} | {2}".format(_clean_text(row.get("Type") or "Job", 50), row.get("Price") or 0, status),
            "text": _clean_text(row.get("Description"), 220),
            "url": "/designer/submit?job_id={0}".format(row.get("Jobid")),
        })
    return results


def search_courses(question, terms):
    clause, params = _and_like_clause(["CourseCategory", "Course", "Name", "VideoLink"], terms)
    rows = _safe_fetch(
        """
        SELECT TOP 8 Id, CourseCategory, Course, Name, VideoLink
        FROM ClassVideo
        WHERE 1 = 1 {0}
        ORDER BY CourseCategory, Id
        """.format(clause),
        params,
    )
    results = []
    for row in rows:
        results.append({
            "type": "Course",
            "title": _clean_text(row.get("Name") or row.get("Course"), 90),
            "meta": _clean_text(row.get("CourseCategory") or row.get("Course") or "Course", 80),
            "text": "YouTube lesson available after student assignment.",
            "url": "/courses/manage?category={0}".format(row.get("CourseCategory") or ""),
        })
    return results


def _context_for_llm(results):
    lines = []
    for index, item in enumerate(results[:12], start=1):
        lines.append(
            "{0}. Type: {1}\nTitle: {2}\nMeta: {3}\nDetails: {4}\nURL: {5}".format(
                index,
                item.get("type", ""),
                item.get("title", ""),
                item.get("meta", ""),
                item.get("text", ""),
                item.get("url", ""),
            )
        )
    return "\n\n".join(lines)


def local_llm_answer(question, results):
    if not LOCAL_LLM_ENABLED or not results:
        return ""

    prompt = """
You are bdallmart.com database assistant.
Answer the user's question using ONLY the database context below.
Use Bangla if the user asks in Bangla, otherwise English.
Do not invent prices, stock, status, links, phone numbers, or records.
If the context does not contain the answer, say that the database result is not enough.
Keep the answer short and useful.

Question:
{question}

Database context:
{context}
""".strip().format(question=question, context=_context_for_llm(results))

    payload = {
        "model": LOCAL_LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 220,
        },
    }

    request = Request(
        LOCAL_LLM_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, ValueError):
        return ""

    return _clean_text(data.get("response"), 900)


def answer_question(question):
    question = str(question or "").strip()
    if not question:
        return {
            "answer": "Please type a question about products, services, courses, jobs, or orders.",
            "results": [],
            "llm_enabled": LOCAL_LLM_ENABLED,
            "llm_model": LOCAL_LLM_MODEL,
            "llm_used": False,
        }

    aggregate = aggregate_answer(question)
    if aggregate:
        return aggregate

    priced = price_answer(question)
    if priced:
        return priced

    listed = listing_answer(question)
    if listed:
        return listed

    terms = _terms(question)
    if not terms:
        terms = [question[:40]]

    results = []
    results.extend(search_products(question, terms))
    results.extend(search_services(question, terms))
    results.extend(search_jobs(question, terms))
    results.extend(search_courses(question, terms))

    if not results:
        return {
            "answer": "I could not find a matching record in the database. Try product name, category, service type, course category, or job title.",
            "results": [],
            "llm_enabled": LOCAL_LLM_ENABLED,
            "llm_model": LOCAL_LLM_MODEL,
            "llm_used": False,
        }

    grouped = {}
    for item in results:
        grouped[item["type"]] = grouped.get(item["type"], 0) + 1

    summary = ", ".join("{0} {1}".format(count, label.lower()) for label, count in grouped.items())
    top = results[0]
    answer = "I found {0} from the database. Best match: {1} ({2}).".format(summary, top["title"], top["type"])
    if top.get("meta"):
        answer += " {0}".format(top["meta"])

    generated = local_llm_answer(question, results)
    if generated:
        answer = generated

    return {
        "answer": answer,
        "results": results[:16],
        "llm_enabled": LOCAL_LLM_ENABLED,
        "llm_model": LOCAL_LLM_MODEL,
        "llm_used": bool(generated),
    }
