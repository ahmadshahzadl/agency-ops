"""Website content helpers: read time, media storage, and telling the website to refresh."""
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.content import BlogPost, CaseStudy, ContentMedia
from app.schemas.content import MediaOut, PublicCaseStudy, PublicPost, PublicPostSummary

logger = logging.getLogger(__name__)

MEDIA_SUBDIR = "cms"
ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}
MAX_MEDIA_MB = 10
WORDS_PER_MINUTE = 220


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:160] or "post"


def word_count(md: str) -> int:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", md or "")  # drop images
    text = re.sub(r"[#>*_`~\-]+", " ", text)
    return len([w for w in text.split() if w.strip()])


def read_time(md: str) -> str:
    minutes = max(1, round(word_count(md) / WORDS_PER_MINUTE))
    return f"{minutes} min read"


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------

def media_dir() -> str:
    d = os.path.join(get_settings().upload_dir, MEDIA_SUBDIR)
    os.makedirs(d, exist_ok=True)
    return d


def media_url(m: ContentMedia) -> str:
    ext = os.path.splitext(m.stored_name)[1]
    return f"/cms/media/{m.id}{ext}"


def media_out(m: ContentMedia) -> MediaOut:
    return MediaOut(id=m.id, filename=m.filename, content_type=m.content_type, size_bytes=m.size_bytes, alt=m.alt, url=media_url(m), created_at=m.created_at)


def save_media(db: Session, *, filename: str, content_type: str, data: bytes, alt: str | None, user_id) -> ContentMedia:
    ext = ALLOWED_IMAGE_TYPES.get(content_type)
    if not ext:
        raise ValueError("Only PNG, JPEG, WebP, GIF or AVIF images are allowed")
    if len(data) > MAX_MEDIA_MB * 1024 * 1024:
        raise ValueError(f"Image is larger than {MAX_MEDIA_MB} MB")
    mid = uuid.uuid4()
    stored = f"{mid}{ext}"
    with open(os.path.join(media_dir(), stored), "wb") as f:
        f.write(data)
    m = ContentMedia(id=mid, filename=(filename or stored)[:255], content_type=content_type, size_bytes=len(data), stored_name=stored, alt=(alt or "")[:500] or None, created_by=user_id)
    db.add(m)
    db.flush()
    return m


def media_path(m: ContentMedia) -> str:
    return os.path.join(media_dir(), m.stored_name)


def delete_media_file(m: ContentMedia) -> None:
    try:
        os.remove(media_path(m))
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Public shapes
# ---------------------------------------------------------------------------

def post_summary(p: BlogPost) -> PublicPostSummary:
    return PublicPostSummary(
        slug=p.slug, title=p.title, excerpt=p.excerpt, category=p.category, cover_url=p.cover_url, cover_alt=p.cover_alt,
        published_at=p.published_at, updated_at=p.updated_at, read_time=read_time(p.body_md),
    )


def post_public(p: BlogPost, related: list[BlogPost]) -> PublicPost:
    base = post_summary(p).model_dump()
    return PublicPost(**base, body_md=p.body_md or "", related=[post_summary(r) for r in related], seo_title=p.seo_title, seo_description=p.seo_description, author_name=p.author_name)


def case_public(c: CaseStudy) -> PublicCaseStudy:
    return PublicCaseStudy(
        slug=c.slug, title=c.title, tagline=c.tagline, category=c.category, tags=c.tags or [], year=c.year,
        overview=c.overview, challenge=c.challenge, solution=c.solution, highlights=c.highlights or [],
        results=c.results or [], stack=c.stack or [], related_slugs=c.related_slugs or [], image_url=c.image_url,
        logo_url=c.logo_url, gradient=c.gradient, featured=c.featured, sort_order=c.sort_order,
        published_at=c.published_at, updated_at=c.updated_at, seo_title=c.seo_title, seo_description=c.seo_description,
    )


# ---------------------------------------------------------------------------
# Website revalidation (Next.js on-demand ISR)
# ---------------------------------------------------------------------------

def revalidate_site(paths: list[str], tags: list[str]) -> None:
    """Ask fuorix.com to rebuild the given pages/tags. Fire-and-forget; no-op when unconfigured."""
    s = get_settings()
    base = (s.booking_public_url or "").rstrip("/")
    secret = (s.site_revalidate_secret or "").strip()
    if not base or not secret:
        return

    def _go():
        try:
            r = httpx.post(f"{base}/api/revalidate", json={"paths": paths, "tags": tags}, headers={"x-revalidate-secret": secret}, timeout=15)
            if r.status_code >= 400:
                logger.warning("site revalidate failed: %s %s", r.status_code, r.text[:200])
            else:
                logger.info("site revalidated paths=%s tags=%s", paths, tags)
        except Exception:
            logger.exception("site revalidate errored")

    threading.Thread(target=_go, daemon=True).start()


def publish_stamp(status: str, published_at: datetime | None) -> datetime | None:
    if status == "published" and published_at is None:
        return datetime.now(timezone.utc)
    return published_at
