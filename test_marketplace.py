"""Isolated SQLite tests exercise real marketplace SQL/workflows without touching production."""
import io
import re
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from market_db import Store, migrate
from market_service import Marketplace, money, uid


class MarketplaceTest(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.store = Store(self.connection, sqlite=True)
        migrate(self.store)
        self.store.run("CREATE TABLE Users (UserId TEXT PRIMARY KEY, UserCatagory TEXT, Active TEXT, Status TEXT, Username TEXT, Email TEXT, Phone TEXT)")
        self.seller = Marketplace(self.store, "seller")
        self.buyer = Marketplace(self.store, "buyer")
        self.admin = Marketplace(self.store, "admin", True)
        self.ref = Marketplace(self.store, "affiliate")
        self.other = Marketplace(self.store, "stranger")
        for actor in [self.seller, self.buyer, self.admin, self.ref, self.other]:
            actor.save_profile({"name": actor.user, "business": "1"})
            self.store.run("INSERT INTO Users VALUES (?,?,?,?,?,?,?)", [actor.user, "Admin" if actor.admin else "Designer" if actor.user=='seller' else "Customer", "1", "True", actor.user, actor.user+"@test.invalid", "phone-"+actor.user])
        self.connection.commit()

    def tearDown(self):
        self.connection.close()

    def listing(self, kind="product", **overrides):
        values = dict(kind=kind, title="Useful listing", description="Detailed description", price="100.00", stock="5",
                      mode="recorded", license="One user", affiliate="1", commission="10", days="3", revisions="1")
        values.update(overrides)
        if kind == "course":
            self.store.update("MarketProfile", "seller", {"InstituteStatus": "approved"})
        identity = self.seller.save_listing(values, "software.zip" if kind == "software" else "")
        self.admin.moderate("publish", identity, {"body": "Reviewed listing"})
        return identity

    def order(self, listing, **values):
        return self.buyer.create_order(listing, dict(brief="Address or requirements", **values), uid())

    def paid(self, order):
        self.buyer.act_order(order, "payment", {"reference": "TX-" + order})
        self.admin.act_order(order, "verify", {})

    def complete(self, order):
        self.paid(order)
        self.seller.act_order(order, "start", {})
        self.seller.act_order(order, "deliver", {"body": "Delivered"})
        self.buyer.act_order(order, "complete", {})

    def test_migration_repeatable_and_money_validation(self):
        migrate(self.store)
        self.assertEqual(money("12.34"), 1234)
        for invalid in ("nan", "Infinity", "-1", "1.234", "not-money", "100000001"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                money(invalid)

    def test_stock_payment_commission_idempotent_order_and_refund(self):
        listing = self.listing()
        self.ref.add_affiliate(listing)
        key = uid()
        order = self.buyer.create_order(listing, {"brief": "Address", "quantity": "2", "referrer": "affiliate"}, key)
        self.assertEqual(self.buyer.create_order(listing, {}, key), order)
        self.assertEqual(self.seller.listing(listing)["Stock"], 3)
        self.complete(order)
        self.assertEqual(self.seller.balance(), 18000)
        self.assertEqual(self.ref.balance(), 2000)
        with self.assertRaises(ValueError):
            self.buyer.act_order(order, "complete", {})
        self.admin.act_order(order, "refund", {"body": "Refund transaction REF-1"})
        self.assertEqual(self.seller.balance(), 0)
        self.assertEqual(self.ref.balance(), 0)
        self.assertEqual(self.seller.listing(listing)["Stock"], 5)
        with self.assertRaises(ValueError):
            self.admin.act_order(order, "refund", {"body": "again"})

    def test_ownership_stock_and_self_commission_protection(self):
        listing = self.listing()
        with self.assertRaises(ValueError):
            self.seller.create_order(listing, {"brief": "Self purchase"}, uid())
        with self.assertRaises(ValueError):
            self.order(listing, quantity="6")
        order = self.order(listing, referrer="buyer")
        self.assertEqual(self.buyer.order(order)["Commission"], 0)
        with self.assertRaises(ValueError):
            self.other.order(order)
        with self.assertRaises(ValueError):
            self.seller.act_order(order, "verify", {})
        with self.assertRaises(ValueError):
            self.seller.act_order(order, "deliver", {"body": "Unpaid"})
        self.buyer.act_order(order, "cancel", {})
        self.assertEqual(self.seller.listing(listing)["Stock"], 5)

    def test_payment_reference_cannot_be_reused(self):
        listing = self.listing()
        first, second = self.order(listing), self.order(listing)
        self.buyer.act_order(first, "payment", {"reference": "SAME-TX"})
        self.admin.act_order(first, "verify", {})
        self.buyer.act_order(second, "payment", {"reference": "SAME-TX"})
        with self.assertRaises(ValueError):
            self.admin.act_order(second, "verify", {})
        self.assertEqual(self.buyer.order(second)["PaymentStatus"], "pending")

    def test_service_revision_limit_dispute_and_single_settlement(self):
        order = self.order(self.listing("service"))
        self.paid(order)
        self.seller.act_order(order, "deliver", {"body": "Initial delivery"})
        self.buyer.act_order(order, "revision", {"body": "Change heading"})
        self.seller.act_order(order, "deliver", {"body": "Final delivery"})
        with self.assertRaises(ValueError):
            self.buyer.act_order(order, "revision", {"body": "Again"})
        self.buyer.act_order(order, "complete", {})
        self.buyer.act_order(order, "dispute", {"body": "Issue after acceptance"})
        self.admin.act_order(order, "resolve", {"body": "Delivery meets agreement"})
        self.assertEqual(self.seller.balance(), 10000)

    def test_withdraw_reserves_rejection_restores_and_blocks_repeat(self):
        self.complete(self.order(self.listing()))
        request = {"amount": "80", "destination": "Bank account", "request_key": uid()}
        first = self.seller.withdraw(request)
        self.assertEqual(self.seller.withdraw(request), first)
        withdrawal = self.store.one("SELECT * FROM MarketWithdrawal")
        self.assertEqual(self.seller.balance(), 2000)
        with self.assertRaises(ValueError):
            self.seller.withdraw({"amount": "30", "destination": "Bank"})
        self.admin.moderate("withdraw_reject", withdrawal["Id"], {"body": "Incorrect destination"})
        self.assertEqual(self.seller.balance(), 10000)
        with self.assertRaises(ValueError):
            self.admin.moderate("withdraw_reject", withdrawal["Id"], {"body": "Again"})

    def test_refund_blocks_reserved_payout(self):
        order = self.order(self.listing())
        self.complete(order)
        self.seller.withdraw({"amount": "100", "destination": "Bank"})
        withdrawal = self.store.one("SELECT * FROM MarketWithdrawal")
        self.admin.act_order(order, "refund", {"body": "REF-2 external refund"})
        self.assertEqual(self.seller.balance(), -10000)
        with self.assertRaises(ValueError):
            self.admin.moderate("withdraw_paid", withdrawal["Id"], {"body": "Review", "reference": "PAY-1"})

    def test_course_paid_access_progress_and_revocation(self):
        course = self.listing("course")
        self.seller.lesson(course, {"title": "Lesson one", "content": "Private lesson", "position": "1"})
        lesson = self.store.one("SELECT * FROM MarketLesson")
        self.assertFalse(self.buyer.course_access(course))
        with self.assertRaises(ValueError):
            self.buyer.progress(lesson["Id"])
        order = self.order(course)
        self.paid(order)
        self.assertTrue(self.buyer.course_access(course))
        self.buyer.progress(lesson["Id"])
        self.buyer.progress(lesson["Id"])
        self.assertEqual(self.store.one("SELECT COUNT(*) AS N FROM MarketProgress")["N"], 1)
        self.admin.act_order(order, "refund", {"body": "REF-course"})
        self.assertFalse(self.buyer.course_access(course))

    def test_free_course_live_seats_attendance_and_duplicate_enrollment(self):
        course = self.listing("course", price="0", mode="offline", location="Dhaka campus", schedule="Every Friday", stock="1")
        order = self.order(course)
        self.assertEqual(self.buyer.order(order)["Status"], "completed")
        self.assertTrue(self.buyer.course_access(course))
        with self.assertRaises(ValueError):
            self.order(course)
        with self.assertRaises(ValueError):
            self.other.create_order(course, {}, uid())
        self.seller.attendance(course, {"student": "buyer", "date": "2026-10-25", "present": "1"})
        self.seller.attendance(course, {"student": "buyer", "date": "2026-10-25"})
        self.assertEqual(self.store.one("SELECT * FROM MarketAttendance")["Present"], 0)

    def test_software_automatic_fulfillment_and_snapshot(self):
        listing = self.listing("software")
        order = self.order(listing)
        self.paid(order)
        row = self.buyer.order(order)
        self.assertEqual(row["Status"], "completed")
        self.assertEqual(row["Asset"], "software.zip")
        self.assertEqual(self.seller.balance(), 10000)

    def job(self, kind="bid"):
        return self.buyer.create_job(dict(kind=kind, title="Design work", description="Deliver final source, one revision",
                                    budget="200", deadline=(date.today()+timedelta(days=3)).isoformat()))

    def test_bid_hire_and_contest_award_full_contracts(self):
        job = self.job()
        with self.assertRaises(ValueError):
            self.buyer.propose(job, {"body": "Self", "amount": "100"})
        self.seller.propose(job, {"body": "I will deliver in two days", "amount": "150"})
        proposal = self.store.one("SELECT * FROM MarketProposal WHERE JobId=?", [job])
        contract = self.buyer.act_job(job, "hire", {"proposal_id": proposal["Id"]})
        self.assertEqual(self.buyer.order(contract)["Amount"], 15000)
        self.complete(contract)
        with self.assertRaises(ValueError):
            self.buyer.act_job(job, "hire", {"proposal_id": proposal["Id"]})
        contest = self.job("contest")
        with self.assertRaises(ValueError):
            self.seller.propose(contest, {"body": "Too early"}, "entry.pdf")
        self.buyer.act_job(contest, "fund", {"reference": "PRIZE-1"})
        self.admin.act_job(contest, "verify", {})
        self.seller.propose(contest, {"body": "Contest entry"}, "entry.pdf")
        entry = self.store.one("SELECT * FROM MarketProposal WHERE JobId=?", [contest])
        with self.assertRaises(ValueError):
            self.buyer.act_job(contest, "award", {"proposal_id": entry["Id"]})
        self.store.update("MarketJob", contest, {"Deadline": (date.today()-timedelta(days=1)).isoformat()})
        awarded = self.buyer.act_job(contest, "award", {"proposal_id": entry["Id"]})
        self.assertEqual(self.buyer.order(awarded)["PaymentStatus"], "paid")
        self.seller.act_order(awarded, "deliver", {"body": "Final source handover"})
        self.buyer.act_order(awarded, "complete", {})
        self.assertEqual(self.seller.balance(), 35000)

    def test_admin_permissions_institute_and_review_rules(self):
        listing = self.listing()
        with self.assertRaises(ValueError):
            self.buyer.moderate("archive", listing, {"body": "Unauthorized"})
        self.buyer.save_profile({"name": "Buyer", "institute": "1"})
        self.assertFalse(self.buyer.institute())
        self.admin.moderate("institute_approve", "buyer", {"body": "Verified institute"})
        self.assertTrue(self.buyer.institute())
        order = self.order(listing)
        with self.assertRaises(ValueError):
            self.buyer.review(order, {"rating": "5", "body": "Before completion"})
        self.complete(order)
        self.buyer.review(order, {"rating": "5", "body": "Great delivery"})
        with self.assertRaises(ValueError):
            self.buyer.review(order, {"rating": "5", "body": "Duplicate"})

    def test_manual_enrollment_lesson_edit_and_proposal_update(self):
        course = self.listing("course", price="0")
        order = self.seller.enroll_student(course, {"student_login": "buyer"})
        self.assertEqual(self.buyer.order(order)["Status"], "completed")
        self.seller.lesson(course, {"title": "First", "content": "Original", "position": "1"}, "lesson.pdf")
        lesson = self.store.one("SELECT * FROM MarketLesson")
        self.seller.lesson(course, {"lesson_id": lesson["Id"], "title": "Updated", "content": "Corrected", "position": "2"})
        self.assertEqual(self.store.get("MarketLesson", lesson["Id"])["Asset"], "lesson.pdf")
        self.assertEqual(self.store.get("MarketLesson", lesson["Id"])["Title"], "Updated")
        with self.assertRaises(ValueError):
            self.other.enroll_student(course, {"student_login": "buyer"})
        job = self.job()
        self.seller.propose(job, {"body": "Initial proposal", "amount": "100"})
        self.seller.propose(job, {"body": "Updated proposal", "amount": "120"})
        proposals = self.store.all("SELECT * FROM MarketProposal WHERE JobId=?", [job])
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["Amount"], 12000)

    def test_unpaid_contract_cancel_reopens_job_and_admin_user_controls(self):
        job = self.job()
        self.seller.propose(job, {"body": "Proposal", "amount": "100"})
        proposal = self.store.one("SELECT Id FROM MarketProposal WHERE JobId=?", [job])
        order = self.buyer.act_job(job, "hire", {"proposal_id": proposal["Id"]})
        self.buyer.act_order(order, "cancel", {})
        self.assertEqual(self.store.get("MarketJob", job)["Status"], "open")
        self.admin.manage_user({"user_id": "buyer", "category": "Vendor", "active": "1", "body": "Business enabled"})
        self.assertEqual(self.store.one("SELECT UserCatagory FROM Users WHERE UserId='buyer'")["UserCatagory"], "Vendor")
        with self.assertRaises(ValueError):
            self.buyer.manage_user({"user_id": "seller", "category": "Admin", "body": "Escalate"})
        with self.assertRaises(ValueError):
            self.admin.manage_user({"user_id": "admin", "category": "Customer", "body": "Demote myself"})

    def test_listing_archive_affiliate_removal_and_configuration(self):
        listing = self.listing()
        self.ref.add_affiliate(listing)
        self.ref.manage_listing("remove_affiliate", listing)
        self.assertFalse(self.store.one("SELECT Id FROM MarketAffiliate WHERE UserId=?", [self.ref.user]))
        with self.assertRaises(ValueError):
            self.buyer.manage_listing("archive", listing)
        self.seller.manage_listing("archive", listing)
        self.assertEqual(self.seller.listing(listing)["Status"], "archived")
        with self.assertRaises(ValueError):
            self.order(listing)
        self.seller.manage_listing("resubmit", listing)
        self.assertEqual(self.seller.listing(listing)["Status"], "pending")
        with self.assertRaises(ValueError):
            self.buyer.configure({"instructions": "Malicious destination"})
        self.admin.configure({"instructions": "Approved account and payment reference"})
        self.assertEqual(self.store.get("MarketSetting", "payment_instructions")["Value"], "Approved account and payment reference")


class PortalTest(unittest.TestCase):
    listing = MarketplaceTest.listing
    order = MarketplaceTest.order
    paid = MarketplaceTest.paid
    complete = MarketplaceTest.complete
    job = MarketplaceTest.job

    def setUp(self):
        MarketplaceTest.setUp(self)
        from app import app
        self.app = app
        self.temp = tempfile.TemporaryDirectory()
        self.app.config.update(TESTING=True, MARKET_PRIVATE_DIR=self.temp.name)

        @contextmanager
        def isolated_transaction():
            try:
                yield self.store
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise

        self.patch = patch("market_routes.transaction", isolated_transaction)
        self.patch.start()
        self.client = self.app.test_client()
        self.login("buyer")

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()
        MarketplaceTest.tearDown(self)

    def login(self, user, category="Customer"):
        with self.client.session_transaction() as active:
            active.clear()
            active.update(user_id=user, username=user, category=category, market_csrf="test-csrf")

    def post(self, path, **data):
        return self.client.post(path, data={"csrf_token": "test-csrf", **data})

    def test_pages_render_and_workflow_posts(self):
        listing = self.listing()
        course = self.listing("course")
        self.seller.lesson(course, {"title": "Preview", "preview": "1", "content": "Hello", "position": "1"})
        lesson = self.store.one("SELECT * FROM MarketLesson")["Id"]
        job = self.job()
        order = self.order(listing)
        self.connection.commit()
        for path in ("/workspace/", "/workspace/settings", "/workspace/catalog", "/workspace/listings", "/workspace/orders",
                     "/workspace/earnings", "/workspace/learning", "/workspace/teaching", "/workspace/jobs",
                     f"/workspace/store/seller", f"/workspace/listing/{listing}", f"/workspace/orders/{order}",
                     f"/workspace/jobs/{job}", f"/workspace/lesson/{lesson}"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, response.data[:500])
        self.assertEqual(self.client.post("/workspace/settings", data={"name": "no-csrf"}).status_code, 400)
        result = self.post(f"/workspace/orders/{order}", action="message", body="Hello seller")
        self.assertEqual(result.status_code, 302)
        self.assertEqual(self.store.one("SELECT * FROM MarketMessage")["Body"], "Hello seller")
        self.login("admin", "Admin")
        self.assertEqual(self.client.get("/workspace/admin").status_code, 200)
        self.assertEqual(self.client.get("/workspace/admin/users").status_code, 200)
        self.assertEqual(self.client.get(f"/workspace/teaching?course={course}").status_code, 200)

    def test_private_files_require_access_and_refund_revokes(self):
        listing = self.listing("software")
        order = self.order(listing)
        Path(self.temp.name, "software.zip").write_bytes(b"PKtest")
        self.connection.commit()
        self.assertEqual(self.client.get("/workspace/files/software.zip").status_code, 403)
        self.paid(order)
        self.connection.commit()
        response = self.client.get("/workspace/files/software.zip")
        self.assertEqual(response.status_code, 200)
        response.close()
        self.login("stranger")
        self.assertEqual(self.client.get("/workspace/files/software.zip").status_code, 403)
        self.assertEqual(self.client.get(f"/workspace/orders/{order}").status_code, 400)
        self.assertEqual(self.client.get("/workspace/admin").status_code, 403)
        self.admin.act_order(order, "refund", {"body": "REF-3"})
        self.connection.commit()
        self.login("buyer")
        self.assertEqual(self.client.get("/workspace/files/software.zip").status_code, 403)

    def test_transaction_rollback_and_upload_validation(self):
        listing = self.listing()
        self.connection.commit()
        response = self.post(f"/workspace/listing/{listing}", request_key=uid(), quantity="99", brief="No stock")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.store.one("SELECT COUNT(*) AS N FROM MarketOrder")["N"], 0)
        response = self.client.post("/workspace/listings", data={"csrf_token": "test-csrf", "asset": (io.BytesIO(b"bad"), "virus.exe")}, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(list(Path(self.temp.name).iterdir()))

    def test_legacy_navigation_and_shared_role_access(self):
        from app import role_required
        from auth_service import dashboard_endpoint_for
        self.assertEqual(dashboard_endpoint_for("Vendor"), "vendor_dashboard")
        self.assertEqual(dashboard_endpoint_for("POS"), "pos_dashboard")
        for category in ("Customer", "Designer", "Vendor", "Institute", "Admin"):
            with self.app.test_request_context("/"):
                from flask import session
                session.update(user_id="1", category=category)
                self.assertEqual(role_required("Customer")(lambda: "ok")(), "ok")
                self.assertEqual(role_required("Designer", "Freelancer")(lambda: "ok")(), "ok")
        with self.app.test_request_context("/"):
            from flask import session
            session.update(user_id="1", category="Vendor")
            self.assertEqual(role_required("Admin")(lambda: "forbidden")().status_code, 302)

    def test_english_navigation_and_original_default_dashboard(self):
        from auth_service import dashboard_endpoint_for
        for role, endpoint in {"Admin":"admin_dashboard", "Customer":"customer_dashboard", "Vendor":"vendor_dashboard",
                               "Designer":"freelancer_dashboard", "Institute":"course_dashboard", "Student":"course_dashboard",
                               "DeliveryMan":"delivery_dashboard", "POS":"pos_dashboard"}.items():
            self.assertEqual(dashboard_endpoint_for(role), endpoint)
        self.assertEqual(self.client.get('/dashboard').location, '/dashboards/customer')
        for user, category in [('buyer','Customer'),('admin','Admin')]:
            self.login(user, category)
            response = self.client.get('/workspace/catalog')
            self.assertEqual(response.status_code, 200)
            nav = re.search(r'<nav aria-label="Main navigation">(.*?)</nav>', response.get_data(as_text=True), re.S)
            self.assertIsNotNone(nav)
            self.assertIsNone(re.search(r'[\u0980-\u09ff]', nav.group(1)))
        source = Path('templates/base.html').read_text(encoding='utf-8')
        self.assertNotIn('নিজের দোকান সাজান', source)

    def test_existing_designer_menu_exposes_new_features_without_replacing_links(self):
        from flask import render_template, session
        from designer_service import DESIGNER_MENU
        with self.app.test_request_context('/designer/messages'):
            session.update(user_id='seller', username='seller', category='Designer')
            html = render_template('designer_dashboard.html', title='Designer Dashboard', role='Designer',
                                   accent='Designer workspace', section='messages', menu=DESIGNER_MENU,
                                   profile={}, summary={}, messages=[])
        self.assertIn('class="workspace-entry" href="/workspace/"', html)
        self.assertIn('New Features', html)
        for _, href in DESIGNER_MENU:
            self.assertIn('href="' + href + '"', html)
        for href in ['/workspace/listings', '/workspace/jobs', '/workspace/learning', '/workspace/earnings']:
            self.assertIn('href="' + href + '"', html)
        group = re.search(r'<div class="sidebar-menu-group workspace-shortcuts">(.*?)</div>', html, re.S)
        self.assertIsNotNone(group)
        self.assertIsNone(re.search(r'[\u0980-\u09ff]', group.group(1)))

    def render_module(self, name, section='profile', workspace=True):
        from flask import render_template, session
        from customer_service import CUSTOMER_MENU
        from designer_service import DESIGNER_MENU
        customer = name.startswith('customer')
        path = '/customer/' if customer else '/designer/'
        with self.app.test_request_context(path+section+('?workspace=1' if workspace else '')):
            session.update(user_id='seller', username='seller', category='Designer')
            self.app.preprocess_request()
            return render_template(name+'.html', title='Customer Dashboard' if customer else 'Designer Dashboard',
                                   role='Customer' if customer else 'Designer', accent='Account workspace', section=section,
                                   menu=CUSTOMER_MENU if customer else DESIGNER_MENU,
                                   profile={'Username':'seller','UserId':'seller','Status':'True','Active':'1'},
                                   summary={}, stats=[('0','Orders'),('0','Jobs'),('0','Submissions'),('0','Messages')], messages=[], offers=[], service_types=[], designer_expertise=[],
                                   public_profile_url='/freelancer/seller', orders=[], new_orders=[], old_orders=[],
                                   product_options={}, categories=[], subcategories=[], job_types=[], jobs=[])

    def test_workspace_modules_share_shell_and_keep_legacy_design_directly(self):
        for name in ['customer_dashboard','designer_dashboard','customer_order_tracking']:
            html = self.render_module(name)
            self.assertIn('class="m-sidebar"', html)
            self.assertIn('class="workspace-module-body"', html)
            self.assertNotIn('<aside class="sidebar">', html)
            self.assertIn('workspace=1', html)
            direct = self.render_module(name, workspace=False)
            self.assertIn('<aside class="sidebar">', direct)
            self.assertNotIn('class="m-sidebar"', direct)
        tracking = self.render_module('customer_order_tracking')
        self.assertIn('name="workspace" value="1"', tracking)

    def test_workspace_theme_survives_form_redirects_without_changing_business_handlers(self):
        with patch('app.update_customer_password') as update:
            response = self.client.post('/customer/profile?workspace=1', data={'action':'password','old_password':'old','new_password':'new','confirm_password':'new'})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/customer/profile?workspace=1')
            update.assert_called_once_with('buyer','new','old')
        with patch('app.update_designer_password') as update:
            response = self.client.post('/designer/profile?workspace=1', data={'action':'password','old_password':'old','new_password':'new','confirm_password':'new'})
            self.assertEqual(response.location, '/designer/profile?workspace=1')
            update.assert_called_once_with('buyer','new','old')
        self.assertEqual(self.client.get('/dashboard?workspace=1').location, '/dashboards/customer?workspace=1')

    def test_english_workspace_interface_preserves_user_entered_bengali(self):
        for path in Path('templates/market').glob('*.html'):
            self.assertIsNone(re.search(r'[\u0980-\u09ff]', path.read_text(encoding='utf-8')), path.name)
        self.buyer.save_profile({'name':'রহিম', 'bio':'আমার নিজের লেখা'})
        self.connection.commit()
        response = self.client.get('/workspace/settings')
        html = response.get_data(as_text=True)
        self.assertIn('Display Name', html)
        self.assertIn('রহিম', html)
        self.assertIn('আমার নিজের লেখা', html)
        response = self.post('/workspace/settings',name='')
        self.assertIn(b'Enter name', response.data)

    def test_designer_cannot_post_even_with_business_enabled_or_direct_urls(self):
        self.store.run("UPDATE Users SET UserCatagory='Designer' WHERE UserId='buyer'")
        self.connection.commit()
        response = self.client.get('/workspace/jobs')
        self.assertIn(b'Find Work &amp; Apply', response.data)
        self.assertNotIn(b'name="bit_or_contest"', response.data)
        data=dict(kind='bid',title='Forbidden job',description='Details',budget='100',
                  deadline=(date.today()+timedelta(days=3)).isoformat(),enable_business='1')
        self.assertEqual(self.post('/workspace/jobs',**data).status_code,200)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS N FROM MarketJob')['N'],0)
        with patch('app.create_customer_job') as create:
            self.assertEqual(self.client.post('/customer/post-job?workspace=1',data=data).status_code,403)
            create.assert_not_called()
        with self.assertRaises(ValueError):
            self.buyer.create_job(data)

    def test_customer_uses_existing_detailed_job_form_without_business_activation(self):
        self.store.update('MarketProfile','buyer',{'Business':0})
        self.connection.commit()
        response=self.client.get('/workspace/jobs')
        self.assertIn(b'action="/customer/post-job?workspace=1"',response.data)
        for field in ['bit_or_contest','logo_text','must_follow','dont_add','styles','sample_images']:
            self.assertIn(('name="'+field+'"').encode(),response.data)
        self.assertNotIn(b'name="enable_business"',response.data)
        with patch('app.create_customer_job',return_value=123) as create:
            rejected=self.client.post('/customer/post-job?workspace=1',data={'title':'Missing token'})
            self.assertEqual(rejected.status_code,400)
            create.assert_not_called()
            response=self.client.post('/customer/post-job?workspace=1',data={'csrf_token':'test-csrf','title':'Existing job','deadline':'2099-01-01','bit_or_contest':'Bit'})
            self.assertEqual(response.status_code,302)
            self.assertIn('/customer/jobs?workspace=1',response.location)
            create.assert_called_once()
        with self.assertRaises(ValueError):
            self.buyer.propose('missing',{'body':'Not a designer','amount':'100'})

    def seed_existing_jobs(self):
        from legacy_jobs import migrate_applications
        migrate_applications(self.store)
        self.store.run('''CREATE TABLE JobsList (Jobid INTEGER PRIMARY KEY, Title TEXT, Type TEXT,
            Description TEXT, Deadline TEXT, Price NUMERIC, Customerid TEXT, BitOrContest TEXT,
            Status TEXT, MustFollow TEXT, DontAdd TEXT,Logotext TEXT,Location TEXT)''')
        for identity,kind in [(1,'Bit'),(2,'Contest'),(3,'Direct Order')]:
            self.store.run('INSERT INTO JobsList VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                [identity,'Existing '+kind,'Logo Design','Existing scope',(date.today()+timedelta(days=4)).isoformat(),100,
                 'buyer',kind,'True','Use clear text','No copied artwork','Brand','Online'])
        self.connection.commit()

    def test_existing_project_jobs_bid_and_contest_applications_use_existing_schema(self):
        self.seed_existing_jobs()
        self.login('seller','Designer')
        html=self.client.get('/workspace/jobs').data
        self.assertIn(b'Existing Bit',html)
        self.assertIn(b'Existing Contest',html)
        self.assertNotIn(b'Existing Direct Order',html)
        self.assertNotIn(b'name="bit_or_contest"',html)
        self.assertEqual(self.post('/workspace/existing-jobs/1',amount='125',body='I will deliver in two days').status_code,302)
        self.assertEqual(self.post('/workspace/existing-jobs/1',amount='150',body='Updated proposal').status_code,302)
        applications=self.store.all('SELECT * FROM JobAppliedList WHERE Jobid=1')
        self.assertEqual(len(applications),1)
        self.assertEqual(applications[0]['CustomerId'],'seller')
        self.assertEqual(applications[0]['Type'],'Bit')
        self.assertEqual(applications[0]['SetBudget'],150)
        self.assertEqual(self.post('/workspace/existing-jobs/2',body='I will enter this contest').status_code,302)
        self.assertIn(b'/designer/submit?job_id=2&amp;workspace=1',self.client.get('/workspace/existing-jobs/2').data)
        self.assertEqual(self.post('/workspace/existing-jobs/3',body='Not allowed').status_code,403)
        self.assertIsNone(self.store.one('SELECT Id FROM JobAppliedList WHERE Jobid=3'))
        self.login('buyer')
        html=self.client.get('/workspace/existing-jobs/1').data
        self.assertIn(b'Updated proposal',html)
        self.assertNotIn(b'Your Bid (BDT)',html)
        self.assertEqual(self.post('/workspace/existing-jobs/1',amount='50',body='Customer cannot bid').status_code,200)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS N FROM JobAppliedList')['N'],2)

    def test_legacy_bid_contract_payment_revision_completion_and_cancel(self):
        from legacy_jobs import apply_to_job, select_designer
        self.seed_existing_jobs()
        apply_to_job(self.store,'seller',1,{'amount':'145.50','body':'Agreed scope'})
        with self.assertRaises(ValueError):
            select_designer(self.other,1,{'designer_id':'seller'})
        order=select_designer(self.buyer,1,{'designer_id':'seller'})
        self.assertEqual(select_designer(self.buyer,1,{'designer_id':'seller'}),order)
        self.assertEqual(self.store.get('MarketOrder',order)['Amount'],14550)
        self.assertEqual(self.store.one('SELECT Status FROM JobsList WHERE Jobid=1')['Status'],'False')
        with self.assertRaises(ValueError):
            self.seller.act_order(order,'deliver',{'body':'Too early'})
        self.buyer.act_order(order,'cancel',{})
        self.assertEqual(self.store.one('SELECT Status FROM JobsList WHERE Jobid=1')['Status'],'True')
        replacement=select_designer(self.buyer,1,{'designer_id':'seller'})
        self.assertNotEqual(replacement,order)
        self.paid(replacement)
        self.seller.act_order(replacement,'start',{})
        self.seller.act_order(replacement,'deliver',{'body':'First version'})
        self.buyer.act_order(replacement,'revision',{'body':'Adjust spacing'})
        self.seller.act_order(replacement,'deliver',{'body':'Final version'})
        self.buyer.act_order(replacement,'complete',{})
        self.assertEqual(self.store.get('MarketOrder',replacement)['Status'],'completed')
        self.assertEqual(self.store.one("SELECT Amount FROM MarketLedger WHERE SourceId=? AND EntryType='sale'",[replacement])['Amount'],14550)
        with self.assertRaises(ValueError):
            self.buyer.act_order(replacement,'complete',{})
        self.buyer.act_order(replacement,'dispute',{'body':'Support request'})
        self.admin.act_order(replacement,'resolve',{'body':'Accepted evidence'})
        self.assertEqual(self.store.one('SELECT COUNT(*) AS N FROM MarketLedger WHERE SourceId=?',[replacement])['N'],1)
        self.admin.act_order(replacement,'refund',{'body':'Refund transfer TX-123'})
        self.assertEqual(self.store.get('MarketOrder',replacement)['Status'],'refunded')
        self.assertEqual(self.store.one('SELECT SUM(Amount) AS N FROM MarketLedger WHERE SourceId=?',[replacement])['N'],0)

    def test_legacy_contest_winner_handover_and_contract_route(self):
        from legacy_jobs import select_designer
        self.seed_existing_jobs()
        self.store.run('CREATE TABLE Submission (subid INTEGER PRIMARY KEY,userid TEXT,jobid INTEGER,title TEXT,jpgfile TEXT,date TEXT,status TEXT,feedback TEXT,AdminStatus TEXT,Price NUMERIC)')
        for identity,job in [(10,2),(11,1),(12,2)]:
            self.store.run('INSERT INTO Submission VALUES (?,?,?,?,?,?,?,?,?,?)',[identity,'seller',job,'Original design','preview.jpg','2026-10-25','','','',0])
        with self.assertRaises(ValueError):
            select_designer(self.buyer,2,{'submission_id':'11'})
        self.connection.commit()
        self.login('buyer')
        response=self.post('/workspace/existing-jobs/2',action='select_designer',submission_id='10')
        self.assertEqual(response.status_code,302)
        mapping=self.store.get('MarketLegacyContract','2')
        order=mapping['OrderId']
        self.assertIn(order,response.location)
        self.assertEqual(self.store.one('SELECT status FROM Submission WHERE subid=12')['status'],'')
        self.assertEqual(self.store.one('SELECT AdminStatus FROM Submission WHERE subid=10')['AdminStatus'],'')
        self.complete(order)
        self.assertEqual(self.store.get('MarketOrder',order)['Amount'],10000)
        self.assertEqual(self.store.one('SELECT Status FROM JobsList WHERE Jobid=2')['Status'],'False')
        self.assertIn(b'Continue Contract',self.client.get('/workspace/existing-jobs/2').data)
        self.login('stranger')
        self.assertNotIn(order.encode(),self.client.get('/workspace/existing-jobs/2').data)

    def test_existing_job_role_checks_run_before_connection_closes(self):
        import market_routes
        from market_db import Store
        self.seed_existing_jobs()
        original=Store.one
        closed={'value':False}
        @contextmanager
        def scoped_transaction():
            closed['value']=False
            try:
                yield self.store
            finally:
                closed['value']=True
        def checked(store,sql,params=None):
            if closed['value']:
                raise AssertionError('Query after transaction closed')
            return original(store,sql,params or [])
        with patch.object(market_routes,'transaction',scoped_transaction), patch.object(Store,'one',checked):
            self.assertEqual(self.client.get('/workspace/existing-jobs/2').status_code,200)

    def test_contest_has_two_steps_without_application_message(self):
        self.seed_existing_jobs()
        self.login('seller','Designer')
        response=self.client.get('/workspace/existing-jobs/2')
        self.assertIn(b'STEP 1 OF 2',response.data)
        self.assertIn(b'Submit Design',response.data)
        self.assertNotIn(b'name="body"',response.data)
        self.assertNotIn(b'Submit Application',response.data)
        self.assertIn(b'name="amount"',self.client.get('/workspace/existing-jobs/1').data)
        self.assertEqual(self.client.get('/UserUI/Submission.aspx?id=2').location,'/designer/submit?job_id=2&workspace=1')
        with patch('app.create_submission') as save:
            self.assertEqual(self.client.post('/designer/submit?workspace=1',data={'job_id':'2'}).status_code,400)
            save.assert_not_called()
        html=self.render_module('designer_dashboard',section='submit')
        self.assertIn('STEP 2 OF 2',html)
        self.assertIn('Submit &amp; Upload',html)
        self.assertIn('name="jpg_file"',html)
        self.assertIn('name="zip_file"',html)

    def test_original_bid_and_contest_page_links_preserve_job_id(self):
        self.seed_existing_jobs()
        self.login('seller','Designer')
        for url,identity in [('/UserUI/JobsDetails.aspx?id=2',2),('/JobDetails.aspx?Id=1&type=',1)]:
            response=self.client.get(url)
            self.assertEqual(response.status_code,302)
            self.assertTrue(response.location.endswith('/workspace/existing-jobs/'+str(identity)))
            self.assertEqual(self.client.get(response.location).status_code,200)
        self.assertEqual(self.client.get('/JobDetails.aspx?Id=bad&type=').status_code,400)
        self.assertEqual(self.client.get('/UserUI/JobsDetails.aspx?id=99999',follow_redirects=True).status_code,404)

    def test_homepage_and_workspace_use_same_real_open_job_feed(self):
        from job_feed import open_jobs
        from market_routes import public_home_jobs
        self.seed_existing_jobs()
        self.store.run("UPDATE JobsList SET Status='False' WHERE Jobid=1")
        modern=self.job()
        self.connection.commit()
        rows=open_jobs(self.store)
        self.assertEqual({str(row['Id']) for row in rows},{'2'})
        legacy=next(row for row in rows if row['Source']=='existing')
        self.assertEqual(legacy['Budget'],10000)
        self.assertEqual(legacy['Endpoint'],'market.existing_job_detail')
        with self.app.test_request_context('/login'):
            self.assertEqual(public_home_jobs(),open_jobs(self.store,limit=6))
        self.login('seller','Designer')
        response=self.client.get('/workspace/jobs')
        self.assertIn(b'Recently Posted Jobs',response.data)
        self.assertIn(b'/workspace/existing-jobs/2',response.data)
        self.assertNotIn(b'Existing Bit',response.data)
        self.store.run("UPDATE JobsList SET Deadline='2000-01-01' WHERE Jobid=2")
        self.store.update('MarketJob',modern,{'Status':'funding'})
        self.connection.commit()
        self.assertEqual(open_jobs(self.store),[])

    def test_customer_cannot_use_designer_submission_endpoint_and_stale_role_is_checked(self):
        self.assertEqual(self.client.post('/designer/submit?workspace=1',data={'job_id':'1'}).status_code,403)
        self.login('seller','Designer')
        self.store.run("UPDATE Users SET UserCatagory='Customer' WHERE UserId='seller'")
        self.connection.commit()
        job=self.job()
        self.assertEqual(self.post('/workspace/jobs/'+job,action='propose',amount='100',body='Spoofed designer').status_code,200)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS N FROM MarketProposal')['N'],0)

    def test_public_registration_cannot_create_admin_and_stale_admin_is_denied(self):
        from auth_service import create_user
        with self.assertRaises(ValueError):
            create_user("untrusted", "test@example.invalid", "", "password", "Admin", "")
        with patch("app.create_user") as create, patch("app.render_template", return_value="registration"):
            response = self.client.post("/register", data={"username": "untrusted", "email": "test@example.invalid", "password": "password", "confirm_password": "password", "category": "Admin"})
            self.assertEqual(response.status_code, 200)
            create.assert_not_called()
        self.login("buyer", "Admin")
        self.assertEqual(self.client.get("/workspace/admin").status_code, 403)
        self.store.run("UPDATE Users SET Active='0' WHERE UserId='buyer'")
        self.connection.commit()
        self.assertEqual(self.client.get("/workspace/").status_code, 302)

    def test_cover_image_and_private_preview_access(self):
        self.login("seller")
        response = self.client.post("/workspace/listings", data={"csrf_token": "test-csrf", "kind": "product", "title": "Photo item",
            "description": "Photo description", "price": "100", "stock": "2", "image": (io.BytesIO(b'\x89PNG\r\n\x1a\nfake-test-image'), "cover.png")}, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 302)
        listing = self.store.one("SELECT * FROM MarketListing WHERE Title='Photo item'")
        self.assertTrue(listing["Image"])
        self.login("stranger")
        self.assertEqual(self.client.get("/workspace/images/" + listing["Image"]).status_code, 404)
        self.admin.moderate("publish", listing["Id"], {"body": "Reviewed"})
        self.connection.commit()
        response = self.client.get("/workspace/images/" + listing["Image"])
        self.assertEqual(response.status_code, 200)
        response.close()
        course = self.listing("course")
        self.seller.lesson(course, {"title": "Hidden preview", "preview": "1", "position": "1"})
        lesson = self.store.one("SELECT Id FROM MarketLesson WHERE ListingId=?", [course])
        self.admin.moderate("archive", course, {"body": "Temporarily unavailable"})
        self.connection.commit()
        self.assertEqual(self.client.get("/workspace/lesson/"+lesson["Id"]).status_code, 403)


if __name__ == "__main__":
    unittest.main()

