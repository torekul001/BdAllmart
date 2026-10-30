# বাস্তবায়ন ও যাচাইয়ের রিপোর্ট

তারিখ: ২৫ অক্টোবর ২০২৬

## যা বাস্তবায়ন হয়েছে

- একই login-এর অধীনে buying, selling, Freelancer, Buyer/Business এবং অনুমোদিত Institute-এর কর্মক্ষেত্র।
- responsive Dashboard, English grouped navigation এবং তিন ধাপের listing form।
- পণ্য, software, service ও recorded/live/offline course listing; image, review, archive ও moderation।
- public profile/store, affiliate listing ও referral-ভিত্তিক কমিশন।
- order snapshot, stock/seat reservation, cancellation, payment verification, delivery, revision, acceptance ও dispute।
- paid software download ও course access; private resource protection এবং refund-এ access revoke।
- Job proposal, proposal update, hire/contract; funded Contest, entry, deadline-পরবর্তী award ও handover।
- course lesson তৈরি/সম্পাদনা, সরাসরি enrollment order, learning progress ও attendance।
- append-only financial ledger, commission reversal, reserved withdrawal, payout/rejection এবং audit events।
- Admin-এর public payment instructions, account category/activation, Institute approval ও সব নতুন workflow-এর তদারকি।
- পুরোনো product catalog ও profile products-এর read-only bridge; পুরোনো checkout, order, POS, delivery ও course URL বজায় রাখা।
- সাধারণ signup থেকে Admin/POS/Delivery privilege পাওয়া বন্ধ; Institute application-এ স্বয়ংক্রিয় instructor অধিকার বন্ধ।
- নতুন financial workflow-তে CSRF, authoritative account status, ownership checks ও duplicate order/payment/withdrawal protection।

## Database

Configured SQL Server-এ ১৭টি `Market`-prefixed table ও প্রয়োজনীয় index যোগ করা হয়েছে। নতুন module-এর table-এ পরবর্তী additive column migration-ও প্রয়োগ হয়েছে। কোনো legacy table drop করা হয়নি এবং কোনো পুরোনো business record migration দিয়ে পরিবর্তন করা হয়নি।

`migrate_marketplace.py` repeatable migration entry point। `instance/migration_audit`-এ schema/count snapshot আছে। এটি full backup নয়। SQL verification-এর সাময়িক test records transaction rollback হয়েছে।

## যাচাই

- `python -m unittest discover -v`: ৩৮টি পরীক্ষা সফল। পূর্বের ৭টি course test-ও এই সংখ্যার অন্তর্ভুক্ত।
- `python verify_marketplace_sqlserver.py`: actual SQL Server-এ workflow/ledger/contest পরীক্ষা সফল; test writes rollback হয়েছে।
- Headless Edge: Dashboard, catalog, listing form ও settings—প্রতিটি 390, 768 এবং 1440 pixel প্রস্থে পরীক্ষা। ১২টি পরীক্ষায় body overflow নেই।
- Browser-এ listing wizard-এর পরবর্তী/আগের ধাপ ও form data retention পরীক্ষা সফল। JavaScript error পাওয়া যায়নি।
- আসল অর্থ স্থানান্তর, আসল customer order সৃষ্টি বা public production deployment করা হয়নি।
- লোকালে Waitress দিয়ে `127.0.0.1:5001`-এ application চালু আছে। `/login`, `/register`, `/workspace/catalog`, `/workspace/jobs` ও বিদ্যমান `/category/1` HTTP 200 দিয়ে খুলেছে।

## ব্যবহার শুরু

লোকাল নতুন panel: `http://127.0.0.1:5001/workspace/`। আগের login ব্যবহার করুন। প্রথমে প্রোফাইল পূরণ করুন। Admin প্রথমে payment নির্দেশনা, Institute approval ও listing moderation করবেন। বিস্তারিত: [NEW_SYSTEM_GUIDE_BN.md](NEW_SYSTEM_GUIDE_BN.md)।

## এই সংস্করণের কার্যসীমা

Payment, refund ও payout মানুষের যাচাই/রেকর্ডে চলে; বাইরের gateway বা ব্যাংকে বোতাম থেকে অর্থ পাঠানো হয় না। SMS/email provider ও private streaming account সংযুক্ত নয়। Live/offline শিক্ষা schedule, external class link, enrollment ও attendance দিয়ে পরিচালিত হয়।

নতুন checkout একটি listing-এর order; multi-seller cart, milestone contract ও partial refund নেই। একটি service listing একটি package; একটি Job-এ একজন Freelancer। Affiliate attribution সরাসরি referral link-ভিত্তিক। এই নিয়মগুলো ব্যবহারকারীর নতুন গাইডে স্পষ্ট করা হয়েছে।

পুরোনো stock, order, POS ও payment accounting নিজস্ব আগের ব্যবস্থায় authoritative আছে; নতুন financial ledger-এ সেগুলো retroactively import হয়নি। পুরোনো catalog-এর bridge পণ্য কপি করে না, তাই তার জন্য দ্বিতীয় stock তৈরি হয় না। নতুন product listing আলাদাভাবে তৈরি করলে সেটি নতুন stock হিসেবে গণ্য হবে।

এই রিপোর্ট সমর্থিত core workflow-এর বাস্তবায়ন বর্ণনা করে; পরিকল্পনার প্রতিটি ভবিষ্যৎ সম্প্রসারণ সম্পূর্ণ হওয়ার দাবি নয়।

## মেনু সংশোধন

ব্যবহারকারীর নির্দেশ অনুযায়ী আগের role-based default Dashboard routing ফিরিয়ে দেওয়া হয়েছে, legacy page-এর অতিরিক্ত menu bar সরানো হয়েছে এবং নতুন Workspace navigation English করা হয়েছে। নতুন business workflow ও database schema রাখা হয়েছে।

নতুন সুবিধার খোঁজ সহজ করতে বিদ্যমান Dashboard-গুলোর top action-এ New Features বোতাম এবং sidebar-এ shared English New Features group যোগ করা হয়েছে। বিদ্যমান মেনুর লিংক ও ক্রম রাখা হয়েছে।

## English forms ও shared module layout

Workspace-এর static interface এবং validation messages English হয়েছে। Customer/Designer-এর existing business handlers পুনর্ব্যবহার করে optional Workspace layout দেওয়া হয়েছে; নতুন করে data বা processing copy করা হয়নি। `workspace=1` link, GET filter এবং POST redirect-এ বজায় থাকে। সরাসরি পুরোনো module URL-এর design রাখা হয়েছে। Unit/regression: ৩৩টি সফল; ৭টি UI page × ৩টি viewport = ২১টি responsive check সফল।

Job/Bid/Contest posting form সরাসরি jobs page-এ রাখা হয়েছে, inline Buyer activation-সহ। নতুন regression suite: ৩৫টি সফল; responsive UI: ২৪টি check সফল।

## Existing Job workflow এবং পৃথক roles

সর্বশেষ নিয়ম: Customer/Buyer কাজ পোস্ট ও পরিচালনা করে; Designer/Freelancer শুধু Bid/Contest-এ আবেদন ও কাজ জমা করে। নতুন ও পুরোনো Python entry point-এ server-side checks আছে। পুরোনো Customer form shared partial হিসেবে পুনর্ব্যবহার করা হয়েছে, এবং JobsList-এর records Workspace-এ সরাসরি দেখা যায়। C# DAL-এর সঙ্গে সামঞ্জস্যপূর্ণ অনুপস্থিত JobAppliedList table যোগ করা হয়েছে। SQL verification-এ compatibility insert rollback হয়েছে। Regression: ৩৭টি সফল; responsive UI: ২৭টি check সফল।

Open-job feed এক করা হয়েছে: homepage ও Workspace-এ একই active/unexpired Bid/Contest দেখায়। পুরোনো sample list constant সরানো হয়েছে। Source অনুযায়ী সঠিক job details/application URL থাকে; নতুন job data বানানো হয়নি। Regression suite: ৩৮টি সফল।


### JobsList Bid / Contest contract integration (2026-10-25)
- Recently Posted Jobs reads open, unexpired Bid / Contest records directly from JobsList; no sample jobs or MarketJob copies.
- Customer selects Hire Designer from actual JobAppliedList bids, or selects a winner from actual Submission contest entries. Designer accounts cannot post jobs or select winners.
- Selection snapshots the agreed price and closes applications. Continue Contract opens payment reference, admin verification, delivery, two revisions and customer acceptance. Earnings are credited once after acceptance.
- Pending cancellation reopens an unexpired job; admin refund reverses credited earnings. Contract terms cannot be edited through the old job editor while an active contract exists.
- Additive MarketLegacyContract links the existing job to MarketOrder; total 18 Market tables. Original jobs and submissions are retained.
- Validation: 40 automated tests pass; SQL Server workflow verification rolls back test changes. Payment verification/refund are manual admin attestations, not automatic bank transfers.
- Changes run locally at http://127.0.0.1:5001; public bdallmart.com requires deployment of these changes.
