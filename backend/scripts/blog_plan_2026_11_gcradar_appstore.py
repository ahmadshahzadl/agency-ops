"""2026-11 follow-up: correct the GC Radar mobile app claim in the construction-leads
post now that it's confirmed live on the Apple App Store (previously said "shipping
through TestFlight", which undersold it). Apply with:

    cd /opt/fuorix/app/backend
    .venv/bin/python scripts/apply_blog_plan.py --plan blog_plan_2026_11_gcradar_appstore --dry-run
    .venv/bin/python scripts/apply_blog_plan.py --plan blog_plan_2026_11_gcradar_appstore
"""

MARK = ""
UNPUBLISH: list[str] = []
UPDATE: list[dict] = []
CREATE: list[dict] = []

REPLACE = [
    {
        "slug": "how-to-get-construction-leads",
        "body_md": """## Why most subcontractors are stuck waiting for the phone to ring

Ask a drywall, framing, or concrete subcontractor how they get work, and you'll hear some version of the same answer: referrals, repeat GCs, and whoever happens to call around when a job opens up. That's not a lead generation strategy — it's hoping you're top of mind on the right day.

The problem isn't effort. It's timing. By the time a general contractor is dialing subcontractors for bids, the job is already public knowledge to everyone else dialing too. You're not competing on price or quality at that point — you're competing on who picked up the phone first. And the subcontractors who always seem to get the good jobs aren't necessarily better at the trade. They're earlier.

## The tactics that still matter

Before getting into what's changing, the fundamentals haven't gone away:

- **Google Business Profile, done properly.** Photos of finished work, service areas listed accurately, and — this is the part most contractors skip — replying to every review within a day. A profile that looks abandoned reads as a business that's slow to respond to calls too.
- **Review velocity, not just review count.** Ten reviews from the last two months outperform fifty reviews from three years ago, both for Google ranking and for a homeowner deciding who to trust.
- **Speed of response.** Multiple studies on lead conversion agree on this: the subcontractor who replies within five minutes converts at dramatically higher rates than one who replies within an hour, regardless of price. Most subcontractors lose jobs to slower follow-up, not worse bids.
- **Repeat GC relationships.** A general contractor who's used you three times stops shopping your trade around. That relationship is worth protecting with on-time, on-budget delivery more than it's worth chasing with discounts.

These tactics compete for the same leads everyone else is chasing. They don't get you there first.

## What's actually new: public records as an early-warning system

Every building permit and every inspection result is public record. A building permit gets filed, a foundation gets poured, a foundation inspection passes, framing starts. That sequence happens in a specific, fairly predictable order — and it happens in county and municipal systems that anyone can look up.

The problem is that "anyone can look it up" and "anyone actually does" are very different things. A single subcontractor checking county permit portals by hand, every day, across every jurisdiction they work in, translating inspection codes into "this house needs drywall in about two weeks" — that's not a weekend project. It's a full-time job on its own, before you've picked up a single tool.

That's the gap. The subcontractors getting ahead of their competition aren't working harder at the same game everyone else is playing. They're watching a signal nobody else is watching.

## How we built this for a real client: GC Radar

We're the engineering team behind [GC Radar](https://gcradar.io), a product that does exactly this for construction subcontractors. It's worth walking through because it shows both what's possible and what it actually takes to build.

GC Radar watches permitting and inspection activity across a growing list of counties, and translates the raw record into a construction stage a subcontractor actually cares about: foundation, framing, rough-in, interior finishes. The moment a house enters the stage that matters for a given trade, the subscriber gets alerted — with the builder's contact information already attached, because a lead with no phone number isn't a lead.

The hard part was never reading a permit. It was making the translation reliable. Every county publishes differently. The same inspection code — "framing," "bond beam," "plumbing slab" — can mean a different construction stage depending on which county and which builder typed it in. Get that wrong and a subcontractor either wastes a call on a house that isn't ready, or misses one that's already framed and gone to a competitor. So the system that powers this runs its own regression test suite built from real county records: a change to how one county's codes get interpreted has to pass every previously-verified case before it ships, or the change doesn't go out.

On top of the signal engine sits a full product: a live feed of new leads, a map of every active opportunity in a subcontractor's county with dollar values attached, and a pipeline board to track a job from new to won. Because crews are on job sites, not at desks, we also built a native companion app with Flutter, giving the same Radar feed, map, route planner and pipeline on a phone — it's [live on the Apple App Store](https://apps.apple.com/us/app/gc-radar/id6806368289) today.

![GC Radar's mobile app showing a live feed of construction leads with builder names, addresses, deal value and one-tap contact buttons](/blog/how-to-get-construction-leads/04.webp)

GC Radar runs today across 16 jurisdictions in South Carolina, North Carolina, Georgia, Florida and Tennessee, with more than a dozen trades using it to find work. It's also a case study in something subcontractors underestimate: we later cut the infrastructure bill behind the product by roughly 90%, with zero downtime and zero data loss, while it kept running the entire time — proof that a system like this doesn't have to be expensive to operate once it's built right.

## What this means if you're not in one of those counties yet

If your market isn't one GC Radar covers, the takeaway isn't "wait until it is." It's that the model — watching a public signal that predicts demand before your competitors notice it — works in any county that publishes permit and inspection data, which is most of them. Some trades and markets will have a different leading indicator entirely: a zoning filing, a demolition permit, a subdivision plat recording. The specific signal changes. The principle — find the public record that fires before your competitors' phones start ringing, and watch it systematically — doesn't.

That's also, honestly, a software project, not a weekend research task. It needs someone to figure out what signal actually predicts a job in your trade, build something that checks it reliably, and keep that running without becoming its own full-time distraction.

## If you want something like this for your own trade or market

This is exactly the kind of system we build: a signal engine that turns messy, inconsistent public data into something your team can act on, wrapped in a product simple enough that a crew on a job site actually uses it. You don't need a finished spec or a technical background to start that conversation — describe the problem in plain language, and we'll tell you honestly whether a permit-tracking system, a simpler automation, or something else entirely is the right first build for your market.

A focused MVP like this typically runs $2,500–15,000 depending on scope, 6–16 weeks, fixed price, quoted after a free scoping call. [See how we build products like this →](/services/ai-automation) or [book a free 30-minute call](/book) and bring your market, not a spec.""",
    },
]
