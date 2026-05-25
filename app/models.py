import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, DateTime, Date, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255))
    telegram_id = Column(String(64), unique=True, nullable=True)
    subscription_tier = Column(String(20), default="free")
    subscription_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    profile = relationship("ActorProfile", back_populates="user", uselist=False)
    tasks = relationship("Task", back_populates="user")
    strategies = relationship("Strategy", back_populates="user")
    documents = relationship("Document", back_populates="user")


class ActorProfile(Base):
    __tablename__ = "actor_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    photo_url = Column(Text)
    photo_url = Column(Text)
    archetype = Column(String(255))
    archetypes_secondary = Column(JSON, default=list)  # list of strings
    age_range = Column(String(50))
    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    actor_type = Column(String(255))  # типаж
    goals = Column(Text)
    experience_level = Column(String(50))  # beginner / intermediate / professional
    bio = Column(Text)

    # Pipeline analysis results (stored as JSON arrays/objects)
    archetype_extra = Column(JSON, default=list)  # list[str] — основные архетипы из анализа
    emotional_range = Column(Integer, nullable=True)  # 1-10
    camera_presence = Column(Integer, nullable=True)  # 1-10
    naturalness = Column(Integer, nullable=True)      # 1-10
    analysis_recommendations = Column(JSON, default=list)  # list[str]
    analysis_summary = Column(Text, nullable=True)        # текст анализа
    analysis_completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    task_type = Column(String(50))  # daily / casting / development
    due_date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="tasks")


class CastingEvent(Base):
    __tablename__ = "casting_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(String(255))
    event_date = Column(DateTime, nullable=False)
    is_reminded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    period_days = Column(Integer, nullable=False)  # 30 / 60 / 90
    content = Column(JSON, nullable=False)  # full strategy JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="strategies")


class SiteContent(Base):
    __tablename__ = "site_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    block_key = Column(String(100), unique=True, nullable=False, index=True)  # hero, how_it_works, archetypes, etc.
    data = Column(JSON, nullable=False)  # весь контент блока
    is_visible = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    phone = Column(String(50))
    source = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    doc_type = Column(String(50))  # contract / portfolio / letter
    title = Column(String(255))
    file_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="documents")


class MessageQueue(Base):
    """Очередь сообщений для единого AI-агента.
    Все запросы от актёров попадают сюда.
    Воркер забирает по одному, обрабатывает и сохраняет ответ.
    """
    __tablename__ = "messages_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    context = Column(JSON, default={})  # фото/профиль на момент запроса

    status = Column(String(20), default="pending", index=True)  # pending / processing / done / error
    reply = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="messages")
