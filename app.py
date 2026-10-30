from functools import wraps
from uuid import uuid4
from course_content import sanitize_course_content
from course_service import get_public_course_videos, get_public_course_video
import html
import hmac
import os
import re
from pathlib import Path
from datetime import date, timedelta
from urllib.parse import urlencode, unquote, urljoin

from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, send_from_directory, session, url_for

from admin_service import (
    approve_product_barcode,
    assign_order_to_delivery_man,
    get_admin_dashboard_summary,
    delete_pending_product,
    get_admin_module_data,
)
from auth_service import authenticate, create_user, dashboard_endpoint_for, normalize_category, phone_exists, user_exists
from checkout_service import create_or_update_customer, find_customer_by_mobile, save_checkout_order
from config import Config
from course_service import (
    add_course_video,
    assign_videos_to_student,
    delete_course_video,
    enroll_student,
    get_course_categories,
    get_course_names,
    get_course_video_groups,
    get_course_videos,
    get_reference_users,
    get_student,
    get_student_assigned_videos,
    get_student_for_user,
    get_students,
)
from customer_service import (
    CUSTOMER_MENU,
    DESIGN_TYPES,
    create_customer_product,
    create_customer_job,
    get_customer_job,
    get_customer_jobs,
    get_customer_messages,
    get_tracking_order_details,
    get_tracking_orders,
    get_customer_products,
    get_customer_profile,
    get_customer_submissions,
    get_customer_summary,
    get_product_form_options,
    get_ecommerce_orders,
    get_job_sample_images,
    send_customer_message,
    update_customer_password,
    update_customer_job,
    update_customer_profile,
    update_submission_review,
)
from designer_service import (
    DESIGNER_MENU,
    PACKAGE_FEATURES,
    add_affiliate_product,
    create_submission,
    create_designer_product,
    create_service_order,
    get_affiliate_products,
    get_all_designs,
    get_categories,
    get_designer_messages,
    get_designer_offers,
    get_designer_orders,
    get_designer_products,
    get_designer_expertise,
    get_designer_profile,
    get_designer_public_profile,
    get_designer_tracking_order_details,
    get_designer_tracking_orders,
    get_designer_summary,
    get_job,
    get_my_submissions,
    get_offer_categories,
    get_offer_images,
    get_public_offer,
    get_open_jobs,
    get_open_job_type_summary,
    get_service_types,
    get_subcategories,
    product_image_path,
    save_designer_offer,
    offer_package_amount,
    search_products,
    update_designer_expertise,
    update_designer_password,
    update_designer_profile,
    user_picture_data_url,
)
from delivery_service import (
    DELIVERY_MENU,
    DELIVERY_STATUSES,
    get_delivery_orders,
    get_delivery_profile,
    get_delivery_summary,
    update_delivery_order_status,
)
from ecommerce_admin_service import (
    delete_admin_product,
    delete_lookup,
    ecommerce_setup_links,
    get_admin_product,
    get_admin_product_count,
    get_admin_products,
    get_lookup_row,
    get_lookup_rows,
    get_product_images,
    get_product_options,
    get_product_sizes,
    lookup_module,
    save_admin_product,
    save_lookup,
)
from product_service import (
    get_category_details,
    get_category_products,
    get_category_shortcuts,
    get_home_product_sections,
    get_product_details,
    get_subcategory_details,
)
from pos_service import get_pos_order, get_pos_sales_report, save_pos_order
from rag_service import answer_question
from support_chat_service import (
    add_customer_message,
    add_support_reply,
    create_support_request,
    get_support_messages,
    get_support_request,
    get_support_requests,
    save_support_feedback,
    update_support_assignment,
)


app = Flask(__name__)
app.config.from_object(Config)

# Additive unified marketplace; all previous URLs remain registered below.
from market_routes import market, public_home_jobs
app.register_blueprint(market)
from special_orders import special_orders, service_types as special_service_types
app.register_blueprint(special_orders)
from workspace_theme import register_workspace_theme
register_workspace_theme(app)
from job_permissions import can_post as can_post_jobs, can_apply as can_apply_jobs


@app.before_request
def configure_course_editor_request_limits():
    if request.endpoint == "course_manage":
        # Rich HTML descriptions can exceed Flask's 500 KB form-field default.
        # Set this before request.values/request.form starts parsing the body.
        request.max_form_memory_size = 10 * 1024 * 1024
        request.max_content_length = 32 * 1024 * 1024


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def legacy_asset_url(asset_path, fallback="ProductImage/download.jpg"):
    path = str(asset_path or "").strip()
    if not path:
        path = fallback
    path = path.replace("\\", "/").replace("~//", "").replace("~/", "").lstrip("/")
    while path.startswith("../"):
        path = path[3:]
    while "//" in path:
        path = path.replace("//", "/")
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("sf/"):
        return "/" + path
    if path.startswith("legacy-assets/"):
        path = path[len("legacy-assets/"):]
    static_asset_roots = ("ProductImage", "CatagoryImage", "SubCatagoryImage")
    if path in static_asset_roots or any(path.startswith(root + "/") for root in static_asset_roots):
        return url_for("static", filename=path or fallback)
    return url_for("legacy_assets", asset_path=path or fallback)


def public_url(path):
    path = str(path or "").strip()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base_url = getattr(Config, "PUBLIC_BASE_URL", "").strip()
    if base_url:
        return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    return urljoin(request.url_root, path.lstrip("/"))


def legacy_asset_external_url(asset_path, fallback="ProductImage/download.jpg"):
    path = str(asset_path or "").strip()
    if not path:
        path = fallback
    path = path.replace("\\", "/").replace("~//", "").replace("~/", "").lstrip("/")
    while path.startswith("../"):
        path = path[3:]
    while "//" in path:
        path = path.replace("//", "/")
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("sf/"):
        return "/" + path
    if path.startswith("legacy-assets/"):
        path = path[len("legacy-assets/"):]
    static_asset_roots = ("ProductImage", "CatagoryImage", "SubCatagoryImage")
    if path in static_asset_roots or any(path.startswith(root + "/") for root in static_asset_roots):
        return public_url(url_for("static", filename=path or fallback))
    return public_url(url_for("legacy_assets", asset_path=path or fallback))


def product_cart_image(product):
    images = product.get("images") or []
    if images:
        return images[0]
    return product.get("image") or "ProductImage/download.jpg"


def get_cart_items(refresh_from_db=True):
    cart = session.get("cart", {})
    items = []
    changed = False

    for key, cart_item in cart.items():
        item = dict(cart_item)
        try:
            item["quantity"] = int(item.get("quantity", 0))
        except (TypeError, ValueError):
            item["quantity"] = 1

        if refresh_from_db:
            try:
                product = get_product_details(int(item.get("id") or key))
            except (TypeError, ValueError):
                product = None
            except Exception:
                product = None

            if product:
                affiliate_price = item.get("affiliate_price")
                fresh_item = {
                    "id": product["id"],
                    "name": product["name"],
                    "price": affiliate_price or product["price"],
                    "image": product_cart_image(product),
                    "seller": product["seller"],
                    "commission": product.get("commission", "0"),
                    "quantity": item["quantity"],
                }
                for field in ("affiliate_user_id", "affiliate_username", "affiliate_price", "affiliate_commission_percent"):
                    if item.get(field):
                        fresh_item[field] = item.get(field)
                if fresh_item != cart_item:
                    cart[key] = fresh_item
                    item = fresh_item
                    changed = True

        items.append(item)

    if changed:
        session["cart"] = cart

    return items


def cart_totals(items):
    count = sum(int(item.get("quantity", 0)) for item in items)
    total = sum(float(item.get("price", 0)) * int(item.get("quantity", 0)) for item in items)
    return count, total


def referral_profile_from_cookie():
    referral_username = str(request.cookies.get("as_ref_user") or "").strip()
    if not referral_username:
        return None
    try:
        return get_designer_public_profile(referral_username)
    except Exception:
        return None


def checkout_affiliate_user():
    referral_profile = referral_profile_from_cookie()
    if referral_profile:
        return str(referral_profile.get("Username") or "hbanucu")
    return "hbanucu"


def referral_response(template_name, profile, **context):
    response = make_response(render_template(template_name, profile=profile, **context))
    response.set_cookie("as_ref_user", str(profile.get("Username") or ""), max_age=60 * 60 * 24 * 180, samesite="Lax")
    response.set_cookie("as_ref_user_id", str(profile.get("UserId") or ""), max_age=60 * 60 * 24 * 180, samesite="Lax")
    return response


@app.context_processor
def inject_cart_summary():
    cart_items = get_cart_items()
    count, total = cart_totals(cart_items)
    cart_state = request.args.get("cart")

    def cart_state_url(state):
        args = request.args.to_dict(flat=True)
        if state:
            args["cart"] = state
        else:
            args.pop("cart", None)
        query = urlencode(args)
        return request.path + (("?" + query) if query else "")

    dashboard_url = ""
    if session.get("user_id"):
        dashboard_url = url_for(dashboard_endpoint_for(session.get("category")))

    return {
        "cart_count": count,
        "cart_total": total,
        "cart_items": cart_items,
        "show_cart_drawer": cart_state == "open",
        "cart_drawer_peek": cart_state == "peek",
        "cart_state_url": cart_state_url,
        "can_add_profile_product": can_add_profile_product(),
        "user_dashboard_url": dashboard_url,
    }


@app.template_filter("legacy_asset")
def legacy_asset_filter(asset_path):
    return legacy_asset_url(asset_path)


@app.template_filter("product_image")
def product_image_filter(row):
    return product_image_path(row)


@app.template_filter("user_picture")
def user_picture_filter(profile):
    return user_picture_data_url(profile)


@app.template_filter("decode_html")
def decode_html_filter(value):
    text = str(value or "")
    for _ in range(5):
        previous = text
        try:
            text = unquote(text)
        except Exception:
            pass
        text = html.unescape(text)
        if text == previous:
            break
    return text


@app.template_filter("plain_product_text")
def plain_product_text_filter(value):
    text = decode_html_filter(value)
    text = re.sub(r"(?is)<\s*(script|style).*?>.*?<\s*/\s*\1\s*>", "", text)
    text = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", text)
    text = re.sub(r"(?i)</\s*(p|div|li|tr|h[1-6])\s*>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


USER_CATEGORIES = [
    ("Customer", "Customer"),
    ("Vendor", "Vendor / Seller"),
    ("Designer", "Freelancer / Service Provider"),
    ("Institute", "Institute — Approval Required"),
    ("Student", "Student"),
]


SERVICE_ITEMS = [
    ("Web & Software", "Business website, ecommerce setup, and custom software."),
    ("Graphic Design", "Logo, banner, product image, and branding support."),
    ("Digital Marketing", "Campaign setup, lead generation, and marketplace promotion."),
    ("Training & Course", "Institute course sales, student admission, and class videos."),
    ("Delivery Support", "Order assignment, delivery confirmation, and status tracking."),
    ("Freelance Jobs", "Buyer job posts, proposals, submissions, and approvals."),
]





DASHBOARD_CONFIG = {
    "Admin": {
        "accent": "Platform control",
        "stats": [("24", "New Orders"), ("08", "Pending Users"), ("16", "Active Vendors"), ("Tk 42K", "Today Sales")],
        "actions": ["Approve Users", "Review Orders", "Manage Modules", "Payment Reports"],
        "activity": ["New vendor registration waiting for approval.", "Checkout order created from Python module.", "Course dashboard content needs review."],
        "menu": [
            ("Dashboard", "/dashboard"),
            ("POS Sale", "/pos"),
            ("POS Reports", "/pos/reports"),
            ("Customer Order", "/UserUI/OrderDetails.aspx"),
            ("Delivery Man", "/UserUI/ToDeliveryman.aspx"),
            ("My Jobs", "/UserUI/MyJobs.aspx"),
            ("My Profile", "/UserUI/Account.aspx"),
            ("Jobs Post", "/UserUI/ShowAllSubmission.aspx"),
            ("Expend Amount", "/UserUI/PaymentDetails.aspx"),
            ("Show all order", "/UserUI/ShowOrder.aspx"),
            ("Order Approve", "/UserUI/Ordercheckforadmin.aspx"),
            ("CustomerOrder Place", "/UserUI/CustomerOrderPlaceForAdmin.aspx"),
            ("Payment Details", "/UserUI/PaymentDetails.aspx"),
            ("Payment Withdrow Request", "/UserUI/PaymentWithdrow.aspx"),
            ("Submited Work", "/UserUI/AdminSubmissionDetails.aspx"),
            ("View Design", "/UserUI/AdminViewDesign.aspx"),
            ("CPA Offer", "/EcommerceUI/CPA_Offer/OfferSend.aspx"),
            ("Message", "/UserUI/SendReceiveMessage.aspx"),
            ("Message Approve", "/UserUI/MessagecheckForAdmin.aspx"),
            ("All Customer Earning", "/UserUI/CustomerEarning.aspx"),
            ("View Information", "/UserUI/ViewInformation.aspx"),
            ("Product List", "/UserUI/ProductList.aspx"),
            ("Account Info", "/UserUI/AccountInfo.aspx"),
            ("Upload Instruction", "/UserUI/InstructionUpload.aspx"),
            ("Upload Video", "/UserUI/ClassVideo.aspx"),
            ("Video For Student", "/UserUI/StudentVideos.aspx"),
            ("Assignment Work", "/UserUI/StudentWorkList.aspx"),
        ],
        "menu_groups": [
            ("Main", [
                ("Dashboard", "/dashboard"),
                ("My Profile", "/UserUI/Account.aspx"),
                ("Account Info", "/UserUI/AccountInfo.aspx"),
                ("View Information", "/UserUI/ViewInformation.aspx"),
            ]),
            ("Ecommerce", [
                ("POS Sale", "/pos"),
                ("POS Reports", "/pos/reports"),
                ("Customer Order", "/UserUI/OrderDetails.aspx"),
                ("Show all order", "/UserUI/ShowOrder.aspx"),
                ("Order Approve", "/UserUI/Ordercheckforadmin.aspx"),
                ("CustomerOrder Place", "/UserUI/CustomerOrderPlaceForAdmin.aspx"),
                ("Delivery Man", "/UserUI/ToDeliveryman.aspx"),
                ("Product List", "/UserUI/ProductList.aspx"),
            ]),
            ("Freelance & Service", [
                ("My Jobs", "/UserUI/MyJobs.aspx"),
                ("Jobs Post", "/UserUI/ShowAllSubmission.aspx"),
                ("Submited Work", "/UserUI/AdminSubmissionDetails.aspx"),
                ("View Design", "/UserUI/AdminViewDesign.aspx"),
                ("CPA Offer", "/EcommerceUI/CPA_Offer/OfferSend.aspx"),
            ]),
            ("Payments", [
                ("Expend Amount", "/UserUI/PaymentDetails.aspx"),
                ("Payment Details", "/UserUI/PaymentDetails.aspx"),
                ("Payment Withdrow Request", "/UserUI/PaymentWithdrow.aspx"),
                ("All Customer Earning", "/UserUI/CustomerEarning.aspx"),
            ]),
            ("Messages", [
                ("Message", "/UserUI/SendReceiveMessage.aspx"),
                ("Message Approve", "/UserUI/MessagecheckForAdmin.aspx"),
            ]),
            ("Course & Training", [
                ("Upload Instruction", "/UserUI/InstructionUpload.aspx"),
                ("Upload Video", "/courses/manage"),
                ("Video For Student", "/courses/assign"),
                ("Assignment Work", "/UserUI/StudentWorkList.aspx"),
            ]),
        ],
    },
    "Customer": {
        "accent": "Shopping and service center",
        "stats": [("03", "Open Orders"), ("02", "Messages"), ("01", "Active Course"), ("05", "Saved Items")],
        "actions": ["Track Order", "Message Seller", "Browse Courses", "Post Service Request"],
        "activity": ["Your latest cart items are ready for checkout.", "A seller reply will appear in Messages.", "Course purchase history will connect next."],
        "menu": CUSTOMER_MENU,
    },
    "Vendor": {
        "accent": "Seller operations",
        "stats": [("18", "Products"), ("07", "Pending Orders"), ("Tk 12K", "Sales"), ("04", "Delivery Ready")],
        "actions": ["Add Product", "Update Stock", "Process Orders", "View Payments"],
        "activity": ["New product approval flow is ready to connect.", "Order status can be managed from this module.", "Delivery assignment will be added later."],
    },
    "Freelancer": {
        "accent": "Designer workspace",
        "stats": [("0", "Open Jobs"), ("0", "Submissions"), ("0", "Selected"), ("Tk 0", "Earnings")],
        "actions": ["Work Order List", "Submit Design", "My Designs", "Client Messages"],
        "activity": ["Open jobs load from JobsList.", "Submitted designs save into Submission.", "Orders and messages read from the old Designer tables."],
        "menu": DESIGNER_MENU,
    },
    "Course": {
        "accent": "Learning management",
        "stats": [("09", "Courses"), ("42", "Students"), ("05", "Lessons"), ("03", "Assignments")],
        "actions": ["Create Course", "Upload Lesson", "Assign Student", "Review Assignment"],
        "activity": ["Course sales management will use this dashboard.", "Student access control is prepared.", "Video lesson module can be added next."],
        "menu": [
            ("Course Dashboard", "/dashboards/course"),
            ("Enroll Student", "/courses/students"),
            ("Add Course Video", "/courses/manage"),
            ("Assign Student Video", "/courses/assign"),
            ("My Courses", "/courses/my"),
        ],
    },
    "Delivery Man": {
        "accent": "Delivery workflow",
        "stats": [("05", "Assigned"), ("02", "Picked Up"), ("03", "Delivered"), ("01", "Pending Issue")],
        "actions": ["View Assignment", "Update Status", "Confirm Delivery", "Delivery History"],
        "activity": ["Order delivery status can be updated here.", "Customer confirmation flow will connect with SMS.", "Completed delivery history will appear after order module."],
    },
    "POS": {
        "accent": "POS counter",
        "stats": [("POS", "Counter Module"), ("Sale", "Product Sale"), ("Report", "Sales Report"), ("Print", "Receipt")],
        "actions": ["Open POS Sale", "View POS Reports", "Print Receipt", "Check Product Sales"],
        "activity": ["POS user can sell products from Python POS.", "Date-to-date POS report is connected.", "Receipt print opens after sale save."],
        "menu": [
            ("POS Dashboard", "/dashboards/pos"),
            ("POS Sale", "/pos"),
            ("POS Reports", "/pos/reports"),
            ("Marketplace", "/login"),
        ],
    },
}


DEFAULT_DASHBOARD_MENU = [
    ("Dashboard", "/dashboard"),
    ("POS Sale", "/pos"),
    ("POS Reports", "/pos/reports"),
    ("Orders", "#"),
    ("Products", "#"),
    ("Services", "#"),
    ("Courses", "#"),
    ("Messages", "#"),
    ("Payments", "#"),
]


def dashboard_payload(role):
    payload = dict(DASHBOARD_CONFIG.get(role, DASHBOARD_CONFIG["Customer"]))
    payload.setdefault("menu", DEFAULT_DASHBOARD_MENU)
    if role == "Customer" and not can_post_jobs(session.get("category")):
        payload["menu"] = [(label,href) for label,href in payload["menu"] if href not in {"/customer/post-job","/customer/jobs","/customer/submissions"}]
    if role == "Freelancer" and not can_apply_jobs(session.get("category")):
        payload["menu"] = [(label,href) for label,href in payload["menu"] if href not in {"/designer/jobs","/designer/submit","/designer/submissions","/designer/status","/designer/designs"}]
    if role == "Admin":
        payload["menu_groups"] = build_admin_menu_groups()
    return payload


ADMIN_MODULE_GROUPS = [
    ("Main", [
        ("Dashboard", "overview", "Python dashboard overview"),
        ("My Profile", "profile", "UserUI/Account.aspx"),
        ("Account Info", "account-info", "UserUI/AccountInfo.aspx"),
        ("View Information", "view-information", "UserUI/ViewInformation.aspx"),
    ]),
    ("Ecommerce", [
        ("POS Sale", "pos-sale", "Python POS sale"),
        ("POS Reports", "pos-reports", "Python POS sales reporting dashboard"),
        ("Add Brand", "ecommerce-setup/brand", "EcommerceUI/AddBrand.aspx"),
        ("Add Category", "ecommerce-setup/category", "EcommerceUI/Addcategory.aspx"),
        ("Add Sub-category", "ecommerce-setup/subcategory", "EcommerceUI/AddSubCategory.aspx"),
        ("Add Gender", "ecommerce-setup/gender", "EcommerceUI/AddGender.aspx"),
        ("Add Sizes", "ecommerce-setup/size", "EcommerceUI/AddSize.aspx"),
        ("Add Product", "ecommerce-setup/product", "EcommerceUI/AddProduct.aspx"),
        ("Customer Order", "customer-order", "UserUI/OrderDetails.aspx"),
        ("Show all order", "all-orders", "UserUI/ShowOrder.aspx"),
        ("Order Approve", "order-approve", "UserUI/Ordercheckforadmin.aspx"),
                ("CustomerOrder Place", "customer-order-place", "UserUI/CustomerOrderPlaceForAdmin.aspx"),
                ("Delivery Man", "delivery-man", "UserUI/ToDeliveryman.aspx"),
                ("Product Barcode", "product-barcode", "EcommerceUI/Productbarcode.aspx"),
                ("Product List", "product-list", "UserUI/ProductList.aspx"),
            ]),
    ("Freelance & Service", [
        ("My Jobs", "my-jobs", "UserUI/MyJobs.aspx"),
        ("Jobs Post", "jobs-post", "UserUI/ShowAllSubmission.aspx"),
        ("Submited Work", "submitted-work", "UserUI/AdminSubmissionDetails.aspx"),
        ("View Design", "view-design", "UserUI/AdminViewDesign.aspx"),
        ("CPA Offer", "cpa-offer", "EcommerceUI/CPA_Offer/OfferSend.aspx"),
    ]),
    ("Payments", [
        ("Expend Amount", "expend-amount", "UserUI/PaymentDetails.aspx"),
        ("Payment Details", "payment-details", "UserUI/PaymentDetails.aspx"),
        ("Payment Withdrow Request", "payment-withdraw", "UserUI/PaymentWithdrow.aspx"),
        ("All Customer Earning", "customer-earning", "UserUI/CustomerEarning.aspx"),
    ]),
    ("Messages", [
        ("Customer Chat", "customer-chat", "Python customer support chat"),
        ("Message", "message", "UserUI/SendReceiveMessage.aspx"),
        ("Message Approve", "message-approve", "UserUI/MessagecheckForAdmin.aspx"),
    ]),
    ("Course & Training", [
        ("Upload Instruction", "upload-instruction", "UserUI/InstructionUpload.aspx"),
        ("Upload Video", "upload-video", "UserUI/ClassVideo.aspx"),
        ("Video For Student", "student-videos", "UserUI/StudentVideos.aspx"),
        ("Assignment Work", "assignment-work", "UserUI/StudentWorkList.aspx"),
    ]),
]


def build_admin_menu_groups():
    groups = []
    for group_title, items in ADMIN_MODULE_GROUPS:
        groups.append((
            group_title,
            [
                (
                    label,
                    "/dashboard" if slug == "overview"
                    else "/pos" if slug == "pos-sale"
                    else "/pos/reports" if slug == "pos-reports"
                    else "/dashboards/admin/{0}".format(slug),
                )
                for label, slug, _ in items
            ],
        ))
    return groups


def admin_module_for(slug):
    slug = slug or "overview"
    for group_title, items in ADMIN_MODULE_GROUPS:
        for label, item_slug, source in items:
            if item_slug == slug:
                return {
                    "group": group_title,
                    "label": label,
                    "slug": item_slug,
                    "source": source,
                    "summary": "This admin menu is now connected inside the Python dashboard.",
                }
    return None


def build_pos_products(sections):
    products = []
    seen = set()
    for section in sections:
        category = str(section.get("title") or "Products").strip()
        for product in section.get("products") or []:
            product_id = str(product.get("id") or product.get("PID") or product.get("name") or "").strip()
            if not product_id:
                product_id = "{0}-{1}".format(category, len(products) + 1)
            if product_id in seen:
                continue
            seen.add(product_id)
            try:
                price = float(str(product.get("price") or "0").replace(",", ""))
            except (TypeError, ValueError):
                price = 0.0
            products.append({
                "id": product_id,
                "barcode": product_id,
                "name": str(product.get("name") or "Product").strip(),
                "price": price,
                "price_text": "{0:.2f}".format(price),
                "category": category,
                "image": legacy_asset_url(product.get("image")),
            })
    return products


def safe_next_url(value):
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return None


PROFILE_PRODUCT_ROLES = {"customer", "designer", "freelancer", "vendor", "seller", "buyer", "user", "institute", "instructor", "student", "admin"}


def can_add_profile_product():
    if not session.get("user_id"):
        return False
    return normalize_category(session.get("category")) in PROFILE_PRODUCT_ROLES


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    normalized_roles = {normalize_category(role) for role in roles}

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            category = normalize_category(session.get("category"))
            # A single commercial account can use both established workspaces.
            commercial = {"customer", "designer", "freelancer", "vendor", "seller", "buyer", "user", "institute", "instructor", "student"}
            shared_workspace = bool(normalized_roles & {"customer", "designer", "freelancer", "student"})
            permitted = category == "admin" or category in normalized_roles or (shared_workspace and category in commercial)
            if not permitted:
                target_endpoint = dashboard_endpoint_for(session.get("category"))
                if target_endpoint == view.__name__:
                    session.clear()
                    return redirect(url_for("login"))
                return redirect(url_for(target_endpoint))
            return view(*args, **kwargs)

        return wrapped

    return decorator


@app.route("/legacy-assets/<path:asset_path>")
def legacy_assets(asset_path):
    return send_from_directory(Config.PROJECT_ROOT, asset_path)


def get_home_slider_images():
    slider_dir = Path(app.static_folder or "") / "slider"
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    if not slider_dir.exists():
        return []
    return [
        "slider/{0}".format(path.name)
        for path in sorted(slider_dir.iterdir(), key=lambda item: item.name.lower())
        if path.is_file() and path.suffix.lower() in allowed
    ]


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for(dashboard_endpoint_for(session.get("category"))))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_name = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        next_url = safe_next_url(request.form.get("next", ""))
        user, error = authenticate(login_name, password)

        if error:
            flash(error, "error")
        else:
            preserved_cart = session.get("cart", {})
            session.clear()
            if preserved_cart:
                session["cart"] = preserved_cart
            session["user_id"] = str(user["UserId"])
            session["username"] = str(user["Username"])
            session["category"] = str(user["UserCatagory"])
            session["admin_status"] = str(user.get("AdminStatus") or "")
            session["email"] = str(user.get("Email") or "")
            session["phone"] = str(user.get("Phone") or "")
            flash("Welcome back, {0}.".format(user["Username"]), "success")
            return redirect(next_url or url_for(dashboard_endpoint_for(user["UserCatagory"])))

    return render_template(
        "login.html",
        training_courses=get_public_course_videos(),
        categories=get_category_shortcuts(),
        sections=get_home_product_sections(),
        slider_images=get_home_slider_images(),
        services=SERVICE_ITEMS,
        market_jobs=public_home_jobs(),
        special_service_types=special_service_types(),
        next_url=safe_next_url(request.args.get("next", "")) or "",
    )


@app.route('/UserUI/JobsDetails.aspx')
@app.route('/JobDetails.aspx')
def legacy_job_details():
    # Original pages used different casing for id; the database decides Bid/Contest.
    raw = next((value for key,value in request.args.items() if key.lower()=='id'), '')
    if not raw.isdecimal() or int(raw)<=0:
        from flask import abort
        abort(400)
    return redirect(url_for('market.existing_job_detail',job_id=int(raw)))


@app.route('/UserUI/Submission.aspx')
def legacy_contest_submission():
    raw=next((v for k,v in request.args.items() if k.lower()=='id'),'')
    if not raw.isdecimal() or int(raw)<=0:
        from flask import abort
        abort(400)
    return redirect(url_for('designer_workspace',section='submit',job_id=int(raw),workspace=1))


@app.route("/ask")
def ask_chat():
    question = request.args.get("q", "").strip()
    payload = answer_question(question) if question else {"answer": "", "results": []}
    return render_template(
        "rag_chat.html",
        title="Ask bdallmart.com",
        question=question,
        answer=payload["answer"],
        results=payload["results"],
        llm_enabled=payload.get("llm_enabled"),
        llm_model=payload.get("llm_model"),
        llm_used=payload.get("llm_used"),
        categories=get_category_shortcuts(),
    )


@app.route("/pos")
@role_required("POS", "Admin")
def pos_sale():
    products = build_pos_products(get_home_product_sections())
    return render_template(
        "pos_sale.html",
        title="POS Sale",
        products=products,
        pos_categories=sorted({product["category"] for product in products}),
        selected_employee=session.get("username") or "Sales Employee",
        current_date=date.today().strftime("%d/%m/%Y"),
    )


@app.route("/api/pos/sale", methods=["POST", "OPTIONS"])
@role_required("POS", "Admin")
def pos_sale_api():
    if request.method == "OPTIONS":
        return jsonify({"ok": True})
    data = request.get_json(silent=True) or request.form
    try:
        order_id = save_pos_order(
            data.get("items") or [],
            customer=data.get("customer") or {},
            sales_employee=data.get("sales_employee") or session.get("username") or "POS",
            status="POS Sale",
        )
        return jsonify({
            "ok": True,
            "order_id": order_id,
            "report_url": url_for("pos_sale_report", order_id=order_id),
            "message": "POS sale saved successfully. Order ID: {0}".format(order_id),
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400


@app.route("/pos/report/<order_id>")
@role_required("POS", "Admin")
def pos_sale_report(order_id):
    order = get_pos_order(order_id)
    if not order:
        return render_template("pos_report.html", title="POS Report", order=None), 404
    return render_template("pos_report.html", title="POS Report", order=order)


@app.route("/pos/reports")
@role_required("POS", "Admin")
def pos_sales_reports():
    today = date.today()
    default_from = today - timedelta(days=30)
    date_from = request.args.get("date_from") or default_from.isoformat()
    date_to = request.args.get("date_to") or today.isoformat()
    try:
        report = get_pos_sales_report(date_from, date_to)
        error = ""
    except Exception as exc:
        report = {"summary": {}, "categories": [], "products": [], "top_products": [], "daily_sales": []}
        error = str(exc)
    report["max_top_qty"] = max([int(row.get("TotalQty") or 0) for row in report.get("top_products", [])] or [1])
    report["max_daily_sales"] = max([float(row.get("TotalSales") or 0) for row in report.get("daily_sales", [])] or [1])
    report["max_category_sales"] = max([float(row.get("TotalSales") or 0) for row in report.get("categories", [])] or [1])
    role = "Admin" if normalize_category(session.get("category")) == "admin" else "POS"
    return render_template(
        "pos_reports.html",
        title="POS Sales Reports",
        role=role,
        date_from=date_from,
        date_to=date_to,
        report=report,
        error=error,
        **dashboard_payload(role),
    )


@app.route("/api/rag-chat", methods=["POST", "OPTIONS"])
def rag_chat_api():
    if request.method == "OPTIONS":
        return jsonify({"ok": True})
    data = request.get_json(silent=True) or request.form
    question = str(data.get("question") or data.get("q") or "").strip()
    return jsonify(answer_question(question))


@app.route("/api/support-chat/request", methods=["POST", "OPTIONS"])
def support_chat_request_api():
    if request.method == "OPTIONS":
        return jsonify({"ok": True})
    data = request.get_json(silent=True) or request.form
    try:
        request_id = create_support_request(
            data.get("name") or session.get("username") or "",
            data.get("contact_no") or data.get("phone") or session.get("phone") or "",
            data.get("address") or "",
            data.get("question") or data.get("message") or "",
            data.get("issue_type") or "Talk to agent",
            data.get("email") or session.get("email") or "",
            data.get("order_id") or "",
            data.get("attachment_url") or "",
        )
        return jsonify({
            "ok": True,
            "request_id": request_id,
            "message": "Customer service request #{0} created. Representative will reply soon.".format(request_id),
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400


@app.route("/api/support-chat/thread/<int:request_id>/feedback", methods=["POST", "OPTIONS"])
def support_chat_feedback_api(request_id):
    if request.method == "OPTIONS":
        return jsonify({"ok": True})
    support_request = get_support_request(request_id)
    if not support_request:
        return jsonify({"ok": False, "message": "Support request not found."}), 404
    data = request.get_json(silent=True) or request.form
    try:
        save_support_feedback(request_id, data.get("rating"), data.get("comment") or "")
        return jsonify({
            "ok": True,
            "message": "Thanks for your feedback.",
            "request": get_support_request(request_id),
            "messages": get_support_messages(request_id),
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400


@app.route("/api/support-chat/thread/<int:request_id>", methods=["GET", "OPTIONS"])
def support_chat_thread_api(request_id):
    if request.method == "OPTIONS":
        return jsonify({"ok": True})
    try:
        support_request = get_support_request(request_id)
        if not support_request:
            return jsonify({"ok": False, "message": "Support request not found."}), 404
        return jsonify({
            "ok": True,
            "request": support_request,
            "messages": get_support_messages(request_id),
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400


@app.route("/api/support-chat/thread/<int:request_id>/message", methods=["POST", "OPTIONS"])
def support_chat_message_api(request_id):
    if request.method == "OPTIONS":
        return jsonify({"ok": True})
    try:
        support_request = get_support_request(request_id)
        if not support_request:
            return jsonify({"ok": False, "message": "Support request not found."}), 404
        data = request.get_json(silent=True) or request.form
        add_customer_message(
            request_id,
            data.get("name") or session.get("username") or support_request.get("CustomerName") or support_request.get("ContactNo"),
            data.get("message") or data.get("question") or "",
        )
        return jsonify({
            "ok": True,
            "message": "Message sent to customer service.",
            "request": get_support_request(request_id),
            "messages": get_support_messages(request_id),
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400


@app.route("/register", methods=["GET", "POST"])
def register():
    referral_profile = referral_profile_from_cookie() or {}
    reference = (
        str(referral_profile.get("Username") or "").strip()
        or "ptifood"
    )
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        category = request.form.get("category", "Customer")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if category not in {key for key, label in USER_CATEGORIES}:
            flash("Please select a valid account category.", "error")
        elif not username or not email or not password:
            flash("Username, email, and password are required.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        elif user_exists(username, email):
            flash("Username or email already exists.", "error")
        elif phone_exists(phone):
            flash("Phone number already exists. Please login with this phone number.", "error")
        else:
            # Institute approval is requested from the unified profile. Do not grant
            # legacy instructor/staff rights through a public registration form.
            create_user(username, email, phone, password, "Customer" if category == "Institute" else category, reference)
            if category == "Institute":
                flash("Account created. Login and request Institute approval from Profile & Features.", "success")
            else:
                flash("Account created successfully. You can login now.", "success")
            return redirect(url_for("login", next=request.args.get("next", "")))

    return render_template("register.html", categories=USER_CATEGORIES, reference=reference)


@app.route("/category/<int:category_id>")
def category_products(category_id):
    subcategory_id = request.args.get("sub")
    try:
        category = get_category_details(category_id)
    except Exception:
        category = None

    if not category:
        category = {
            "id": str(category_id),
            "name": "Category {0}".format(category_id),
            "description": "Database is temporarily unavailable or this category was not found.",
            "image": "CatagoryImage/48.png",
        }

    try:
        subcategory = get_subcategory_details(subcategory_id) if subcategory_id else None
    except Exception:
        subcategory = None

    try:
        products = get_category_products(category_id, subcategory_id)
    except Exception:
        products = []

    try:
        categories = get_category_shortcuts()
    except Exception:
        categories = []

    active_subcategories = []
    for item in categories:
        if item["id"] == str(category_id):
            active_subcategories = item.get("subcategories", [])
            break

    return render_template(
        "category_products.html",
        training_courses=get_public_course_videos() if any(str((item or {}).get('name', '')).strip().lower() == 'training' for item in [category, subcategory]) else [],
        category=category,
        subcategory=subcategory,
        subcategories=active_subcategories,
        products=products,
        categories=categories,
    )


@app.route("/product/<int:product_id>")
def product_details(product_id):
    product = get_product_details(product_id)
    if not product:
        flash("Product was not found.", "error")
        return redirect(url_for("login"))

    return render_template(
        "product_details.html",
        product=product,
        categories=get_category_shortcuts(),
    )


@app.route("/cart")
def cart():
    items = get_cart_items()
    _, total = cart_totals(items)
    return render_template("cart.html", items=items, total=total, categories=get_category_shortcuts())


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items = get_cart_items()
    if not items:
        flash("Your cart is empty. Please add products before checkout.", "error")
        return redirect(url_for("cart"))

    _, total = cart_totals(items)
    order_data = {
        "mobile": "",
        "name": session.get("username", ""),
        "email": "",
        "address": "",
        "payment_method": "bKash",
        "payment_type": "Cash On Delivery",
        "affiliate_user": checkout_affiliate_user(),
    }

    if request.method == "POST":
        order_data = {
            "mobile": request.form.get("mobile", "").strip(),
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "address": request.form.get("address", "").strip(),
            "payment_method": request.form.get("payment_method", "bKash"),
            "payment_type": request.form.get("payment_type", "Cash On Delivery"),
            "affiliate_user": request.form.get("affiliate_user", "").strip() or checkout_affiliate_user(),
        }
        if not order_data["mobile"] or not order_data["name"] or not order_data["address"]:
            flash("Mobile, name, and address are required to confirm order.", "error")
        else:
            for item in items:
                if not item.get("affiliate_username"):
                    item["affiliate_username"] = order_data["affiliate_user"] or "hbanucu"
                    item["affiliate_commission_percent"] = item.get("commission", "0")
            customer_id = create_or_update_customer(order_data)
            order_id = save_checkout_order(
                customer_id,
                order_data,
                items,
                order_data["payment_type"],
                order_data["payment_method"],
                total,
            )
            session.pop("cart", None)
            return redirect(url_for("checkout_success", order_id=order_id))

    return render_template(
        "checkout.html",
        items=items,
        total=total,
        order=order_data,
        categories=get_category_shortcuts(),
    )


@app.route("/checkout/success/<order_id>")
def checkout_success(order_id):
    return render_template("checkout_success.html", order_id=order_id)


@app.route("/api/customer-lookup")
def customer_lookup():
    mobile = request.args.get("mobile", "").strip()
    if not mobile:
        return jsonify({"found": False})

    customer = find_customer_by_mobile(mobile)
    if not customer:
        return jsonify({"found": False})

    return jsonify({
        "found": True,
        "name": customer.get("name") or "",
        "email": customer.get("email") or "",
        "address": customer.get("address") or "",
        "mobile": customer.get("contactno") or mobile,
    })


def api_product(product):
    return {
        "id": str(product.get("id") or ""),
        "name": str(product.get("name") or ""),
        "price": str(product.get("price") or "0"),
        "image": str(product.get("image") or ""),
        "image_url": legacy_asset_external_url(product.get("image")),
        "seller": str(product.get("seller") or ""),
    }


@app.route("/api/mobile/home")
def api_mobile_home():
    sections = []
    for section in get_home_product_sections():
        sections.append({
            "id": str(section.get("id") or ""),
            "title": section.get("title") or "Products",
            "tag": section.get("tag") or "",
            "products": [api_product(product) for product in section.get("products", [])[:12]],
        })
    return jsonify({
        "categories": get_category_shortcuts(),
        "sections": sections,
        "slider_images": [
            public_url(url_for("static", filename=image, v="20260520-mobile-slider"))
            for image in get_home_slider_images()
        ],
    })


@app.route("/api/mobile/categories")
def api_mobile_categories():
    return jsonify({"categories": get_category_shortcuts()})


@app.route("/api/mobile/categories/<int:category_id>/products")
def api_mobile_category_products(category_id):
    subcategory_id = request.args.get("sub")
    products = get_category_products(category_id, subcategory_id)
    return jsonify({"products": [api_product(product) for product in products]})


@app.route("/api/mobile/products/<int:product_id>")
def api_mobile_product_details(product_id):
    product = get_product_details(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    data = api_product(product)
    data.update({
        "category_id": product.get("category_id") or "",
        "subcategory_id": product.get("subcategory_id") or "",
        "category_name": product.get("category_name") or "",
        "subcategory_name": product.get("subcategory_name") or "",
        "description": product.get("description") or "",
        "details": product.get("details") or "",
        "unit": product.get("unit") or "",
        "made_by": product.get("made_by") or "",
        "images": [legacy_asset_external_url(image) for image in product.get("images", [])],
    })
    return jsonify({"product": data})


@app.route("/api/mobile/customer")
def api_mobile_customer_lookup():
    return customer_lookup()


@app.route("/api/mobile/orders", methods=["POST"])
def api_mobile_place_order():
    payload = request.get_json(silent=True) or {}
    customer = payload.get("customer") or {}
    items = payload.get("items") or []
    order_data = {
        "mobile": str(customer.get("mobile") or "").strip(),
        "name": str(customer.get("name") or "").strip(),
        "email": str(customer.get("email") or "").strip(),
        "address": str(customer.get("address") or "").strip(),
    }
    payment_type = str(payload.get("payment_type") or "Cash On Delivery")
    payment_method = str(payload.get("payment_method") or "Cash On Delivery")

    if not order_data["mobile"] or not order_data["name"] or not order_data["address"]:
        return jsonify({"error": "Mobile, name, and address are required."}), 400
    if not items:
        return jsonify({"error": "Cart is empty."}), 400

    order_items = []
    for item in items:
        try:
            product_id = int(item.get("id"))
            quantity = max(1, int(item.get("quantity") or 1))
        except (TypeError, ValueError):
            continue
        product = get_product_details(product_id)
        if product:
            order_items.append({
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "image": product_cart_image(product),
                "seller": product["seller"],
                "quantity": quantity,
            })

    if not order_items:
        return jsonify({"error": "No valid products found."}), 400

    _, total = cart_totals(order_items)
    customer_id = create_or_update_customer(order_data)
    order_id = save_checkout_order(customer_id, order_data, order_items, payment_type, payment_method, total)
    return jsonify({
        "success": True,
        "order_id": order_id,
        "total": "{0:.2f}".format(total),
        "message": "Order placed successfully.",
    })


@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = get_product_details(product_id)
    if not product:
        flash("Product was not found.", "error")
        return redirect(request.referrer or url_for("login"))

    try:
        quantity = max(1, int(request.form.get("quantity", "1")))
    except ValueError:
        quantity = 1

    cart_data = session.get("cart", {})
    key = str(product_id)
    affiliate_fields = {
        "affiliate_user_id": request.form.get("affiliate_user_id", "").strip(),
        "affiliate_username": request.form.get("affiliate_username", "").strip(),
        "affiliate_price": request.form.get("affiliate_price", "").strip(),
        "affiliate_commission_percent": request.form.get("affiliate_commission_percent", "").strip(),
    }
    affiliate_fields = {name: value for name, value in affiliate_fields.items() if value}
    if not affiliate_fields.get("affiliate_username"):
        referral_profile = referral_profile_from_cookie()
        if referral_profile:
            affiliate_fields = {
                "affiliate_user_id": str(referral_profile.get("UserId") or ""),
                "affiliate_username": str(referral_profile.get("Username") or ""),
                "affiliate_price": product["price"],
                "affiliate_commission_percent": product.get("commission", "0"),
            }
    if key in cart_data:
        cart_data[key]["quantity"] = int(cart_data[key]["quantity"]) + quantity
        cart_data[key].update(affiliate_fields)
        if affiliate_fields.get("affiliate_price"):
            cart_data[key]["price"] = affiliate_fields["affiliate_price"]
    else:
        cart_data[key] = {
            "id": product["id"],
            "name": product["name"],
            "price": affiliate_fields.get("affiliate_price") or product["price"],
            "image": product_cart_image(product),
            "seller": product["seller"],
            "commission": product.get("commission", "0"),
            "quantity": quantity,
        }
        cart_data[key].update(affiliate_fields)

    session["cart"] = cart_data
    flash("Product added to cart.", "success")
    next_url = request.form.get("next") or request.referrer or url_for("login")
    separator = "&" if "?" in next_url else "?"
    if "cart=open" not in next_url:
        next_url = next_url + separator + "cart=open"
    return redirect(next_url)


@app.route("/profile-products/add/<int:product_id>", methods=["POST"])
@login_required
def add_product_to_profile(product_id):
    if not can_add_profile_product():
        flash("Only customer or designer profiles can add affiliate products.", "error")
        return redirect(request.form.get("next") or request.referrer or url_for("login"))
    try:
        add_affiliate_product(
            session.get("user_id"),
            {
                "product_id": str(product_id),
                "affiliate_price": request.form.get("affiliate_price", ""),
                "commission_percent": request.form.get("commission_percent", ""),
                "note": request.form.get("note", ""),
            },
        )
        flash("Product added to your profile successfully.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(request.form.get("next") or request.referrer or url_for("login"))


@app.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    cart_data = session.get("cart", {})
    key = str(product_id)
    if key in cart_data:
        try:
            quantity = int(request.form.get("quantity", "1"))
        except ValueError:
            quantity = 1

        if quantity <= 0:
            cart_data.pop(key, None)
        else:
            cart_data[key]["quantity"] = quantity
        session["cart"] = cart_data
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart_data = session.get("cart", {})
    removed = cart_data.pop(str(product_id), None)
    session["cart"] = cart_data
    session.modified = True
    if removed:
        flash("Product deleted from cart.", "success")
    next_url = request.form.get("next") or request.referrer or url_for("cart")
    return redirect(next_url)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/courses/manage", methods=["GET", "POST"])
@role_required("Admin", "Institute", "Instructor")
def course_manage():
    selected_category = request.values.get("category", "").strip()
    editing_video = get_public_course_video(request.args.get("edit", type=int)) if request.args.get("edit", type=int) else None
    if editing_video and request.method == "GET":
        selected_category = editing_video.get("CourseCategory") or ""
    if request.method == "POST":
        category = request.form.get("category", "").strip()
        title = request.form.get("title", "").strip()
        youtube_link = request.form.get("youtube_link", "").strip()
        try:
            video_id = request.form.get("video_id", type=int)
            if video_id and not get_public_course_video(video_id):
                raise ValueError("Course video was not found.")
            add_course_video(category, title, youtube_link, request.form.get("content_html", ""), video_id)
            flash("Course updated successfully." if video_id else "Course video added successfully.", "success")
            return redirect(url_for("course_manage", category=category))
        except Exception as exc:
            selected_category = category
            flash(str(exc), "error")

    categories = get_course_categories()
    videos = get_course_videos(category=selected_category or None)
    video_groups = get_course_video_groups(selected_category or None)
    return render_template(
        "course_manage.html",
        editing_video=editing_video,
        content_draft=sanitize_course_content(request.form.get('content_html', (editing_video or {}).get('ContentHtml'))),
        title="Course Video Management",
        role="Course",
        categories=categories,
        selected_category=selected_category,
        videos=videos,
        video_groups=video_groups,
        **dashboard_payload("Course"),
    )


@app.route("/training/<int:video_id>")
def training_details(video_id):
    from flask import abort
    course = get_public_course_video(video_id)
    if not course:
        abort(404)
    course["ContentHtml"] = sanitize_course_content(course.get("ContentHtml"))
    return render_template("training_details.html", title=course.get("Name"), course=course)


@app.route("/courses/content-image", methods=["POST"])
@role_required("Admin", "Institute", "Instructor")
def course_content_image():
    image = request.files.get("image")
    if not image:
        return jsonify(error="Choose an image."), 400
    data = image.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        return jsonify(error="Image must be smaller than 5 MB."), 400
    extension = None
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        extension = 'png'
    elif data.startswith(b'\xff\xd8\xff'):
        extension = 'jpg'
    elif data.startswith((b'GIF87a', b'GIF89a')):
        extension = 'gif'
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        extension = 'webp'
    if not extension:
        return jsonify(error="Use a PNG, JPEG, GIF, or WebP image."), 400
    folder = Path(app.static_folder) / 'course-images'
    folder.mkdir(parents=True, exist_ok=True)
    filename = uuid4().hex + '.' + extension
    (folder / filename).write_bytes(data)
    return jsonify(url=url_for('static', filename='course-images/' + filename))


@app.route("/courses/students", methods=["GET", "POST"])
@role_required("Admin", "Institute", "Instructor")
def course_students():
    if request.method == "POST":
        try:
            enrollment = enroll_student(
                request.form.get("name", "").strip(),
                request.form.get("mobile", "").strip(),
                request.form.get("email", "").strip(),
                request.form.get("address", "").strip(),
                request.form.get("course", "").strip(),
                request.form.get("fee", "0").strip(),
                session.get("username") or "Admin",
                request.form.get("reference", "").strip(),
            )
            flash(
                "Student enrolled successfully. Student ID: {0}. Login user: {1}, default password: {2}.".format(
                    enrollment["student_id"],
                    enrollment["username"],
                    enrollment["password"],
                ),
                "success",
            )
            return redirect(url_for("course_assign", student=enrollment["student_id"], category=request.form.get("course", "").strip()))
        except Exception as exc:
            flash(str(exc), "error")

    return render_template(
        "course_students.html",
        title="Enroll Student",
        role="Course",
        categories=get_course_categories(),
        reference_users=get_reference_users(),
        students=get_students(),
        **dashboard_payload("Course"),
    )


@app.route("/courses/videos/<int:video_id>/delete", methods=["POST"])
@role_required("Admin", "Institute", "Instructor")
def course_video_delete(video_id):
    selected_category = request.form.get("category", "").strip()
    delete_course_video(video_id)
    flash("Course video deleted.", "success")
    return redirect(url_for("course_manage", category=selected_category))


@app.route("/courses/assign", methods=["GET", "POST"])
@role_required("Admin", "Institute", "Instructor")
def course_assign():
    students = get_students()
    categories = get_course_categories()
    selected_student = request.values.get("student", "").strip()
    selected_course = request.values.get("category", request.values.get("course", "")).strip()
    if not selected_course and selected_student:
        student = get_student(selected_student)
        selected_course = (student or {}).get("Course") or ""

    if request.method == "POST":
        selected_student = request.form.get("student", "").strip()
        selected_course = request.form.get("category", request.form.get("course", "")).strip()
        selected_videos = request.form.getlist("video_ids")
        try:
            added = assign_videos_to_student(selected_student, selected_course, selected_videos)
            flash("{0} video assigned to student.".format(added), "success")
            return redirect(url_for("course_assign", student=selected_student, category=selected_course))
        except Exception as exc:
            flash(str(exc), "error")

    videos = get_course_videos(category=selected_course) if selected_course else []
    assigned_links = get_student_assigned_videos(selected_student) if selected_student else []
    return render_template(
        "course_assign.html",
        title="Assign Course Video",
        role="Course",
        students=students,
        categories=categories,
        videos=videos,
        assigned_links={str(row.get("VideoLink") or "") for row in assigned_links},
        assigned_videos=assigned_links,
        selected_student=selected_student,
        selected_course=selected_course,
        **dashboard_payload("Course"),
    )


@app.route("/courses/my")
@role_required("Student", "Institute", "Instructor", "Admin")
def my_courses():
    student = get_student_for_user(
        session.get("username", ""),
        session.get("phone", ""),
        session.get("email", ""),
    )
    videos = get_student_assigned_videos(student["StdId"]) if student else []
    return render_template(
        "course_student.html",
        title="My Courses",
        role="Course",
        student=student,
        videos=videos,
        **dashboard_payload("Course"),
    )


@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return redirect(url_for(dashboard_endpoint_for(session.get("category"))))


@app.route("/dashboards/pos")
@role_required("POS", "Admin")
def pos_dashboard():
    role = "POS"
    return render_template("dashboard.html", title="POS Dashboard", role=role, **dashboard_payload(role), cards=[
        ("POS Sale", "Product search, customer information, sale save, and receipt print."),
        ("POS Reports", "Date-to-date sales report, category/product breakdown, and graphs."),
        ("Receipt Print", "Saved POS sales open printable receipt report."),
    ])


@app.route("/dashboards/admin")
@role_required("Admin")
def admin_dashboard():
    return render_admin_dashboard("overview")


@app.route("/dashboards/admin/<path:module_slug>", methods=["GET", "POST"])
@role_required("Admin")
def admin_module_dashboard(module_slug):
    module = admin_module_for(module_slug)
    if not module:
        flash("Admin module was not found.", "error")
        return redirect(url_for("admin_dashboard"))
    if module_slug == "customer-chat":
        return admin_customer_chat()
    if module_slug.startswith("ecommerce-setup/"):
        setup_slug = module_slug.split("/", 1)[1]
        if setup_slug == "product":
            return admin_ecommerce_product()
        return admin_ecommerce_lookup(setup_slug)
    if request.method == "POST" and module_slug == "customer-order":
        try:
            assign_order_to_delivery_man(
                request.form.get("order_row_id", "").strip(),
                request.form.get("delivery_man", "").strip(),
            )
            flash("Order assigned to delivery man successfully.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for(
            "admin_module_dashboard",
            module_slug=module_slug,
            date_from=request.form.get("date_from", "").strip(),
            date_to=request.form.get("date_to", "").strip(),
        ))
    if request.method == "POST" and module_slug == "product-barcode":
        try:
            action = request.form.get("action", "").strip()
            product_id = request.form.get("product_id", "").strip()
            if action == "delete":
                delete_pending_product(product_id)
                flash("Pending product deleted successfully.", "success")
            else:
                approve_product_barcode(product_id, session.get("username", "admin"))
                flash("Product approved and barcode created successfully.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin_module_dashboard", module_slug=module_slug))
    return render_admin_dashboard(module_slug)


def admin_ecommerce_lookup(setup_slug):
    config = lookup_module(setup_slug)
    if not config:
        flash("Ecommerce setup module was not found.", "error")
        return redirect(url_for("admin_dashboard"))

    edit_id = request.args.get("edit", "").strip()
    selected_row = get_lookup_row(setup_slug, edit_id) if edit_id else None
    if request.method == "POST":
        action = request.form.get("action", "save").strip()
        try:
            if action == "delete":
                delete_lookup(setup_slug, request.form.get("item_id", "").strip())
                flash("{0} deleted successfully.".format(config["title"]), "success")
            else:
                saved_id = save_lookup(setup_slug, request.form, request.files)
                flash("{0} saved successfully.".format(config["title"]), "success")
                if request.form.get("save_and_continue"):
                    return redirect(url_for("admin_module_dashboard", module_slug="ecommerce-setup/{0}".format(setup_slug), edit=saved_id))
        except Exception as exc:
            flash(str(exc), "error")
            return redirect(request.url)
        return redirect(url_for("admin_module_dashboard", module_slug="ecommerce-setup/{0}".format(setup_slug)))

    payload = dashboard_payload("Admin")
    payload["accent"] = "Ecommerce setup"
    return render_template(
        "admin_ecommerce_lookup.html",
        title=config["title"],
        role="Admin",
        selected_module=admin_module_for("ecommerce-setup/{0}".format(setup_slug)),
        setup_slug=setup_slug,
        config=config,
        rows=get_lookup_rows(setup_slug),
        selected_row=selected_row,
        setup_links=ecommerce_setup_links(),
        categories=get_lookup_rows("category"),
        **payload,
    )


def admin_ecommerce_product():
    edit_id = request.args.get("edit", "").strip()
    q = request.args.get("q", "").strip()
    per_page = 20
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    total_products = get_admin_product_count(q)
    total_pages = max(1, (total_products + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    selected_product = get_admin_product(edit_id) if edit_id else None
    if request.method == "POST":
        action = request.form.get("action", "save").strip()
        try:
            if action == "delete":
                delete_admin_product(request.form.get("product_id", "").strip())
                flash("Product deleted successfully.", "success")
            else:
                product_id = save_admin_product(request.form, request.files, session.get("username", "admin"))
                flash("Product saved successfully.", "success")
                if request.form.get("save_and_continue"):
                    return redirect(url_for("admin_module_dashboard", module_slug="ecommerce-setup/product", edit=product_id))
        except Exception as exc:
            flash(str(exc), "error")
            return redirect(request.url)
        return redirect(url_for("admin_module_dashboard", module_slug="ecommerce-setup/product"))

    product_sizes = get_product_sizes(edit_id) if edit_id else []
    selected_size_ids = {str(row.get("SizeID")) for row in product_sizes}
    first_quantity = product_sizes[0].get("Quantity") if product_sizes else 1
    payload = dashboard_payload("Admin")
    payload["accent"] = "Ecommerce setup"
    return render_template(
        "admin_ecommerce_product.html",
        title="Add Product",
        role="Admin",
        selected_module=admin_module_for("ecommerce-setup/product"),
        setup_links=ecommerce_setup_links(),
        product_options=get_product_options(),
        products=get_admin_products(q, page=page, per_page=per_page),
        total_products=total_products,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        selected_product=selected_product,
        selected_size_ids=selected_size_ids,
        first_quantity=first_quantity,
        product_images=get_product_images(edit_id) if edit_id else [],
        q=q,
        **payload,
    )


def render_admin_dashboard(module_slug):
    role = "Admin"
    selected_module = admin_module_for(module_slug)
    admin_summary = get_admin_dashboard_summary()
    payload = dashboard_payload(role)
    payload["stats"] = [
        (str(admin_summary["total_orders"]), "Total Orders"),
        (admin_summary["sales"], "Total Sales Amount"),
        (admin_summary["month_sales"], "This Month Sales"),
        (admin_summary["today_sales"], "Today's Sale"),
        (admin_summary["delivery_man_commission"], "Delivery Man Commission"),
    ]
    module_data = None
    if module_slug != "overview":
        module_data = get_admin_module_data(
            module_slug,
            {
                "date_from": request.args.get("date_from", "").strip(),
                "date_to": request.args.get("date_to", "").strip(),
                "delivery_man": request.args.get("delivery_man", "").strip(),
            },
        )
    return render_template("dashboard.html", title="Admin Dashboard", role=role, selected_module=selected_module, module_data=module_data, admin_summary=admin_summary, **payload, cards=[
        ("Users", "Approve accounts and manage all platform users."),
        ("Modules", "Control ecommerce, freelance, services, and course workflows."),
        ("Reports", "Review orders, sales, payments, and platform activity."),
    ])


def admin_customer_chat():
    if request.method == "POST":
        request_id = request.form.get("request_id", "").strip()
        try:
            action = request.form.get("action", "reply").strip()
            if action == "update":
                update_support_assignment(
                    int(request_id),
                    request.form.get("assigned_to", "").strip(),
                    request.form.get("status", "").strip(),
                    request.form.get("priority", "").strip(),
                    request.form.get("department", "").strip(),
                    request.form.get("escalated_to", "").strip(),
                )
                flash("Ticket updated successfully.", "success")
            else:
                add_support_reply(
                    int(request_id),
                    session.get("username") or "Admin",
                    request.form.get("message", "").strip(),
                    request.form.get("status", "Answered").strip(),
                )
                flash("Reply sent successfully.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin_module_dashboard", module_slug="customer-chat", selected=request_id))

    status = request.args.get("status", "").strip()
    contact_no = request.args.get("contact_no", "").strip()
    issue_type = request.args.get("issue_type", "").strip()
    priority = request.args.get("priority", "").strip()
    department = request.args.get("department", "").strip()
    selected_id = request.args.get("selected", "").strip()
    requests = get_support_requests(status, contact_no, issue_type, priority, department)
    if not selected_id and requests:
        selected_id = str(requests[0].get("Id"))
    selected_request = get_support_request(selected_id) if selected_id else None
    messages = get_support_messages(selected_id) if selected_id else []
    payload = dashboard_payload("Admin")
    payload["accent"] = "Customer service"
    return render_template(
        "support_chat_admin.html",
        title="Customer Chat",
        role="Admin",
        requests=requests,
        selected_request=selected_request,
        messages=messages,
        selected_id=selected_id,
        selected_status=status,
        contact_no=contact_no,
        selected_issue_type=issue_type,
        selected_priority=priority,
        selected_department=department,
        issue_types=["Product information", "Order status", "Payment issue", "Return/refund", "Technical support", "Talk to agent"],
        priorities=["Low", "Medium", "High", "Urgent"],
        departments=["Sales", "Order", "Accounts", "Returns", "Technical", "Support"],
        **payload,
    )


@app.route("/dashboards/customer")
@role_required("Customer")
def customer_dashboard():
    return redirect(url_for("customer_workspace", section="orders"))


@app.route("/customer")
@role_required("Customer")
def customer_home():
    return redirect(url_for("customer_workspace", section="orders"))


@app.route("/customer/order-tracking")
@role_required("Customer")
def customer_order_tracking():
    username = session.get("username", "")
    email = session.get("email", "")
    phone = session.get("phone", "")
    status = request.args.get("status", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    return render_template(
        "customer_order_tracking.html",
        title="Order Tracking",
        role="Customer",
        accent="Order tracking",
        menu=CUSTOMER_MENU,
        orders=get_tracking_orders(username, email, phone, status, date_from, date_to),
        selected_status=status,
        date_from=date_from,
        date_to=date_to,
    )


@app.route("/customer/order-tracking/<order_id>")
@role_required("Customer")
def customer_order_tracking_details(order_id):
    order = get_tracking_order_details(
        order_id,
        session.get("username", ""),
        session.get("email", ""),
        session.get("phone", ""),
    )
    if not order:
        flash("Order was not found.", "error")
        return redirect(url_for("customer_order_tracking"))
    return render_template(
        "customer_order_details.html",
        title="Order Details",
        role="Customer",
        accent="Order tracking",
        menu=CUSTOMER_MENU,
        order=order,
    )


@app.route("/customer/<section>", methods=["GET", "POST"])
@role_required("Customer")
def customer_workspace(section):
    if section in {"post-job", "jobs", "submissions"} and not can_post_jobs(session.get("category")):
        return "Only Customer accounts can post and manage jobs. Designers can apply from Jobs, Bids & Contests.", 403
    if section == "post-job" and request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        if not submitted or not hmac.compare_digest(submitted, session.get("market_csrf", "")):
            return "This form has expired. Reload the job form and try again.", 400
    allowed_sections = {"orders", "products", "profile-products", "post-job", "jobs", "submissions", "messages", "profile"}
    if section not in allowed_sections:
        flash("Customer module page was not found.", "error")
        return redirect(url_for("customer_workspace", section="orders"))

    user_id = session.get("user_id")
    username = session.get("username", "")
    email = session.get("email", "")
    phone = session.get("phone", "")

    if request.method == "POST":
        try:
            if section == "profile":
                if request.form.get("action") == "password":
                    if request.form.get("new_password") != request.form.get("confirm_password"):
                        raise ValueError("Password confirmation does not match.")
                    update_customer_password(user_id, request.form.get("new_password", ""), request.form.get("old_password", ""))
                    flash("Password updated successfully.", "success")
                else:
                    update_customer_profile(
                        user_id,
                        {
                            "username": request.form.get("username", "").strip(),
                            "first_name": request.form.get("first_name", "").strip(),
                            "last_name": request.form.get("last_name", "").strip(),
                            "phone": request.form.get("phone", "").strip(),
                            "address": request.form.get("address", "").strip(),
                            "city": request.form.get("city", "").strip(),
                            "state": request.form.get("state", "").strip(),
                            "postal_code": request.form.get("postal_code", "").strip(),
                            "country": request.form.get("country", "").strip(),
                            "about_me": request.form.get("about_me", "").strip(),
                        },
                        request.files.get("picture"),
                    )
                    session["username"] = request.form.get("username", "").strip() or username
                    session["phone"] = request.form.get("phone", "").strip() or phone
                    flash("Profile updated successfully.", "success")
                return redirect(url_for("customer_workspace", section="profile"))

            if section == "post-job":
                files = request.files.getlist("sample_images")
                edit_job_id = request.form.get("job_id", "").strip()
                if edit_job_id:
                    job_id = update_customer_job(user_id, edit_job_id, request.form, files)
                    flash("Design job updated successfully. Job #{0}".format(job_id), "success")
                else:
                    job_id = create_customer_job(user_id, request.form, files)
                    flash("Design job posted successfully. Job #{0}".format(job_id), "success")
                return redirect(url_for("customer_workspace", section="jobs"))

            if section == "products":
                product_id = create_customer_product(
                    user_id,
                    username,
                    request.form,
                    request.files.getlist("product_images"),
                )
                flash("Product submitted successfully. Admin approval pending. Product #{0}".format(product_id), "success")
                return redirect(url_for("customer_workspace", section="products"))

            if section == "submissions":
                update_submission_review(
                    user_id,
                    request.form.get("subid", "").strip(),
                    request.form.get("status", "").strip(),
                    request.form.get("feedback", "").strip(),
                )
                flash("Submission review updated.", "success")
                return redirect(url_for("customer_workspace", section="submissions", job_id=request.form.get("job_id", "")))

            if section == "messages":
                send_customer_message(
                    user_id,
                    request.form.get("receiver_id", "").strip(),
                    request.form.get("subject", "").strip(),
                    request.form.get("details", "").strip(),
                    request.form.get("job_id", "").strip(),
                    request.form.get("submission_id", "").strip(),
                )
                flash("Message saved successfully.", "success")
                return redirect(url_for("customer_workspace", section="messages"))
        except Exception as exc:
            flash(str(exc), "error")

    profile = get_customer_profile(user_id) or {}
    email = email or str(profile.get("Email") or "")
    phone = phone or str(profile.get("Phone") or "")
    summary = get_customer_summary(user_id, username, email, phone)
    stats = [
        (str(summary["orders"]), "Ecommerce Orders"),
        (str(summary["jobs"]), "Posted Jobs"),
        (str(summary["submissions"]), "Submitted Designs"),
        (str(summary["messages"]), "Messages"),
    ]
    payload = dashboard_payload("Customer")
    payload["stats"] = stats

    selected_job_id = request.values.get("job_id", "").strip()
    selected_job = get_customer_job(selected_job_id, user_id) if selected_job_id else None
    new_orders, old_orders = get_ecommerce_orders(user_id, username, email, phone)

    return render_template(
        "customer_dashboard.html",
        title="Customer Dashboard",
        role="Customer",
        section=section,
        profile=profile,
        design_types=DESIGN_TYPES,
        product_options=get_product_form_options(),
        own_products=get_customer_products(username),
        affiliate_products=get_affiliate_products(user_id),
        jobs=get_customer_jobs(user_id),
        selected_job=selected_job,
        selected_job_images=get_job_sample_images(selected_job_id) if selected_job_id else [],
        submissions=get_customer_submissions(user_id, selected_job_id or None),
        messages=get_customer_messages(user_id, username),
        new_orders=new_orders,
        old_orders=old_orders,
        **payload,
    )


@app.route("/dashboards/vendor")
@role_required("Vendor", "Seller")
def vendor_dashboard():
    role = "Vendor"
    return render_template("dashboard.html", title="Vendor Dashboard", role=role, **dashboard_payload(role), cards=[
        ("Products", "Add, edit, and publish ecommerce products."),
        ("Sales", "Review order status and sales history."),
        ("Delivery", "Prepare orders for delivery assignment."),
    ])


@app.route("/dashboards/freelancer")
@role_required("Designer", "Freelancer")
def freelancer_dashboard():
    return redirect(url_for("designer_workspace", section="dashboard"))


@app.route("/designer")
@role_required("Designer", "Freelancer")
def designer_home():
    return redirect(url_for("designer_workspace", section="dashboard"))


@app.route("/designer/order-tracking")
@role_required("Designer", "Freelancer")
def designer_order_tracking():
    username = session.get("username", "")
    status = request.args.get("status", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    return render_template(
        "customer_order_tracking.html",
        title="Order Tracking",
        role="Designer",
        accent="Order tracking",
        menu=DESIGNER_MENU,
        orders=get_designer_tracking_orders(username, status, date_from, date_to),
        selected_status=status,
        date_from=date_from,
        date_to=date_to,
        tracking_list_endpoint="designer_order_tracking",
        tracking_detail_endpoint="designer_order_tracking_details",
        tracking_secondary_url=url_for("designer_workspace", section="orders"),
        tracking_secondary_label="My Orders",
        tracking_jobs_url=url_for("designer_workspace", section="jobs"),
        tracking_messages_url=url_for("designer_workspace", section="messages"),
    )


@app.route("/designer/order-tracking/<order_id>")
@role_required("Designer", "Freelancer")
def designer_order_tracking_details(order_id):
    order = get_designer_tracking_order_details(order_id, session.get("username", ""))
    if not order:
        flash("Order was not found.", "error")
        return redirect(url_for("designer_order_tracking"))
    return render_template(
        "customer_order_details.html",
        title="Order Details",
        role="Designer",
        accent="Order tracking",
        menu=DESIGNER_MENU,
        order=order,
        tracking_list_endpoint="designer_order_tracking",
    )


@app.route("/designer/<section>", methods=["GET", "POST"])
@role_required("Designer", "Freelancer")
def designer_workspace(section):
    if section in {"jobs", "submit", "submissions", "status", "designs"} and not can_apply_jobs(session.get("category")):
        return "Only Designer accounts can apply and submit work. Customers can post jobs from Jobs, Bids & Contests.", 403
    allowed_sections = {"dashboard", "jobs", "submit", "submissions", "status", "designs", "orders", "messages", "offers", "products", "affiliate", "profile"}
    if section not in allowed_sections:
        flash("Designer module page was not found.", "error")
        return redirect(url_for("designer_workspace", section="dashboard"))

    user_id = session.get("user_id")
    if request.method == "POST" and section == "submit":
        from flask import abort
        token=session.get('market_csrf','')
        if not token or not hmac.compare_digest(token,request.form.get('csrf_token','')):
            abort(400)
        try:
            create_submission(
                user_id,
                request.form.get("job_id", "").strip() or None,
                request.form.get("design_link", "").strip(),
                request.form.get("title", "").strip(),
                request.files.get("jpg_file"),
                request.files.get("zip_file"),
                request.files.get("ai_file"),
            )
            flash("Design submitted successfully.", "success")
            return redirect(url_for("designer_workspace", section="submissions"))
        except Exception as exc:
            flash(str(exc), "error")
    elif request.method == "POST" and section == "offers":
        try:
            offer_id = save_designer_offer(
                user_id,
                session.get("username", ""),
                request.form,
                request.files.getlist("offer_images"),
                request.files.get("zip_file"),
            )
            flash("Offer saved successfully. Offer #{0}".format(offer_id), "success")
            return redirect(url_for("designer_workspace", section="offers", offer_id=offer_id))
        except Exception as exc:
            flash(str(exc), "error")
    elif request.method == "POST" and section == "products":
        try:
            product_id = create_designer_product(
                user_id,
                session.get("username", ""),
                request.form,
                request.files.getlist("product_images"),
            )
            flash("Own ecommerce product saved successfully. Product #{0}".format(product_id), "success")
            return redirect(url_for("designer_workspace", section="products"))
        except Exception as exc:
            flash(str(exc), "error")
    elif request.method == "POST" and section == "affiliate":
        try:
            add_affiliate_product(user_id, request.form)
            flash("Affiliate product added successfully.", "success")
            return redirect(url_for("designer_workspace", section="affiliate"))
        except Exception as exc:
            flash(str(exc), "error")
    elif request.method == "POST" and section == "profile":
        action = request.form.get("action", "profile")
        try:
            if action == "password":
                old_password = request.form.get("old_password", "")
                new_password = request.form.get("new_password", "")
                confirm_password = request.form.get("confirm_password", "")
                if new_password != confirm_password:
                    raise ValueError("Password confirmation does not match.")
                update_designer_password(user_id, new_password, old_password)
                flash("Password updated successfully.", "success")
            else:
                previous_username = session.get("username", "")
                update_designer_profile(user_id, request.form, request.files.get("picture"))
                selected_expertise = request.form.getlist("expertise")
                update_designer_expertise(user_id, request.form.get("username", previous_username), selected_expertise, previous_username)
                if request.form.get("username"):
                    session["username"] = request.form.get("username").strip()
                if request.form.get("phone"):
                    session["phone"] = request.form.get("phone").strip()
                flash("Designer profile updated successfully.", "success")
            return redirect(url_for("designer_workspace", section="profile"))
        except Exception as exc:
            flash(str(exc), "error")

    selected_job = None
    selected_job_id = request.values.get("job_id", "").strip()
    if selected_job_id:
        selected_job = get_job(selected_job_id)

    selected_offer_id = request.values.get("offer_id", "").strip()
    selected_offer = None
    selected_offer_images = []
    if selected_offer_id:
        for offer in get_designer_offers(user_id):
            if str(offer.get("id")) == selected_offer_id:
                selected_offer = offer
                selected_offer_images = get_offer_images(selected_offer_id)
                break

    summary = get_designer_summary(user_id, session.get("username", ""))
    stats = [
        (str(summary["open_jobs"]), "Open Jobs"),
        (str(summary["offers"]), "Services"),
        (str(summary["submissions"]), "Designs"),
        (summary["earnings"], "Earnings"),
    ]
    payload = dashboard_payload("Freelancer")
    payload["stats"] = stats
    jobs = get_open_jobs()
    offers = get_designer_offers(user_id)
    submissions = get_my_submissions(user_id)
    selected_submissions = get_my_submissions(user_id, "Selected")
    designs = get_all_designs(user_id)
    orders = get_designer_orders(user_id, session.get("username", ""))
    messages = get_designer_messages(user_id, session.get("username", ""))

    return render_template(
        "designer_dashboard.html",
        title="Designer Dashboard",
        role="Designer",
        section=section,
        profile=get_designer_profile(user_id),
        summary=summary,
        job_types=get_open_job_type_summary(),
        jobs=jobs,
        selected_job=selected_job,
        offer_categories=get_offer_categories(),
        service_types=get_service_types(),
        designer_expertise=get_designer_expertise(user_id, session.get("username", "")),
        public_profile_url=public_url(url_for("freelancer_public_profile", username=session.get("username", "")).lstrip("/")),
        package_features=PACKAGE_FEATURES,
        offers=offers,
        selected_offer=selected_offer,
        selected_offer_images=selected_offer_images,
        categories=get_categories(),
        subcategories=get_subcategories(),
        own_products=get_designer_products(session.get("username", "")),
        product_search=request.values.get("q", "").strip(),
        product_results=search_products(request.values.get("q", "").strip()),
        affiliate_products=get_affiliate_products(user_id),
        submissions=submissions,
        selected_submissions=selected_submissions,
        designs=designs,
        orders=orders,
        messages=messages,
        **payload,
    )


@app.route("/freelancer/<username>")
def freelancer_public_profile(username):
    profile = get_designer_public_profile(username)
    if not profile:
        flash("Freelancer profile was not found.", "error")
        return redirect(url_for("login"))
    return referral_response(
        "freelancer_profile.html",
        profile=profile,
        title="{0} Profile".format(profile.get("Username")),
        offers=get_designer_offers(profile["UserId"]),
        own_products=get_designer_products(profile.get("Username") or ""),
        affiliate_products=get_affiliate_products(profile["UserId"]),
        categories=get_category_shortcuts(),
    )


@app.route("/service/order/<int:offer_id>", methods=["GET", "POST"])
def public_service_order(offer_id):
    offer = get_public_offer(offer_id)
    if not offer:
        flash("Service offer was not found.", "error")
        return redirect(url_for("login"))

    selected_package = request.values.get("package", "3").strip() or "3"
    amount = offer_package_amount(offer, selected_package)
    if request.method == "POST":
        try:
            customer_id = session.get("user_id") or request.form.get("customer_phone", "").strip() or "0"
            create_service_order(offer, customer_id, selected_package, amount)
            flash("Service order placed successfully.", "success")
            username = offer.get("Username") or request.cookies.get("as_ref_user") or "login"
            return redirect(url_for("public_user_profile", username=username))
        except Exception as exc:
            flash(str(exc), "error")

    return render_template(
        "service_order.html",
        title="Service Order",
        offer=offer,
        offer_images=get_offer_images(offer_id),
        package_features=PACKAGE_FEATURES,
        selected_package=selected_package,
        amount=amount,
    )


@app.route("/<username>")
def public_user_profile(username):
    reserved = {
        "login", "logout", "register", "dashboard", "dashboards", "customer", "designer",
        "freelancer", "cart", "checkout", "category", "product", "courses", "api",
        "static", "legacy-assets", "profile-products", "service", "pos", "favicon.ico",
    }
    if str(username or "").lower() in reserved:
        return redirect(url_for("login"))
    profile = get_designer_public_profile(username)
    if not profile:
        flash("User profile was not found.", "error")
        return redirect(url_for("login"))
    return referral_response(
        "freelancer_profile.html",
        profile=profile,
        title="{0} Profile".format(profile.get("Username")),
        offers=get_designer_offers(profile["UserId"]),
        own_products=get_designer_products(profile.get("Username") or ""),
        affiliate_products=get_affiliate_products(profile["UserId"]),
        categories=get_category_shortcuts(),
    )


@app.route("/dashboards/course")
@role_required("Institute", "Instructor", "Student")
def course_dashboard():
    role = "Course"
    return render_template("dashboard.html", title="Course Dashboard", role=role, **dashboard_payload(role), cards=[
        ("Courses", "Manage course content, videos, and student access."),
        ("Students", "Track admissions, payments, and progress."),
        ("Assignments", "Review submissions and training activity."),
    ])


@app.route("/dashboards/delivery", methods=["GET", "POST"])
@role_required("DeliveryMan", "Delivery")
def delivery_dashboard():
    user_id = session.get("user_id")
    username = session.get("username", "")
    if request.method == "POST":
        try:
            update_delivery_order_status(
                username,
                request.form.get("assign_id", "").strip(),
                request.form.get("status", "").strip(),
            )
            flash("Delivery status updated successfully.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for(
            "delivery_dashboard",
            date_from=request.form.get("date_from", "").strip(),
            date_to=request.form.get("date_to", "").strip(),
            status=request.form.get("current_status", "").strip(),
        ))

    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    selected_status = request.args.get("status", "").strip()
    summary = get_delivery_summary(username)
    stats = [
        (str(summary["assigned"]), "Assigned"),
        (str(summary["picked_up"]), "Picked Up"),
        (str(summary["complete"]), "Complete"),
        (str(summary["closed"]), "Closed"),
    ]
    return render_template(
        "delivery_dashboard.html",
        title="Delivery Dashboard",
        role="Delivery Man",
        accent="Delivery workflow",
        menu=DELIVERY_MENU,
        profile=get_delivery_profile(user_id) or {},
        stats=stats,
        orders=get_delivery_orders(username, date_from, date_to, selected_status),
        statuses=DELIVERY_STATUSES,
        selected_status=selected_status,
        date_from=date_from,
        date_to=date_to,
    )


if __name__ == "__main__":
    app.run(debug=True, host=os.environ.get("FLASK_HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5001")))
