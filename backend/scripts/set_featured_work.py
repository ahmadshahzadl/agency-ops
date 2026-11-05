"""Set which case studies appear in the homepage 'Selected Works' section
(getFeaturedCaseStudies(4)), and in what order. Generic, reusable.

Usage (on the droplet, as the portal user):
    cd /opt/fuorix/app/backend
    .venv/bin/python scripts/set_featured_work.py gcradar authorestimation saakht editdeckpro --dry-run
    .venv/bin/python scripts/set_featured_work.py gcradar authorestimation saakht editdeckpro

Sets featured=True with sort_order matching the order given for exactly
those slugs, and featured=False for every other case study (their
sort_order is left untouched, since it still affects ordering elsewhere,
e.g. the full /portfolio listing).
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models.content import CaseStudy  # noqa: E402
from app.services.content_service import revalidate_site  # noqa: E402


def main(slugs: list[str], dry_run: bool) -> None:
    db = SessionLocal()
    try:
        missing = [s for s in slugs if not db.query(CaseStudy).filter(CaseStudy.slug == s).first()]
        if missing:
            print(f"ERROR: unknown slug(s): {', '.join(missing)}")
            sys.exit(1)

        changed = []
        for row in db.query(CaseStudy).all():
            if row.slug in slugs:
                new_order = slugs.index(row.slug)
                if not row.featured or row.sort_order != new_order:
                    row.featured = True
                    row.sort_order = new_order
                    changed.append(f"{row.slug} -> featured, sort_order={new_order}")
            elif row.featured:
                row.featured = False
                changed.append(f"{row.slug} -> unfeatured")

        if not changed:
            print("ok     nothing to do: featured set already matches")
            db.rollback()
            return

        if dry_run:
            db.rollback()
            print("DRY RUN: would change:")
            for c in changed:
                print(f"  {c}")
            print("Re-run without --dry-run to apply.")
            return

        db.commit()
        print("CHANGE applied:")
        for c in changed:
            print(f"  {c}")
    finally:
        db.close()

    if not dry_run:
        revalidate_site(["/", "/portfolio"], ["case-studies"])
        time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("slugs", nargs="+", help="Case study slugs, in the order they should appear")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(args.slugs, args.dry_run)
