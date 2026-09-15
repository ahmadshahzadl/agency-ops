"""Unauthenticated read API for the website: published blog posts, case studies and media."""
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content import BlogPost, CaseStudy, ContentMedia
from app.schemas.content import PublicCaseStudy, PublicPost, PublicPostList
from app.services import content_service as cs

router = APIRouter(prefix="/public/content", tags=["content-public"])


def _published_posts(db: Session):
    return db.query(BlogPost).filter(BlogPost.status == "published").order_by(BlogPost.published_at.desc(), BlogPost.created_at.desc())


@router.get("/posts", response_model=PublicPostList)
def list_posts(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    qry = _published_posts(db)
    total = qry.count()
    return PublicPostList(items=[cs.post_summary(p) for p in qry.offset(offset).limit(limit).all()], total=total)


@router.get("/posts/{slug}", response_model=PublicPost)
def get_post(slug: str, db: Session = Depends(get_db)):
    p = db.query(BlogPost).filter(BlogPost.slug == slug, BlogPost.status == "published").first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    related = []
    if p.related_slugs:
        by_slug = {r.slug: r for r in db.query(BlogPost).filter(BlogPost.slug.in_(p.related_slugs), BlogPost.status == "published").all()}
        related = [by_slug[s] for s in p.related_slugs if s in by_slug]
    if not related:
        related = _published_posts(db).filter(BlogPost.id != p.id).limit(2).all()
    return cs.post_public(p, related)


@router.get("/case-studies", response_model=list[PublicCaseStudy])
def list_cases(db: Session = Depends(get_db)):
    rows = db.query(CaseStudy).filter(CaseStudy.status == "published").order_by(CaseStudy.sort_order, CaseStudy.created_at).all()
    return [cs.case_public(c) for c in rows]


@router.get("/case-studies/{slug}", response_model=PublicCaseStudy)
def get_case(slug: str, db: Session = Depends(get_db)):
    c = db.query(CaseStudy).filter(CaseStudy.slug == slug, CaseStudy.status == "published").first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return cs.case_public(c)


@router.get("/media/{name}")
def get_media(name: str, db: Session = Depends(get_db)):
    """Serve an uploaded image. ``name`` is ``<uuid>`` or ``<uuid>.<ext>``."""
    raw = name.split(".", 1)[0]
    try:
        mid = UUID(raw)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    m = db.query(ContentMedia).filter(ContentMedia.id == mid).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    path = cs.media_path(m)
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return FileResponse(path, media_type=m.content_type, headers={"Cache-Control": "public, max-age=31536000, immutable"})
