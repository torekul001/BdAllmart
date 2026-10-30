"""Transactional workflows for the unified marketplace (all monetary values in paisa)."""
import json
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from job_permissions import actor_category, can_post, can_apply

KINDS = {"product": "Products", "software": "Software", "service": "Services", "course": "Courses"}
MODES = {"recorded": "Recorded", "live": "Online Live", "offline": "Offline"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def uid():
    return str(uuid4())


def today():
    return datetime.now(timezone(timedelta(hours=6))).date()


def money(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or result > 100000000 or result.as_tuple().exponent < -2:
            raise ValueError
        return int(result * 100)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Enter a valid amount with no more than two decimal places.")


def number(value, minimum=0, maximum=100000):
    try:
        result = int(value)
    except (ValueError, TypeError):
        raise ValueError("Enter a valid whole number.")
    if not minimum <= result <= maximum:
        raise ValueError(f"Enter a whole number between {minimum} and {maximum}.")
    return result


def text(value, label, maximum=2000, required=True):
    value = str(value or "").strip()
    if (required and not value) or len(value) > maximum:
        raise ValueError(f"Enter {label} (maximum {maximum} characters).")
    return value


def require(condition, message="You do not have permission, or this action is not available in the current state."):
    if not condition:
        raise ValueError(message)


def meta(row):
    return json.loads(row.get("Meta") or "{}")


class Marketplace:
    def __init__(self, store, user_id, admin=False):
        self.db = store
        self.user = str(user_id)
        self.admin = admin

    def event(self, target, action, details="", recipient=""):
        self.db.insert("MarketEvent", dict(Id=uid(), ActorId=self.user, TargetId=str(target), Event=action,
                                         Details=str(details)[:2000], RecipientId=str(recipient), Created=now()))

    def profile(self, user=None, lock=False):
        return self.db.get("MarketProfile", user or self.user, lock, "UserId")

    def save_profile(self, data):
        previous = self.profile(lock=True)
        values = dict(DisplayName=text(data.get("name"), "name", 160), Bio=text(data.get("bio"), "introduction", required=False),
                      Business=1 if data.get("business") else 0)
        if previous:
            self.db.update("MarketProfile", self.user, values)
        else:
            self.db.insert("MarketProfile", dict(UserId=self.user, InstituteStatus="none", **values))
        if data.get("institute") and (not previous or previous["InstituteStatus"] in ("none", "rejected")):
            self.db.update("MarketProfile", self.user, {"InstituteStatus": "pending"})
        self.event(self.user, "profile.updated")

    def institute(self):
        profile = self.profile()
        return self.admin or bool(profile and profile["InstituteStatus"] == "approved")

    def business(self):
        profile = self.profile()
        return self.admin or bool(profile and profile["Business"])

    def listing(self, listing_id, lock=False):
        row = self.db.get("MarketListing", listing_id, lock)
        require(row is not None, "Listing not found.")
        return row

    def save_listing(self, data, asset="", identity=None, image=""):
        require(self.profile(), "Save your name and introduction in Profile & Features first.")
        previous = self.listing(identity, True) if identity else None
        require(not previous or self.admin or previous["OwnerId"] == self.user)
        kind = previous["Kind"] if previous else data.get("kind")
        require(kind in KINDS, "Select a listing type.")
        if kind == "course":
            require(self.institute(), "Institute approval is required to publish courses.")
        mode = data.get("mode", "recorded") if kind == "course" else kind
        require(kind != "course" or mode in MODES)
        details = {key: text(data.get(key), key, 1500, False) for key in
                   ("terms", "schedule", "location", "meeting", "license", "compatibility")}
        details["days"] = number(data.get("days", 7), 1, 365)
        details["revisions"] = number(data.get("revisions", 1), 0, 50)
        if kind == "course" and mode in ("live", "offline"):
            require(details["schedule"], "Enter the class schedule.")
            require(details["meeting"] if mode == "live" else details["location"], "Enter the class link or address.")
        if kind == "software":
            require(asset or (previous and previous["Asset"]), "Upload the software delivery file as ZIP or PDF.")
            require((asset or previous["Asset"]).lower().endswith((".zip", ".pdf")), "Software must be provided as a ZIP or PDF file.")
            require(details["license"], "Enter the software license terms.")
        if previous:
            active = self.db.one("SELECT COUNT(*) AS N FROM MarketOrder WHERE ListingId=? AND Status NOT IN ('completed','cancelled','refunded')", [identity])
            if kind == "course":
                require(not active["N"], "Core course terms cannot change while an order is active.")
                enrolled = self.db.one("SELECT COUNT(*) AS N FROM MarketEnrollment WHERE ListingId=? AND Status='active'", [identity])
                require(not enrolled["N"], "Core terms of an enrolled course cannot change. Create a new batch instead.")
        values = dict(Kind=kind, Mode=mode, Title=text(data.get("title"), "title", 180),
                      Description=text(data.get("description"), "description", 12000), Price=money(data.get("price")),
                      Stock=number(data.get("stock", 1), 0), Status="published" if self.admin else "pending",
                      Commission=number(data.get("commission", 0), 0, 80), Affiliate=1 if data.get("affiliate") else 0,
                      Asset=asset or (previous["Asset"] if previous else ""), Image=image or (previous["Image"] if previous else ""),
                      Meta=json.dumps(details, ensure_ascii=False))
        require(values["Price"] > 0 or kind == "course", "Only courses can be offered free of charge.")
        identity = identity or uid()
        if previous:
            self.db.update("MarketListing", identity, values)
        else:
            self.db.insert("MarketListing", dict(Id=identity, OwnerId=self.user, Created=now(), **values))
        self.event(identity, "listing.submitted")
        return identity

    def add_affiliate(self, listing_id):
        listing = self.listing(listing_id, True)
        require(listing["Status"] == "published" and listing["Affiliate"] and listing["OwnerId"] != self.user)
        previous = self.db.one("SELECT Id FROM MarketAffiliate WHERE UserId=? AND ListingId=?", [self.user, listing_id])
        if not previous:
            self.db.insert("MarketAffiliate", dict(Id=uid(), UserId=self.user, ListingId=listing_id, Created=now()))
        self.event(listing_id, "affiliate.added")

    def manage_listing(self, action, listing_id):
        listing = self.listing(listing_id, True)
        if action == "remove_affiliate":
            self.db.run("DELETE FROM MarketAffiliate WHERE ListingId=? AND UserId=?", [listing_id, self.user])
        else:
            require(self.admin or listing["OwnerId"] == self.user)
            require(action in ("archive", "resubmit"))
            require((action == "archive" and listing["Status"] == "published") or
                    (action == "resubmit" and listing["Status"] in ("archived", "rejected")))
            self.db.update("MarketListing", listing_id, {"Status": "archived" if action == "archive" else "pending"})
        self.event(listing_id, "listing."+action)

    def configure(self, data):
        require(self.admin)
        value = text(data.get("instructions"), "approved payment instructions", 4000, False)
        if self.db.get("MarketSetting", "payment_instructions", True):
            self.db.update("MarketSetting", "payment_instructions", {"Value": value, "Updated": now()})
        else:
            self.db.insert("MarketSetting", dict(Id="payment_instructions", Value=value, Updated=now()))
        self.event("payment_instructions", "configuration.updated", "Payment instructions updated")

    def ledger(self, user, source, kind, amount, note=""):
        self.db.insert("MarketLedger", dict(Id=uid(), UserId=str(user), SourceId=source, EntryType=kind,
                                          Amount=amount, Note=note, Created=now()))

    def balance(self, user=None):
        row = self.db.one("SELECT COALESCE(SUM(Amount),0) AS Total FROM MarketLedger WHERE UserId=?", [user or self.user])
        return int(row["Total"])

    def order(self, order_id, lock=False):
        row = self.db.get("MarketOrder", order_id, lock)
        require(row and (self.admin or self.user in (row["BuyerId"], row["SellerId"])), "Order not found or access denied.")
        return row

    def create_order(self, listing_id, data, request_key):
        # Unique request key is also stored with the order; retries return the original order.
        listing = self.listing(listing_id, True)
        prior = self.db.one("SELECT * FROM MarketOrder WHERE RequestKey=?", [request_key])
        if prior:
            require(prior["BuyerId"] == self.user)
            return prior["Id"]
        require(listing["Status"] == "published" and listing["OwnerId"] != self.user, "You cannot buy your own listing or an unpublished listing.")
        quantity = number(data.get("quantity", 1), 1, 100)
        if listing["Kind"] != "product":
            require(quantity == 1)
        if listing["Kind"] == "course":
            require(not self.db.one("SELECT Id FROM MarketEnrollment WHERE ListingId=? AND UserId=? AND Status='active'", [listing_id, self.user]), "You are already enrolled in this course.")
            require(not self.db.one("SELECT Id FROM MarketOrder WHERE ListingId=? AND BuyerId=? AND Status NOT IN ('cancelled','refunded')", [listing_id, self.user]), "You already have an order for this course. Check your orders.")
        reserve = listing["Kind"] == "product" or (listing["Kind"] == "course" and listing["Mode"] != "recorded")
        if reserve:
            require(listing["Stock"] >= quantity, "Not enough stock or seats are available.")
        brief = text(data.get("brief"), "address / requirements", 6000, listing["Kind"] in ("product", "service"))
        referrer = str(data.get("referrer", ""))
        ref = self.db.one("SELECT Id FROM MarketAffiliate WHERE UserId=? AND ListingId=?", [referrer, listing_id]) if referrer else None
        if not listing["Affiliate"] or not ref or referrer in (self.user, listing["OwnerId"]):
            referrer = ""
        amount = listing["Price"] * quantity
        order_id = uid()
        values = dict(Id=order_id, BuyerId=self.user, SellerId=listing["OwnerId"], ListingId=listing_id, ProposalId="",
                      Kind=listing["Kind"], Title=listing["Title"], Amount=amount, Quantity=quantity, Status="placed",
                      PaymentStatus="pending", PaymentRef="", ReferrerId=referrer,
                      Commission=amount * listing["Commission"] // 100 if referrer else 0,
                      Brief=brief, Delivery="", Asset=listing["Asset"], Meta=listing["Meta"], RequestKey=request_key, Created=now())
        self.db.insert("MarketOrder", values)
        if reserve:
            self.db.update("MarketListing", listing_id, {"Stock": listing["Stock"] - quantity})
        self.event(order_id, "order.placed", recipient=listing["OwnerId"])
        if amount == 0:
            self.db.update("MarketOrder", order_id, {"PaymentStatus": "paid"})
            values["PaymentStatus"] = "paid"
            self.finish(values)
        return order_id

    def finish(self, order):
        require(order["PaymentStatus"] == "paid")
        self.db.update("MarketOrder", order["Id"], {"Status": "completed"})
        self.ledger(order["SellerId"], order["Id"], "sale", order["Amount"] - order["Commission"], order["Title"])
        if order["ReferrerId"]:
            self.ledger(order["ReferrerId"], order["Id"], "commission", order["Commission"], order["Title"])
        if order["Kind"] == "course":
            existing = self.db.one("SELECT * FROM MarketEnrollment WHERE ListingId=? AND UserId=?", [order["ListingId"], order["BuyerId"]])
            if existing:
                self.db.update("MarketEnrollment", existing["Id"], {"Status": "active", "OrderId": order["Id"]})
            else:
                self.db.insert("MarketEnrollment", dict(Id=uid(), ListingId=order["ListingId"], UserId=order["BuyerId"],
                                                       OrderId=order["Id"], Status="active", Created=now()))
        if order["Kind"] == "job":
            job_id = meta(order).get("job_id")
            if job_id:
                self.db.update("MarketJob", job_id, {"Status": "completed"})
        self.event(order["Id"], "order.completed", recipient=order["SellerId"])

    def claim_payment(self, reference, source):
        reference = text(reference, "payment transaction reference", 120)
        claim = self.db.get("MarketPaymentClaim", reference, True, "Reference")
        require(not claim, "This payment reference has already been used.")
        self.db.insert("MarketPaymentClaim", dict(Reference=reference, SourceId=source, Created=now()))
        return reference

    def act_order(self, order_id, action, data, asset=""):
        order = self.order(order_id, True)
        state, paid = order["Status"], order["PaymentStatus"]
        buyer, seller = self.user == order["BuyerId"], self.user == order["SellerId"]
        terminal = state in ("cancelled", "refunded", "completed")
        if action == "payment":
            require(buyer and not terminal and paid == "pending")
            reference = text(data.get("reference"), "payment reference", 120)
            self.db.update("MarketOrder", order_id, {"PaymentRef": reference})
        elif action == "verify":
            require(self.admin and paid == "pending" and state == "placed")
            self.claim_payment(order["PaymentRef"], order_id)
            self.db.update("MarketOrder", order_id, {"PaymentStatus": "paid", "Status": "confirmed"})
            order["PaymentStatus"] = "paid"
            if order["Kind"] in ("software", "course"):
                self.finish(order)
        elif action == "start":
            require((seller or self.admin) and paid == "paid" and state == "confirmed")
            self.db.update("MarketOrder", order_id, {"Status": "in_progress"})
        elif action == "deliver":
            require((seller or self.admin) and paid == "paid" and state in ("confirmed", "in_progress", "revision"))
            delivery = text(data.get("body"), "delivery details / tracking", 6000)
            self.db.update("MarketOrder", order_id, {"Status": "delivered", "Delivery": delivery, "Asset": asset or order["Asset"]})
        elif action == "revision":
            require(buyer and state == "delivered" and order["Kind"] in ("service", "job"))
            details = meta(order)
            used = int(details.get("revision_used", 0))
            require(used < int(details.get("revisions", 1)), "No included revisions remain. Open a dispute if necessary.")
            details["revision_used"] = used + 1
            self.db.update("MarketOrder", order_id, {"Status": "revision", "Meta": json.dumps(details)})
            self.message(order_id, text(data.get("body"), "revision instructions", 6000))
        elif action == "complete":
            require((buyer or self.admin) and paid == "paid" and state == "delivered")
            self.finish(order)
        elif action == "cancel":
            require((buyer or self.admin) and paid == "pending" and state == "placed")
            self.restore_stock(order)
            self.db.update("MarketOrder", order_id, {"Status": "cancelled"})
            if order["Kind"] == "job":
                job_id = meta(order).get("job_id")
                job = self.db.get("MarketJob", job_id, True)
                if job and job["Kind"] == "bid":
                    self.db.update("MarketJob", job_id, {"Status": "open" if job["Deadline"] >= today().isoformat() else "cancelled", "WinnerId": ""})
                    self.db.update("MarketProposal", order["ProposalId"], {"Status": "submitted"})
        elif action == "dispute":
            require(not self.admin and paid == "paid" and state not in ("refunded", "cancelled", "disputed"))
            self.db.update("MarketOrder", order_id, {"Status": "disputed"})
            self.message(order_id, text(data.get("body"), "dispute reason", 6000))
        elif action == "resolve":
            require(self.admin and state == "disputed" and paid == "paid")
            require(text(data.get("body"), "decision reason", 2000))
            # A completed sale already has ledger credits. Do not credit twice.
            settled = self.db.one("SELECT Id FROM MarketLedger WHERE SourceId=? AND EntryType='sale'", [order_id])
            if settled:
                self.db.update("MarketOrder", order_id, {"Status": "completed"})
                if order["Kind"] == "job" and meta(order).get("job_id"):
                    self.db.update("MarketJob", meta(order)["job_id"], {"Status": "completed"})
            else:
                self.finish(order)
        elif action == "refund":
            require(self.admin and paid == "paid" and state not in ("refunded", "cancelled"))
            reason = text(data.get("body"), "refund reason and actual refund transaction reference", 2000)
            require(order["Amount"] > 0, "Free orders cannot be refunded.")
            # Refunding is an admin attestation that the external transfer has occurred.
            credits = self.db.all("SELECT * FROM MarketLedger WHERE SourceId=? AND EntryType IN ('sale','commission')", [order_id])
            for user in sorted({credit["UserId"] for credit in credits}):
                self.profile(user, True)
            for credit in credits:
                self.ledger(credit["UserId"], order_id, "refund_" + credit["EntryType"], -credit["Amount"], reason)
            self.restore_stock(order)
            self.db.update("MarketOrder", order_id, {"Status": "refunded", "PaymentStatus": "refunded"})
            if order["Kind"] == "job" and meta(order).get("job_id"):
                self.db.update("MarketJob", meta(order)["job_id"], {"Status": "cancelled"})
            enroll = self.db.one("SELECT * FROM MarketEnrollment WHERE OrderId=?", [order_id])
            if enroll:
                self.db.update("MarketEnrollment", enroll["Id"], {"Status": "revoked"})
        else:
            raise ValueError("Unknown order action.")
        if meta(order).get("legacy_job_id"):
            from legacy_jobs import sync_contract
            sync_contract(self, order, action)
        self.event(order_id, "order." + action, str(data.get("body", "")), order["SellerId"] if buyer else order["BuyerId"])

    def restore_stock(self, order):
        if not order["ListingId"]:
            return
        listing = self.listing(order["ListingId"], True)
        if listing["Kind"] == "product" or (listing["Kind"] == "course" and listing["Mode"] != "recorded"):
            self.db.update("MarketListing", listing["Id"], {"Stock": listing["Stock"] + order["Quantity"]})

    def message(self, order_id, body, asset=""):
        order = self.order(order_id)
        self.db.insert("MarketMessage", dict(Id=uid(), OrderId=order_id, SenderId=self.user,
                                           Body=text(body, "message", 6000), Asset=asset, Created=now()))
        self.event(order_id, "message.received", recipient=order["SellerId"] if self.user == order["BuyerId"] else order["BuyerId"])

    def review(self, order_id, data):
        order = self.order(order_id, True)
        require(order["BuyerId"] == self.user and order["Status"] == "completed")
        require(not self.db.one("SELECT Id FROM MarketReview WHERE OrderId=?", [order_id]), "You have already submitted a review.")
        self.db.insert("MarketReview", dict(Id=uid(), OrderId=order_id, UserId=self.user, SellerId=order["SellerId"],
                                          Rating=number(data.get("rating"), 1, 5), Body=text(data.get("body"), "Review", 2000), Created=now()))

    def create_job(self, data):
        require(self.can_post_jobs(), "Only Customer / Buyer accounts can post jobs or contests. Designers can apply only.")
        kind = data.get("kind")
        require(kind in ("bid", "contest"))
        deadline = text(data.get("deadline"), "Deadline", 10)
        try:
            require(date.fromisoformat(deadline) > today(), "Choose a future deadline.")
        except ValueError:
            raise ValueError("Enter a valid future deadline.")
        budget = money(data.get("budget"))
        require(budget > 0, "The budget must be greater than zero.")
        identity = uid()
        self.db.insert("MarketJob", dict(Id=identity, OwnerId=self.user, Kind=kind, Title=text(data.get("title"), "Title", 180),
                                        Description=text(data.get("description"), "Scope / judging rules / deliverables", 12000),
                                        Budget=budget, Deadline=deadline, Status="funding" if kind == "contest" else "open",
                                        PaymentRef="", WinnerId="", Created=now()))
        self.event(identity, "job.created")
        return identity

    def propose(self, job_id, data, asset=""):
        require(self.can_apply_jobs(), "Only Designer / Freelancer accounts can apply to jobs and contests.")
        require(self.profile(), "Complete your profile before submitting a proposal.")
        job = self.db.get("MarketJob", job_id, True)
        require(job and job["Status"] == "open" and job["OwnerId"] != self.user)
        require(job["Deadline"] >= today().isoformat(), "The submission deadline has passed.")
        previous = self.db.one("SELECT * FROM MarketProposal WHERE JobId=? AND UserId=?", [job_id, self.user])
        require(job["Kind"] != "contest" or asset or (previous and previous["Asset"]), "Upload a file for your contest entry.")
        amount = job["Budget"] if job["Kind"] == "contest" else money(data.get("amount"))
        require(amount > 0)
        values = dict(Body=text(data.get("body"), "proposal / entry description", 6000), Amount=amount,
                      Asset=asset or (previous["Asset"] if previous else ""), Status="submitted")
        if previous:
            require(previous["Status"] == "submitted")
            self.db.update("MarketProposal", previous["Id"], values)
        else:
            self.db.insert("MarketProposal", dict(Id=uid(), JobId=job_id, UserId=self.user, Created=now(), **values))
        self.event(job_id, "proposal.received", recipient=job["OwnerId"])

    def act_job(self, job_id, action, data):
        require(self.admin or self.can_post_jobs(), "Only the Customer / Buyer can manage posted work.")
        job = self.db.get("MarketJob", job_id, True)
        require(job and (self.admin or job["OwnerId"] == self.user))
        if action == "fund":
            require(job["Status"] == "funding")
            self.db.update("MarketJob", job_id, {"PaymentRef": text(data.get("reference"), "Prize payment reference", 120)})
        elif action == "verify":
            require(self.admin and job["Status"] == "funding")
            require(job["Deadline"] >= today().isoformat(), "The contest deadline has passed. Create a new contest.")
            self.claim_payment(job["PaymentRef"], job_id)
            self.db.update("MarketJob", job_id, {"Status": "open"})
        elif action in ("hire", "award"):
            require(job["Status"] == "open")
            require((action == "hire" and job["Kind"] == "bid") or (action == "award" and job["Kind"] == "contest"))
            proposal = self.db.get("MarketProposal", data.get("proposal_id"), True)
            require(proposal and proposal["JobId"] == job_id and proposal["UserId"] != job["OwnerId"])
            identity = uid()
            is_contest = job["Kind"] == "contest"
            require(not is_contest or job["Deadline"] < today().isoformat(), "Select a winner after the contest submission deadline has passed.")
            self.db.insert("MarketOrder", dict(Id=identity, BuyerId=job["OwnerId"], SellerId=proposal["UserId"], ListingId="", ProposalId=proposal["Id"],
                        Kind="job", Title=job["Title"], Amount=proposal["Amount"], Quantity=1, Status="confirmed" if is_contest else "placed",
                        PaymentStatus="paid" if is_contest else "pending", PaymentRef=job["PaymentRef"] if is_contest else "",
                        ReferrerId="", Commission=0, Brief=job["Description"] + "\n\nAccepted proposal: " + proposal["Body"], Delivery="", Asset=proposal["Asset"],
                        Meta=json.dumps({"revisions": 1, "deadline": job["Deadline"], "job_id": job_id}), RequestKey=uid(), Created=now()))
            self.db.update("MarketJob", job_id, {"Status": "awarded" if is_contest else "hired", "WinnerId": proposal["Id"]})
            self.db.update("MarketProposal", proposal["Id"], {"Status": "accepted"})
            self.event(identity, "contract.created", recipient=proposal["UserId"])
            return identity
        elif action == "cancel":
            require(job["Status"] in ("funding", "open"))
            if job["Kind"] == "contest" and job["Status"] == "open":
                require(self.admin, "Contact an admin to cancel a funded contest.")
                text(data.get("body"), "Prize refund reference / cancellation reason", 2000)
            self.db.update("MarketJob", job_id, {"Status": "cancelled"})
        else:
            raise ValueError("Unknown job action.")
        self.event(job_id, "job." + action, str(data.get("body", "")), job["OwnerId"])

    def withdraw(self, data):
        require(self.profile(lock=True), "Complete your profile in Settings first.")
        request_key = data.get("request_key") or uid()
        previous = self.db.one("SELECT * FROM MarketWithdrawal WHERE RequestKey=?", [request_key])
        if previous:
            require(previous["UserId"] == self.user)
            return previous["Id"]
        amount = money(data.get("amount"))
        require(0 < amount <= self.balance(), "You do not have enough available balance for this withdrawal.")
        identity = uid()
        destination = text(data.get("destination"), "withdrawal method and account", 300)
        self.db.insert("MarketWithdrawal", dict(Id=identity, UserId=self.user, Amount=amount, Destination=destination,
                                               Status="requested", Reference="", RequestKey=request_key, Created=now()))
        self.ledger(self.user, identity, "withdrawal", -amount, destination)
        self.event(identity, "withdrawal.requested")
        return identity

    def course_access(self, listing_id, user=None):
        listing = self.listing(listing_id)
        who = user or self.user
        return self.admin or listing["OwnerId"] == who or bool(self.db.one(
            "SELECT Id FROM MarketEnrollment WHERE ListingId=? AND UserId=? AND Status='active'", [listing_id, who]))

    def lesson(self, listing_id, data, asset=""):
        listing = self.listing(listing_id, True)
        require(listing["Kind"] == "course" and (self.admin or listing["OwnerId"] == self.user))
        video = text(data.get("video"), "video link", 1000, False)
        require(not video or video.startswith("https://"), "Enter an HTTPS video URL.")
        previous = self.db.get("MarketLesson", data.get("lesson_id"), True) if data.get("lesson_id") else None
        require(not data.get("lesson_id") or (previous and previous["ListingId"] == listing_id))
        values = dict(Title=text(data.get("title"), "Lesson title", 180),
                         Content=text(data.get("content"), "lesson content", 12000, False), Video=video, Asset=asset,
                         Preview=1 if data.get("preview") else 0, Position=number(data.get("position", 1), 1))
        if previous:
            values["Asset"] = asset or previous["Asset"]
            self.db.update("MarketLesson", previous["Id"], values)
        else:
            self.db.insert("MarketLesson", dict(Id=uid(), ListingId=listing_id, **values))
        self.event(listing_id, "lesson.updated" if previous else "lesson.created")

    def enroll_student(self, listing_id, data):
        listing = self.listing(listing_id, True)
        require(listing["Kind"] == "course" and (self.admin or listing["OwnerId"] == self.user))
        login = text(data.get("student_login"), "student username / email / phone", 160)
        student = self.db.one("SELECT UserId,Active,Status FROM Users WHERE Username=? OR Email=? OR Phone=?", [login, login, login])
        require(student and str(student["Active"]).strip().lower() in ("true", "1") and str(student["Status"] or "").strip().lower() in ("", "true"), "No active student account was found. Ask the student to register first.")
        buyer = Marketplace(self.db, str(student["UserId"]))
        identity = buyer.create_order(listing_id, {"brief": "Institute enrollment"}, uid())
        if listing["Price"]:
            buyer.act_order(identity, "payment", {"reference": text(data.get("reference"), "Fee payment reference", 120)})
        self.event(identity, "institute.enrollment_requested", recipient=str(student["UserId"]))
        return identity

    def progress(self, lesson_id):
        lesson = self.db.get("MarketLesson", lesson_id, True)
        require(lesson and self.course_access(lesson["ListingId"]))
        if not self.db.one("SELECT Id FROM MarketProgress WHERE LessonId=? AND UserId=?", [lesson_id, self.user]):
            self.db.insert("MarketProgress", dict(Id=uid(), LessonId=lesson_id, UserId=self.user, Created=now()))

    def attendance(self, listing_id, data):
        listing = self.listing(listing_id, True)
        require(listing["Kind"] == "course" and (self.admin or listing["OwnerId"] == self.user))
        student = text(data.get("student"), "Student", 100)
        require(self.db.one("SELECT Id FROM MarketEnrollment WHERE ListingId=? AND UserId=? AND Status='active'", [listing_id, student]))
        class_date = date.fromisoformat(data.get("date", "")).isoformat()
        previous = self.db.one("SELECT Id FROM MarketAttendance WHERE ListingId=? AND UserId=? AND ClassDate=?", [listing_id, student, class_date])
        values = dict(Present=1 if data.get("present") else 0)
        if previous:
            self.db.update("MarketAttendance", previous["Id"], values)
        else:
            self.db.insert("MarketAttendance", dict(Id=uid(), ListingId=listing_id, UserId=student, ClassDate=class_date, **values))
        self.event(listing_id, "attendance.saved", recipient=student)

    def moderate(self, action, identity, data):
        require(self.admin)
        reason = text(data.get("body"), "reason / verification notes", 2000)
        if action in ("publish", "reject", "archive"):
            listing = self.listing(identity, True)
            allowed = {"publish": ("pending", "rejected", "archived"), "reject": ("pending",), "archive": ("published",)}
            require(listing["Status"] in allowed[action])
            self.db.update("MarketListing", identity, {"Status": {"publish": "published", "reject": "rejected", "archive": "archived"}[action]})
            recipient = listing["OwnerId"]
        elif action in ("institute_approve", "institute_reject"):
            profile = self.profile(identity, True)
            require(profile and profile["InstituteStatus"] == "pending")
            self.db.update("MarketProfile", identity, {"InstituteStatus": "approved" if action.endswith("approve") else "rejected"})
            recipient = identity
        elif action in ("withdraw_paid", "withdraw_reject"):
            withdrawal = self.db.get("MarketWithdrawal", identity, True)
            require(withdrawal and withdrawal["Status"] == "requested")
            self.profile(withdrawal["UserId"], True)
            if action == "withdraw_paid":
                require(self.balance(withdrawal["UserId"]) >= 0, "A refund has made this balance negative. Reconcile the account before paying out.")
                reference = text(data.get("reference"), "actual payout transaction reference", 120)
                require(not self.db.one("SELECT Id FROM MarketWithdrawal WHERE Reference=? AND Status='paid'", [reference]), "This payout reference has already been used.")
                self.db.update("MarketWithdrawal", identity, {"Status": "paid", "Reference": reference})
            else:
                self.db.update("MarketWithdrawal", identity, {"Status": "rejected"})
                self.ledger(withdrawal["UserId"], identity, "withdrawal_reversed", withdrawal["Amount"], reason)
            recipient = withdrawal["UserId"]
        else:
            raise ValueError("Unknown admin action.")
        self.event(identity, action, reason, recipient)

    def manage_user(self, data):
        require(self.admin)
        target = text(data.get("user_id"), "User ID", 100)
        reason = text(data.get("body"), "reason for change", 2000)
        category = data.get("category")
        require(category in {"Admin", "Customer", "Designer", "Vendor", "Seller", "Buyer", "User", "Freelancer", "Institute", "Instructor", "Student", "DeliveryMan", "POS"})
        active = bool(data.get("active"))
        require(target != self.user, "You cannot change your own admin category or activation here.")
        hint = " WITH (UPDLOCK,HOLDLOCK)" if not self.db.sqlite else ""
        admins = self.db.all(f"SELECT UserId FROM Users{hint} WHERE LOWER(REPLACE(UserCatagory,' ',''))='admin' AND Active IN ('1','True')")
        previous = self.db.one(f"SELECT UserId,UserCatagory FROM Users{hint} WHERE UserId=?", [target])
        require(previous, "User not found.")
        if str(previous["UserCatagory"]).lower() == "admin" and (not active or category != "Admin"):
            require(len(admins)>1, "The last active admin cannot be deactivated or demoted.")
        self.db.run("UPDATE Users SET UserCatagory=?,Active=?,Status=? WHERE UserId=?", [category, "1" if active else "0", "True" if active else "False", target])
        if not active:
            self.db.run("UPDATE MarketListing SET Status='archived' WHERE OwnerId=? AND Status='published'", [target])
        self.event(target, "account.updated", f"{category}; active={active}; {reason}", target)

    def can_post_jobs(self):
        return can_post(actor_category(self.db, self.user, self.admin))

    def can_apply_jobs(self):
        return can_apply(actor_category(self.db, self.user, self.admin))
