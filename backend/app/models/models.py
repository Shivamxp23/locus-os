import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Float,
    Integer,
    Text,
    TIMESTAMP,
    Date,
    ForeignKey,
    ARRAY,
    JSON,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
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
    __table_args__ = (
        CheckConstraint(
            "horizon IN ('week','month','quarter','year','lifetime')",
            name="ck_goals_horizon",
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
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
    __table_args__ = (
        CheckConstraint(
            "status IN ('planning','active','on_hold','completed')",
            name="ck_projects_status",
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    description = Column(Text)
    goal_id = Column(UUID(as_uuid=False), ForeignKey("goals.id"))
    status = Column(String, default="active")
    notion_page_id = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "source IN ('pwa','notion','telegram','graphrag','manual')",
            name="ck_tasks_source",
        ),
        CheckConstraint(
            "status IN ('pending','in_progress','completed','deferred','cancelled')",
            name="ck_tasks_status",
        ),
        CheckConstraint(
            "energy_type IN ('deep','creative','shallow','review')",
            name="ck_tasks_energy",
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
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
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
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
    embedding = Column(Vector(768))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    received_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    obsidian_path = Column(String)
    processed_by_e2 = Column(Boolean, default=False)


class PersonalityInsight(Base):
    __tablename__ = "personality_insights"
    __table_args__ = (
        CheckConstraint(
            "delivery_channel IN ('telegram','pwa','both')",
            name="ck_personality_insights_channel",
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
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
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    model_used = Column(String, nullable=False)
    model_source = Column(String, nullable=False)
    messages = Column(JSON, nullable=False)
    topic_tags = Column(ARRAY(String))
    summary = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    obsidian_path = Column(String)
    token_count = Column(Integer)


class SyncEvent(Base):
    __tablename__ = "sync_events"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "client_event_id", name="uq_sync_events_user_client"
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    device_id = Column(String, nullable=False)
    client_event_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    synced_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    conflict_detected = Column(Boolean, default=False)
    conflict_resolution = Column(Text)


class PersonalitySnapshot(Base):
    __tablename__ = "personality_snapshots"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    generated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    snapshot_data = Column(JSON, nullable=False)
    version = Column(Integer, default=1)


class DailyMetrics(Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_metrics_user_date"),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date = Column(Date, nullable=False)
    mood_score = Column(Float)
    energy_score = Column(Float)
    focus_score = Column(Float)
    productivity_score = Column(Float)
    tasks_completed = Column(Integer, default=0)
    tasks_deferred = Column(Integer, default=0)
    tasks_created = Column(Integer, default=0)
    deep_work_minutes = Column(Integer, default=0)
    creative_minutes = Column(Integer, default=0)
    dominant_topic = Column(String)
    dominant_category = Column(String)
    obsidian_log_path = Column(String)


class Habit(Base):
    __tablename__ = "habits"
    __table_args__ = (
        CheckConstraint(
            "frequency IN ('daily','weekdays','weekly','custom')",
            name="ck_habits_frequency",
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    frequency = Column(String)
    custom_days = Column(ARRAY(Integer))
    goal_id = Column(UUID(as_uuid=False), ForeignKey("goals.id"))
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_completed = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class HabitCompletion(Base):
    __tablename__ = "habit_completions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    habit_id = Column(
        UUID(as_uuid=False), ForeignKey("habits.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(UUID(as_uuid=False), nullable=False)
    completed_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    notes = Column(Text)


class ContentItem(Base):
    __tablename__ = "content_items"
    __table_args__ = (
        CheckConstraint(
            "platform IN ('linkedin','twitter','newsletter','blog')",
            name="ck_content_items_platform",
        ),
        CheckConstraint(
            "status IN ('draft','pending_approval','approved','published','rejected')",
            name="ck_content_items_status",
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    platform = Column(String)
    status = Column(String, default="draft")
    content = Column(Text, nullable=False)
    title = Column(String)
    source_event_ids = Column(ARRAY(UUID(as_uuid=False)))
    source_insight_ids = Column(ARRAY(UUID(as_uuid=False)))
    source_obsidian_paths = Column(ARRAY(Text))
    approved_at = Column(TIMESTAMP(timezone=True))
    published_at = Column(TIMESTAMP(timezone=True))
    rejection_reason = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    notion_page_id = Column(String)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(
            "rec_type IN ('book','article','podcast','video','course','blog')",
            name="ck_recommendations_rec_type",
        ),
        CheckConstraint(
            "status IN ('recommended','saved','reading','completed','dismissed')",
            name="ck_recommendations_status",
        ),
        CheckConstraint(
            "user_rating BETWEEN 1 AND 5", name="ck_recommendations_rating"
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    rec_type = Column(String)
    title = Column(String, nullable=False)
    author = Column(String)
    url = Column(String)
    relevance_reason = Column(Text, nullable=False)
    interest_tags = Column(ARRAY(String))
    goal_tags = Column(ARRAY(String))
    status = Column(String, default="recommended")
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    user_rating = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class DailyLog(Base):
    __tablename__ = "daily_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_logs_user_date"),
        CheckConstraint("energy_score BETWEEN 1 AND 10", name="ck_daily_logs_energy"),
        CheckConstraint("mood_score BETWEEN 1 AND 10", name="ck_daily_logs_mood"),
        CheckConstraint("sleep_score BETWEEN 1 AND 10", name="ck_daily_logs_sleep"),
        CheckConstraint("stress_score BETWEEN 1 AND 10", name="ck_daily_logs_stress"),
        CheckConstraint(
            "mode IN ('SURVIVAL','RECOVERY','NORMAL','DEEP_WORK','PEAK')",
            name="ck_daily_logs_mode",
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date = Column(Date, nullable=False)
    energy_score = Column(Integer)
    mood_score = Column(Integer)
    sleep_score = Column(Integer)
    stress_score = Column(Integer)
    time_available = Column(Float)
    dcs_score = Column(Float)
    mode = Column(String)
    morning_logged_at = Column(TIMESTAMP(timezone=True))
    evening_logged_at = Column(TIMESTAMP(timezone=True))
    what_i_did = Column(Text)
    what_i_avoided = Column(Text)
    tomorrow_priority = Column(Text)


class SavedLink(Base):
    __tablename__ = "saved_links"
    __table_args__ = (
        CheckConstraint(
            "faction IN ('health','leverage','craft','expression')",
            name="ck_saved_links_faction",
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    url = Column(Text, nullable=False)
    title = Column(String)
    description = Column(Text)
    faction = Column(String)
    tags = Column(ARRAY(String))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class RawNote(Base):
    __tablename__ = "raw_notes"
    __table_args__ = (
        CheckConstraint(
            "note_type IN ('idea','note','journal')", name="ck_raw_notes_type"
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content = Column(Text, nullable=False)
    note_type = Column(String)
    enriched_content = Column(Text)
    suggested_faction = Column(String)
    suggested_project_id = Column(UUID(as_uuid=False))
    obsidian_path = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    processed_at = Column(TIMESTAMP(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    payload_hash = Column(String)
    response_status = Column(Integer)
    duration_ms = Column(Integer)
    ip_address = Column(String)
    user_agent = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class LlmTrainingData(Base):
    __tablename__ = "llm_training_data"
    __table_args__ = (
        CheckConstraint("reward IN (-1, 0, 1)", name="ck_llm_training_reward"),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_type = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    model_used = Column(String, nullable=False)
    model_source = Column(String, nullable=False)
    reward = Column(Integer)
    feedback_notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class FactionWeeklyMetric(Base):
    __tablename__ = "faction_weekly_metrics"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "faction",
            "week_start",
            name="uq_faction_metrics_user_faction_week",
        ),
        CheckConstraint(
            "faction IN ('health','leverage','craft','expression')",
            name="ck_faction_weekly_faction",
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    faction = Column(String, nullable=False)
    week_start = Column(Date, nullable=False)
    target_hours = Column(Float, default=0)
    actual_hours = Column(Float, default=0)
    completion_rate = Column(Float, default=0)
    consistency_score = Column(Float, default=0)
    momentum_score = Column(Float)
    lag_score = Column(Float, default=0)
    action_gap = Column(Float, default=0)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class AiReport(Base):
    __tablename__ = "ai_reports"
    __table_args__ = (
        CheckConstraint(
            "report_type IN ('weekly_pattern','weekly_self','monthly','quarterly')",
            name="ck_ai_reports_type",
        ),
        CheckConstraint(
            "delivery_channel IN ('telegram','pwa','both')",
            name="ck_ai_reports_channel",
        ),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    report_type = Column(String, nullable=False)
    title = Column(String)
    content = Column(Text, nullable=False)
    week_start = Column(Date)
    generated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    delivered_at = Column(TIMESTAMP(timezone=True))
    delivery_channel = Column(String)
