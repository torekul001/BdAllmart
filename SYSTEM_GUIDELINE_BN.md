# All Servicer / bdallmart — ব্যবহারবান্ধব ও কার্যকর সিস্টেমের পূর্ণাঙ্গ নির্দেশিকা

তারিখ: ২৫ অক্টোবর ২০২৬ | সংস্করণ: ১.০

এটি বর্তমান প্রজেক্ট ও মালিকের নতুন পরিকল্পনা মিলিয়ে তৈরি পণ্য ও কার্যক্রমের নকশা। এখানে দেওয়া ভবিষ্যৎ সুবিধাগুলো প্রস্তাব; ইতোমধ্যে তৈরি বা চালু হয়েছে এমন দাবি নয়। এই কাজের অংশ হিসেবে অ্যাপ্লিকেশনের কোড বা ডেটাবেস পরিবর্তন করা হয়নি। বর্তমান অবস্থার মূল্যায়ন সোর্স কোড ও বিদ্যমান ইউজার গাইডভিত্তিক; লাইভ লেনদেন দিয়ে যাচাই করা হয়নি।

## ১. মূল সিদ্ধান্ত

সাইটের সেবা অনেক ধরনের হলেও ব্যবহারকারীর সামনে তার পরবর্তী কাজটি স্পষ্ট থাকতে হবে। একজন ব্যক্তি একই অ্যাকাউন্ট দিয়ে কিনবেন, বিক্রি করবেন, Freelancer হিসেবে কাজ করবেন এবং কোর্স করবেন। Institute-এর জন্য শিক্ষা ব্যবস্থাপনার অতিরিক্ত অনুমতি থাকবে। Admin পুরো ব্যবস্থা পরিচালনা করবেন।

সফলতার মূল নিয়ম: প্রতিটি সুবিধার শুরু, তথ্য দেওয়া, মূল্য বা শর্তে সম্মতি, কাজ সম্পন্ন, সমস্যা সমাধান এবং ইতিহাস—সম্পূর্ণ পথ থাকতে হবে। শুধু মেনু বা ফর্ম থাকাকে কার্যকর সুবিধা হিসেবে ধরা যাবে না।

## ২. বর্তমান অবস্থা ও নতুন পরিকল্পনার পার্থক্য

| অংশ | বর্তমান প্রজেক্টে যা পাওয়া গেছে | পরিকল্পনা পূরণে যা প্রয়োজন |
|---|---|---|
| অ্যাকাউন্ট | আলাদা Customer, Designer, Vendor, Institute, Student, POS ও Delivery category | একই পরিচয়ের অধীনে একাধিক অনুমতি ও কাজের মোড |
| পণ্য | Category, Product, Cart, Checkout, Customer/Designer product submission | বিক্রেতার পূর্ণ অর্ডার, স্টক, ফেরত ও আয়ের ব্যবস্থাপনা |
| পাবলিক প্রোফাইল | প্রোফাইল, অফার ও প্রোফাইল প্রোডাক্টের ভিত্তি | একই প্রোফাইলে পণ্য, সফটওয়্যার, কোর্স, সার্ভিস, পোর্টফোলিও |
| অ্যাফিলিয়েট | প্রোফাইলে পণ্য যোগ ও অর্ডারে referral তথ্য বহনের ভিত্তি | অনুমোদন, attribution নিয়ম, কমিশন হিসাব, reversal ও payout |
| সার্ভিস | প্যাকেজ অফার ও সার্ভিস অর্ডারের ভিত্তি | brief সংরক্ষণ, delivery, revision, acceptance ও dispute |
| ডিজাইন জব | Job post, design submission ও review | পরিষ্কার Contest workflow এবং আলাদা Bid/Proposal workflow |
| কোর্স | YouTube lesson, content editor, enrollment ও video assignment | Paid access, recorded sales, live/offline batch, attendance ও resale permission |
| Vendor | Dashboard আছে; নিজস্ব পূর্ণ ব্যবসায়িক workflow নিশ্চিত নয় | User-এর সব সাধারণ সুবিধা এবং business management |
| POS ও Delivery | Sale/report/receipt এবং assigned delivery status update | কেন্দ্রীয় order/stock হিসাবের সঙ্গে সামঞ্জস্য |
| Payment | Checkout-এ payment type/method নির্বাচন | বাস্তব payment verification, refund, seller settlement ও reconciliation |
| সাপোর্ট | Ticket, reply, filtering, assignment ও feedback-এর ভিত্তি | অর্ডারভিত্তিক dispute ও দায়িত্ব/সময়সীমার সংযোগ |
| সফটওয়্যার | আলাদা পূর্ণ digital-delivery workflow নিশ্চিত নয় | Version, license, download access, update ও support entitlement |
| Dashboard | কিছু বাস্তব তথ্য; কিছু স্থির বা নমুনা কার্ড | কেবল যাচাইযোগ্য প্রকৃত সংখ্যা ও করণীয় |

বর্তমান ডিজাইন জমার সুবিধাকে পূর্ণ Contest বা Bid ব্যবস্থা বলা উচিত নয়। নতুন নকশায় দুটির নিয়ম আলাদা হবে।

## ৩. অ্যাকাউন্ট ও অনুমতির নকশা

### ৩.১ একটি পরিচয়, একাধিক কাজ

রেজিস্ট্রেশনে প্রথমে নাম, যোগাযোগ ও পাসওয়ার্ড নেওয়া হবে। এরপর সহজ প্রশ্ন: “আপনি কী করতে চান?” ব্যবহারকারী একাধিক উদ্দেশ্য নির্বাচন করতে পারবেন: কিনতে চাই, বিক্রি করতে চাই, Freelancer হিসেবে কাজ করতে চাই, লোক নিয়োগ দিতে চাই, কোর্স পরিচালনা করতে চাই।

শুরুতেই সব ব্যবসায়িক তথ্য চাইতে হবে না। প্রথম পণ্য প্রকাশ, প্রথম Job, Institute সক্রিয় করা বা আয় উত্তোলনের সময় সংশ্লিষ্ট অতিরিক্ত তথ্য চাইতে হবে।

### ৩.২ ভূমিকার প্রস্তাব

| ভূমিকা / অনুমতি | অধিকার |
|---|---|
| সাধারণ User | Customer ও Freelancer হিসেবে কেনা, সেবা বিক্রি, কাজ করা এবং অনুমোদিত নিজস্ব/অ্যাফিলিয়েট বিক্রয় |
| Vendor / Buyer business profile | সাধারণ User-এর সুবিধা, business store, Job/Contest আয়োজন ও Freelancer নিয়োগ |
| Institute | সাধারণ অ্যাকাউন্টের সঙ্গে অনুমোদিত course ও batch management |
| Student access | কোর্স কেনা বা ভর্তি অনুযায়ী শেখার অধিকার; আলাদা পরিচয় খোলার প্রয়োজন নেই |
| POS / Delivery staff | দায়িত্ব অনুযায়ী সীমিত operational permission |
| Admin | সব মডিউল পরিচালনা, অনুমতি দেওয়া, audit ও সমস্যা নিষ্পত্তি |

প্রাথমিক পরিকল্পনা অনুযায়ী Job/Contest আয়োজন Vendor / Buyer-এর সক্রিয় সুবিধা থাকবে। সাধারণ User পরে একই অ্যাকাউন্টে Buyer সুবিধা সক্রিয় করতে পারবেন। এতে অধিকার ও onboarding স্পষ্ট থাকে।

Admin-এর পূর্ণ প্রবেশাধিকার থাকলেও কারও পাসওয়ার্ড দেখা বা অপরিবর্তনীয় আর্থিক ইতিহাস মুছে দেওয়া স্বাভাবিক কাজের অংশ হবে না। গুরুত্বপূর্ণ পরিবর্তনের কারণ ও ইতিহাস রাখতে হবে। প্রয়োজনে Support, Finance, Catalog ও Course staff-কে সীমিত Admin permission দেওয়া যাবে।

### ৩.৩ মালিকানা ও স্বার্থের দ্বন্দ্ব

- ব্যবহারকারী শুধু নিজের order, product, course, submission ও আয় দেখবেন; যৌথ প্রতিষ্ঠানে নির্দিষ্ট team permission প্রযোজ্য হবে।
- নিজের Job-এ নিজে Bid বা নিজের Contest-এ নিজে অংশ নেওয়া যাবে না।
- নিজের লেনদেনে নিজের review দিয়ে rating বাড়ানো যাবে না।
- Referral-এর নিজস্ব কেনাকাটায় কমিশন হবে কি না আগেই নির্ধারণ করতে হবে; প্রস্তাব হলো self-commission বন্ধ রাখা।

## ৪. ব্যবহারকারীর সামনে সাইট কীভাবে সাজবে

### ৪.১ মূল নেভিগেশন

প্রধান মেনু: **পণ্য | সফটওয়্যার | সার্ভিস | কাজ ও কনটেস্ট | কোর্স**। সঙ্গে Search, Cart, Notifications, Messages ও Profile থাকবে। Search-এ ধরন, category, price এবং প্রযোজ্য delivery/rating filter থাকবে।

হোমপেজের প্রথম অংশে তিনটি কাজ স্পষ্ট হবে: **কিনতে চাই**, **বিক্রি/কাজ করতে চাই**, **কোর্স করতে চাই**। Institute ও business onboarding-এর আলাদা প্রবেশপথ থাকবে। সব মডিউল একসঙ্গে বড় তালিকা করে দেখানো হবে না।

### ৪.২ ব্যক্তিগত Dashboard

সব ব্যবহারকারীর সাধারণ অংশ:

- Overview: pending action, চলমান অর্ডার, unread message ও আসন্ন ক্লাস।
- My Purchases: পণ্য, software, service ও course purchase history।
- My Store: নিজের listings, inventory, affiliate items ও sales orders।
- Freelance Work: available jobs, proposals, contests ও active contracts।
- Hiring: নিজের jobs, received proposals, contests ও hired freelancers।
- My Learning: enrolled courses, lessons ও class schedule।
- Earnings: pending, available, withdrawal ও transaction statement।
- Messages, Support এবং Settings।

অসক্রিয় সুবিধা Sidebar ভরিয়ে রাখবে না। “নতুন সুবিধা চালু করুন” থেকে Store, Hiring বা Institute management সক্রিয় করা যাবে। Institute সক্রিয় হলে Course Management, Students, Batches ও Classes যুক্ত হবে।

প্রথম Dashboard-এ অন্তত তিনটি তথ্য থাকবে: “কী চলছে”, “আমার কী করা দরকার”, “পরবর্তী সময়সীমা কী”। নমুনা আয়ের সংখ্যা বা অকার্যকর বোতাম থাকবে না।

### ৪.৩ Public Profile / Store

একটি শেয়ারযোগ্য প্রোফাইলে পরিচিতি, দক্ষতা, যাচাইকরণের অবস্থা ও আলাদা ট্যাব থাকবে: **Products, Software, Services, Courses, Portfolio, Reviews**। যে ট্যাবে কোনো প্রকাশিত তথ্য নেই, তা লুকানো বা উপযুক্ত খালি বার্তা দেখানো যাবে।

নিজস্ব ও অ্যাফিলিয়েট listing-এ মূল বিক্রেতা, fulfilment/support-এর দায়িত্ব এবং প্রযোজ্য affiliate পরিচয় স্পষ্ট থাকবে। পণ্য বিক্রির জন্য প্রোফাইল মালিককে স্বয়ংক্রিয়ভাবে delivery provider দেখানো যাবে না।

## ৫. ব্যবহারবান্ধব পেজ ও ফর্মের নিয়ম

1. প্রতিটি পেজে একটি প্রধান কাজ থাকবে: যেমন “অর্ডার করুন”, “প্রস্তাব পাঠান”, “লেসন যোগ করুন”।
2. বাংলা সহজ নাম ব্যবহার করুন; প্রয়োজনীয় ইংরেজি মেনুর নাম সামঞ্জস্যপূর্ণ রাখুন। Customer, Buyer ও User-এর একই কাজের জন্য বারবার আলাদা নাম ব্যবহার করবেন না।
3. দীর্ঘ ফর্ম ভাগ করুন: Basic Information → Price/Package → Media → Preview → Submit। Draft এবং autosave থাকলে কাজ হারাবে না।
4. Required field, file type/size এবং fee আগে দেখান। ত্রুটি সংশ্লিষ্ট field-এর পাশে দেখিয়ে আগের তথ্য অক্ষত রাখুন।
5. Submit-এর পরে ফলাফল দেখান: ID, status, পরবর্তী ধাপ এবং দায়িত্ব কার। শুধু “Success” যথেষ্ট নয়।
6. তালিকায় Search, Filter, Sort, Pagination এবং পরিষ্কার Reset থাকবে।
7. খালি তালিকায় কারণ ও করণীয় দেখান: “আপনি এখনো কোনো সার্ভিস যোগ করেননি → সার্ভিস যোগ করুন”।
8. ভুল বা offline অবস্থায় retry দিন; payment/order submit বারবার চাপলে duplicate সৃষ্টি হবে না।
9. Delete, cancel, refund ও অন্য গুরুত্বপূর্ণ কাজে প্রভাব দেখিয়ে নিশ্চিত করুন। সম্ভব হলে Archive ব্যবহার করুন।
10. Mobile-এ একই কাজ সম্পন্ন হতে হবে; গুরুত্বপূর্ণ বোতাম আড়াল, অতিরিক্ত horizontal scroll বা ছোট touch target থাকবে না।
11. Keyboard navigation, field label, visible focus, readable contrast ও image description রাখুন। শুধু রঙ দিয়ে status বোঝাবেন না।
12. সময়সীমায় তারিখ, সময় ও timezone স্পষ্ট করুন; মূল ব্যবহারকারীর জন্য Asia/Dhaka প্রদর্শন উপযোগী।

## ৬. পণ্য কেনাবেচার পূর্ণ কার্যপ্রবাহ

**বিক্রেতা:** Draft → Submit → Review → Published → Stock/price update → Order fulfilment → Sales statement। Rejected হলে কারণ ও resubmit পথ থাকবে।

**ক্রেতা:** Search → Product details → Variant/quantity → Cart → Checkout → Order confirmation → Tracking → Delivery → Review/support।

পণ্যে seller, price, available stock, variant, delivery charge/estimate, return eligibility এবং মোট খরচ দেখাতে হবে। Checkout-এ শেষ বোতাম চাপার আগে সব charge দেখাতে হবে।

প্রথম পর্যায়ে একটি cart-এ একজন seller-এর পণ্য রাখার প্রস্তাব। বহু seller-এর cart পরে চালু করলে প্রতিটি seller-এর আলাদা sub-order, shipping charge, tracking, refund ও settlement করতে হবে।

Stock checkout-এর সময় যাচাই হবে। Prepaid pending order-এর জন্য কতক্ষণ stock reserve থাকবে তা নির্ধারিত থাকবে; timeout/cancel-এ release হবে। COD stock reservation ও cancellation-এর নিয়মও স্পষ্ট থাকতে হবে।

প্রস্তাবিত fulfilment status: **Placed → Confirmed → Processing → Shipped → Delivered**। প্রয়োজন অনুযায়ী Cancelled, Return Requested, Returned থাকবে। Payment status আলাদা থাকবে।

Guest checkout রাখতে পারেন; কিন্তু order detail বা tracking দেখতে নিরাপদ verification প্রয়োজন। শুধু Order ID জানলেই ব্যক্তিগত তথ্য দেখা যাবে না। পরে verified contact দিয়ে guest order নিজের account-এ যুক্ত করা যাবে।

## ৭. সফটওয়্যার বিক্রয়

Software listing সাধারণ physical product থেকে আলাদা হবে। প্রতিটি listing-এ version, compatibility, demo, license scope, download format, support duration, update entitlement ও ব্যবহারের শর্ত থাকবে।

প্রবাহ: **Listing → Purchase → Verified payment → License/download access → Support/update history**। Payment pending হলে paid download দেওয়া হবে না।

Download link public স্থায়ী URL হবে না; অধিকার যাচাই করে access দিতে হবে। Refund বা invalid payment হলে access revoke-এর নিয়ম থাকবে। Digital software order-এ shipping address বা delivery tracking বাধ্যতামূলক হবে না। Resale permission ছাড়া অন্যের software পুনর্বিক্রয় করা যাবে না।

## ৮. সার্ভিস বিক্রয় ও অর্ডার

Service package-এ deliverables, price, delivery time, revision count, customer requirements ও অতিরিক্ত খরচ স্পষ্ট থাকবে। Basic/Standard/Premium ঐচ্ছিক; এক প্যাকেজেও সার্ভিস প্রকাশ করা যাবে।

প্রবাহ: **Package নির্বাচন → Brief ও attachment → Order/payment → Seller acceptance → In Progress → Delivery → Revision অথবা Acceptance → Completed → Review**।

বর্তমান service form-এর Customer Name/Note প্রকৃত order record-এ রাখা নিশ্চিত করা অগ্রাধিকার। অর্ডারের সময়কার package, price, scope ও deadline-এর snapshot রাখতে হবে; পরে listing বদলালে পুরোনো অর্ডার বদলাবে না।

Seller response deadline, revision request deadline, cancellation ও dispute নিয়ম order-এর আগে দেখাতে হবে। ক্রেতা চুপ থাকলে কী হবে তা লিখিত নীতি ছাড়া স্বয়ংক্রিয় completed করা যাবে না।

## ৯. Bid ও Contest আলাদা ব্যবস্থা

### ৯.১ Bid / Proposal

Buyer Job post করবেন: scope, budget, deadline, required skills, deliverables ও selection criteria। Freelancer Proposal দেবেন: approach, price, timeline ও relevant portfolio।

প্রবাহ: **Job Draft → Review/Publish → Proposals → Shortlist → Hire → Contract → Delivery → Acceptance → Completion**। প্রয়োজন হলে চুক্তির স্পষ্ট scope-সহ milestone যোগ হবে।

একজনকে Hire করার সময় শর্তে উভয়ের সম্মতি, payment readiness এবং job status update একসঙ্গে সম্পন্ন হতে হবে। কতজন hire করা যাবে তা Job-এ উল্লেখ থাকবে। Bid পাঠানো মানে সম্পূর্ণ কাজ আগেই জমা দেওয়া বাধ্যতামূলক নয়।

### ৯.২ Contest

Contest-এ prize, deadline, submission format, public/private visibility, winner count, judging এবং ownership transfer-এর শর্ত আগে প্রকাশ করতে হবে।

প্রবাহ: **Draft → Prize/payment verification → Open → Entries → Judging → Winner selected → Final handover → Completed**।

প্রস্তাব হলো পুরস্কারের অর্থ যাচাই হওয়ার পর Contest খুলবে। Winner নির্বাচন না হলে, Contest বাতিল হলে বা কাজ নিয়ে বিরোধ হলে কী হবে তা প্রকাশিত নিয়মে থাকতে হবে। বিজয়ী নয় এমন কাজের ownership আয়োজকের কাছে চলে যাবে না। পূর্ণাঙ্গ ফাইল গ্রহণ ও অধিকার হস্তান্তর agreed শর্ত অনুযায়ী হবে।

## ১০. কোর্স ও Institute-এর নকশা

### ১০.১ তিন ধরনের শিক্ষা

| ধরন | প্রয়োজনীয় তথ্য ও সুবিধা |
|---|---|
| Recorded | Curriculum, preview, lesson access, purchase/enrollment ও progress |
| Online Live | Batch, teacher, schedule/timezone, class link, attendance ও প্রযোজ্য recording |
| Offline | Branch/address, batch, seat limit, schedule, enrollment, fee ও attendance |

Institute-এর dashboard-এ Courses, Batches, Teachers, Students, Enrollment, Classes ও Sales থাকবে। Instructor শুধু দায়িত্বপ্রাপ্ত course/batch পরিচালনা করবেন।

### ১০.২ কোর্স কেনা ও access

**Course details → Enroll/Buy → Payment verification অথবা অনুমোদিত manual enrollment → Access granted → Lessons/classes → Progress**।

Free/preview content public থাকবে। Paid lesson শুধু button বা page লুকিয়ে সুরক্ষিত করা যাবে না; content/video access-এর অধিকারও যাচাই করতে হবে। সাধারণ public/unlisted YouTube link একা paid content protection দেয় না। বর্তমান Public course content-এ কোন অংশ প্রকাশ্য থাকবে তা আলাদা নির্ধারণ প্রয়োজন।

Offline course-এর seat ও schedule এবং live course-এর class link শুধু উপযুক্ত শিক্ষার্থীকে দেখাতে হবে। Course access duration, missed class ও refund-এর নিয়ম আগে জানাতে হবে। Certificate বা exam বাধ্যতামূলক প্রথম ধাপ নয়; প্রক্রিয়া প্রস্তুত হলে যোগ করা যাবে।

### ১০.৩ অন্যের recorded course বিক্রয়

প্রথম পর্যায়ে affiliate model ব্যবহার করার প্রস্তাব: মালিক কোর্স নিয়ন্ত্রণ করবেন; অনুমোদিত User/Institute নিজের profile দিয়ে বিক্রি করে কমিশন পাবেন। শিক্ষার্থী জানবেন course creator, seller/referrer ও support provider কে।

Reseller license আলাদা ভবিষ্যৎ ব্যবস্থা হতে পারে। কেবল কোর্স কিনলেই lesson download, copy, rebrand বা resale-এর অধিকার তৈরি হবে না।

## ১১. অ্যাফিলিয়েট বিক্রয় ও আয়ের নিয়ম

প্রস্তাবিত কার্যপ্রবাহ: **Owner অনুমোদন → Profile-এ listing যুক্ত → Referral purchase → Verified eligible sale → Pending commission → Available commission → Withdrawal → Paid**।

প্রকাশের আগে নির্ধারণ করতে হবে:

- কোন listing affiliate হবে এবং কে অনুমতি দেবেন।
- Referral link-এর মেয়াদ ও কোন referrer credit পাবেন; প্রস্তাবিত baseline হলো নির্দিষ্ট মেয়াদের last eligible referral। মেয়াদ ব্যবসার সিদ্ধান্ত হিসেবে লিখিত হবে।
- কমিশন কোন অঙ্কের ওপর হবে: প্রস্তাব হলো discount-এর পর eligible item price; shipping ও আলাদা tax/fee বাদ।
- Commission seller-এর revenue থেকে যাবে নাকি platform দেবে; একই বিক্রিতে একাধিক কমিশন হবে কি না।
- Return/refund/cancel হলে pending বা paid commission কীভাবে reverse হবে।
- নিজের পণ্য নিজে কেনা, duplicate attribution ও অপব্যবহারের নিয়ন্ত্রণ।

কমিশনের হার order-time snapshot হবে। পরে হার বদলালে পুরোনো order-এর হিসাব বদলাবে না। Affiliate item সরাসরি নতুন কপি হিসেবে তৈরি না করে মূল listing-এর সঙ্গে যুক্ত থাকবে; stock, price ও publication status মূল উৎস থেকে আসবে।

## ১২. Payment, earnings ও refund

Order, payment, fulfilment, commission ও payout—প্রতিটির আলাদা status রাখতে হবে। একটিকে completed করলে সবগুলো completed হয়ে যাবে না।

| হিসাব | উদাহরণ অবস্থা |
|---|---|
| Payment | Pending, Verified/Paid, Failed, Partially Refunded, Refunded |
| Service/Job | Awaiting acceptance, In Progress, Delivered, Revision, Completed, Disputed |
| Commission | Pending, Available, Reversed |
| Withdrawal | Requested, Under Review, Approved, Paid, Rejected |

Payment method বেছে নেওয়া মানেই paid নয়। Gateway event বা অনুমোদিত manual verification দিয়ে payment নিশ্চিত হবে। COD-এর ক্ষেত্রে order delivery এবং টাকা সংগ্রহ/হিসাব মেলানো আলাদা ঘটনা।

প্রথম পর্যায়ে নিয়ন্ত্রিত manual payment verification রাখা সম্ভব: reference/transaction ID, amount, verifier ও verified time থাকবে। Payment screenshot একাই paid status দেওয়ার ভিত্তি হবে না। পরবর্তী automation-এ duplicate notification বা submit-এ দ্বিগুণ credit হবে না।

Earnings page-এ gross sale, discount, refund, platform fee, affiliate commission, seller net, pending এবং withdrawable amount আলাদা দেখাতে হবে। প্রতিটি পরিবর্তনের transaction history থাকবে।

Withdrawal একই amount একাধিকবার reserve করতে পারবে না। Failed payout হলে reserved balance ফেরত যাবে। Refund, charge reversal ও manual adjustment পুরোনো record মুছে নয়, নতুন সংশোধনী entry দিয়ে হবে। Split refund/partial fulfilment-এর ক্ষেত্রে item-level হিসাব প্রয়োজন।

টাকা কতদিন hold হবে, withdrawal minimum/fee, cancellation ও refund eligibility—চালুর আগে ব্যবসায়িক নীতি হিসেবে নির্ধারণ করতে হবে। এখানে কোনো বাস্তব escrow বা payment custody চালু আছে ধরে নেওয়া হয়নি।

## ১৩. POS, delivery ও কেন্দ্রীয় অর্ডার

POS ও online order একই product identity ও stock হিসাব ব্যবহার করবে। POS sale-এ stock কমবে; sale ব্যর্থ হলে কমবে না; return অনুমোদিত হলে উপযুক্ত stock adjustment হবে।

Delivery staff শুধু assigned order-এর প্রয়োজনীয় তথ্য দেখবেন। অবৈধ status jump আটকাতে হবে; যেমন Cancelled order Delivered করা যাবে না। Delivered, Returned ও COD collected অবস্থার জন্য প্রয়োজনীয় প্রমাণ/কারণ থাকবে।

Admin delivery assignment পরিবর্তন করলে আগের ও নতুন কর্মী, সময় ও কারণ ইতিহাসে থাকবে। User-facing সহজ status এবং internal operational status-এর mapping এক জায়গায় নির্ধারিত থাকবে।

## ১৪. Admin, support, trust ও notification

Admin dashboard-এ আজকের revenue-এর পাশাপাশি **করণীয় তালিকা** প্রধান হবে: pending listing, unverified payment, unassigned order, dispute, withdrawal ও flagged content।

প্রতিটি review-এ Approve, Reject with reason, Request changes এবং history থাকবে। Support ticket সংশ্লিষ্ট order/job/course-এর সঙ্গে যুক্ত করা যাবে। ব্যবসার সক্ষমতা অনুযায়ী response ও resolution target প্রকাশ করতে হবে।

আসল transaction সম্পন্ন হলে review দেওয়া যাবে। Seller response, delivery timeliness, cancellation ও dispute তথ্য দিয়ে ভবিষ্যতে performance দেখা যাবে। কোনো badge-এর মানে পরিষ্কার থাকবে; verified contact ও verified business একই দাবি নয়।

In-app notification-এ প্রতিটি ঘটনার next action link থাকবে: new order, proposal, hired, delivered, revision requested, payment verified, class reminder, support reply। Email/SMS পরে যুক্ত হলেও user preference, delivery failure এবং অতিরিক্ত notification নিয়ন্ত্রণ করতে হবে।

Order message, file delivery ও support আলাদা চিহ্নিত থাকবে; কিন্তু একই order থেকে সব history পাওয়া যাবে। ব্যক্তিগত যোগাযোগ, private file ও student data কেবল সংশ্লিষ্ট পক্ষ দেখবেন।

## ১৫. কারিগরি ও ডেটার নির্দেশনা — ভবিষ্যৎ বাস্তবায়নের জন্য

এ অংশ বাস্তবায়নের নীতি; এখন কোনো পরিবর্তন করা হয়নি।

- Identity, permissions, catalog, order, payment, fulfilment, course access, proposal, submission ও financial transaction আলাদা দায়িত্বের মডিউল হবে।
- Listing-এর ধরন থাকবে physical product, software, service ও course; সবার জন্য একই checkout/fulfilment বাধ্য করা যাবে না।
- Order ও order item-এ প্রয়োজনীয় price, owner, referrer, terms এবং commission snapshot থাকবে।
- Job-এর সঙ্গে proposal, contract ও delivery; Contest-এর সঙ্গে entry ও award আলাদা সম্পর্ক হবে।
- Institute, course, batch, lesson, enrollment ও access entitlement আলাদা তথ্য হিসেবে থাকবে।
- Login থাকলেই অনুমতি যথেষ্ট নয়; প্রতিটি read/update-এ ownership ও role যাচাই করতে হবে।
- Password-এর বর্তমান storage configuration যাচাই করে নিরাপদ hash-এ migration পরিকল্পনা করতে হবে; recovery ও পুরোনো login compatibility একসঙ্গে বিবেচনা প্রয়োজন।
- Form/request protection, upload type/size যাচাই, private file access এবং abuse throttling প্রয়োজন।
- Order submit, payment callback, hire, stock decrement ও payout-এ পুনরাবৃত্ত request ও simultaneous action-এর নিরাপদ আচরণ প্রয়োজন।
- Error-এ user-friendly message; বিস্তারিত server log-এ থাকবে, password বা payment secret থাকবে না।
- Backup, restore rehearsal, deployment rollback ও পর্যবেক্ষণ প্রস্তুত থাকতে হবে।

## ১৬. বর্তমান সিস্টেম থেকে ধাপে ধাপে যাওয়া

### ধাপ ১ — বর্তমান সুবিধার বিশ্বাসযোগ্যতা ও usability

কাজ: বাস্তব Dashboard data, consistent menu, dead/legacy link যাচাই, service requirement persistence, পরিষ্কার error/success, permissions, guest order protection এবং বিদ্যমান checkout/course/POS/delivery flow যাচাই।

ফলাফল: বর্তমানে দেখানো সুবিধাগুলো শুরু থেকে শেষ পর্যন্ত ব্যবহার করা যাবে এবং অকার্যকর অংশ স্পষ্ট থাকবে।

### ধাপ ২ — একই অ্যাকাউন্ট ও public store

কাজ: multiple capabilities, unified dashboard, profile tabs, own/affiliate listing distinction এবং seller order management।

ফলাফল: নতুন account না খুলেই ব্যবহারকারী কেনা, বিক্রি ও কাজের প্রয়োজনীয় অংশে যেতে পারবেন।

### ধাপ ৩ — লেনদেন ও fulfilment সম্পূর্ণ করা

কাজ: payment verification, stock consistency, service delivery/revision, refunds, income statement, commission ও controlled withdrawal।

ফলাফল: একটি sale-এর order থেকে seller payment পর্যন্ত হিসাব মেলানো যাবে।

### ধাপ ৪ — Freelancer hiring ও Contest

কাজ: proposals, hire/contract, funded contest, submission, award, handover ও dispute।

ফলাফল: Bid ও Contest-এর আলাদা নিয়মে Buyer ও Freelancer কাজ শেষ করতে পারবেন।

### ধাপ ৫ — Course business ও software delivery

কাজ: paid recorded access, live/offline batches, Institute workflow, অনুমোদিত course affiliate এবং software license/download।

ফলাফল: শিক্ষা ও digital sale-এর নিজস্ব access ও fulfilment কাজ করবে।

### ধাপ ৬ — উন্নতি ও সম্প্রসারণ

কাজ: multi-seller cart, advanced reports, milestone contracts, automation, recommendation এবং বাস্তব প্রয়োজন অনুযায়ী certificate/exam।

প্রতিটি ধাপের সময় ও খরচ দল, ডেটা ও গ্রহণযোগ্য কাজের পরিধি নির্ধারণের পর হিসাব হবে। নির্দিষ্ট দিন বা বাজেট এখানে অনুমান করা হয়নি। বিদ্যমান চাহিদা বেশি হলে ধাপ ৪ ও ৫-এর ক্রম বদলানো যাবে; payment/access ভিত্তি আগে প্রয়োজন।

## ১৭. Migration-এর নিয়ম

1. বর্তমান Users, Customer, Designer, Student ও Institute record-এর সম্পর্কের তালিকা তৈরি করুন। একই email/phone থাকলেই স্বয়ংক্রিয় merge নয়; ownership নিশ্চিত করতে হবে।
2. পুরোনো User ID, Order ID, course assignment ও financial reference অক্ষত রেখে নতুন mapping পরিকল্পনা করুন।
3. পুরোনো category থেকে নতুন capability দিন; বিদ্যমান login হঠাৎ বন্ধ করবেন না।
4. Legacy ASP.NET link ও Python page-এর কোনটি authoritative তা নির্ধারণ করুন; একই তথ্যের দুই জায়গায় দ্বন্দ্বপূর্ণ update এড়ান।
5. Staging copy-তে user, order, stock, course access ও financial totals মিলিয়ে দেখুন।
6. সীমিত ব্যবহারকারী দিয়ে pilot চালান; সমস্যা হলে আগের অবস্থায় ফেরার পরিকল্পনা রাখুন।
7. পুরোনো URL redirect, ব্যবহারকারীর নির্দেশনা ও support প্রস্তুত রেখে ধাপে চালু করুন।

## ১৮. কখন কোনো সুবিধাকে সম্পূর্ণ বলা যাবে

| সুবিধা | গ্রহণযোগ্যতার ন্যূনতম পরীক্ষা |
|---|---|
| Account | একই ব্যক্তি permission অনুযায়ী কেনা/বিক্রি করতে পারেন; অন্যের তথ্য পান না |
| Product | Publish → order → stock update → delivery → return/refund-এর প্রযোজ্য পথ চলে |
| Service | Brief ও terms সংরক্ষিত; delivery, revision ও acceptance কাজ করে |
| Affiliate | সঠিক referrer credit পান; refund-এ কমিশন ঠিকভাবে reverse হয় |
| Job/Bid | Proposal → hire → contract → delivery → completion সম্ভব; self-hire আটকে যায় |
| Contest | Prize যাচাই, entry, award, handover ও cancellation rule কার্যকর |
| Recorded Course | ক্রেতা access পান; অননুমোদিত ব্যবহারকারী paid lesson পান না |
| Live/Offline | সঠিক batch, seat/schedule ও student access কাজ করে |
| Software | বৈধ ক্রেতা license/download পান; অন্য account/private link misuse আটকে যায় |
| Payment/Payout | Duplicate request দ্বিগুণ অর্থ তৈরি করে না; statement ও source transaction মেলে |
| POS/Delivery | Online/POS stock সামঞ্জস্যপূর্ণ; assigned staff উপযুক্ত status দিতে পারেন |
| Mobile/Support | ফোনে মূল flow শেষ হয়; ব্যর্থ হলে তথ্য না হারিয়ে সহায়তা পাওয়া যায় |

শুধু সফল পরিস্থিতি নয়—payment failure, double-click, stock শেষ, deadline পার হওয়া, rejected upload, access denied, cancelled order ও refund-এর পরিস্থিতিও দেখতে হবে। Pilot-এর আগে backup restore ও rollback যাচাই প্রয়োজন।

## ১৯. ব্যবহারবান্ধবতা কীভাবে মাপবেন

প্রথমে ছোট pilot-এর baseline নিন; তারপর লক্ষ্য নির্ধারণ করুন।

- নতুন ব্যবহারকারী সহায়তা ছাড়াই account খুলে প্রথম কাজ শেষ করতে পারেন কি না।
- Product খোঁজা থেকে checkout পর্যন্ত কোথায় বেশি মানুষ থামছেন।
- Listing publish, proposal পাঠানো এবং course enroll করতে কত ধাপ লাগে।
- কত order/payment duplicate, unmatched বা manual correction প্রয়োজন হচ্ছে।
- কোন পেজে বেশি error ও support request হচ্ছে।
- Seller response, service completion, refund/dispute ও support resolution-এর সময়।
- Paid course কেনার পর access পেতে কত সময় লাগে।

Pilot-এ অন্তত Buyer, Seller/Freelancer, Student, Institute ও Admin-এর প্রতিনিধিকে বাস্তবসম্মত কাজ দিন। শুধু “পেজ সুন্দর” কি না নয়, কাজটি কোথায় আটকে যায় তা লিখুন।

## ২০. উন্নয়ন শুরুর আগে মালিকের সিদ্ধান্ত তালিকা

| সিদ্ধান্ত | প্রস্তাবিত শুরু |
|---|---|
| User বনাম Vendor | একই account; business/hiring capability সক্রিয় করার আলাদা ধাপ |
| প্রথম চালুর পরিধি | বর্তমান flow নির্ভরযোগ্য করা, তারপর unified store ও সম্পূর্ণ sale |
| অন্যের পণ্য/course বিক্রি | Owner-approved affiliate; licensed resale পরে |
| Multi-seller checkout | প্রথমে single seller; পরে sub-order সহ multi-seller |
| Payment verification | যাচাইযোগ্য controlled manual process; পরে gateway automation |
| Commission | Eligible net item price-এর ভিত্তিতে; হার ও attribution মেয়াদ লিখিত করতে হবে |
| Earnings release | fulfilment/acceptance ও প্রযোজ্য dispute/return period অনুযায়ী নিয়ম নির্ধারণ |
| Contest prize | Open করার আগে অর্থ যাচাই |
| Paid course | Public preview আলাদা; paid entitlement যাচাই |
| Staff access | দায়িত্ব অনুযায়ী সীমিত access; Admin oversight ও audit |
| Return/refund/support | প্রতিটি listing type-এর পরিষ্কার নিয়ম ও দায়িত্ব |

এই নথির সিদ্ধান্তগুলো অনুমোদিত হওয়ার পর page-by-page specification, data model এবং implementation backlog তৈরি করা যাবে। বর্তমান নথি পরিকল্পনা ও পর্যালোচনার জন্য; এটি ডেভেলপমেন্ট শুরুর অনুমোদন নয়।
