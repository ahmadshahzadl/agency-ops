"""Apply the September 2026 blog content plan (scripts/blog_plan_2026_09.py) to the CMS.

Usage (on the droplet, as the portal user):
    cd /opt/fuorix/app/backend
    .venv/bin/python scripts/apply_blog_plan.py --dry-run   # show what would change
    .venv/bin/python scripts/apply_blog_plan.py             # apply

Idempotent: retitle intros are prepended once (marked with an HTML comment), new posts are
created only if their slug does not exist, unpublished posts are set to draft (never deleted).
After applying, the script asks fuorix.com to revalidate the blog pages if SITE_REVALIDATE_SECRET
is configured; otherwise pages refresh on their own within ten minutes.
"""
import os
import sys
import time
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models.content import BlogPost  # noqa: E402
from app.services.content_service import revalidate_site  # noqa: E402
from scripts.blog_plan_2026_09 import CREATE, MARK, REPLACE, UNPUBLISH, UPDATE  # noqa: E402


def _dt(s: str | None) -> datetime:
    if not s:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main(dry_run: bool) -> None:
    db = SessionLocal()
    touched: list[str] = []
    log: list[str] = []
    try:
        for slug in UNPUBLISH:
            row = db.query(BlogPost).filter(BlogPost.slug == slug).first()
            if not row:
                log.append(f"skip   unpublish {slug}: not found")
                continue
            if row.status == "draft":
                log.append(f"ok     unpublish {slug}: already draft")
                continue
            row.status = "draft"
            touched.append(slug)
            log.append(f"CHANGE unpublish {slug}")

        for u in UPDATE:
            row = db.query(BlogPost).filter(BlogPost.slug == u["slug"]).first()
            if not row:
                log.append(f"skip   update {u['slug']}: not found")
                continue
            changed = []
            for field in ("title", "seo_title", "seo_description", "excerpt", "category"):
                if field in u and getattr(row, field) != u[field]:
                    setattr(row, field, u[field])
                    changed.append(field)
            body = row.body_md or ""
            if u.get("prepend_md") and MARK not in body:
                row.body_md = f"{MARK}\n\n{u['prepend_md'].strip()}\n\n{body}"
                changed.append("body(prepend)")
            if changed:
                touched.append(u["slug"])
                log.append(f"CHANGE update {u['slug']}: {', '.join(changed)}")
            else:
                log.append(f"ok     update {u['slug']}: nothing to do")

        for r in REPLACE:
            row = db.query(BlogPost).filter(BlogPost.slug == r["slug"]).first()
            if not row:
                log.append(f"skip   replace {r['slug']}: not found")
                continue
            new_body = f"{MARK}\n\n{r['body_md'].strip()}\n"
            changed = []
            for field in ("title", "seo_title", "seo_description", "excerpt", "category", "related_slugs"):
                if field in r and getattr(row, field) != r[field]:
                    setattr(row, field, r[field])
                    changed.append(field)
            if (row.body_md or "") != new_body:
                row.body_md = new_body
                changed.append("body")
            if changed:
                touched.append(r["slug"])
                log.append(f"CHANGE replace {r['slug']}: {', '.join(changed)}")
            else:
                log.append(f"ok     replace {r['slug']}: nothing to do")

        for c in CREATE:
            row = db.query(BlogPost).filter(BlogPost.slug == c["slug"]).first()
            if row:
                log.append(f"ok     create {c['slug']}: exists")
                continue
            row = BlogPost(
                id=uuid.uuid4(),
                slug=c["slug"],
                title=c["title"],
                excerpt=c.get("excerpt"),
                category=c.get("category"),
                body_md=f"{MARK}\n\n{c['body_md'].strip()}\n",
                cover_url=c.get("cover_url"),
                cover_alt=c.get("cover_alt"),
                status="published",
                published_at=_dt(c.get("published_at")),
                related_slugs=c.get("related_slugs") or [],
                seo_title=c.get("seo_title"),
                seo_description=c.get("seo_description"),
                author_name="Fuorix",
            )
            db.add(row)
            touched.append(c["slug"])
            log.append(f"CHANGE create {c['slug']}")

        print("\n".join(log))
        if dry_run:
            db.rollback()
            print(f"\nDRY RUN: {len(touched)} post(s) would change. Re-run without --dry-run to apply.")
            return
        db.commit()
        print(f"\nApplied: {len(touched)} post(s) changed.")
    finally:
        db.close()

    if touched:
        paths = ["/blog", "/feed.xml", "/sitemap.xml", "/industries"] + [f"/blog/{s}" for s in touched]
        tags = ["blog"] + [f"blog:{s}" for s in touched]
        revalidate_site(paths, tags)  # fire-and-forget daemon thread
        time.sleep(5)  # give it time to finish before the interpreter exits
        print("Requested site revalidation (no-op if SITE_REVALIDATE_SECRET is not configured).")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
