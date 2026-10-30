# নতুন Marketplace — ব্যবহার ও পরিচালনার গাইড

প্রস্তুত: ২৫ অক্টোবর ২০২৬

## শুরু করুন

চালু সাইটের ঠিকানার শেষে `/workspace/` খুলুন। লোকালে সাধারণ ঠিকানা: `http://127.0.0.1:5001/workspace/`। আগের Username / Email / Phone ও পাসওয়ার্ড দিয়ে লগইন করুন। Login-এর পরে আগের role অনুযায়ী Dashboard খুলবে; নতুন সুবিধা আগের Dashboard-এর উপরের **New Features ↗** বোতাম ও sidebar-এর **New Features** গ্রুপ থেকে খুলুন। সরাসরি `/workspace/` প্রবেশপথও আছে। মেনুর ভাষা English।

পুরোনো পণ্য, অর্ডার, Designer-এর কাজ ও কোর্স অক্ষত আছে। Workspace-এর **Existing Modules** গ্রুপ থেকে সেগুলো ব্যবহার করুন। নতুন Marketplace-এর listing, order ও earnings আলাদা হিসাব রাখে। বিদ্যমান পণ্য নতুন catalog ও public store-এ read-only সংযোগের মাধ্যমে দেখা যায়; কেনাকাটার জন্য আগের checkout/profile ব্যবহার হয়। পুরোনো তথ্য নতুন টেবিলে কপি করা হয়নি। একই পণ্য দুই জায়গায় আলাদাভাবে তৈরি করলে stock নিজে থেকে sync হবে না।

## ১. একই অ্যাকাউন্টে একাধিক কাজ

1. **Profile & Features** খুলে নাম ও পরিচিতি দিন।
2. নিজের অ্যাকাউন্টে কেনাকাটা ও বিক্রয় করুন। Job-এর ক্ষেত্রে Customer পোস্ট করবে এবং Designer আবেদন করবে।
3. Customer / Buyer role দিয়ে Job বা Contest পোস্ট করুন। Designer role শুধু Bid / Contest-এ আবেদন করতে পারবে; Business checkbox দিয়ে এই নিয়ম বদলায় না।
4. নিজের কোর্স তৈরি করতে Institute আবেদন দিন; Admin অনুমোদন করবেন।

নতুন Institute registration স্বয়ংক্রিয় instructor access দেয় না। POS, Delivery ও Admin category সাধারণ signup-এ দেওয়া যায় না; Admin তা নির্ধারণ করবেন। আগের কর্মীদের login ও কাজের পেজ বজায় আছে।

## ২. নিজের দোকান ও listing

**My Store → পরিচিতি → দাম ও শর্ত → যাচাই ও জমা**।

| ধরন | কী তথ্য দেবেন |
|---|---|
| Product | শিরোনাম, বিবরণ, মূল্য, available stock, delivery ও return-এর শর্ত |
| Software | ZIP/PDF delivery file, license, version ও compatibility |
| Service | কাজের scope, মূল্য, delivery days ও included revision; একটি listing একটি package |
| Course | Recorded/Live/Offline, মূল্য, সময়সূচি, প্রযোজ্য seat এবং class link/address |

Cover image JPG/PNG/WebP হতে পারে; listing প্রকাশিত হলে সেটি public। Delivery file আলাদা ও অনুমতিনির্ভর। সর্বোচ্চ file size ১০ MB।

Admin review-এর পর listing প্রকাশিত হবে। নিজের listing Archive করা এবং আবার Review চাওয়া যায়। সম্পাদনা করলে আবার review প্রয়োজন। পুরোনো অর্ডারের মূল্য ও শর্ত বদলায় না। ভর্তি থাকা course-এর মূল শর্ত পরিবর্তন সীমিত; লেসন সংশোধন করা যায়। Live/Offline-এর প্রতিটি নির্দিষ্ট batch-এর জন্য আলাদা course listing ব্যবহার করুন।

**Profile & Features → আমার প্রোফাইল দেখুন** থেকে public store-এর ঠিকানা শেয়ার করুন। সেখানে নতুন প্রকাশিত নিজস্ব listing, অনুমোদিত affiliate listing ও ক্রেতার review দেখা যাবে।

## ৩. কেনাকাটা

1. **Browse Marketplace** থেকে ধরন নির্বাচন ও Search করুন।
2. Seller, মূল্য, terms, license ও stock মিলিয়ে listing খুলুন।
3. Quantity এবং পণ্যের ঠিকানা/যোগাযোগ বা সার্ভিসের requirements দিন।
4. মোট মূল্য দেখে Order তৈরি করুন। নতুন checkout একবারে একটি listing-এর জন্য; আলাদা shipping fee যোগ করে না। Seller-এর মূল্য ও শর্তে shipping স্পষ্ট থাকতে হবে।
5. Order-এর অনুমোদিত payment নির্দেশনা অনুসরণ করে Transaction ID দিন। নির্দেশনা না থাকলে আগে support-এর সহায়তা নিন।
6. Admin অর্থ যাচাই করলে paid হবে। Software download ও course access তখন সক্রিয় হবে। Free course-এ সঙ্গে সঙ্গে ভর্তি হয়।

Payment reference জমা দেওয়া মানেই payment verified নয়। বর্তমান ব্যবস্থা manual verification-ভিত্তিক। কোনো Paid/Refund/Payout বোতাম নিজে ব্যাংক বা মোবাইল অ্যাকাউন্টে অর্থ স্থানান্তর করে না।

## ৪. অর্ডার, ডেলিভারি ও Review

**Orders & Contracts**-এ কেনা/বিক্রি filter করুন এবং title বা সম্পূর্ণ Order ID দিয়ে খুঁজুন। একই পেজে brief, terms snapshot, file, message ও পরিবর্তনের ইতিহাস থাকে।

- Buyer: payment reference, unpaid cancel, message, revision, delivery গ্রহণ, dispute ও completed order review।
- Seller: paid কাজ শুরু, delivery/tracking এবং file জমা, order message।
- Admin: payment verification, cancellation, fulfilment, dispute resolution ও প্রকৃত refund রেকর্ড।

পণ্য/সার্ভিস/Job-এর delivery Buyer গ্রহণ করলে seller-এর আয় release হয়। Software ও course-এর paid access চালু হলে সেগুলোর digital fulfilment completed ধরা হয়। সার্ভিসের ঘোষিত revision limit কার্যকর।

## ৫. Affiliate বিক্রয়

Owner listing-এ affiliate অনুমতি ও commission rate দেবেন। অন্য User সেটি **প্রোফাইলে যুক্ত করুন** দিয়ে যোগ করে নিজের referral link বা public store শেয়ার করবেন। মূল seller fulfilment ও support দেবেন।

সেই link থেকে order হলে commission তথ্য সংরক্ষিত হয়; completed হলে আয় যোগ হয়। নিজের listing বা নিজের কেনাকাটায় self-commission নেই। Refund হলে কমিশন reverse হবে। Profile থেকে listing সরালেও আগের order-এর হিসাব অক্ষত থাকে।

এই সংস্করণে সরাসরি referral link-এর attribution কাজ করে; নির্দিষ্ট দিনের cookie attribution window নেই। Order-এর সময়কার rate-ই পরবর্তী হিসাবের ভিত্তি।

## ৬. Job / Bid — আগের প্রজেক্টের কার্যপ্রবাহ

Customer / Buyer হিসেবে **Jobs, Bids & Contests** খুলুন। এখানে AllServicer-এর আগের বিস্তারিত Job form আছে: title, category, deadline, price, Bid/Contest type, logo text, colour, must-follow/do-not-add, logo style ও sample images। একই form আগের Customer Post Job পেজেও ব্যবহার হয়। পোস্ট `JobsList`-এ জমা হয়; আলাদা duplicate job তৈরি হয় না।

Designer হিসেবে ওই পেজে posting form থাকবে না। তালিকার Bid খুলে **Your Bid** ও proposal দিয়ে আবেদন করুন। **My Applications** থেকে নিজের আবেদন দেখা যায়। Customer **View Applications** থেকে প্রাপ্ত আবেদন দেখবেন। URL বা form request দিয়ে Designer posting restriction অতিক্রম করতে পারবে না। Customer-ও Designer application বা submission করতে পারবে না। Admin-এর পরিচালনার অনুমতি বজায় আছে।

## ৭. Contest

Customer-এর Job form-এ Contest নির্বাচন করুন। Designer Contest খুলে আবেদন করবেন, তারপর **Submit Contest Design** থেকে আগের JPG/JPEG preview এবং ZIP/source-file submission form ব্যবহার করবেন। Customer আগের **Submitted Designs** পেজে কাজ পর্যালোচনা করবেন। Direct Order-এ Designer Bid/Contest application করা যাবে না।

মূল উৎস: `UserUI/CustomerOrderPlace.aspx.cs`, `JobDetails.aspx.cs`, `UserUI/Submission.aspx.cs` এবং `App_Code/DAL.cs`। Bid/Contest application-এর জন্য মূল C#-এর `JobAppliedList` schema ব্যবহার হচ্ছে; configured database-এ অনুপস্থিত থাকায় সেই compatibility table যোগ করা হয়েছে। তার `CustomerId` কলামে মূল C# অনুযায়ী আবেদনকারী Designer-এর ID থাকে। পুরোনো job ও submission মুছে বা কপি করা হয়নি।

পূর্বের নতুন-module সংস্করণে তৈরি `MarketJob`/funded contest থাকলে তার contract ও payment verification নিয়ম আগের মতো থাকবে। Existing `JobsList`-এর কাজ আগের project-এর review/payment ব্যবস্থার অংশ; সেটি স্বয়ংক্রিয়ভাবে নতুন earnings ledger-এ স্থানান্তর হয় না।

## ৮. Institute ও শিক্ষার্থী

1. **Course Management** থেকে course/batch নির্বাচন করুন।
2. Title, description, HTTPS video link, resource file ও ক্রম দিয়ে Lesson যোগ করুন। পাশের **সম্পাদনা** থেকে সংশোধন করুন।
3. Public Preview নির্বাচন করলে শুধু সেই lesson সবার জন্য হবে; অন্য lesson-এর জন্য active enrollment প্রয়োজন।
4. শিক্ষার্থী নিজে কোর্স কিনতে পারবেন। Institute সক্রিয় Username/Email/Phone দিয়ে সরাসরি enrollment order-ও করতে পারে। Paid fee Admin যাচাইয়ের পরে access চালু হয়।
5. তারিখ ও শিক্ষার্থী দিয়ে attendance রাখুন।
6. শিক্ষার্থী **My Learning** থেকে course/class/lesson খুলবেন এবং completed lesson সংরক্ষণ করবেন; progress count দেখা যাবে।

Live meeting link শুধু owner, Admin ও enrolled student দেখবেন। সাইট class schedule/link ও attendance পরিচালনা করে; নিজস্ব conference server বা DRM streaming নয়। Public/unlisted video link শেয়ার হওয়া আটকাতে উপযুক্ত private hosting প্রয়োজন।

অন্যের Recorded Course নিজের profile দিয়ে বিক্রি করতে মূল owner affiliate permission দেবেন। এটি course copy বা rebrand-এর অধিকার নয়।

## ৯. আয়, উত্তোলন ও Refund

**Earnings & Withdrawals**-এ Available, paid কিন্তু কাজ বাকি থাকা sales, ledger ও withdrawal history দেখুন। এই সংস্করণে আলাদা platform fee নেই; ঘোষিত affiliate commission বাদ দিয়ে seller net income হিসাব হয়।

Amount ও destination দিয়ে withdrawal দিন। অর্থ reserve হবে; একই ফর্ম বারবার জমা দিলেও duplicate request হবে না। Admin প্রকৃত অর্থ পাঠিয়ে reference দিয়ে Paid করবেন; reject করলে reserve ফেরত আসবে।

Refund কেবল Admin বাস্তবে অর্থ ফেরত দেওয়ার পরে reason/reference-সহ রেকর্ড করবেন। এই সংস্করণে full-order refund আছে; partial refund নেই। Seller/affiliate ledger reverse, course/download access revoke এবং প্রযোজ্য stock/seat restore হয়। আগে payout হলে balance negative হতে পারে; তখন নতুন payout দেওয়া যাবে না।

## ১০. Admin-এর করণীয়

1. **Platform Management → প্রথম সেটআপ** থেকে public Payment নির্দেশনা দিন; API secret লিখবেন না।
2. **Users & Permissions** থেকে category ও activation পরিচালনা করুন। নিজের Admin access পরিবর্তন করা যায় না।
3. Institute আবেদন ও listing review করুন; reason-সহ approve/reject/archive দিন।
4. Order খুলে প্রকৃত payment amount, recipient ও Transaction ID মিলিয়ে verify করুন। একই payment reference দ্বিতীয়বার credit হয় না।
5. Contest prize, disputes ও withdrawals সম্পন্ন করুন; audit history দেখুন।
6. আগের POS, delivery, product/category setup ও support-এর জন্য **Admin Dashboard** ব্যবহার করুন।

## ১১. চালু ও রক্ষণাবেক্ষণ

Configured SQL Server-এ additive migration প্রয়োগ করা হয়েছে। অন্য server-এ code বসালে আগে চালান:

```powershell
.\.venv\Scripts\python.exe migrate_marketplace.py
.\.venv\Scripts\python.exe app.py
```

Migration repeatable। নতুন Market-prefixed table/index যোগ করে; legacy table drop বা data import করে না। `instance/migration_audit`-এ schema ও row-count audit থাকে; এটি full database backup নয়।

`MARKET_PAYMENT_INSTRUCTIONS` environment fallback আছে; Admin panel-এর সংরক্ষিত নির্দেশনা অগ্রাধিকার পায়। `MARKET_PRIVATE_DIR` private file directory নির্ধারণ করে। এটি public/static-এর বাইরে রাখুন এবং database-এর সঙ্গে backup নিন।

`FLASK_SECRET_KEY` না থাকলে `instance/session_secret`-এ স্থায়ী random key তৈরি হয়। প্রকাশ্য পুরোনো default key বাদ দেওয়ায় একবার আবার login লাগতে পারে। একাধিক server-এ একই সুরক্ষিত key ব্যবহার করতে হবে।

স্বয়ংক্রিয় payment gateway, SMS/email বা video-hosting account সংযুক্ত হয়নি। বর্তমান core flow manual payment verification ও class link দিয়ে ব্যবহারযোগ্য। বাইরের automation-এর জন্য provider account/configuration প্রয়োজন।

## ১২. পরীক্ষা

```powershell
.\.venv\Scripts\python.exe -m unittest test_marketplace test_course_content -v
.\.venv\Scripts\python.exe verify_marketplace_sqlserver.py
.\.venv\Scripts\python.exe preview_marketplace.py
```

SQL Server verifier সব test write rollback করে। Preview in-memory test database ব্যবহার করে; আসল database-এ demo data লেখে না। Screenshot ও sample `instance/ui_preview`-এ থাকে।

## English forms এবং একই Workspace design

Workspace-এর heading, form label, placeholder, button, সাহায্যের লেখা ও validation message English করা হয়েছে। ব্যবহারকারীর নিজের বাংলা নাম বা লেখা পরিবর্তন করা হয় না।

Workspace-এর Existing Modules থেকে Customer Dashboard বা Freelancer Dashboard খুললে একই Workspace header, sidebar ও form styling থাকবে। Module-এর নিজস্ব কাজ ও সাবমেনুও ওই sidebar-এ দেখা যাবে। Filter, section link ও form-submit redirect-এ design বজায় থাকে। এ জন্য module URL-এ `workspace=1` ব্যবহৃত হয়। সরাসরি আগের URL খুললে আগের Dashboard design পাওয়া যাবে।



## Open Jobs তালিকা

Homepage-এর Recently Posted Jobs এবং Workspace-এর Open Jobs একই feed ব্যবহার করে। Existing JobsList এবং নতুন module-এর published/open কাজ দেখায়; বন্ধ, expired, unfunded বা Direct Order এখানে থাকে না। Apply সংশ্লিষ্ট আসল job-এর বিস্তারিত খোলে। নিজের আগের/বন্ধ job My Jobs বা My Posted Jobs থেকে পরিচালনা করুন।


### JobsList Bid / Contest contract integration (2026-10-25)
- Recently Posted Jobs reads open, unexpired Bid / Contest records directly from JobsList; no sample jobs or MarketJob copies.
- Customer selects Hire Designer from actual JobAppliedList bids, or selects a winner from actual Submission contest entries. Designer accounts cannot post jobs or select winners.
- Selection snapshots the agreed price and closes applications. Continue Contract opens payment reference, admin verification, delivery, two revisions and customer acceptance. Earnings are credited once after acceptance.
- Pending cancellation reopens an unexpired job; admin refund reverses credited earnings. Contract terms cannot be edited through the old job editor while an active contract exists.
- Additive MarketLegacyContract links the existing job to MarketOrder; total 18 Market tables. Original jobs and submissions are retained.
- Validation: 40 automated tests pass; SQL Server workflow verification rolls back test changes. Payment verification/refund are manual admin attestations, not automatic bank transfers.
- Changes run locally at http://127.0.0.1:5001; public bdallmart.com requires deployment of these changes.
