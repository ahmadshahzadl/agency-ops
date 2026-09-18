"""Content plan for the September 2026 blog overhaul (see fuorix.com/GROWTH-PLAN.md §5).

Applied by scripts/apply_blog_plan.py. Pure data: no imports, no side effects.

Prices follow the service pages on fuorix.com (web from $500, spreadsheet-to-software from $800,
dashboards from $800, ERP from $1,500). AED figures use 1 USD = 3.67 AED, GBP 1 USD = 0.79 GBP.
"""

MARK = "<!-- plan-2026-09 -->"

# Developer-audience posts: unpublish (status -> draft). Nothing is deleted; republish from the portal to restore.
UNPUBLISH = [
    "saas-architecture-patterns-2026",
    "api-design-best-practices",
    "cloud-migration-strategy",
    "devops-ci-cd-pipeline-guide",
    "database-scaling-postgresql",
]

# Retitles: new title/SEO/excerpt plus an intro prepended to the existing body (marked so it is applied once).
UPDATE = [
    {
        "slug": "why-nextjs-is-the-best-framework-for-business-websites",
        "title": "Why We Build UAE and UK Business Websites in Next.js (and When We Don't)",
        "seo_title": "Next.js for Business Websites: Why We Use It for UAE & UK SMBs | Fuorix",
        "seo_description": "Why Fuorix builds most UAE and UK business websites in Next.js instead of WordPress: speed, SEO, security, and lower running costs. Plus the cases where we recommend something else.",
        "excerpt": "Most of the business websites we ship for UAE and UK clients are built in Next.js. Here is what that means for your speed, Google rankings and hosting bill, and the three cases where we recommend something else.",
        "category": "Web Development",
        "prepend_md": """If you run a business in Dubai, Manchester or Lahore and you are getting quotes for a new website, you will hear two words a lot: WordPress and Next.js. Here is the short version of how we decide, then the technical detail below.

**We build in Next.js when:** you care about page speed and Google rankings, you want the site to become an app later (customer portal, booking, quotes), or you have been burned by plugin updates breaking a WordPress site.

**We still recommend WordPress or a website builder when:** you need to publish long-form content daily with a non-technical team, your budget is under $500, or you only need a five-page brochure site that will never change.

Our business websites start from $500 (about AED 1,800 or £400) and most launch in 3 to 4 weeks. See [Website Design & Development](/services/web-development) for what is included, or [book a free call](/book) and we will tell you honestly which option fits.""",
    },
    {
        "slug": "how-to-reduce-website-load-time",
        "title": "Slow Website Costing You Leads? How We Fix Load Time for SMB Sites",
        "seo_title": "Slow Website Losing Leads? How We Fix Load Time for Small Business Sites | Fuorix",
        "seo_description": "A slow website quietly loses enquiries. How Fuorix diagnoses and fixes load time for UAE and UK small business sites, what it costs, and what you can do yourself this week.",
        "excerpt": "Every extra second of load time costs you enquiries, especially on mobile in the UAE where most visitors arrive from Instagram and WhatsApp. Here is how we diagnose a slow site, what we fix first, and what it costs.",
        "category": "Performance",
        "prepend_md": """A business owner in Sharjah sent us a site last month that took nine seconds to load on a phone. Their Instagram ads were working. The website was throwing the leads away.

If your site takes more than three seconds to become usable on mobile, you are losing enquiries you already paid for. The good news is that most of it is fixable without a redesign.

**What a speed fix costs with us:** an audit and the first round of fixes (images, caching, scripts, hosting) is a fixed $300 to $800 depending on the platform, and takes about a week. If the site is on an old template that cannot be saved, a rebuild in Next.js starts from $500. Run your site through [PageSpeed Insights](https://pagespeed.web.dev/) first, then [send us the score](/contact) and we will tell you which of the two you need.

The rest of this post is the practical checklist we work through.""",
    },
    {
        "slug": "react-native-vs-flutter-2026",
        "title": "React Native vs Flutter for a Small Business App: Cost, Timeline, Our Pick",
        "seo_title": "React Native vs Flutter for a Small Business App: Cost & Timeline | Fuorix",
        "seo_description": "Choosing React Native or Flutter for a small business app in the UAE or UK? A plain-English comparison of cost, timeline, hiring and maintenance from a team that ships both.",
        "excerpt": "You do not need to understand the frameworks to make this decision. You need to know what each one costs to build, to run and to hire for. Here is our honest answer for small business apps, with prices.",
        "category": "Mobile Development",
        "prepend_md": """You are a business owner, not a developer. You want an app for your customers or your staff, and someone has asked you whether you want it in React Native or Flutter. Here is what actually matters to you.

**Cost.** For a typical small business app (ordering, bookings, a staff tool, a loyalty app) both come out similar. Our mobile apps start from $800 (about AED 2,900 or £630) for a focused single-purpose app, with most business apps landing between $3,000 and $8,000.

**Who will maintain it.** React Native uses JavaScript, which almost every web developer knows. If you ever need someone else to take over, it is far easier to find them in Lahore, Dubai or London. This is why React Native is our default for SMB apps.

**When we pick Flutter anyway:** heavy custom animation, unusual UI, or a team that already runs Flutter.

If your app also needs a website and an admin panel, React Native lets us share code with the web app, which cuts the total price. See [Mobile App Development](/services/mobile-apps) or [book a call](/book) to get a fixed quote. The detailed comparison follows.""",
    },
    {
        "slug": "what-to-look-for-when-hiring-a-software-development-company",
        "title": "How to Hire a Software Development Company in the UAE Without Getting Burned",
        "seo_title": "How to Hire a Software Development Company in the UAE (Without Getting Burned) | Fuorix",
        "seo_description": "Hiring a software development company in Dubai or the UAE? The red flags, the 12 questions to ask, how fixed-price quotes should work, and what a fair contract looks like.",
        "excerpt": "Most bad software projects in the UAE fail at the hiring stage, not the coding stage. The questions to ask, the contract terms that protect you, and the red flags that mean walk away.",
        "category": "Business",
        "prepend_md": """We hear the same story from UAE business owners every month: they paid a deposit, the agency went quiet, the demo did not match the brief, and the final invoice was double the quote. None of that is bad luck. It is a hiring process that skipped a few questions.

Before you read the checklist, here are the three things that protect you most:

1. **A written, fixed-price scope before any deposit.** If the company cannot describe what you will receive in plain language with a price attached, they do not understand your project yet. We send one within 48 hours of a call, free.
2. **Weekly demos of working software**, not slides. You should see your system running every week from week two.
3. **You own the code and the accounts.** Domain, hosting, app store accounts and the source code should be in your name from day one.

Where the company is based matters less than how it communicates. We are a remote-first team headquartered in Lahore working on Gulf Standard Time, and our UAE clients get same-day answers. Ask any agency, onshore or offshore, the twelve questions below.""",
    },
    {
        "slug": "mvp-development-guide",
        "title": "How Much Does an MVP Cost in 2026? Fixed-Price Examples from Real Builds",
        "seo_title": "How Much Does an MVP Cost in 2026? Fixed-Price Examples | Fuorix",
        "seo_description": "What an MVP really costs in 2026, with fixed-price examples from marketplaces, SaaS tools and business apps we have built, and the 12-week process we use to get to launch.",
        "excerpt": "An MVP should cost a fraction of the full product, but only if it is scoped like one. Real price bands from marketplaces, SaaS tools and internal apps we have shipped, and the 12-week process behind them.",
        "category": "Startups",
        "prepend_md": """Here are the price bands we actually quote for MVPs, before the process detail below.

| MVP type | Typical fixed price | Timeline | Example |
|---|---|---|---|
| Internal business tool (replace a spreadsheet, one workflow) | $800 to $2,500 | 3 to 5 weeks | Inventory or quoting tool for a trading company |
| Customer-facing web app with logins and payments | $2,500 to $6,000 | 6 to 10 weeks | Booking platform, client portal, subscription tool |
| Two-sided marketplace (web) | $6,000 to $15,000 | 10 to 16 weeks | [Buy Sell Liberia](/portfolio/buysell), a national classifieds marketplace |
| Mobile app plus backend | $5,000 to $12,000 | 10 to 14 weeks | Ordering or loyalty app with an admin panel |

Three things keep an MVP in these bands: one core user journey, off-the-shelf services for payments and email, and a fixed scope agreed in writing before the deposit. Add a second user type or a second platform and the price roughly doubles.

Every quote we give is fixed. If you have a one-page description of the idea, [book a call](/book) and you will have a scope and price within 48 hours. Now, the 12-week process.""",
    },
    {
        "slug": "ai-integration-for-business-applications",
        "title": "AI Automation for Small Businesses: 7 Things Worth Automating (and 5 That Aren't)",
        "seo_title": "AI Automation for Small Businesses: What's Worth Automating in 2026 | Fuorix",
        "seo_description": "Which AI automations pay for themselves in a small business, which are hype, and what each costs to build. Practical examples for UAE and UK SMBs from Fuorix.",
        "excerpt": "Most AI pitches to small businesses are hype. A few automations genuinely pay for themselves within months. Here are the seven we recommend, the five we talk clients out of, and what each costs.",
        "category": "AI & Automation",
        "prepend_md": """**Worth automating (we build these from $600):**

1. **WhatsApp and email enquiry triage.** Reads incoming messages, answers the common questions, books a call or creates a lead in your CRM. Pays for itself in the first month for any business with more than twenty enquiries a week.
2. **Quote and invoice drafting** from a short form or a voice note, using your own price list.
3. **Document extraction.** Supplier invoices, delivery notes and ID documents read into your system instead of retyped.
4. **Daily summaries** of sales, stock and cash across branches, sent to the owner every morning.
5. **Review and social replies** drafted for approval, in English and Arabic.
6. **Lead scoring and follow-up reminders** in your CRM.
7. **Internal search** over your policies, contracts and past quotes.

**Usually not worth it yet:** a fully autonomous sales agent, predictive analytics on fewer than two years of clean data, custom-trained models, AI-generated product descriptions at scale without review, and chatbots on a website that gets fewer than 500 visits a month.

Most of these automations are $600 to $3,000 fixed, plus the AI provider's usage cost, which is usually under $50 a month for an SMB. See [AI & Automation](/services/ai-automation) or read on for how we approach integration without the hype.""",
    },
    {
        "slug": "ui-ux-design-roi",
        "title": "Why Your Staff Hate the Software You Bought: UX for Internal Business Tools",
        "seo_title": "Why Staff Hate Your Business Software: UX for Internal Tools | Fuorix",
        "seo_description": "Internal software fails when staff route around it. Why UX matters for ERPs, CRMs and back-office tools, what good design costs, and how it shows up in adoption and revenue.",
        "excerpt": "The ERP is installed, the training is done, and everyone is still using WhatsApp and Excel. That is a design problem, not a discipline problem. What good UX looks like for internal tools and what it costs.",
        "category": "Design",
        "prepend_md": """A distributor in Ajman spent a year's budget on an off-the-shelf ERP. Eight months later, the warehouse team was still writing stock on paper and one admin was typing it in on Thursdays. The software worked. Nobody wanted to use it.

Internal tools fail for predictable reasons: too many fields, screens designed for the vendor's demo rather than the person on the warehouse floor, no mobile version, and no Arabic. Every one of those is a design decision.

When we build a custom system we design for the slowest, busiest user first. That usually means a phone-friendly layout, big buttons for gloves and sunlight, three fields instead of fifteen, and defaults that match how the team already talks about the work. Design is included in every fixed-price project we quote, and standalone UI/UX work starts from $400. See [UI/UX Design](/services/ui-ux-design).

The rest of this article covers the evidence that design pays for itself, for customer-facing products and internal ones alike.""",
    },
    {
        "slug": "managing-remote-development-teams",
        "title": "How to Work With a Remote Development Agency From Dubai or London (Timezones, Contracts, Payments)",
        "seo_title": "Working With a Remote Software Agency From Dubai or London: A Practical Guide | Fuorix",
        "seo_description": "How UAE and UK businesses work successfully with a remote software development team: timezones, communication cadence, contracts, payments, IP ownership and the red flags.",
        "excerpt": "Most software for UAE and UK businesses is built remotely, and most of it goes fine. Here is what a well-run remote engagement looks like: the timezone plan, the weekly cadence, the contract terms and how payment should work.",
        "category": "Business",
        "prepend_md": """If you are in Dubai or London and hiring a development team in Lahore, Cairo or Kyiv, the question is not whether remote works. It is whether the engagement is set up properly. Here is the setup we use with every client.

**Timezone.** We work Gulf Standard Time. Dubai clients have full overlap; London clients have overlap from 9am to 1pm UK time, which is enough for a daily check-in and a weekly demo.

**Cadence.** A written update every working day, a live demo every week, and a shared board you can open any time. If an agency cannot commit to that in writing, do not proceed.

**Contract.** Fixed price per milestone, IP assigned to you on payment of each milestone, source code in a repository you own, and a clear change-request process with prices.

**Payment.** Milestone-based, typically 30% to start, 40% at mid-project demo, 30% at launch. Bank transfer, Wise or card. Never 100% upfront.

The rest of this post is written from the team's side: how we run our own engineers remotely so that you get the responsiveness of an in-house team.""",
    },
    {
        "slug": "startup-tech-stack-2026",
        "title": "The Best Tech Stack for Startups in 2026: A Founder's Guide (With a $10k Budget Example)",
        "seo_title": "Best Tech Stack for Startups in 2026: A Founder's Guide | Fuorix",
        "seo_description": "The tech stack we recommend to founders in 2026 and why: Next.js, React Native, PostgreSQL and managed hosting. Includes exactly what we would build with a $10,000 budget.",
        "excerpt": "Founders do not need to pick technologies. They need a stack that is cheap to run, easy to hire for and does not need rebuilding at 10,000 users. Here is ours, and exactly what we would build with a $10k budget.",
        "category": "Startups",
        "prepend_md": """**What we would build with a $10,000 budget.** A founder came to us with $10k, an idea for a B2B booking tool, and a deadline of three months. This is how we would spend it, and it is the same shape for most SaaS ideas:

- $1,500: discovery, wireframes and a clickable prototype to validate with ten customers before building.
- $6,000: a Next.js web app with logins, one core workflow, Stripe subscriptions and an admin panel, on PostgreSQL.
- $1,000: a simple marketing site with a waitlist, analytics and email capture.
- $1,500: reserve for the changes you will inevitably want after the first real users.

Running cost after launch: roughly $30 to $80 a month on managed hosting until you have meaningful traffic. No mobile app in version one; a responsive web app covers it and saves $5,000.

That is a live product with paying customers for $10k. What follows is why we choose each part of the stack.""",
    },
    {
        "slug": "uk-business-custom-web-app",
        "title": "5 Signs Your UK Business Needs a Custom Web App",
        "seo_title": "5 Signs Your UK Business Needs a Custom Web App (and What It Costs) | Fuorix",
        "seo_description": "Spreadsheets, disconnected SaaS subscriptions and manual double entry are the signs a UK small business has outgrown off-the-shelf tools. What a custom web app costs and where to start.",
        "excerpt": "If your UK business is still running on spreadsheets, generic SaaS tools, or manual processes that eat up hours every week, it might be time for a custom web application built around the way you actually work.",
        "category": "Business Strategy",
        "prepend_md": """Before the five signs: if you recognise yourself in this post, the two pages to read next are [Spreadsheet to Software](/services/spreadsheet-to-software) (from $800, about £630) and our industry pages for [construction](/industries/construction), [real estate](/industries/real-estate) and [restaurants and retail](/industries/restaurants-retail), which show what we have built for businesses like yours.""",
    },
    {
        "slug": "dubai-restaurants-custom-erp",
        "title": "How Dubai Restaurants Are Replacing Excel with Custom ERP Systems",
        "seo_title": "How Dubai Restaurants Replace Excel with Custom ERP Systems (Costs Inside) | Fuorix",
        "seo_description": "Dubai restaurant groups are moving stock, purchasing, rotas and multi-branch reporting out of Excel into custom ERP systems. What they build, what it costs, and where to start.",
        "excerpt": "Restaurant businesses across Dubai and the UAE are ditching spreadsheets in favor of custom ERP systems that unify inventory, staff scheduling, and order management into a single platform.",
        "category": "Digital Transformation",
        "prepend_md": """See what we build for this sector, with pricing, on our [restaurant and retail software page](/industries/restaurants-retail). A single-restaurant inventory and purchasing system starts around $1,500 (AED 5,500); multi-branch dashboards and online ordering are added as separate fixed-price phases.""",
    },
    {
        "slug": "uae-business-dashboards-2026",
        "title": "Why UAE SMBs Are Investing in Custom Business Dashboards in 2026",
        "seo_title": "Why UAE SMBs Are Building Custom Business Dashboards in 2026 (Costs & Examples) | Fuorix",
        "seo_description": "UAE small and mid-sized businesses are replacing scattered Excel reports with live dashboards. What they track, what a custom dashboard costs from $800, and how to start with one data source.",
        "excerpt": "UAE small and mid-sized businesses are moving from scattered Excel reports and disconnected SaaS tools to unified real-time dashboards, and the results are transforming how they make decisions and grow.",
        "category": "Business Intelligence",
        "prepend_md": """**What a dashboard costs.** A single-view dashboard connected to one data source (your POS, accounting software or a Google Sheet) starts from $800 (AED 2,900) and takes two to three weeks. Multi-department analytics with several sources, scheduled reports and role-based views run $3,000 to $8,000. Details and FAQs on the [Business Dashboards](/services/business-dashboards) page.""",
    },
]

# Full rewrites: body replaced.
REPLACE = [
    {
        "slug": "how-much-does-custom-software-cost",
        "title": "Custom Software Cost in 2026: Real Price Bands for UAE and UK Small Businesses",
        "seo_title": "Custom Software Development Cost 2026: Real Prices for UAE & UK SMBs | Fuorix",
        "seo_description": "What custom software actually costs a small business in 2026: fixed-price bands for websites, web apps, spreadsheet replacements, ERPs, dashboards and mobile apps, with three worked examples in USD, AED and GBP.",
        "excerpt": "Forget the '$50,000 to $500,000' articles written for enterprises. Here are the fixed-price bands we quote small and mid-sized businesses in the UAE and UK, three worked examples, and the five things that move the price.",
        "category": "Pricing",
        "related_slugs": ["custom-erp-cost-uae", "mvp-development-guide", "what-to-look-for-when-hiring-a-software-development-company"],
        "body_md": """## The short answer

Most articles about custom software cost are written for enterprises and quote $50,000 to $500,000. If you run a 5 to 100 person business in Dubai, Manchester or Lahore, those numbers are useless to you.

Here is what we actually quote, as fixed prices, in 2026:

| What you need | Fixed price (USD) | Approx. AED | Approx. GBP | Timeline |
|---|---|---|---|---|
| Business website (custom-coded, fast, SEO-ready) | $500 to $2,000 | AED 1,800 to 7,300 | £400 to £1,600 | 3 to 4 weeks |
| Replace a spreadsheet with a web app | $800 to $2,500 | AED 2,900 to 9,200 | £630 to £2,000 | 3 to 5 weeks |
| Business dashboard (one to three data sources) | $800 to $3,000 | AED 2,900 to 11,000 | £630 to £2,400 | 2 to 4 weeks |
| Customer-facing web app with logins and payments | $2,500 to $6,000 | AED 9,200 to 22,000 | £2,000 to £4,700 | 6 to 10 weeks |
| Custom ERP (2 to 3 modules) | $1,500 to $5,000 | AED 5,500 to 18,400 | £1,200 to £4,000 | 8 to 12 weeks |
| Custom ERP (full suite: inventory, HR, accounting, CRM) | $5,000 to $15,000 | AED 18,400 to 55,000 | £4,000 to £11,900 | 12 to 16 weeks |
| Mobile app plus backend | $3,000 to $12,000 | AED 11,000 to 44,000 | £2,400 to £9,500 | 8 to 14 weeks |
| Marketplace or multi-vendor platform | $6,000 to $15,000 | AED 22,000 to 55,000 | £4,700 to £11,900 | 10 to 16 weeks |

Every number is a fixed price agreed before work starts, not an hourly estimate that grows. If a quote you receive elsewhere has no number attached, it is not a quote.

## Three worked examples

**A trading company in Sharjah replacing its stock spreadsheet.** Twelve staff, one Excel file that only the owner understood, stock counts on paper. We built a web app with product and supplier records, stock in and out on a phone, low-stock alerts and a daily summary email. Data was migrated from the spreadsheet. Fixed price $1,800 (AED 6,600), live in four weeks.

**A real estate brokerage in Dubai that needed a CRM.** Leads arriving from three portals and Instagram into separate inboxes. We built lead capture, automatic assignment to agents, viewing scheduling, a pipeline from enquiry to closing, and an owner dashboard. Fixed price $4,500 (AED 16,500), ten weeks, with a mobile agent app quoted separately as a later phase.

**A UK consultancy productising its service.** Clients were emailing documents and getting PDFs back. We built a client portal with logins, document upload, status tracking, Stripe payments and an admin queue. Fixed price £3,600 ($4,500), eight weeks.

## The five things that move the price

1. **Number of user types.** Owner-only is cheapest. Owner plus staff plus customers roughly doubles the screens, the permissions and the testing.
2. **Integrations.** Each connection to accounting software, a POS, a payment gateway or a government portal adds $300 to $1,500 depending on how good its API is.
3. **Data migration.** Clean spreadsheets migrate for almost nothing. Ten years of inconsistent Excel tabs can add 10 to 20 percent for cleaning and validation.
4. **Mobile.** A responsive web app works on phones and is included. A native app in the stores is a separate build, usually $3,000 or more.
5. **Language and compliance.** Arabic interfaces, UAE VAT and WPS reporting, UK GDPR data handling. Necessary, and each adds a little scope.

## What is included in our fixed price

Discovery and a written scope, UI design, development, data migration, testing, deployment to hosting you own, training for each user role, and 30 days of post-launch support. Hosting after that is typically $20 to $80 a month for an SMB system.

## What is not included, and what to budget for later

Ongoing feature changes (quoted per request or as a monthly retainer from $300), third-party subscriptions such as payment gateways or SMS, and app store fees.

## How to get an accurate price in 48 hours

Send us a one-paragraph description of the problem, a screenshot or export of the spreadsheet or tool you use today, and the number of people who will use the system. That is enough for a fixed-price scope within two working days. [Book a free call](/book) or [send the details](/contact).

For ERP-specific pricing in the UAE, see [How much does a custom ERP cost for a small business in the UAE?](/blog/custom-erp-cost-uae).""",
    },
    {
        "slug": "custom-erp-cost-uae",
        "title": "How Much Does a Custom ERP Cost for a Small Business in the UAE? (2026 Prices, Module by Module)",
        "seo_title": "Custom ERP Cost for a UAE Small Business: 2026 Prices by Module | Fuorix",
        "seo_description": "Custom ERP pricing for UAE small businesses in 2026, module by module in AED: inventory, invoicing and VAT, HR and WPS payroll, CRM, reporting. Includes a worked example and the questions that change the price.",
        "excerpt": "Most 'ERP cost in UAE' articles give you a range from AED 40,000 to AED 300,000 and no way to place yourself in it. Here is our pricing module by module, a worked example for a 25-person business, and what makes the number go up or down.",
        "category": "Pricing",
        "related_slugs": ["how-much-does-custom-software-cost", "dubai-restaurants-custom-erp", "uae-business-dashboards-2026"],
        "body_md": """## The short answer

A custom ERP for a UAE small business costs between **AED 5,500 and AED 55,000** ($1,500 to $15,000) as a fixed price, depending on how many modules you need. Most 10 to 50 person businesses land between AED 15,000 and AED 30,000 for their first version, and go live in 8 to 14 weeks.

That is far below the AED 100,000 to 300,000 figures in most articles, for two reasons. Those articles are written by agencies with Dubai offices and enterprise overheads, and they describe systems for hundreds of users. We are a remote-first team working on Gulf time, and we build for businesses that need three modules, not thirty.

## Pricing module by module

| Module | What it covers | Fixed price (AED) |
|---|---|---|
| Core (always included) | Company setup, user logins, roles and permissions, audit log, Excel and PDF export | Included |
| Inventory and purchasing | Products, suppliers, stock in and out, multi-location stock, reorder alerts, stock counts on a phone | AED 5,500 to 11,000 |
| Sales, invoicing and VAT | Quotes, invoices, credit notes, payment tracking, FTA-compliant VAT reports | AED 5,500 to 11,000 |
| CRM and pipeline | Leads, follow-up reminders, deal stages, customer history, WhatsApp click-to-chat | AED 4,000 to 9,000 |
| HR and payroll | Employee records, leave, attendance, WPS-format payroll files, gratuity accrual | AED 5,500 to 11,000 |
| Projects or jobs | Job cards, costing against estimate, site photos, client approvals | AED 5,500 to 11,000 |
| Reporting dashboard | Owner dashboard across every module, scheduled email reports | AED 3,000 to 7,000 |
| Arabic interface | Full right-to-left bilingual UI | AED 2,000 to 4,000 |
| Data migration | Import and cleaning of existing spreadsheets or legacy system | AED 1,000 to 5,000 |

Pick the modules you need, add them up, and you have a realistic budget before you speak to anyone.

## A worked example: 25-person distribution company in Dubai

Current state: stock in an Excel file, invoices in a desktop accounting tool, payroll done by hand, no view of profit per product line.

What we would build in version one: inventory and purchasing (AED 8,000), sales and invoicing with VAT (AED 8,000), owner dashboard (AED 4,000), migration of three years of data (AED 2,500). **Total AED 22,500, 12 weeks.** HR and payroll added in a second phase three months later for AED 7,000 once the team is comfortable with the first system.

Time saved after launch, based on what similar clients report: 15 to 25 staff-hours a week on data entry and reconciliation, which at UAE salary levels is AED 8,000 to 15,000 a month. The system pays for itself in under six months.

## What makes the price go up

- Integrating with an existing accounting package or POS through its API (AED 1,000 to 5,000 per integration).
- More than one legal entity or currency.
- Customer-facing portals in addition to the internal system.
- Offline mobile use for warehouse or site staff.
- Ten years of messy historical data.

## What makes the price go down

- Starting with two modules and adding the rest in later phases.
- Clean data in well-structured spreadsheets.
- Using our standard modules and adjusting them, rather than reinventing invoicing from scratch.
- Being available for a weekly one-hour review so decisions do not stall.

## Custom ERP vs Odoo, Zoho and other off-the-shelf options

Off-the-shelf ERPs cost less on day one and more every month: AED 100 to 300 per user per month, plus AED 20,000 to 60,000 for an implementation partner to configure them. For a 25-person team that is AED 30,000 to 90,000 a year in licences, forever, for a system that still needs workarounds. A custom ERP is a one-time fixed price, has no per-user fees, and does exactly what your process needs. Off-the-shelf is the right answer when your process is completely standard and you have fewer than five users.

## Getting a fixed quote

Send us a description of your current process, screenshots or exports of the spreadsheets you use, and the number of users. We return a written module-by-module scope with a fixed price within 48 hours. [Book a free call](/book), or read what we have built for [restaurants and retail](/industries/restaurants-retail), [construction](/industries/construction) and [real estate](/industries/real-estate).""",
    },
]

# New posts.
CREATE = [
    {
        "slug": "replace-excel-with-custom-app-cost",
        "title": "Replace Excel With a Custom App: What It Costs and How Long It Takes",
        "seo_title": "Replace Excel With a Custom App: Cost & Timeline in 2026 | Fuorix",
        "seo_description": "What it costs to replace an Excel or Google Sheets process with a custom web app: fixed price bands from $800, a four-week timeline, what gets migrated, and how to know if you are ready.",
        "excerpt": "The stock sheet only one person understands, the quoting template with broken formulas, the client list in three versions. Here is what it costs to turn those into a proper multi-user app, how long it takes, and how to tell if you are ready.",
        "category": "Digital Transformation",
        "cover_url": "/blog/dubai-restaurants-custom-erp/01.png",
        "cover_alt": "Spreadsheet being replaced by a custom web application dashboard",
        "published_at": "2026-09-18T09:00:00Z",
        "related_slugs": ["how-much-does-custom-software-cost", "custom-erp-cost-uae", "uk-business-custom-web-app"],
        "body_md": """## The spreadsheet that runs the company

Almost every business we work with in the UAE, UK and Pakistan has one. It started as a quick way to track stock, quotes, jobs or clients. Five years later it has fourteen tabs, formulas nobody dares touch, and a name like `Master_FINAL_v7_use_this_one.xlsx`. One person knows how it works. When they are on leave, things stop.

You do not need an ERP to fix this. You need that one spreadsheet turned into a small web application. This post explains what that costs, how long it takes, and what actually happens during the project.

## What it costs

| Scope | Fixed price (USD) | Approx. AED | Approx. GBP | Timeline |
|---|---|---|---|---|
| One spreadsheet, one workflow (stock list, quote calculator, job tracker, client register) | $800 to $1,500 | AED 2,900 to 5,500 | £630 to £1,200 | 3 to 4 weeks |
| One spreadsheet with several roles and approvals (staff enter, manager approves, owner reports) | $1,500 to $2,500 | AED 5,500 to 9,200 | £1,200 to £2,000 | 4 to 6 weeks |
| Several connected spreadsheets across departments | $2,500 to $8,000 | AED 9,200 to 29,000 | £2,000 to £6,300 | 6 to 10 weeks |

The price is fixed before we start. It includes design, development, migration of your existing data, training and 30 days of support. Hosting afterwards is typically $20 to $40 a month.

## What you get that the spreadsheet cannot give you

- **Everyone works on the same live data.** No more emailing files or asking who has the latest version.
- **Logins and permissions.** Staff see and edit only what their role needs. Nobody can overwrite the wrong row or delete a tab.
- **Validated entry.** Dropdowns instead of free text, required fields, automatic calculations. Data goes in right the first time.
- **A phone-friendly version.** Stock counts, job updates and customer notes from the warehouse, the site or the car.
- **Reports that build themselves.** The totals and charts you used to assemble every Monday are live.
- **Export to Excel any time.** Your accountant still gets a spreadsheet. It is just generated from clean data.

## The four-week timeline

**Week 1: audit and scope.** You send us the spreadsheet. We map every tab, formula and hand-off between people, then show you screens of what the app will look like and a fixed price. You approve before anything is built.

**Week 2 and 3: build and import.** We build the app, import your real data, and give your team access while the spreadsheet is still running in parallel. They test with real work, and we adjust.

**Week 4: switch-over and training.** A short training session per role, a cut-over date, and the spreadsheet is retired. We stay on for 30 days after that.

Bigger scopes stretch the middle phase; the shape is the same.

## Signs you are ready

- More than two people need to edit the same sheet.
- Someone spends more than two hours a week copying data between files.
- You have been burned by a broken formula or an overwritten file at least once.
- Staff need to enter or check data from a phone.
- You cannot answer "how did we do last month?" without building a report by hand.

Two of those is enough. Five means it is costing you real money every week.

## What we need from you to quote

The spreadsheet (or a copy with sensitive figures removed), a short description of who uses it and for what, and the number of users. That is enough for a fixed-price scope within 48 hours.

Read more on the [Spreadsheet to Software](/services/spreadsheet-to-software) page, or [book a free call](/book) and bring the file.""",
    },
    {
        "slug": "custom-erp-vs-odoo-vs-zoho",
        "title": "Custom ERP vs Odoo vs Zoho: Which Is Right for a 10 to 50 Person Company?",
        "seo_title": "Custom ERP vs Odoo vs Zoho for a 10-50 Person Company (2026 Comparison) | Fuorix",
        "seo_description": "An honest comparison of a custom ERP against Odoo and Zoho for small businesses in the UAE and UK: total cost over three years, fit, implementation time, and when each option is the right call.",
        "excerpt": "Odoo and Zoho are excellent products, and we still recommend them to some clients. Here is a three-year cost comparison against a custom ERP for a 25-person business, and a plain rule for choosing.",
        "category": "Business",
        "cover_url": "/blog/custom-erp-cost-uae/01.png",
        "cover_alt": "Comparison of custom ERP, Odoo and Zoho for small businesses",
        "published_at": "2026-09-18T09:05:00Z",
        "related_slugs": ["custom-erp-cost-uae", "how-much-does-custom-software-cost", "replace-excel-with-custom-app-cost"],
        "body_md": """## The honest starting point

We build custom ERPs. We also tell roughly a third of the businesses who ask us about one to go and buy Zoho or Odoo instead. This comparison is the one we walk clients through.

## The three options in one paragraph each

**Zoho One and Zoho's individual apps.** A large suite of cloud apps (CRM, Books, Inventory, People) that work together reasonably well. Cheap per user, fast to start, good for standard processes. Customisation is possible but quickly becomes a second job.

**Odoo.** An open-source ERP with hundreds of modules. Very capable, and in the UAE there is a large ecosystem of implementation partners. Community edition is free to license but you will pay a partner to set it up; Enterprise adds per-user fees. Customising Odoo deeply means paying Odoo developers, which is a specialist skill.

**Custom ERP.** Built around your process with only the modules you need. One-time fixed price, no per-user fees, yours to change. Nothing you do not need, but also nothing you did not ask for.

## Three-year cost for a 25-person company

Assumptions: 25 users, inventory plus invoicing plus CRM, UAE VAT, modest customisation. Prices in USD; multiply by 3.67 for AED.

| | Zoho | Odoo Enterprise with partner | Custom ERP (Fuorix) |
|---|---|---|---|
| Setup and implementation | $2,000 to $5,000 | $8,000 to $20,000 | $6,000 to $12,000 (fixed) |
| Licences, per year | $9,000 to $15,000 (25 users) | $7,500 to $12,000 (25 users) | $0 |
| Customisation over 3 years | $3,000 to $10,000 | $5,000 to $20,000 | $2,000 to $6,000 |
| Hosting, per year | Included | $600 to $1,500 | $400 to $1,000 |
| **Three-year total** | **$32,000 to $60,000** | **$37,000 to $80,000** | **$9,000 to $21,000** |

The pattern is consistent: off-the-shelf is cheaper in month one and more expensive by year two. The crossover is usually around 12 to 18 months for a team of this size, earlier for larger teams because per-user fees scale.

## When Zoho is the right answer

- Fewer than ten users and a standard process (sell, invoice, collect).
- You need it running next week.
- You want dozens of small tools (email marketing, sign, help desk) from one vendor.
- Nobody on your team will ever want a screen that works differently from the default.

## When Odoo is the right answer

- You have a manufacturing, multi-warehouse or accounting-heavy operation that maps closely to Odoo's modules.
- You have, or will hire, an in-house person who can administer it.
- You are comfortable with a partner relationship for changes.

## When a custom ERP is the right answer

- You have already bent a spreadsheet or a SaaS tool around a process that is genuinely different: construction estimating, real estate commissions, restaurant recipe costing, trading with credit terms.
- You have more than ten users, so per-user fees hurt.
- Your staff need a simple phone-friendly screen with three fields, not a full ERP interface.
- You want to own the system and never lose access if a vendor changes its pricing.

## A plain rule

If you can describe your process in the words the software vendor uses, buy the software. If you keep saying "but we do it differently because...", build.

## What a custom ERP costs with us

Two to three modules from $1,500 to $5,000; a full suite from $5,000 to $15,000; fixed before we start. Details module by module in [How much does a custom ERP cost in the UAE?](/blog/custom-erp-cost-uae) and on the [Custom ERP Systems](/services/erp-systems) page. If Zoho or Odoo is the better fit, we will say so on the call. [Book one here](/book).""",
    },
    {
        "slug": "real-estate-crm-build-vs-buy-uae",
        "title": "Real Estate CRM: Build Custom or Buy? A Cost Comparison for UAE Brokerages",
        "seo_title": "Real Estate CRM for UAE Brokerages: Build Custom or Buy? Cost Comparison | Fuorix",
        "seo_description": "Should a Dubai or UAE real estate brokerage buy a CRM or build one? Costs of off-the-shelf property CRMs vs a custom CRM, what agents actually use, portal integrations, and a decision checklist.",
        "excerpt": "Off-the-shelf property CRMs charge per agent forever and still do not handle your commission structure. A custom CRM is a one-time cost but has to be built well. Here is how UAE brokerages should decide, with numbers.",
        "category": "Real Estate",
        "cover_url": "/portfolio/powersell.webp",
        "cover_alt": "Real estate CRM dashboard with leads pipeline and agent leaderboard",
        "published_at": "2026-09-18T09:10:00Z",
        "related_slugs": ["custom-erp-vs-odoo-vs-zoho", "how-much-does-custom-software-cost"],
        "body_md": """## Why brokerages keep switching CRMs

Ask a Dubai brokerage owner which CRM they use and you will usually hear a list: the one they started with, the one the portal recommended, the one an agent brought from a previous company, and the WhatsApp groups where the real work happens. Each switch cost onboarding time and lost data. The reason is the same every time: the CRM was built for a generic sales team, not for property in the UAE.

## What a real estate CRM in the UAE actually has to do

- Capture leads from Property Finder, Bayut, Dubizzle, your website, Instagram and walk-ins into one queue.
- Assign leads fairly (round robin, by area, by language) and show who is not following up.
- Track units, not just contacts: availability, price changes, viewings, offers, MoUs.
- Handle commission splits, referral fees and off-plan payment plans.
- Give the owner a dashboard: leads by source, conversion by agent, days on market.
- Work in English and Arabic, on a phone, from a car.

## The cost of buying

Property-specific CRMs and generic ones configured for property typically cost **AED 150 to 400 per agent per month**, plus setup. For a 15-agent brokerage that is AED 27,000 to 72,000 a year, every year, and most still need spreadsheets for commissions and a separate tool for portal feeds. Over three years: AED 80,000 to 220,000.

## The cost of building

A custom CRM for a single brokerage, covering lead capture from every source, assignment, pipeline, viewings, unit inventory and owner dashboards, is a fixed **$2,500 to $6,000 (AED 9,200 to 22,000)** with us and takes 6 to 10 weeks. Portal feed integrations and a mobile agent app are usually added as later phases at $1,000 to $4,000 each. Hosting is about AED 100 to 300 a month. Three-year total, including a second phase: **AED 25,000 to 50,000**, with no per-agent fees as you grow.

## What agents will actually use

This is where most CRM projects fail, bought or built. Agents use tools that are faster than WhatsApp. That means: one tap to log a call, a lead card that shows the last three interactions, viewing scheduling that sends the client a confirmation, and nothing that takes more than 20 seconds. We build the agent screen first and the owner reports second. [PowerSell](/portfolio/powersell), a real estate platform we built with more than 1,000 active users, uses leaderboards and gamification for the same reason: agents use what rewards them.

## Decision checklist

Buy if:

- You have fewer than eight agents and a standard sales process.
- You have no unusual commission or referral structure.
- You want it live this month.

Build if:

- You have more than ten agents (per-seat fees now cost more than a build within two years).
- Your commission, referral or off-plan logic lives in a spreadsheet because no CRM handles it.
- You want lead data and client history to be yours permanently.
- Agents have already abandoned two CRMs.

## Getting a quote

Tell us how many agents you have, which portals you list on, and where leads currently go. We return a fixed-price scope within 48 hours. See what we build for the sector on the [real estate software page](/industries/real-estate) or [book a call](/book).""",
    },
    {
        "slug": "construction-estimation-software-excel-limits",
        "title": "Construction Estimation Software: Why Excel Breaks at 20 Tenders a Month",
        "seo_title": "Construction Estimation Software vs Excel: Why Spreadsheets Break at Scale | Fuorix",
        "seo_description": "Why Excel estimating breaks once a contractor is quoting 20 or more tenders a month, what custom estimation and BOQ software does instead, what it costs, and how we built estimation platforms for construction firms.",
        "excerpt": "Every contractor starts estimating in Excel and most never leave. Here is the point where it starts costing you tenders, what purpose-built estimation software does differently, and what it costs to build one around your rate libraries.",
        "category": "Construction",
        "cover_url": "/portfolio/authorestimation.com_.png",
        "cover_alt": "Construction estimation software showing a bill of quantities and rate library",
        "published_at": "2026-09-18T09:15:00Z",
        "related_slugs": ["replace-excel-with-custom-app-cost", "custom-erp-cost-uae"],
        "body_md": """## Excel is a fine estimating tool, until it isn't

Every estimator we have worked with started in Excel. It is flexible, everyone knows it, and a good template can produce a decent bill of quantities. We built estimation platforms for [Tameer Estimations](/portfolio/tameer), [Author Estimation](/portfolio/authorestimation) and [Ashlar](/portfolio/ashlar), and every one of them began as a spreadsheet that had stopped keeping up.

The breaking point is usually volume. Somewhere around 15 to 20 tenders a month, with two or more estimators, the things that made Excel convenient start costing you money.

## The five ways it breaks

**1. Rates drift.** Each estimator keeps their own copy of the rate sheet. Supplier prices change, one copy gets updated, the others quote last quarter's numbers. You find out when the job runs over.

**2. Formulas break silently.** A row inserted in the wrong place, a range that no longer covers the new items, a markup cell overwritten with a number. The total looks plausible and is wrong.

**3. Revisions are unmanageable.** Tender revision three lives in an email attachment. Nobody can say what changed between revisions two and three, or which one the client accepted.

**4. Nothing is reusable.** The assemblies you priced last month (a square metre of blockwork, a bathroom fit-out) are buried in an old file. Every estimate starts from scratch.

**5. No link to actuals.** Once the job is won, costs are tracked in a different file. You never learn which line items you consistently under-price.

## What estimation software does instead

- **One rate library** for the whole company, by trade and supplier, with a history of changes. Update a rate and every open estimate can be refreshed.
- **Assemblies and templates.** Price a bathroom once, reuse it with quantities adjusted.
- **Structured take-off entry** with units, waste factors and markup rules applied consistently.
- **Versioned estimates** with a diff between revisions and a record of which was sent.
- **Branded PDF quotes and BOQs** generated in seconds, in your format.
- **Estimate versus actual** per cost code once the job starts, so your rates improve every project.

## What it costs

A quoting and BOQ platform for one company, with a rate library, take-off entry, assemblies, versioning, PDF output and user accounts, is a fixed **$2,000 to $6,000 (AED 7,300 to 22,000)** and takes 6 to 10 weeks. We import your existing rate sheets and historical quotes, so the first estimate in the new system is faster than the last one in Excel. Project cost tracking, a site app for daily logs and a client approval portal are usually later phases at $1,500 to $4,000 each.

Compare that with the margin on one under-priced tender.

## How the project runs

We start by auditing your current templates and keeping the calculation logic you trust. Estimators test with real tenders while Excel is still in use. Switch-over happens when they prefer the new system, which in our experience takes about two weeks.

See what we build for contractors on the [construction and estimation software page](/industries/construction), or [book a call](/book) and bring your rate sheet.""",
    },
    {
        "slug": "software-house-lahore-vs-dubai-agency",
        "title": "Software House in Lahore vs Dubai Agency: An Honest Cost and Quality Comparison",
        "seo_title": "Software House in Lahore vs Dubai Agency: Honest Cost & Quality Comparison | Fuorix",
        "seo_description": "What a UAE business actually gets from a Dubai agency versus a Lahore software house: price, seniority, communication, contracts and risk. Written by a Lahore-headquartered team that serves Dubai clients.",
        "excerpt": "Most Dubai agencies subcontract to Lahore, Karachi or Cairo anyway. Here is what you pay for the office in between, when it is worth it, and how to get senior engineers directly with the same accountability.",
        "category": "Business",
        "cover_url": "/blog/what-to-look-for-when-hiring-a-software-development-company/01.webp",
        "cover_alt": "Comparing a Dubai software agency with a Lahore software house",
        "published_at": "2026-09-18T09:20:00Z",
        "related_slugs": ["what-to-look-for-when-hiring-a-software-development-company", "managing-remote-development-teams", "how-much-does-custom-software-cost"],
        "body_md": """## Where this is written from

We are headquartered in Lahore and most of our clients are in the UAE and UK. So read this knowing where we sit. We have tried to be fair to Dubai agencies, several of which do excellent work, and honest about the offshore failure modes that give Pakistani software houses a bad name.

## The open secret

A large share of software sold by Dubai agencies is built in Lahore, Karachi, Cairo or Hyderabad. The Dubai office handles sales, account management and sometimes design. This is not a scandal; it is how the industry works. The question for you is what the layer in between costs and what it gives you.

## Price

| | Dubai agency | Lahore software house (senior team) |
|---|---|---|
| Business website | AED 15,000 to 50,000 | AED 1,800 to 7,300 |
| Custom web app or CRM | AED 60,000 to 200,000 | AED 9,000 to 22,000 |
| Custom ERP (2 to 3 modules) | AED 100,000 to 250,000 | AED 5,500 to 18,000 |
| Senior developer day rate | AED 2,500 to 4,500 | AED 600 to 1,200 |

The difference is mostly rent, salaries at Dubai levels, and sales overhead. It is not, in our experience, engineering quality, provided you are actually getting senior engineers.

## What the Dubai office genuinely gives you

- A person you can meet in the same city, which matters for some owners and for large contracts.
- Familiarity with UAE compliance, government tenders and local payment norms.
- A legal entity in the UAE, which some procurement departments require.
- Accountability you can enforce locally if things go wrong.

If you are spending AED 500,000 or more, or bidding for government work, these are worth paying for.

## What a good Lahore software house gives you

- Senior engineers directly, without a sales layer between you and the people building.
- Gulf Standard Time working hours; Lahore is one hour ahead of Dubai.
- Fixed prices at a fraction of the cost, which for an SMB is the difference between building and not building.
- English-speaking teams with years of experience serving Gulf clients. Arabic UI support is standard.

## The offshore failure modes, and how to avoid them

Cheap offshore work fails in predictable ways: junior developers presented as senior, no written scope, silence after the deposit, code you do not own. Every one of these is avoidable with the same checks you would apply anywhere:

1. Insist on a written fixed-price scope before paying anything.
2. Ask to speak to the engineers, not just the account manager.
3. Require weekly demos of working software.
4. Put the code in a repository you own, from day one.
5. Pay by milestone, never 100% upfront.
6. Ask for references you can call.

A firm that agrees to all six readily is safe to work with, in Lahore or Dubai. A firm that resists any of them is a risk in either city.

## Our honest recommendation

For projects under AED 100,000, a senior Lahore or Karachi team working directly with you gives the best value by a wide margin, as long as you apply the six checks. For very large or government projects, a Dubai entity with a strong delivery partner is often the pragmatic choice.

If you want to see how we work before committing, [book a free call](/book): you will speak to an engineer, and you will have a fixed-price scope within 48 hours. How we run remote engagements is described in [How to work with a remote development agency](/blog/managing-remote-development-teams).""",
    },
]
