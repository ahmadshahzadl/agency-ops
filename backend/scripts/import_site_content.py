"""One-off import of the website's original blog posts and case studies into the CMS tables.

Usage:
    python scripts/import_site_content.py            # insert missing, leave existing rows alone
    python scripts/import_site_content.py --overwrite  # also refresh rows that already exist

Reads scripts/seed_content/site_content.json (exported from fuorix.com's src/data). Safe to
re-run. Everything is imported as *published* with the original dates, so the live site does
not change when it switches to the CMS.
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models.content import BlogPost, CaseStudy  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "seed_content", "site_content.json")


def _dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def main(overwrite: bool) -> None:
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    db = SessionLocal()
    made = updated = skipped = 0
    try:
        for p in data.get("posts", []):
            row = db.query(BlogPost).filter(BlogPost.slug == p["slug"]).first()
            if row and not overwrite:
                skipped += 1
                continue
            if row is None:
                row = BlogPost(id=uuid.uuid4(), slug=p["slug"])
                db.add(row)
                made += 1
            else:
                updated += 1
            row.title = p["title"]
            row.excerpt = p.get("excerpt")
            row.category = p.get("category")
            row.body_md = p.get("body_md") or ""
            row.cover_url = p.get("cover_url")
            row.cover_alt = p.get("cover_alt")
            row.related_slugs = p.get("related_slugs") or []
            row.status = "published"
            row.published_at = _dt(p.get("published_at")) or datetime.now(timezone.utc)
            row.author_name = row.author_name or "Fuorix"
        for c in data.get("case_studies", []):
            row = db.query(CaseStudy).filter(CaseStudy.slug == c["slug"]).first()
            if row and not overwrite:
                skipped += 1
                continue
            if row is None:
                row = CaseStudy(id=uuid.uuid4(), slug=c["slug"])
                db.add(row)
                made += 1
            else:
                updated += 1
            for k in ("title", "tagline", "category", "tags", "year", "overview", "challenge", "solution", "highlights", "results", "stack", "related_slugs", "image_url", "logo_url", "gradient", "sort_order", "featured"):
                if k in c:
                    setattr(row, k, c[k])
            row.status = "published"
            row.published_at = row.published_at or datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
    print(f"created {made}, updated {updated}, skipped {skipped}")


if __name__ == "__main__":
    main("--overwrite" in sys.argv[1:])
