"""Unified portal. Existing Flask routes and legacy data remain available."""
import hmac
import json
import logging
import secrets
from functools import wraps
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, session, url_for
from werkzeug.exceptions import HTTPException

from market_db import transaction
from market_legacy import products as legacy_products
import legacy_jobs
from job_feed import open_jobs
from customer_service import DESIGN_TYPES
from job_permissions import can_post as category_can_post, can_apply as category_can_apply
from market_service import Marketplace, KINDS, MODES, meta, uid, require, text, today

market = Blueprint("market", __name__, url_prefix="/workspace")
log = logging.getLogger(__name__)


def is_admin():
    return str(session.get("category", "")).strip().lower() == "admin"


def login_needed(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return function(*args, **kwargs)
    return wrapper


def service(store):
    return Marketplace(store, session.get("user_id", ""), is_admin())


def payment_instructions(store):
    setting = store.get("MarketSetting", "payment_instructions")
    return setting["Value"] if setting else current_app.config.get("MARKET_PAYMENT_INSTRUCTIONS", "")


def public_home_jobs():
    try:
        with transaction() as store:
            return open_jobs(store,limit=6)
    except Exception:
        log.exception("Could not load marketplace jobs for the legacy home page")
        return []


def csrf():
    if not session.get("market_csrf"):
        session["market_csrf"] = secrets.token_urlsafe(32)
    return session["market_csrf"]


@market.before_request
def protect_forms():
    request.max_content_length = 20 * 1024 * 1024
    request.max_form_memory_size = 256 * 1024
    if session.get("user_id"):
        with transaction() as store:
            identity = store.one("SELECT UserId, UserCatagory, Active, Status FROM Users WHERE UserId=?", [str(session["user_id"])])
        if not identity or str(identity.get("Active") or "").strip().lower() not in ("1", "true") or str(identity.get("Status") or "").strip().lower() not in ("", "true"):
            session.clear()
            return redirect(url_for("login", next=request.path))
        # Promotions, demotions and deactivation take effect without trusting stale cookies.
        session["category"] = str(identity["UserCatagory"])
    if request.method == "POST":
        if not session.get("user_id"):
            abort(401)
        submitted = request.form.get("csrf_token", "")
        if not submitted or not hmac.compare_digest(submitted, session.get("market_csrf", "")):
            abort(400, "This form has expired. Reload the page and try again.")


@market.after_request
def private_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@market.app_context_processor
def portal_context():
    return dict(portal_csrf=csrf, market_kinds=KINDS, market_modes=MODES, market_admin=is_admin(),
                market_meta=meta, portal_user=str(session.get("user_id", "")), new_key=uid,
                job_can_post=category_can_post(session.get('category')), job_can_apply=category_can_apply(session.get('category')))


@market.app_template_filter("taka")
def taka(value):
    return f"BDT {int(value or 0) / 100:,.2f}"


def asset_directory():
    root = Path(current_app.config.get("MARKET_PRIVATE_DIR") or Path(current_app.instance_path) / "market_files")
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def upload(field="asset"):
    incoming = request.files.get(field)
    if not incoming or not incoming.filename:
        return ""
    suffix = Path(incoming.filename).suffix.lower()
    if field == "image":
        require(suffix in {".jpg", ".jpeg", ".png", ".webp"}, "Use a JPG, PNG or WebP cover image.")
    require(suffix in {".zip", ".pdf", ".jpg", ".jpeg", ".png", ".webp", ".ai"}, "Upload a ZIP, PDF, JPG, PNG, WebP or AI file.")
    content = incoming.read(10 * 1024 * 1024 + 1)
    require(content and len(content) <= 10 * 1024 * 1024, "Upload a non-empty file up to 10 MB.")
    if suffix in {".jpg", ".jpeg"}:
        require(content.startswith(b"\xff\xd8\xff"), "Upload a valid JPG file.")
    elif suffix == ".png":
        require(content.startswith(b"\x89PNG\r\n\x1a\n"), "Upload a valid PNG file.")
    elif suffix == ".pdf":
        require(content.startswith(b"%PDF-"), "Upload a valid PDF file.")
    elif suffix == ".zip":
        require(content.startswith(b"PK"), "Upload a valid ZIP file.")
    elif suffix == ".webp":
        require(content.startswith(b"RIFF") and content[8:12] == b"WEBP", "Upload a valid WebP file.")
    elif suffix == ".ai":
        require(content.startswith((b"%PDF-", b"%!PS-Adobe")), "Upload a valid Illustrator file.")
    identity = uid() + suffix
    (asset_directory() / identity).write_bytes(content)
    request.environ.setdefault("market_uploads", []).append(identity)
    return identity


def mutate(callback):
    """Commit only successful workflows; remove uploaded orphans on validation/DB failure."""
    asset = ""
    try:
        request.environ["market_uploads"] = []
        asset = upload()
        request.environ["market_image"] = upload("image")
        with transaction() as store:
            result = callback(service(store), asset)
            for uploaded in request.environ["market_uploads"]:
                referenced = any(store.one(f"SELECT Id FROM {table} WHERE Asset=?", [uploaded]) for table in
                                 ("MarketListing", "MarketOrder", "MarketLesson", "MarketProposal", "MarketMessage"))
                referenced = referenced or store.one("SELECT Id FROM MarketListing WHERE Image=?", [uploaded])
                require(referenced, "This form does not accept file uploads.")
        flash("Saved successfully. See the next step below.", "success")
        return result, True
    except HTTPException:
        for uploaded in request.environ.get("market_uploads", []):
            (asset_directory() / uploaded).unlink(missing_ok=True)
        raise
    except Exception as error:
        for uploaded in request.environ.get("market_uploads", []):
            (asset_directory() / uploaded).unlink(missing_ok=True)
        if isinstance(error, ValueError):
            flash(str(error), "error")
        else:
            log.exception("Marketplace write failed")
            flash("Your changes were not saved. Try again or contact support if the problem continues.", "error")
        return None, False


def view(template, **context):
    return render_template("market/" + template + ".html", **context)


@market.route("/")
@login_needed
def home():
    with transaction() as store:
        svc = service(store)
        profile = svc.profile()
        orders = store.all("SELECT * FROM MarketOrder WHERE BuyerId=? OR SellerId=? ORDER BY Created DESC", [svc.user, svc.user])
        listings = store.all("SELECT * FROM MarketListing WHERE OwnerId=? ORDER BY Created DESC", [svc.user])
        events = store.all("SELECT * FROM MarketEvent WHERE RecipientId=? ORDER BY Created DESC", [svc.user])[:12]
        balance = svc.balance()
    return view("home", title="Workspace Overview", section="home", profile=profile, orders=orders, listings=listings,
                events=events, balance=balance)


@market.route("/settings", methods=["GET", "POST"])
@login_needed
def settings():
    if request.method == "POST":
        _, ok = mutate(lambda svc, asset: svc.save_profile(request.form))
        if ok:
            return redirect(url_for("market.settings"))
    with transaction() as store:
        profile = service(store).profile()
    return view("settings", title="Profile & Features", section="settings", profile=profile or {})


@market.route("/catalog")
def catalog():
    kind = request.args.get("kind", "")
    query = request.args.get("q", "").strip()[:160]
    page = max(1, min(request.args.get("page", 1, type=int) or 1, 10000))
    sql = "SELECT l.*, p.DisplayName FROM MarketListing l LEFT JOIN MarketProfile p ON p.UserId=l.OwnerId WHERE l.Status='published'"
    params = []
    if kind in KINDS:
        sql += " AND l.Kind=?"
        params.append(kind)
    if query:
        sql += " AND (l.Title LIKE ? OR l.Description LIKE ?)"
        params += ["%" + query + "%"] * 2
    with transaction() as store:
        rows = store.page(sql + " ORDER BY l.Created DESC,l.Id", params, (page-1)*24, 25)
        legacy, _ = legacy_products(store, query) if kind in ("", "product") and page == 1 else ([], "")
    return view("catalog", title="Marketplace", section="catalog", listings=rows[:24],
                page=page, has_next=len(rows)>24, kind=kind, query=query, legacy_products=legacy)


@market.route("/store/<user_id>")
def public_store(user_id):
    with transaction() as store:
        profile = store.get("MarketProfile", user_id, key="UserId")
        if not profile:
            abort(404)
        listings = store.all("SELECT * FROM MarketListing WHERE OwnerId=? AND Status='published' ORDER BY Created DESC", [user_id])
        affiliates = store.all("SELECT l.* FROM MarketListing l JOIN MarketAffiliate a ON a.ListingId=l.Id WHERE a.UserId=? AND l.Status='published' AND l.Affiliate=1", [user_id])
        reviews = store.all("SELECT * FROM MarketReview WHERE SellerId=? ORDER BY Created DESC", [user_id])
        legacy, legacy_username = legacy_products(store, owner_id=user_id)
    return view("store", title=profile["DisplayName"], section="catalog", profile=profile, listings=listings,
                affiliates=affiliates, reviews=reviews, owner_id=user_id, legacy_products=legacy, legacy_username=legacy_username)


@market.route("/listings", methods=["GET", "POST"])
@login_needed
def listings():
    identity = request.args.get("edit", "")
    if request.method == "POST":
        action = request.form.get("action")
        if action in ("archive", "resubmit", "remove_affiliate"):
            _, ok = mutate(lambda svc, asset: svc.manage_listing(action, request.form.get("listing_id")))
            if ok:
                return redirect(url_for("market.listings"))
            result = None
        else:
            result, ok = mutate(lambda svc, asset: svc.save_listing(request.form, asset, identity or None, request.environ.get("market_image", "")))
        if ok:
            return redirect(url_for("market.listing_detail", listing_id=result))
    with transaction() as store:
        svc = service(store)
        rows = store.all("SELECT * FROM MarketListing WHERE OwnerId=? ORDER BY Created DESC", [svc.user])
        affiliates = store.all("SELECT l.* FROM MarketListing l JOIN MarketAffiliate a ON a.ListingId=l.Id WHERE a.UserId=?", [svc.user])
        editing = svc.listing(identity) if identity else None
        if editing and not (svc.admin or editing["OwnerId"] == svc.user):
            abort(403)
        institute = svc.institute()
    return view("listings", title="My Store", section="listings", listings=rows, affiliates=affiliates,
                editing=editing or {}, institute=institute)


@market.route("/listing/<listing_id>", methods=["GET", "POST"])
def listing_detail(listing_id):
    with transaction() as store:
        svc = service(store)
        row = svc.listing(listing_id)
        access = row["Kind"] == "course" and svc.course_access(listing_id)
        if row["Status"] != "published" and not (svc.admin or row["OwnerId"] == svc.user or access):
            abort(404)
        profile = svc.profile(row["OwnerId"])
        lessons = store.all("SELECT Id,Title,Preview,Position FROM MarketLesson WHERE ListingId=? ORDER BY Position,Id", [listing_id])
    if request.method == "POST":
        if request.form.get("action") == "affiliate":
            _, ok = mutate(lambda svc, asset: svc.add_affiliate(listing_id))
            if ok:
                return redirect(url_for("market.listings"))
        else:
            key = request.form.get("request_key", "")
            require_key(key)
            result, ok = mutate(lambda svc, asset: svc.create_order(listing_id, request.form, key))
            if ok:
                return redirect(url_for("market.order_detail", order_id=result))
    return view("detail", title=row["Title"], section="catalog", item=row, profile=profile,
                access=access, lessons=lessons, referrer=request.args.get("ref", "")[:100])


def require_key(value):
    try:
        UUID(value)
    except (ValueError, TypeError, AttributeError):
        abort(400, "Reopen the order form and try again.")


@market.route("/orders")
@login_needed
def orders():
    role = request.args.get("role", "all")
    query = request.args.get("q", "").strip()[:160]
    page = max(1, min(request.args.get("page", 1, type=int) or 1, 10000))
    with transaction() as store:
        svc = service(store)
        sql, params = "SELECT * FROM MarketOrder WHERE ", []
        if role in ("buying", "selling"):
            sql += ("BuyerId=?" if role == "buying" else "SellerId=?")
            params.append(svc.user)
        else:
            sql += "(BuyerId=? OR SellerId=?)"
            params.extend([svc.user, svc.user])
        if query:
            sql += " AND (Title LIKE ? OR Id=?)"
            params.extend(["%" + query + "%", query])
        rows = store.page(sql + " ORDER BY Created DESC,Id", params, (page-1)*25, 26)
    return view("orders", title="Buying & Selling", section="orders", orders=rows[:25], role=role, query=query,
                page=page, has_next=len(rows)>25)


@market.route("/orders/<order_id>", methods=["GET", "POST"])
@login_needed
def order_detail(order_id):
    if request.method == "POST":
        def callback(svc, asset):
            action = request.form.get("action")
            if action == "message":
                return svc.message(order_id, request.form.get("body"), asset)
            if action == "review":
                return svc.review(order_id, request.form)
            return svc.act_order(order_id, action, request.form, asset)
        _, ok = mutate(callback)
        if ok:
            return redirect(url_for("market.order_detail", order_id=order_id))
    with transaction() as store:
        svc = service(store)
        order = svc.order(order_id)
        messages = store.all("SELECT * FROM MarketMessage WHERE OrderId=? ORDER BY Created", [order_id])
        events = store.all("SELECT * FROM MarketEvent WHERE TargetId=? ORDER BY Created", [order_id])
        review = store.one("SELECT * FROM MarketReview WHERE OrderId=?", [order_id])
        instructions = payment_instructions(store)
    return view("order", title="Order & Work Progress", section="orders", order=order, messages=messages,
                events=events, review=review, payment_instructions=instructions)


@market.route("/jobs", methods=["GET", "POST"])
def jobs():
    if request.method == "POST":
        def create_work(svc, asset):
            require(svc.can_post_jobs(), "Only Customer / Buyer accounts can post work. Designers can apply only.")
            return svc.create_job(request.form)
        result, ok = mutate(create_work)
        if ok:
            return redirect(url_for("market.job_detail", job_id=result))
    with transaction() as store:
        rows = store.all("SELECT * FROM MarketJob WHERE Status='open' OR OwnerId=? ORDER BY Created DESC", [str(session.get("user_id", ""))])
        business = bool(session.get("user_id")) and service(store).business()
        profile = service(store).profile() if session.get("user_id") else None
        can_post = bool(session.get("user_id")) and service(store).can_post_jobs()
        can_apply = bool(session.get("user_id")) and service(store).can_apply_jobs()
        existing_jobs = legacy_jobs.list_jobs(store,session.get('user_id',''))
        open_work=open_jobs(store)
        applications = legacy_jobs.my_applications(store,session.get('user_id','')) if can_apply else []
    return view("jobs", title="Jobs, Bids & Contests", section="jobs", jobs=rows, business=business,
                profile=profile, can_post_jobs=can_post, can_apply_jobs=can_apply, existing_jobs=existing_jobs,applications=applications,open_jobs=open_work,
                design_types=DESIGN_TYPES, selected_job=None, workspace_job_form=True,
                job_post_action=url_for('customer_workspace',section='post-job',workspace=1),
                minimum_deadline=(today()+timedelta(days=1)).isoformat())


@market.route("/jobs/<job_id>", methods=["GET", "POST"])
def job_detail(job_id):
    if request.method == "POST":
        def callback(svc, asset):
            if request.form.get("action") == "propose":
                return svc.propose(job_id, request.form, asset)
            return svc.act_job(job_id, request.form.get("action"), request.form)
        result, ok = mutate(callback)
        if ok:
            return redirect(url_for("market.order_detail", order_id=result) if result else url_for("market.job_detail", job_id=job_id))
    with transaction() as store:
        svc = service(store)
        job = store.get("MarketJob", job_id)
        if not job or (job["Status"] == "funding" and not (svc.admin or job["OwnerId"] == svc.user)):
            abort(404)
        # Private proposals/contest assets are visible only to the author and organizer.
        if svc.admin or job["OwnerId"] == svc.user:
            proposals = store.all("SELECT * FROM MarketProposal WHERE JobId=? ORDER BY Created", [job_id])
        else:
            proposals = store.all("SELECT * FROM MarketProposal WHERE JobId=? AND UserId=?", [job_id, svc.user])
        contract = store.one("SELECT o.Id FROM MarketOrder o JOIN MarketProposal p ON p.Id=o.ProposalId WHERE p.JobId=? AND o.Status NOT IN ('cancelled','refunded')", [job_id]) if (svc.admin or job["OwnerId"] == svc.user or job["WinnerId"] in {proposal["Id"] for proposal in proposals}) else None
        instructions = payment_instructions(store)
    return view("job", title=job["Title"], section="jobs", job=job, proposals=proposals, contract=contract, today=today().isoformat(),
                payment_instructions=instructions, can_post_jobs=svc.can_post_jobs(), can_apply_jobs=svc.can_apply_jobs())


@market.route('/existing-jobs/<int:job_id>', methods=['GET','POST'])
def existing_job_detail(job_id):
    if request.method=='POST':
        selecting=request.form.get('action')=='select_designer'
        result, ok = mutate(lambda svc, asset: legacy_jobs.select_designer(svc,job_id,request.form) if selecting else legacy_jobs.apply_to_job(svc.db,svc.user,job_id,request.form,svc.admin))
        if ok:
            return redirect(url_for('market.order_detail',order_id=result) if selecting else url_for('market.existing_job_detail',job_id=job_id))
    with transaction() as store:
        svc=service(store)
        job=legacy_jobs.get_job(store,job_id)
        if not job:
            abort(404)
        owner=str(job['Customerid'])==svc.user
        kind=str(job.get('BitOrContest') or 'Contest').strip().lower()
        if kind not in {'bit','bid','contest'} and not (owner or svc.admin):
            abort(403)
        if svc.admin or owner:
            applications=store.all('SELECT * FROM JobAppliedList WHERE Jobid=? ORDER BY [Date] DESC',[job_id])
        else:
            applications=store.all('SELECT * FROM JobAppliedList WHERE Jobid=? AND CustomerId=?',[job_id,svc.user])
        open_job=kind in {'bit','bid','contest'} and str(job.get('Status') or '').strip().lower() in {'true','1','active'} and str(job.get('Deadline') or '')[:10]>=today().isoformat()
        mapping=store.get('MarketLegacyContract',job_id)
        contract=store.get('MarketOrder',mapping['OrderId']) if mapping else None
        if contract and not (owner or svc.admin or contract['SellerId']==svc.user):
            contract=None
        submissions=legacy_jobs.job_submissions(store,job_id,svc.user,owner or svc.admin)
        post_allowed=svc.can_post_jobs()
        apply=svc.can_apply_jobs() and not owner and open_job
    return view('existing_job',title=str(job.get('Title') or 'Job Details'),section='jobs',job=job,
                owner=owner,applications=applications,contract=contract,submissions=submissions,can_apply_jobs=apply,can_post_jobs=post_allowed,job_open=open_job,
                is_bid=str(job.get('BitOrContest') or 'Contest').strip().lower() in {'bit','bid'})


@market.route("/earnings", methods=["GET", "POST"])
@login_needed
def earnings():
    if request.method == "POST":
        require_key(request.form.get("request_key"))
        _, ok = mutate(lambda svc, asset: svc.withdraw(request.form))
        if ok:
            return redirect(url_for("market.earnings"))
    with transaction() as store:
        svc = service(store)
        balance = svc.balance()
        ledger = store.all("SELECT * FROM MarketLedger WHERE UserId=? ORDER BY Created DESC", [svc.user])
        withdrawals = store.all("SELECT * FROM MarketWithdrawal WHERE UserId=? ORDER BY Created DESC", [svc.user])
        pending = store.one("SELECT COALESCE(SUM(Amount-Commission),0) AS Total FROM MarketOrder WHERE SellerId=? AND PaymentStatus='paid' AND Status NOT IN ('completed','refunded')", [svc.user])["Total"]
    return view("earnings", title="Earnings & Withdrawals", section="earnings", balance=balance, ledger=ledger,
                withdrawals=withdrawals, pending=pending)


@market.route("/learning")
@login_needed
def learning():
    with transaction() as store:
        rows = store.all("""SELECT l.*, e.Status AS AccessStatus,
            (SELECT COUNT(*) FROM MarketLesson x WHERE x.ListingId=l.Id) AS LessonCount,
            (SELECT COUNT(*) FROM MarketProgress g JOIN MarketLesson x ON x.Id=g.LessonId WHERE x.ListingId=l.Id AND g.UserId=e.UserId) AS CompletedCount
            FROM MarketEnrollment e JOIN MarketListing l ON l.Id=e.ListingId WHERE e.UserId=? ORDER BY e.Created DESC""", [str(session["user_id"])])
    return view("learning", title="My Learning", section="learning", courses=rows)


@market.route("/teaching", methods=["GET", "POST"])
@login_needed
def teaching():
    listing_id = request.values.get("course", "")
    if request.method == "POST":
        def callback(svc, asset):
            if request.form.get("action") == "attendance":
                return svc.attendance(listing_id, request.form)
            if request.form.get("action") == "enroll":
                return svc.enroll_student(listing_id, request.form)
            return svc.lesson(listing_id, request.form, asset)
        result, ok = mutate(callback)
        if ok:
            if result:
                return redirect(url_for("market.order_detail", order_id=result))
            return redirect(url_for("market.teaching", course=listing_id))
    with transaction() as store:
        svc = service(store)
        courses = store.all("SELECT * FROM MarketListing WHERE Kind='course'" + ("" if svc.admin else " AND OwnerId=?"), [] if svc.admin else [svc.user])
        selected = svc.listing(listing_id) if listing_id else None
        if selected and not (selected["Kind"] == "course" and (svc.admin or selected["OwnerId"] == svc.user)):
            abort(403)
        students = store.all("SELECT e.*, p.DisplayName FROM MarketEnrollment e LEFT JOIN MarketProfile p ON p.UserId=e.UserId WHERE e.ListingId=?", [listing_id]) if selected else []
        lessons = store.all("SELECT * FROM MarketLesson WHERE ListingId=? ORDER BY Position,Id", [listing_id]) if selected else []
        attendance = store.all("SELECT * FROM MarketAttendance WHERE ListingId=? ORDER BY ClassDate DESC", [listing_id]) if selected else []
        editing_lesson = store.get("MarketLesson", request.args.get("edit")) if request.args.get("edit") else None
        if editing_lesson and (not selected or editing_lesson["ListingId"] != selected["Id"]):
            abort(403)
    return view("teaching", title="Institute & Course Management", section="teaching", courses=courses, selected=selected,
                students=students, lessons=lessons, attendance=attendance, editing_lesson=editing_lesson or {})


@market.route("/images/<asset>")
def cover_image(asset):
    if Path(asset).name != asset or Path(asset).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        abort(404)
    with transaction() as store:
        row = store.one("SELECT OwnerId,Status FROM MarketListing WHERE Image=?", [asset])
        if not row or not (row["Status"] == "published" or is_admin() or row["OwnerId"] == str(session.get("user_id", ""))):
            abort(404)
    path = asset_directory() / asset
    if not path.is_file():
        abort(404)
    return send_file(path)


@market.route("/lesson/<lesson_id>", methods=["GET", "POST"])
def lesson_detail(lesson_id):
    if request.method == "POST":
        _, ok = mutate(lambda svc, asset: svc.progress(lesson_id))
        if ok:
            return redirect(url_for("market.lesson_detail", lesson_id=lesson_id))
    with transaction() as store:
        svc = service(store)
        lesson = store.get("MarketLesson", lesson_id)
        if not lesson:
            abort(404)
        course = svc.listing(lesson["ListingId"])
        access = svc.course_access(lesson["ListingId"])
        if not access and (not lesson["Preview"] or course["Status"] != "published"):
            abort(403, "Enroll in this course to view the lesson.")
        completed = store.one("SELECT Id FROM MarketProgress WHERE LessonId=? AND UserId=?", [lesson_id, svc.user])
    return view("lesson", title=lesson["Title"], section="learning", lesson=lesson, completed=completed)


@market.route("/admin", methods=["GET", "POST"])
@login_needed
def admin():
    if not is_admin():
        abort(403)
    if request.method == "POST":
        def callback(svc, asset):
            if request.form.get("action") == "configure":
                return svc.configure(request.form)
            return svc.moderate(request.form.get("action"), request.form.get("identity"), request.form)
        _, ok = mutate(callback)
        if ok:
            return redirect(url_for("market.admin"))
    with transaction() as store:
        listings = store.all("SELECT * FROM MarketListing ORDER BY Created DESC")
        profiles = store.all("SELECT * FROM MarketProfile WHERE InstituteStatus='pending'")
        orders = store.all("SELECT * FROM MarketOrder ORDER BY Created DESC")
        jobs = store.all("SELECT * FROM MarketJob WHERE Kind='contest' AND Status IN ('funding','open') ORDER BY Created DESC")
        withdrawals = store.all("SELECT * FROM MarketWithdrawal ORDER BY Created DESC")
        events = store.all("SELECT * FROM MarketEvent ORDER BY Created DESC")[:100]
        instructions = payment_instructions(store)
    return view("admin", title="Platform Management", section="admin", listings=listings, profiles=profiles,
                orders=orders, jobs=jobs, withdrawals=withdrawals, events=events, instructions=instructions)


@market.route("/admin/users", methods=["GET", "POST"])
@login_needed
def admin_users():
    if not is_admin():
        abort(403)
    if request.method == "POST":
        _, ok = mutate(lambda svc, asset: svc.manage_user(request.form))
        if ok:
            return redirect(url_for("market.admin_users"))
    query = request.args.get("q", "").strip()[:160]
    page = max(1, min(request.args.get("page", 1, type=int) or 1, 10000))
    with transaction() as store:
        rows = store.page("SELECT UserId,Username,Email,Phone,UserCatagory,Active,Status FROM Users WHERE Username LIKE ? OR Email LIKE ? ORDER BY UserId", ["%"+query+"%"]*2, (page-1)*25, 26)
    return view("users", title="User Management", section="admin", users=rows[:25], page=page,
                query=query, has_next=len(rows)>25)


@market.route("/files/<asset>")
def download(asset):
    if Path(asset).name != asset:
        abort(404)
    with transaction() as store:
        svc = service(store)
        allowed = False
        # Owners may inspect listing assets; buyers get the order snapshot only after payment.
        rows = store.all("SELECT * FROM MarketListing WHERE Asset=?", [asset])
        allowed = any(svc.admin or row["OwnerId"] == svc.user for row in rows)
        if not allowed:
            orders = store.all("SELECT * FROM MarketOrder WHERE Asset=?", [asset])
            allowed = any(svc.admin or row["SellerId"] == svc.user or
                          (row["BuyerId"] == svc.user and row["PaymentStatus"] == "paid" and row["Status"] not in ("cancelled", "refunded")) for row in orders)
        if not allowed:
            for lesson in store.all("SELECT * FROM MarketLesson WHERE Asset=?", [asset]):
                course = svc.listing(lesson["ListingId"])
                if (lesson["Preview"] and course["Status"] == "published") or svc.course_access(lesson["ListingId"]):
                    allowed = True
        if not allowed:
            for proposal in store.all("SELECT p.*,j.OwnerId FROM MarketProposal p JOIN MarketJob j ON j.Id=p.JobId WHERE p.Asset=?", [asset]):
                if svc.admin or svc.user in (proposal["UserId"], proposal["OwnerId"]):
                    allowed = True
        if not allowed:
            for message in store.all("SELECT m.*,o.BuyerId,o.SellerId FROM MarketMessage m JOIN MarketOrder o ON o.Id=m.OrderId WHERE m.Asset=?", [asset]):
                if svc.admin or svc.user in (message["BuyerId"], message["SellerId"]):
                    allowed = True
        if not allowed:
            abort(403)
    path = asset_directory() / asset
    if not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name="download" + path.suffix)


@market.errorhandler(ValueError)
def invalid_value(error):
    return view("error", title="Please Check Your Information", section="", message=str(error)), 400


@market.errorhandler(HTTPException)
def http_error(error):
    return view("error", title="Unable to Open This Page", section="", message=str(error.description)), error.code


@market.errorhandler(Exception)
def unavailable(error):
    log.exception("Marketplace unavailable")
    return view("error", title="Temporarily Unavailable", section="", message="Unable to load the information. Try again or use your existing dashboard."), 503
