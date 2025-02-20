from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Table, Boolean, JSON, LargeBinary, Interval
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from ..database.connection import Base

def generate_uuid():
    return str(uuid.uuid4())

# Many-to-many relationship table for opportunities and systems
opportunity_systems = Table(
    'opportunity_systems', 
    Base.metadata,
    Column('id', UUID(as_uuid=True), primary_key=True, default=generate_uuid),
    Column('opportunity_id', UUID(as_uuid=True), ForeignKey('opportunities.id')),
    Column('system_id', UUID(as_uuid=True), ForeignKey('adas_systems.id'))
)

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False)
    pin = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    team = Column(String, nullable=False)
    department = Column(String, nullable=False)
    role = Column(String, nullable=False)
    preferences = Column(JSONB)
    statistics = Column(JSONB)
    last_login = Column(DateTime(timezone=True))
    last_active = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean)
    notifications_enabled = Column(Boolean)
    monday_id = Column(String)
    icon_theme = Column(String, default="Rainbow Animation")

    # Relationships
    created_opportunities = relationship("Opportunity", back_populates="creator", foreign_keys="[Opportunity.creator_id]")
    accepted_opportunities = relationship("Opportunity", back_populates="acceptor", foreign_keys="[Opportunity.acceptor_id]")

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    year = Column(String, nullable=False)
    make = Column(String, nullable=False)
    model = Column(String, nullable=False)
    is_custom = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True))
    created_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    last_modified_at = Column(DateTime(timezone=True))
    last_modified_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    notes = Column(String)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    last_modified_by = relationship("User", foreign_keys=[last_modified_by_id])

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"

class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String)
    creator_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    acceptor_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    year = Column(String)
    make = Column(String)
    model = Column(String)
    systems = Column(JSONB)
    affected_portions = Column(JSONB)
    meta_data = Column(JSONB)
    comments = Column(JSONB, default=list)  # Store comments as a list of dictionaries
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    response_time = Column(Interval)
    work_time = Column(Interval)

    # Relationships
    creator = relationship("User", back_populates="created_opportunities", foreign_keys=[creator_id])
    acceptor = relationship("User", back_populates="accepted_opportunities", foreign_keys=[acceptor_id])
    files = relationship("File", back_populates="opportunity")
    notifications = relationship("Notification", back_populates="opportunity")
    activity_logs = relationship("ActivityLog", back_populates="opportunity")
    systems_rel = relationship("AdasSystem", secondary="opportunity_systems", back_populates="opportunities")
    file_attachments = relationship("FileAttachment", back_populates="opportunity")
    attachments = relationship("Attachment", back_populates="opportunity")

    @property
    def display_title(self):
        return f"{self.year} {self.make} {self.model}" if all([self.year, self.make, self.model]) else "No Vehicle Specified"

class AdasSystem(Base):
    __tablename__ = "adas_systems"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True))

    # Relationships
    opportunities = relationship("Opportunity", secondary="opportunity_systems", back_populates="systems_rel")

class File(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey('opportunities.id'), nullable=False)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String, nullable=False)
    original_name = Column(String, nullable=False)  # Original filename before storage
    storage_path = Column(String, nullable=False)  # Path in storage system
    size = Column(Integer)
    mime_type = Column(String)
    hash = Column(String)
    created_at = Column(DateTime(timezone=True))
    is_deleted = Column(Boolean, default=False)  # Soft delete flag

    # Relationships
    opportunity = relationship("Opportunity", back_populates="files")
    uploader = relationship("User")

    @property
    def display_name(self):
        """Return user-friendly display name"""
        return self.original_name or self.name

    @property
    def file_url(self):
        """Return the URL/path to access this file"""
        return f"/files/{self.id}/{self.name}"

class FileAttachment(Base):
    __tablename__ = "file_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey('opportunities.id'))
    filename = Column(String, nullable=False)
    file_type = Column(String)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)
    uploaded_at = Column(DateTime(timezone=True))
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    # Relationships
    opportunity = relationship("Opportunity", back_populates="file_attachments")
    uploaded_by = relationship("User")

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey('opportunities.id'))
    file_path = Column(String, nullable=False)
    file_type = Column(String)
    created_at = Column(DateTime(timezone=True))

    # Relationships
    opportunity = relationship("Opportunity", back_populates="attachments")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey('opportunities.id'))
    type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean)
    created_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User")
    opportunity = relationship("Opportunity", back_populates="notifications")

class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey('opportunities.id'))
    action = Column(String, nullable=False)
    details = Column(JSONB)
    created_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User")
    opportunity = relationship("Opportunity", back_populates="activity_logs")

class Settings(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, nullable=False)
    value = Column(JSONB, nullable=False)
    updated_at = Column(DateTime(timezone=True)) 