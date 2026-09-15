"""Authoring API for website content (blog posts, case studies, media). Requires content:manage."""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database import get_db
from app.models.content import BlogPost, CaseStudy, ContentMedia
from app.schemas.content import (
    BlogPostCreate, BlogPostOut, BlogPostUpdate,
    CaseStudyCreate, CaseStudyOut, CaseStudyUpdate,
    MediaOut,
)
from app.services import content_service as cs
from app.services.activity_service import log_activity

router = APIRouter(prefix="/content", tags=["content"])
CONTENT = "content:manage"


def _post_out(p: BlogPost) -> BlogPostOut:
    return BlogPostOut(
        id=p.id, slug=p.slug, title=p.title, excerpt=p.excerpt, category=p.category, body_md=p.body_md or "",
        cover_url=p.cover_url, cover_alt=p.cover_alt, related_slugs=p.related_slugs or [], seo_title=p.seo_title,
        seo_description=p.seo_description, author_name=p.author_name, status=p.status, published_at=p.published_at,
        read_time=cs.read_time(p.body_md), word_count=cs.word_count(p.body_md), created_at=p.created_at, updated_at=p.updated_at,
    )


def _case_out(c: CaseStudy) -> CaseStudyOut:
    return CaseStudyOut(
        id=c.id, slug=c.slug, title=c.title, tagline=c.tagline, category=c.category, tags=c.tags or [], year=c.year,
        overview=c.overview, challenge=c.challenge, solution=c.solution, highlights=c.highlights or [],
        results=c.results or [], stack=c.stack or [], related_slugs=c.related_slugs or [], image_url=c.image_url,
        logo_url=c.logo_url, gradient=c.gradient, featured=c.featured, sort_order=c.sort_order, seo_title=c.seo_title,
        seo_description=c.seo_description, status=c.status, published_at=c.published_at, created_at=c.created_at, updated_at=c.updated_at,
    )


def _post_paths(slug: str) -> tuple[list[str], list[str]]:
    return ["/blog", f"/blog/{slug}", "/", "/sitemap.xml", "/feed.xml"], ["blog"]


def _case_paths(slug: str) -> tuple[list[str], list[str]]:
    return ["/portfolio", f"/portfolio/{slug}", "/", "/sitemap.xml"], ["case-studies"]


# ============================ posts ============================

@router.get("/posts", response_model=list[BlogPostOut])
def list_posts(db: Session = Depends(get_db), user=Depends(require_permission(CONTENT)), q: str | None = None, status_: str | None = Query(None, alias="status")):
    qry = db.query(BlogPost)
    if q:
        like = f"%{q}%"
        qry = qry.filter(or_(BlogPost.title.ilike(like), BlogPost.slug.ilike(like), BlogPost.category.ilike(like)))
    if status_:
        qry = qry.filter(BlogPost.status == status_)
    return [_post_out(p) for p in qry.order_by(BlogPost.published_at.desc().nullsfirst(), BlogPost.updated_at.desc()).all()]


@router.post("/posts", response_model=BlogPostOut, status_code=status.HTTP_201_CREATED)
def create_post(data: BlogPostCreate, db: Session = Depends(get_db), user=Depends(require_permission(CONTENT))):
    if db.query(BlogPost).filter(BlogPost.slug == data.slug).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
    p = BlogPost(**data.model_dump(exclude={"published_at"}), published_at=cs.publish_stamp(data.status, data.published_at), created_by=user.id)
    db.add(p)
    log_activity(db, user.id, "post_created", "blog_post", p.id, details=p.title)
    db.commit()
    db.refresh(p)
    if p.status == "published":
        cs.revalidate_site(*_post_paths(p.slug))
    return _post_out(p)


@router.get("/posts/{post_id}", response_model=BlogPostOut)
def get_post(post_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission(CONTENT))):
    p = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    return _post_out(p)


@router.patch("/posts/{post_id}", response_model=BlogPostOut)
def update_post(post_id: UUID, data: BlogPostUpdate, db: Session = Depends(get_db), user=Depends(require_permission(CONTENT))):
    p = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    changes = data.model_dump(exclude_unset=True)
    old_slug, was_published = p.slug, p.status == "published"
    if "slug" in changes and changes["slug"] != p.slug and db.query(BlogPost).filter(BlogPost.slug == changes["slug"]).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
    for k, v in changes.items():
        setattr(p, k, v)
    p.published_at = cs.publish_stamp(p.status, p.published_at)
    log_activity(db, user.id, "post_updated", "blog_post", p.id, details=p.title)
    db.commit()
    db.refresh(p)
    if was_published or p.status == "published":
        paths, tags = _post_paths(p.slug)
        if old_slug != p.slug:
            paths.append(f"/blog/{old_slug}")
        cs.revalidate_site(paths, tags)
    return _post_out(p)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission(CONTENT))):
    p = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    slug, was_published = p.slug, p.status == "published"
    log_activity(db, user.id, "post_deleted", "blog_post", p.id, details=p.title)
    db.delete(p)
    db.commit()
    if was_published:
        cs.revalidate_site(*_post_paths(slug))


# ============================ case studies ============================

@router.get("/case-studies", response_model=list[CaseStudyOut])
def list_cases(db: Session = Depends(get_db), user=Depends(require_permission(CONTENT)), q: str | None = None):
    qry = db.query(CaseStudy)
    if q:
        like = f"%{q}%"
        qry = qry.filter(or_(CaseStudy.title.ilike(like), CaseStudy.slug.ilike(like), CaseStudy.category.ilike(like)))
    return [_case_out(c) for c in qry.order_by(CaseStudy.sort_order, CaseStudy.created_at).all()]


@router.post("/case-studies", response_model=CaseStudyOut, status_code=status.HTTP_201_CREATED)
def create_case(data: CaseStudyCreate, db: Session = Depends(get_db), user=Depends(require_permission(CONTENT))):
    if db.query(CaseStudy).filter(CaseStudy.slug == data.slug).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
    payload = data.model_dump(exclude={"published_at"})
    payload["results"] = [r.model_dump() for r in data.results]
    c = CaseStudy(**payload, published_at=cs.publish_stamp(data.status, data.published_at), created_by=user.id)
    db.add(c)
    log_activity(db, user.id, "case_study_created", "case_study", c.id, details=c.title)
    db.commit()
    db.refresh(c)
    if c.status == "published":
        cs.revalidate_site(*_case_paths(c.slug))
    return _case_out(c)


@router.get("/case-studies/{case_id}", response_model=CaseStudyOut)
def get_case(case_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission(CONTENT))):
    c = db.query(CaseStudy).filter(CaseStudy.id == case_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    return _case_out(c)


@router.patch("/case-studies/{case_id}", response_model=CaseStudyOut)
def update_case(case_id: UUID, data: CaseStudyUpdate, db: Session = Depends(get_db), user=Depends(require_permission(CONTENT))):
    c = db.query(CaseStudy).filter(CaseStudy.id == case_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    changes = data.model_dump(exclude_unset=True)
    if "results" in changes and data.results is not None:
        changes["results"] = [r.model_dump() for r in data.results]
    old_slug, was_published = c.slug, c.status == "published"
    if "slug" in changes and changes["slug"] != c.slug and db.query(CaseStudy).filter(CaseStudy.slug == changes["slug"]).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
    for k, v in changes.items():
        setattr(c, k, v)
    c.published_at = cs.publish_stamp(c.status, c.published_at)
    log_activity(db, user.id, "case_study_updated", "case_study", c.id, details=c.title)
    db.commit()
    db.refresh(c)
    if was_published or c.status == "published":
        paths, tags = _case_paths(c.slug)
        if old_slug != c.slug:
            paths.append(f"/portfolio/{old_slug}")
        cs.revalidate_site(paths, tags)
    return _case_out(c)


@router.delete("/case-studies/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission(CONTENT))):
    c = db.query(CaseStudy).filter(CaseStudy.id == case_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    slug, was_published = c.slug, c.status == "published"
    log_activity(db, user.id, "case_study_deleted", "case_study", c.id, details=c.title)
    db.delete(c)
    db.commit()
    if was_published:
        cs.revalidate_site(*_case_paths(slug))


# ============================ media ============================

@router.get("/media", response_model=list[MediaOut])
def list_media(db: Session = Depends(get_db), user=Depends(require_permission(CONTENT)), limit: int = Query(100, ge=1, le=500)):
    return [cs.media_out(m) for m in db.query(ContentMedia).order_by(ContentMedia.created_at.desc()).limit(limit).all()]


@router.post("/media", response_model=MediaOut, status_code=status.HTTP_201_CREATED)
async def upload_media(file: UploadFile = File(...), alt: str | None = Form(None), db: Session = Depends(get_db), user=Depends(require_permission(CONTENT))):
    data = await file.read()
    try:
        m = cs.save_media(db, filename=file.filename or "", content_type=(file.content_type or "").lower(), data=data, alt=alt, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    db.commit()
    db.refresh(m)
    return cs.media_out(m)


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(media_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission(CONTENT))):
    m = db.query(ContentMedia).filter(ContentMedia.id == media_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Not found")
    cs.delete_media_file(m)
    db.delete(m)
    db.commit()
