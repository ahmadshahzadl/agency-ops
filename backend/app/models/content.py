"""Website content managed from the portal: blog posts, case studies, uploaded media.

Only ``status == "published"`` rows are exposed through the public API that fuorix.com reads.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class ContentMedia(Base):
    __tablename__ = "content_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    stored_name = Column(String(255), nullable=False)
    alt = Column(String(500))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(160), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    excerpt = Column(Text)
    category = Column(String(80))
    body_md = Column(Text, nullable=False, default="")
    cover_url = Column(String(500))
    cover_alt = Column(String(500))
    status = Column(String(16), nullable=False, default="draft")  # draft | published
    published_at = Column(DateTime(timezone=True))
    related_slugs = Column(JSONB, nullable=False, default=list)
    seo_title = Column(String(255))
    seo_description = Column(String(500))
    author_name = Column(String(120))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class CaseStudy(Base):
    __tablename__ = "case_studies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(160), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    tagline = Column(String(500))
    category = Column(String(80))
    tags = Column(JSONB, nullable=False, default=list)
    year = Column(String(16))
    overview = Column(Text)
    challenge = Column(Text)
    solution = Column(Text)
    highlights = Column(JSONB, nullable=False, default=list)
    results = Column(JSONB, nullable=False, default=list)  # [{"label": "...", "value": "..."}]
    stack = Column(JSONB, nullable=False, default=list)
    related_slugs = Column(JSONB, nullable=False, default=list)
    image_url = Column(String(500))
    logo_url = Column(String(500))
    gradient = Column(String(300))
    status = Column(String(16), nullable=False, default="draft")
    published_at = Column(DateTime(timezone=True))
    featured = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    seo_title = Column(String(255))
    seo_description = Column(String(500))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
