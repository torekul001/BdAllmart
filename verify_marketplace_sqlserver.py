"""Exercise the real SQL Server dialect in one transaction that ALWAYS rolls back.

No real account or money transfer is used. Legacy business records are not altered.
Compatibility application fixtures are also rolled back. Run after migration.
"""
from datetime import date, timedelta
from market_db import transaction
from market_service import Marketplace, uid
from market_legacy import products
from unittest.mock import patch


class RollbackVerification(Exception):
    pass


def main():
    prefix = "verification-" + uid()
    try:
        # Role fixtures are injected; do not create or modify real legacy user accounts.
        with transaction() as store, patch('market_service.actor_category',side_effect=lambda db,user,admin=False: 'admin' if admin else 'designer' if user.endswith('-seller') else 'customer'):
            store.run("SET LOCK_TIMEOUT 5000")
            products(store)
            # Verify compatibility with the C# SaveAppliedJob fields, rolled back below.
            store.run('''INSERT INTO JobAppliedList (Type,Jobid,Title,CustomerId,CustomerName,[Date],SetBudget,Msg)
                VALUES (?,?,?,?,?,?,?,?)''', ['Bit',-1,'SQL rollback verification',prefix,prefix,'2026-10-25 00:00:00','100.50','Verification only'])
            application=store.one('SELECT SetBudget FROM JobAppliedList WHERE CustomerId=?',[prefix])
            assert str(application['SetBudget'])=='100.50'
            seller = Marketplace(store, prefix + "-seller")
            buyer = Marketplace(store, prefix + "-buyer")
            admin = Marketplace(store, prefix + "-admin", True)
            referrer = Marketplace(store, prefix + "-ref")
            for actor in (seller, buyer, admin, referrer):
                actor.save_profile({"name": "Rollback verification", "business": "1"})
            listing = seller.save_listing(dict(kind="service", title="Verification only", description="Transaction rollback",
                                               price="100", stock="1", commission="10", affiliate="1", days="2", revisions="1"))
            admin.moderate("publish", listing, {"body": "Verification"})
            referrer.add_affiliate(listing)
            order = buyer.create_order(listing, {"brief": "Verification", "referrer": referrer.user}, uid())
            buyer.act_order(order, "payment", {"reference": prefix})
            admin.act_order(order, "verify", {})
            seller.act_order(order, "deliver", {"body": "Verification"})
            buyer.act_order(order, "complete", {})
            assert seller.balance() == 9000 and referrer.balance() == 1000
            seller.withdraw({"amount": "50", "destination": "Verification only"})
            request = store.one("SELECT Id FROM MarketWithdrawal WHERE UserId=?", [seller.user])
            admin.moderate("withdraw_reject", request["Id"], {"body": "Verification reversal"})
            admin.act_order(order, "refund", {"body": "Verification refund"})
            assert seller.balance() == 0 and referrer.balance() == 0
            contest = buyer.create_job(dict(kind="contest", title="Verification contest", description="Verification", budget="100",
                                            deadline=(date.today()+timedelta(days=2)).isoformat()))
            buyer.act_job(contest, "fund", {"reference": prefix + "-contest"})
            admin.act_job(contest, "verify", {})
            seller.propose(contest, {"body": "Verification entry"}, "verification.pdf")
            entry = store.one("SELECT Id FROM MarketProposal WHERE JobId=?", [contest])
            store.update("MarketJob", contest, {"Deadline": (date.today()-timedelta(days=1)).isoformat()})
            buyer.act_job(contest, "award", {"proposal_id": entry["Id"]})
            raise RollbackVerification()
    except RollbackVerification:
        pass
    with transaction() as store:
        assert not store.one("SELECT UserId FROM MarketProfile WHERE UserId LIKE ?", [prefix + "%"])
    print("SQL Server workflow verification passed. All test changes rolled back; no test accounts/orders remain.")


if __name__ == "__main__":
    main()
