"""Set (or update) a case study's image_url in the CMS. Generic, reusable —
not just for one project.

Usage (on the droplet, as the portal user):
    cd /opt/fuorix/app/backend
    .venv/bin/python scripts/set_case_study_image.py siteday /portfolio/siteday.webp --dry-run
    .venv/bin/python scripts/set_case_study_image.py siteday /portfolio/siteday.webp

Idempotent: does nothing (and exits 0) if the case study already has that exact
image_url. Fails with a clear error if the slug doesn't exist — it does not
create case studies (use apply_case_study_gcradar.py as a template for that).
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models.content import CaseStudy  # noqa: E402
from app.services.content_service import revalidate_site  # noqa: E402


def main(slug: str, image_url: str, dry_run: bool) -> None:
    db = SessionLocal()
    try:
        row = db.query(CaseStudy).filter(CaseStudy.slug == slug).first()
        if not row:
            print(f"ERROR: no case study with slug '{slug}'. Known slugs are managed in the CMS; this script only updates existing rows.")
            sys.exit(1)

        if row.image_url == image_url:
            print(f"ok     {slug}: image_url already '{image_url}', nothing to do")
            return

        old = row.image_url
        row.image_url = image_url

        if dry_run:
            db.rollback()
            print(f"DRY RUN: would update {slug}.image_url: '{old}' -> '{image_url}'. Re-run without --dry-run to apply.")
            return

        db.commit()
        print(f"CHANGE updated {slug}.image_url: '{old}' -> '{image_url}'")
    finally:
        db.close()

    if not dry_run:
        revalidate_site(["/portfolio", f"/portfolio/{slug}"], ["case-studies", f"case:{slug}"])
        time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", help="Case study slug, e.g. siteday")
    parser.add_argument("image_url", help="Public path to the image, e.g. /portfolio/siteday.webp")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(args.slug, args.image_url, args.dry_run)
