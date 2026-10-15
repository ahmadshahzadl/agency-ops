"""Refresh the Next.js security post with the published advisories (October 2026).

Applied by:  scripts/apply_blog_plan.py --plan blog_plan_2026_10_nextjs_refresh
Pure data: no imports, no side effects. Same shape as blog_plan_2026_09.py.

The post was written on 26 September against Vercel's pre-announcement. Vercel shipped seven of the
nine fixes on 30 September (15.5.27 / 16.3.8) and the two deferred ones on 14 October (15.5.28 /
16.4.1). This plan replaces the body and metadata with the final list. Slug stays the same so the
URL and any links to it keep working.

Sources: nextjs.org/blog/upcoming-nextjs-security-release-september-2026 and the GitHub advisories
GHSA-2464-fhr4-w9xw, GHSA-p3m5-59mp-jv5r, GHSA-673q-mjm6-r5xr, GHSA-cjq9-62q9-8jv4,
GHSA-f87g-xv8r-7p7x, GHSA-4jqv-mc3x-m676, GHSA-mcj8-r9mp-w47p, GHSA-3w37-wq28-93x7,
GHSA-h694-7cp9-m8p3, GHSA-39w2-rjm5-chcv, GHSA-vcvr-r3jv-pc5j.
"""

MARK = "<!-- plan-2026-10-nextjs-refresh -->"

UNPUBLISH: list[str] = []
UPDATE: list[dict] = []
CREATE: list[dict] = []

REPLACE = [
    {
        "slug": "nextjs-security-release-september-2026",
        "title": "Next.js Shipped Two Security Releases in Two Weeks. Here Is the Full List and the Version Your Site Needs",
        "seo_title": "Next.js Security Patches September and October 2026: Full List, Affected Versions, What to Do | Fuorix",
        "seo_description": "Next.js fixed nine vulnerabilities across 30 September and 14 October 2026, including a critical remote code execution in image optimization. Which versions are safe (15.5.28, 16.4.1), how to check your site, and what to do if nobody maintains it.",
        "excerpt": "Vercel's September security release landed on 30 September, and the two issues it deferred, one of them critical, followed on 14 October. If your business website runs Next.js, it needs to be on 15.5.28 or 16.4.1. Here is the full list and how to check.",
        "category": "Web Development",
        "related_slugs": ["why-nextjs-is-the-best-framework-for-business-websites", "how-to-reduce-website-load-time", "what-to-look-for-when-hiring-a-software-development-company"],
        "body_md": """*Updated 15 October 2026. This post first went up on 26 September, when Vercel pre-announced the release. It now reflects the published advisories.*

## What actually shipped

Vercel, the company behind Next.js, pre-announced a security release for 30 September covering nine vulnerabilities. It arrived in two parts.

**30 September: Next.js 15.5.27 and 16.3.8.** Seven fixes: one high, five medium, one low. Two issues, one critical and one high, were held back for upstream coordination.

**14 October: Next.js 15.5.28 and 16.4.1.** The two deferred fixes, plus a third critical issue that affects Next.js 16 only.

A separate critical fix for the `next/og` image package shipped on 22 September in 16.3.6.

So the versions a site needs today are **15.5.28** on the 15 line and **16.4.1** on the 16 line. Anything older is missing at least one critical fix.

## The full list

The ones that matter most to a typical business website:

- **Critical. Remote code execution through image optimization when SVG files are used** (CVE-2026-96889, CVSS 9.5). Affects every version from 10.0.0 to 15.5.27 and 16.0.0 to 16.4.0 when Next.js runs on a glibc-based Linux server, which covers almost every VPS, droplet and container deployment. The flaw is in `sharp`, the image library Next.js uses, so the fix is two parts: Next.js 15.5.28 or 16.4.1, and `sharp` 0.35.5 or newer. Fixed on 14 October.
- **High. Denial of service through Server Actions** (CVSS 8.2). A crafted request can pin the CPU and block every other request in the process. Affects 13.0.0 to 15.5.27 and 16.0.0 to 16.4.0 on sites that use the App Router with at least one Server Action. No workaround. Fixed on 14 October.
- **High. Server-side request forgery in image optimization** (CVE-2026-94483, CVSS 8.3). An attacker can use an allow-listed remote image host to make the server fetch private addresses. Only affects sites with `images.remotePatterns` configured, and only on the 16 line. Fixed on 30 September.
- **Medium. Two cache-poisoning bugs in self-hosted static and ISR pages.** One lets content from one user's request be served to others; the other causes a persistent denial of service. Both fixed on 30 September in 15.5.27 and 16.3.8.
- **Medium. Information disclosure in App Router metadata image routes.** Fixed on 30 September in both lines.

The rest affect Next.js 16 only: a critical remote code execution in `use cache` functions that return typed arrays (fixed 14 October in 16.4.1), two medium cache leaks around `use cache` and Draft Mode, a low-severity disclosure in the development server, and the `next/og` remote code execution from 22 September (versions 16.2.0 to 16.3.5).

## Why this matters to you, not just your developer

Next.js is the framework behind a large share of the business websites built in the last three years, including most of the ones we ship for clients in the UAE, the UK and Pakistan. It is a good choice, and this release does not change that. Every serious framework has security releases. What matters is whether anyone is going to apply this one to your site.

Here is the uncomfortable pattern we see. A business pays an agency for a website. The site launches. The agency's involvement ends. Two years later the site is still running the version of Next.js it launched with, and nobody has an account on the server. That site was not patched on 30 September, was not patched on 14 October, and will not be patched next time either.

The image optimization bug is the one to worry about. It needs no login, it affects six years of Next.js versions, and it hits the plain self-hosted setup most small businesses have.

## How to check if your site runs Next.js

You do not need a developer for this step.

1. Open your website in Chrome.
2. Right-click anywhere and choose **View page source**.
3. Press Ctrl+F (Cmd+F on a Mac) and search for `_next/`.

If you see it, your site runs Next.js. To find which version, ask whoever hosts the site for the `next` line in the `package.json` file. Anything on the 15 line below **15.5.28**, or the 16 line below **16.4.1**, needs the update. Ask them to confirm the `sharp` version too: it must be **0.35.5** or newer.

If you are hosted on Vercel and have automatic deployments from a repository, the update still does not happen by itself. Someone has to bump the version and deploy.

## What we did with our own site

We run fuorix.com on Next.js 15 on a Linux server, which put us squarely in the affected range for the image optimization bug. We moved to 15.5.28 and `sharp` 0.35.5 on 15 October, the day after the second release. The update took under an hour including the build, the deploy and checking the key pages. That is what a maintained site looks like: not immune, just patched within a day.

## What to do this week

**If you have a maintenance contract:** send your provider this post and ask them to confirm, in writing, that the site is on 15.5.28 or 16.4.1. A same-week answer is reasonable for a critical fix that is already two weeks old.

**If your developer is a freelancer who has moved on:** you need access to the code repository and the hosting account. Ask for both now. If they cannot give you either, that is a bigger problem than this patch.

**If you do not know who maintains your site:** that is the most common answer, and it is fixable. We take over Next.js sites we did not build. The first step is a free 15-minute check where we confirm the version, the hosting and whether anything else is out of date.

## What the update involves

For a well-built site the patch is routine: update one dependency, run the build, deploy, check the key pages. An hour of work, sometimes less. It is not a redesign and it does not change how the site looks.

Where it gets harder is a site that has not been updated in a long time. Jumping several major versions of Next.js can break things, and the fix becomes a small project rather than a patch. That is one reason we put every site we build on a maintenance plan from day one: keeping a site current costs far less than catching it up.

## Our maintenance plans

We keep client sites patched as part of our [cloud and DevOps](/services/cloud-devops) service, from $300 a month (about AED 1,100 or £240), which also covers hosting, backups, uptime monitoring and speed checks. For a small marketing site that does not need the full plan, a one-off update and security review is a fixed $150.

Not sure whether your site is affected or who looks after it? [Book a free 15-minute check](/book) and we will tell you where you stand.""",
    },
]
