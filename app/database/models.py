from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # For PostgreSQL specific UUID type
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # For server-side default timestamps

import uuid # For client-side default UUIDs if needed, though PG_UUID can auto-generate

from .base import Base # Import Base from the same directory


class Workflow(Base):
    __tablename__ = "workflows"

    workflow_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_prompt = Column(Text, nullable=True) # Can be null if task is initiated differently
    status = Column(String(50), nullable=False, default="PENDING", index=True) # e.g., PENDING, RUNNING, COMPLETED, FAILED, WAITING_HUMAN
    current_dag_representation = Column(JSON, nullable=True) # Store the DAG of subtasks

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    subtasks = relationship("Subtask", back_populates="workflow", cascade="all, delete-orphan")
    checkpoints = relationship("Checkpoint", back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workflow(workflow_id='{self.workflow_id}', status='{self.status}')>"


class Subtask(Base):
    __tablename__ = "subtasks"

    subtask_id = Column(String, primary_key=True) # Can be a human-readable ID or a generated one
    workflow_id = Column(PG_UUID(as_uuid=True), ForeignKey("workflows.workflow_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING", index=True) # PENDING, RUNNING, COMPLETED, FAILED, WAITING_HUMAN
    agent_name = Column(String(100), nullable=True)
    depends_on = Column(JSON, nullable=True) # List of subtask_ids this task depends on
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    workflow = relationship("Workflow", back_populates="subtasks")
    checkpoints = relationship("Checkpoint", back_populates="subtask", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_subtasks_workflow_id_name', 'workflow_id', 'name'), # Index for faster lookups by workflow and name
    )

    def __repr__(self):
        return f"<Subtask(subtask_id='{self.subtask_id}', name='{self.name}', status='{self.status}')>"


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    checkpoint_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(PG_UUID(as_uuid=True), ForeignKey("workflows.workflow_id"), nullable=False, index=True)
    subtask_id = Column(String, ForeignKey("subtasks.subtask_id"), nullable=True, index=True) # Nullable if checkpoint is for the whole workflow
    agent_name = Column(String(100), nullable=True) # If checkpoint is specific to an agent's state for a subtask

    # Snapshots of state
    agent_memory_snapshot = Column(JSON, nullable=True)
    agent_internal_state_snapshot = Column(JSON, nullable=True) # Other relevant agent attributes
    tool_states_snapshot = Column(JSON, nullable=True) # e.g., browser state if applicable
    planning_flow_snapshot = Column(JSON, nullable=True) # State of PlanningFlow or WorkflowOrchestrator

    reason = Column(String(255), nullable=True) # e.g., "periodic", "before_human_input", "subtask_completed"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="checkpoints")
    subtask = relationship("Subtask", back_populates="checkpoints")

    def __repr__(self):
        return f"<Checkpoint(checkpoint_id='{self.checkpoint_id}', workflow_id='{self.workflow_id}', reason='{self.reason}')>"

# Example of how to generate the schema in a database (using Alembic is preferred for migrations):
# from sqlalchemy.ext.asyncio import create_async_engine
# from app.config import config # Assuming config is set up
#
# async def create_tables():
#     engine = create_async_engine(config.postgresql.db_url, echo=True)
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#
# if __name__ == "__main__":
# import asyncio
# asyncio.run(create_tables())
#
# Remember to set up Alembic for proper schema migration management in a real application.
# `alembic init alembic`
# Then configure env.py and alembic.ini, and create migration scripts.
# `alembic revision -m "create_initial_tables"`
# Edit the generated script with these model definitions.
# `alembic upgrade head`
