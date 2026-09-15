from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

SLUG_RE = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
Status = Literal["draft", "published"]


def _clean_list(v: list[str]) -> list[str]:
    return [s.strip()[:120] for s in (v or []) if s and s.strip()]


# ---------------- media ----------------

class MediaOut(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    alt: Optional[str] = None
    url: str  # path the website serves it from (/cms/media/<id>.<ext>)
    created_at: Optional[datetime] = None


# ---------------- blog posts ----------------

class BlogPostBase(BaseModel):
    slug: str = Field(min_length=2, max_length=160, pattern=SLUG_RE)
    title: str = Field(min_length=1, max_length=255)
    excerpt: Optional[str] = Field(None, max_length=600)
    category: Optional[str] = Field(None, max_length=80)
    body_md: str = ""
    cover_url: Optional[str] = Field(None, max_length=500)
    cover_alt: Optional[str] = Field(None, max_length=500)
    related_slugs: list[str] = []
    seo_title: Optional[str] = Field(None, max_length=255)
    seo_description: Optional[str] = Field(None, max_length=500)
    author_name: Optional[str] = Field(None, max_length=120)

    @field_validator("related_slugs")
    @classmethod
    def _rel(cls, v: list[str]) -> list[str]:
        return _clean_list(v)[:6]


class BlogPostCreate(BlogPostBase):
    status: Status = "draft"
    published_at: Optional[datetime] = None


class BlogPostUpdate(BaseModel):
    slug: Optional[str] = Field(None, min_length=2, max_length=160, pattern=SLUG_RE)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    excerpt: Optional[str] = Field(None, max_length=600)
    category: Optional[str] = Field(None, max_length=80)
    body_md: Optional[str] = None
    cover_url: Optional[str] = Field(None, max_length=500)
    cover_alt: Optional[str] = Field(None, max_length=500)
    related_slugs: Optional[list[str]] = None
    seo_title: Optional[str] = Field(None, max_length=255)
    seo_description: Optional[str] = Field(None, max_length=500)
    author_name: Optional[str] = Field(None, max_length=120)
    status: Optional[Status] = None
    published_at: Optional[datetime] = None


class BlogPostOut(BlogPostBase):
    id: UUID
    status: str
    published_at: Optional[datetime] = None
    read_time: str
    word_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------- case studies ----------------

class ResultItem(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=80)


class CaseStudyBase(BaseModel):
    slug: str = Field(min_length=2, max_length=160, pattern=SLUG_RE)
    title: str = Field(min_length=1, max_length=255)
    tagline: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=80)
    tags: list[str] = []
    year: Optional[str] = Field(None, max_length=16)
    overview: Optional[str] = None
    challenge: Optional[str] = None
    solution: Optional[str] = None
    highlights: list[str] = []
    results: list[ResultItem] = []
    stack: list[str] = []
    related_slugs: list[str] = []
    image_url: Optional[str] = Field(None, max_length=500)
    logo_url: Optional[str] = Field(None, max_length=500)
    gradient: Optional[str] = Field(None, max_length=300)
    featured: bool = False
    sort_order: int = 0
    seo_title: Optional[str] = Field(None, max_length=255)
    seo_description: Optional[str] = Field(None, max_length=500)

    @field_validator("tags", "highlights", "stack", "related_slugs")
    @classmethod
    def _lists(cls, v: list[str]) -> list[str]:
        return _clean_list(v)[:20]


class CaseStudyCreate(CaseStudyBase):
    status: Status = "draft"
    published_at: Optional[datetime] = None


class CaseStudyUpdate(BaseModel):
    slug: Optional[str] = Field(None, min_length=2, max_length=160, pattern=SLUG_RE)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    tagline: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=80)
    tags: Optional[list[str]] = None
    year: Optional[str] = Field(None, max_length=16)
    overview: Optional[str] = None
    challenge: Optional[str] = None
    solution: Optional[str] = None
    highlights: Optional[list[str]] = None
    results: Optional[list[ResultItem]] = None
    stack: Optional[list[str]] = None
    related_slugs: Optional[list[str]] = None
    image_url: Optional[str] = Field(None, max_length=500)
    logo_url: Optional[str] = Field(None, max_length=500)
    gradient: Optional[str] = Field(None, max_length=300)
    featured: Optional[bool] = None
    sort_order: Optional[int] = None
    seo_title: Optional[str] = Field(None, max_length=255)
    seo_description: Optional[str] = Field(None, max_length=500)
    status: Optional[Status] = None
    published_at: Optional[datetime] = None


class CaseStudyOut(CaseStudyBase):
    id: UUID
    status: str
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------- public (website) ----------------

class PublicPostSummary(BaseModel):
    slug: str
    title: str
    excerpt: Optional[str] = None
    category: Optional[str] = None
    cover_url: Optional[str] = None
    cover_alt: Optional[str] = None
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    read_time: str


class PublicPost(PublicPostSummary):
    body_md: str
    related: list[PublicPostSummary] = []
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    author_name: Optional[str] = None


class PublicPostList(BaseModel):
    items: list[PublicPostSummary]
    total: int


class PublicCaseStudy(BaseModel):
    slug: str
    title: str
    tagline: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = []
    year: Optional[str] = None
    overview: Optional[str] = None
    challenge: Optional[str] = None
    solution: Optional[str] = None
    highlights: list[str] = []
    results: list[ResultItem] = []
    stack: list[str] = []
    related_slugs: list[str] = []
    image_url: Optional[str] = None
    logo_url: Optional[str] = None
    gradient: Optional[str] = None
    featured: bool = False
    sort_order: int = 0
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
