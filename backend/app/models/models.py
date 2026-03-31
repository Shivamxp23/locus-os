import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Float, Integer, Text,
    TIMESTAMP, Date, ForeignKey, ARRAY, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=True)
    timezone = Column(String, default="Asia/Kolkata")
    genesis_completed = Column(Boolean, default=False)
    genesis_data = Column(JSON)
    google_access_token = Column(Text)
    google_refresh_token = Column(Text)
    google_token_expiry = Column(TIMESTAMP(timezone=True))
    notion_access_token = Column(Text)
    telegram_chat_id = Column(String)
    preferences = Column(JSON, default={})
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    last_active = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, default=True)

    goals = relationship("Goal", back_populates="user", cascade="all, delete")
    tasks = relationship("Task", back_populates="user", cascade="all, delete")

class Goal(Base):
    __tablename__ = "goals"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    horizon = Column(String)
    progress_score = Column(Float, default=0.0)
    neo4j_node_id = Column(String)
    notion_page_id = Column(String)
    is_active = Column(Boolean, default=True)
    is_stale = Column(Boolean, default=False)
    stale_since = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    last_task_completed = Column(TIMESTAMP(timezone=True))
    deadline = Column(Date)

    user = relationship("User", back_populates="goals")
    tasks = relationship("Task", back_populates="goal")

class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    goal_id = Column(UUID(as_uuid=False), ForeignKey("goals.id"))
    status = Column(String, default="active")
    notion_page_id = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    parent_task_id = Column(UUID(as_uuid=False), ForeignKey("tasks.id"))
    goal_id = Column(UUID(as_uuid=False), ForeignKey("goals.id"))
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"))
    source = Column(String, default="pwa")
    notion_page_id = Column(String)
    status = Column(String, default="pending")
    priority_score = Column(Float)
    energy_type = Column(String)
    estimated_minutes = Column(Integer)
    scheduled_at = Column(TIMESTAMP(timezone=True))
    deferral_count = Column(Integer, default=0)
    deferral_flag = Column(Text)
    completed_at = Column(TIMESTAMP(timezone=True))
    completion_duration_minutes = Column(Integer)
    engine_annotations = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    deadline = Column(TIMESTAMP(timezone=True))

    user = relationship("User", back_populates="tasks")
    goal = relationship("Goal", back_populates="tasks")

class BehavioralEvent(Base):
    __tablename__ = "behavioral_events"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    intent = Column(String)
    raw_content = Column(Text)
    normalized_content = Column(Text)
    summary = Column(Text)
    topic_tags = Column(ARRAY(String))
    mood_indicator = Column(Float)
    energy_required = Column(Integer)
    goal_tags = Column(ARRAY(String))
    signal_weight = Column(Float, default=1.0)
    task_id = Column(UUID(as_uuid=False), ForeignKey("tasks.id"))
    goal_id = Column(UUID(as_uuid=False), ForeignKey("goals.id"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    received_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    obsidian_path = Column(String)
    processed_by_e2 = Column(Boolean, default=False)

class PersonalityInsight(Base):
    __tablename__ = "personality_insights"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    insight_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    confidence = Column(Float)
    neo4j_node_id = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    delivered_at = Column(TIMESTAMP(timezone=True))
    delivery_channel = Column(String)

class AiConversation(Base):
    __tablename__ = "ai_conversations"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model_used = Column(String, nullable=False)
    model_source = Column(String, nullable=False)
    messages = Column(JSON, nullable=False)
    topic_tags = Column(ARRAY(String))
    summary = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    obsidian_path = Column(String)
    token_count = Column(Integer)
