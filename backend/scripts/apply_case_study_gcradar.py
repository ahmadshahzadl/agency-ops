"""Create the GC Radar case study in the CMS.

Usage (on the droplet, as the portal user):
    cd /opt/fuorix/app/backend
    .venv/bin/python scripts/apply_case_study_gcradar.py --dry-run
    .venv/bin/python scripts/apply_case_study_gcradar.py

Idempotent: does nothing if a case study with this slug already exists (reports it
instead). After creating, asks fuorix.com to revalidate the portfolio pages if
SITE_REVALIDATE_SECRET is configured; otherwise pages refresh on their own within
ten minutes (ISR revalidate=600 on /portfolio).

Content here mirrors the PUBLIC-SAFE sections of D:\\Fuorix\\Case-Studies\\GC-Radar-Case-Study.md
exactly — do not add internal figures, infra topology, or incident detail from that
file's INTERNAL-ONLY sections if this script is ever edited.
"""
import argparse
import os
import sys
import time
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models.content import CaseStudy  # noqa: E402
from app.services.content_service import revalidate_site  # noqa: E402

CASE_STUDY = {
    "slug": "gcradar",
    "title": "GC Radar",
    "tagline": "Real-time lead alerts for drywall, framing and concrete subcontractors, built from public county permit records — then a 90% infrastructure cost cut with zero downtime.",
    "category": "Construction",
    "tags": ["SaaS", "Lead Generation", "Mobile App", "Stripe"],
    "year": "2026",
    "overview": (
        "GC Radar sells a simple promise to small construction subcontractors: know which houses are "
        "about to need your trade before the general contractor starts calling around. The product watches "
        "public permitting and inspection activity across a growing list of counties, figures out which "
        "stage of construction a project is actually in, and alerts drywall, framing and concrete "
        "subcontractors the moment a house becomes a live opportunity — with the builder's contact "
        "information filled in automatically. Fuorix is the ongoing engineering team: product build-out, "
        "feature delivery, infrastructure and cost management, not a fixed-scope delivery."
    ),
    "challenge": (
        "Every county publishes permit and inspection data differently, and the same inspection code can "
        "mean a different construction stage depending on which county and which builder typed it in — get "
        "it wrong and a subcontractor either wastes a call on a house that isn't ready, or misses one "
        "that's already framed. A raw permit record also means nothing to a drywall crew; it has to be "
        "translated into \"this house enters framing today,\" with a real, verified phone number attached, "
        "never a permit number or the word \"scraping.\""
    ),
    "solution": (
        "We built a taxonomy engine that maps thousands of county-specific inspection codes onto one "
        "canonical construction timeline per trade, backed by an automated regression suite of real-world "
        "permit cases that blocks any deploy which breaks a previously-verified case. Permit and inspection "
        "data is ingested from more than a dozen independent sources and normalized into one shape before "
        "the signal engine sees it. When a county doesn't publish a usable phone number, the system looks "
        "up and verifies the builder and finds a contact itself. On top sits a full subscriber SaaS: "
        "seat-based pricing per trade per county, a Radar feed, a map view, and an opportunities pipeline, "
        "with Stripe handling subscriptions end to end, a clean personal-link attribution system for every "
        "closer and affiliate, an internal admin console for the operations team, and a native companion app "
        "for field crews, built with Flutter and live on the Apple App Store."
    ),
    "highlights": [
        "Taxonomy engine mapping county-specific permit codes to one construction timeline, regression-tested against real records",
        "Multi-source permit and inspection ingestion normalized into one pipeline",
        "Contact enrichment that verifies a builder is a real construction business before it ever reaches a subscriber",
        "Seat-based Stripe subscriptions with a one-link attribution and commission system for sales and affiliates",
        "Native companion app built with Flutter — live on the Apple App Store today, giving field crews the Radar feed, a live map, route planning and the deal pipeline on their phone",
        "Migrated the production database live with zero downtime as part of a 90% infrastructure cost reduction",
    ],
    "results": [
        {"label": "Infrastructure cost", "value": "-90%"},
        {"label": "Migration downtime", "value": "Zero"},
        {"label": "Counties covered", "value": "16"},
        {"label": "Platforms shipped", "value": "5"},
    ],
    "stack": ["Next.js", "TypeScript", "PostgreSQL", "Stripe", "Resend", "MapLibre GL", "Flutter", "Anthropic"],
    "related_slugs": ["siteday", "tameer", "authorestimation"],
    "image_url": "/portfolio/gcradar.webp",
    "gradient": "linear-gradient(135deg, #1a1a1a 0%, #292524 50%, #ea580c 100%)",
    "live_url": "https://gcradar.io",
    "featured": True,
    "sort_order": 1,
    "seo_title": "GC Radar Case Study — Lead Generation SaaS for Construction Subcontractors | Fuorix",
    "seo_description": "How Fuorix built GC Radar's permit-tracking taxonomy engine, subscriber SaaS and native mobile app for construction subcontractors, then cut infrastructure costs 90% with zero downtime.",
}


def main(dry_run: bool) -> None:
    db = SessionLocal()
    try:
        # Fields that are safe to overwrite on a re-run (everything except identity/publish bookkeeping).
        MUTABLE_FIELDS = (
            "title", "tagline", "category", "tags", "year", "overview", "challenge", "solution",
            "highlights", "results", "stack", "related_slugs", "image_url", "gradient", "live_url",
            "featured", "sort_order", "seo_title", "seo_description",
        )

        row = db.query(CaseStudy).filter(CaseStudy.slug == CASE_STUDY["slug"]).first()
        verb = "update"
        if not row:
            verb = "create"
            row = CaseStudy(id=uuid.uuid4(), slug=CASE_STUDY["slug"], status="published", published_at=datetime.now(timezone.utc))
            db.add(row)

        changed = []
        for field in MUTABLE_FIELDS:
            if getattr(row, field, None) != CASE_STUDY[field]:
                setattr(row, field, CASE_STUDY[field])
                changed.append(field)

        if dry_run:
            db.rollback()
            if verb == "create":
                print(f"DRY RUN: would create case study '{CASE_STUDY['slug']}'. Re-run without --dry-run to apply.")
            elif changed:
                print(f"DRY RUN: would update '{CASE_STUDY['slug']}': {', '.join(changed)}. Re-run without --dry-run to apply.")
            else:
                print(f"ok     {CASE_STUDY['slug']}: nothing to do")
            return

        if verb == "create":
            db.commit()
            print(f"CHANGE created: {CASE_STUDY['slug']}")
        elif changed:
            db.commit()
            print(f"CHANGE updated {CASE_STUDY['slug']}: {', '.join(changed)}")
        else:
            db.rollback()
            print(f"ok     {CASE_STUDY['slug']}: nothing to do")
            return
    finally:
        db.close()

    if not dry_run:
        revalidate_site(
            ["/portfolio", f"/portfolio/{CASE_STUDY['slug']}", "/industries/construction", "/llms.txt"],
            ["case-studies", f"case:{CASE_STUDY['slug']}"],
        )
        time.sleep(5)  # give the fire-and-forget revalidate request time to land


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(args.dry_run)
