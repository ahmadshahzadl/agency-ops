import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(32), nullable=False)  # task, project, client, lead, meeting, invoice, expense
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    filename = Column(String(255), nullable=False)  # original name, shown to users
    stored_name = Column(String(128), unique=True, nullable=False)  # random name on disk
    content_type = Column(String(128))
    size_bytes = Column(Integer, nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    uploader = relationship("User")
