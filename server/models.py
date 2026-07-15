import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class TaskORM(Base):
    __tablename__ = "tasks"

    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String, nullable=False)
    input = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserORM(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SessionORM(Base):
    __tablename__ = "sessions"

    token = Column(String, primary_key=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ConversationORM(Base):
    __tablename__ = "conversations"

    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    title = Column(String, nullable=False, default="New conversation")
    model = Column(String, nullable=True)
    settings = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConversationEventORM(Base):
    __tablename__ = "conversation_events"

    event_id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id"),
        nullable=False,
        index=True,
    )
    task_id = Column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=True, index=True
    )
    event_type = Column(String, nullable=False, index=True)
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class AppSettingORM(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ObsidianNoteORM(Base):
    __tablename__ = "obsidian_notes"
    __table_args__ = (
        UniqueConstraint("conversation_id", "path", name="uq_obsidian_note_conv_path"),
    )

    note_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id"),
        nullable=False,
        index=True,
    )
    path = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    content = Column(String, nullable=False, default="")
    tags = Column(JSONB, nullable=False, default=list)
    meta = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ObsidianEdgeORM(Base):
    __tablename__ = "obsidian_edges"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "source_note_id", "target_note_id", "relation",
            name="uq_obsidian_edge_conv_src_tgt_rel",
        ),
    )

    edge_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id"),
        nullable=False,
        index=True,
    )
    source_note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("obsidian_notes.note_id"),
        nullable=False,
        index=True,
    )
    target_note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("obsidian_notes.note_id"),
        nullable=False,
        index=True,
    )
    relation = Column(String, nullable=False, default="wikilink")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


__all__ = [
    "Base",
    "TaskORM",
    "UserORM",
    "SessionORM",
    "ConversationORM",
    "ConversationEventORM",
    "AppSettingORM",
    "ObsidianNoteORM",
    "ObsidianEdgeORM",
]
