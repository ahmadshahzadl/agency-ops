"""One-time rebrand: Ashlar -> Saakht (saakth.com).

Renames the 'ashlar' case study to 'saakht' (new slug, new content matching
saakth.com's current positioning) and fixes 'ashlar' in any other case
study's related_slugs so nothing links to a dead slug.

Usage (on the droplet, as the portal user):
    cd /opt/fuorix/app/backend
    .venv/bin/python scripts/rebrand_ashlar_to_saakht.py --dry-run
    .venv/bin/python scripts/rebrand_ashlar_to_saakht.py

Idempotent: if 'ashlar' no longer exists but 'saakht' does, just fixes any
stale related_slugs and exits cleanly. Safe to re-run.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models.content import CaseStudy  # noqa: E402
from app.services.content_service import revalidate_site  # noqa: E402

NEW_CONTENT = {
    "slug": "saakht",
    "title": "Saakht",
    "tagline": "One firm, fully accountable for design, cost and construction, for homeowners across Lahore and DHA.",
    "category": "Construction",
    "tags": ["Portfolio", "CRM", "SEO"],
    "overview": (
        "Saakht — formerly Ashlar — is a construction engineering firm in Lahore, Pakistan, built on one "
        "promise to homeowners: one firm, one contract, fully accountable for design, cost and construction "
        "from the first drawing to the last brick, instead of a fragmented chain of contractors nobody can "
        "hold to the outcome. Fuorix built the digital presence and lead-management system the brand runs on."
    ),
    "challenge": (
        "Before this, the brand had no digital footprint. Potential clients couldn't find them online, and "
        "every lead came in through phone calls and paper notes with no way to track a follow-up. Competitors "
        "with weaker portfolios were winning contracts simply by ranking higher on Google and looking more "
        "credible online."
    ),
    "solution": (
        "We designed and built a high-performance Next.js site with a project gallery, service pages and a "
        "built-in CRM for lead tracking, with full technical and on-page SEO — schema markup, meta "
        "optimization, sitemap generation and Core Web Vitals tuning — to drive organic traffic from day one. "
        "The brand has since repositioned as Saakht, built around the same one-firm, fully-accountable "
        "promise, serving private residential clients across Lahore and DHA."
    ),
    "image_url": "/portfolio/saakht.webp",
    "logo_url": "/logos/saakht.png",
    "gradient": "linear-gradient(135deg, #1c1917 0%, #3d0f1a 50%, #6b1530 100%)",
    "live_url": "https://saakth.com",
}


def main(dry_run: bool) -> None:
    db = SessionLocal()
    try:
        row = db.query(CaseStudy).filter(CaseStudy.slug == "ashlar").first()
        renamed = False
        if row:
            for field, value in NEW_CONTENT.items():
                setattr(row, field, value)
            renamed = True
        elif not db.query(CaseStudy).filter(CaseStudy.slug == "saakht").first():
            print("ERROR: neither 'ashlar' nor 'saakht' exists. Nothing to rename.")
            sys.exit(1)

        # Fix related_slugs on every other case study that still points at 'ashlar'.
        fixed_related = []
        for other in db.query(CaseStudy).filter(CaseStudy.slug != "saakht").all():
            slugs = other.related_slugs or []
            if "ashlar" in slugs:
                other.related_slugs = ["saakht" if s == "ashlar" else s for s in slugs]
                fixed_related.append(other.slug)

        if not renamed and not fixed_related:
            print("ok     nothing to do: 'saakht' already exists and no stale related_slugs found")
            db.rollback()
            return

        if dry_run:
            db.rollback()
            if renamed:
                print("DRY RUN: would rename 'ashlar' -> 'saakht' with updated content.")
            if fixed_related:
                print(f"DRY RUN: would fix related_slugs (ashlar -> saakht) on: {', '.join(fixed_related)}")
            print("Re-run without --dry-run to apply.")
            return

        db.commit()
        if renamed:
            print("CHANGE renamed ashlar -> saakht")
        if fixed_related:
            print(f"CHANGE fixed related_slugs on: {', '.join(fixed_related)}")
    finally:
        db.close()

    if not dry_run:
        revalidate_site(
            ["/portfolio", "/portfolio/saakht", "/portfolio/ashlar", "/industries/construction", "/portfolio/construction", "/llms.txt", "/"],
            ["case-studies", "case:saakht", "case:ashlar"],
        )
        time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(args.dry_run)
