import json
from typing import Any, Dict, Optional, Tuple, List
from uuid import UUID

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal, get_db # Assuming get_db yields an AsyncSession
from app.database.models import Workflow, Subtask, Checkpoint
from app.logger import logger
from app.event_bus.events import WorkflowCheckpointEvent # To publish after saving
# from app.event_bus.redis_bus import RedisEventBus # Import if publishing event here

# Placeholder for event bus instance if used directly by checkpointer
# event_bus_instance = RedisEventBus()
# await event_bus_instance.connect() # Needs to be managed within an async context


class PostgreSQLCheckpointer:
    def __init__(self):
        # SessionLocal will be used via get_db context manager typically
        pass

    async def _serialize_agent_state(self, agent_state: Any) -> Optional[Dict[str, Any]]:
        """
        Serializes the relevant parts of an agent's state for checkpointing.
        This needs to be adapted based on what's in BaseAgent/Manus/ToolCallAgent.
        """
        if not agent_state:
            return None

        serialized_state = {}
        # Memory (messages)
        if hasattr(agent_state, 'memory') and hasattr(agent_state.memory, 'messages'):
            try:
                # Assuming messages are Pydantic models, convert to dicts
                serialized_state['memory_messages'] = [msg.model_dump(mode='json') for msg in agent_state.memory.messages]
            except Exception as e:
                logger.error(f"Error serializing agent memory messages: {e}")
                serialized_state['memory_messages'] = None # Or handle more gracefully

        # Internal state attributes (example for Manus)
        # This list should be comprehensive for the agent being checkpointed.
        # Be careful about serializing non-JSON-serializable types directly.
        internal_attrs_to_save = [
            'current_step', '_autonomous_mode', '_monitoring_background_task',
            '_background_task_log_file', '_background_task_expected_artifact',
            '_background_task_artifact_path', '_background_task_description',
            '_pending_script_after_dependency',
            # '_original_tool_call_for_pending_script', # This is a ToolCall object, needs careful serialization
            # '_pending_fallback_tool_call', # Also ToolCall
            # Add other relevant Manus-specific or ToolCallAgent-specific fields
        ]
        internal_state_snapshot = {}
        for attr_name in internal_attrs_to_save:
            if hasattr(agent_state, attr_name):
                internal_state_snapshot[attr_name] = getattr(agent_state, attr_name)

        # Handle complex objects that need custom serialization (like ToolCall)
        if hasattr(agent_state, '_original_tool_call_for_pending_script') and agent_state._original_tool_call_for_pending_script:
            try:
                internal_state_snapshot['_original_tool_call_for_pending_script'] = agent_state._original_tool_call_for_pending_script.model_dump(mode='json')
            except Exception as e:
                logger.error(f"Error serializing _original_tool_call_for_pending_script: {e}")

        if hasattr(agent_state, '_pending_fallback_tool_call') and agent_state._pending_fallback_tool_call:
            try:
                internal_state_snapshot['_pending_fallback_tool_call'] = agent_state._pending_fallback_tool_call.model_dump(mode='json')
            except Exception as e:
                logger.error(f"Error serializing _pending_fallback_tool_call: {e}")

        serialized_state['internal_state'] = internal_state_snapshot
        return serialized_state

    async def _deserialize_agent_state(self, agent_instance: Any, memory_snapshot: Optional[List[Dict]], internal_state_snapshot: Optional[Dict]):
        """
        Deserializes and applies state to an agent instance.
        """
        if not agent_instance:
            return

        from app.schema import Message # Local import to avoid circularity if models are complex

        # Memory messages
        if memory_snapshot and hasattr(agent_instance, 'memory'):
            try:
                agent_instance.memory.messages = [Message(**msg_data) for msg_data in memory_snapshot]
            except Exception as e:
                logger.error(f"Error deserializing agent memory messages: {e}")

        # Internal state
        if internal_state_snapshot and hasattr(agent_instance, '__dict__'):
             # Simple attribute setting for now. More complex state might need specific handling.
            for attr_name, value in internal_state_snapshot.items():
                if hasattr(agent_instance, attr_name):
                    try:
                        # Handle deserialization of complex objects like ToolCall if stored as dicts
                        if attr_name in ['_original_tool_call_for_pending_script', '_pending_fallback_tool_call'] and value:
                            from app.schema import ToolCall # Local import
                            setattr(agent_instance, attr_name, ToolCall(**value))
                        else:
                            setattr(agent_instance, attr_name, value)
                    except Exception as e:
                         logger.error(f"Error setting attribute {attr_name} during deserialization: {e}")
                else:
                    logger.warning(f"Attribute {attr_name} from checkpoint not found on agent instance.")

        # Special handling for re-initializing transient or complex fields after state load
        if hasattr(agent_instance, '__setstate__'):
            # If agent has __setstate__, it might handle its own re-initialization logic
            # For Manus, __setstate__ re-initializes LLM, tools, MCP clients etc.
            # We need to ensure the state passed to __setstate__ is what it expects,
            # or call specific re-init methods if __setstate__ is too broad.
            # For now, we assume direct attribute setting is enough for core state,
            # and __setstate__ or other methods handle complex re-init if called elsewhere.
            # Manus.__setstate__ seems to expect the full dict.
            # This part needs careful review based on specific agent's __setstate__ logic.
            # A simpler approach for now: let the caller of load_checkpoint handle re-init.
            pass


    async def save_checkpoint(
        self,
        workflow_id: UUID,
        reason: str,
        agent_state: Optional[Any] = None, # Agent instance
        flow_state: Optional[Dict[str, Any]] = None, # e.g., WorkflowOrchestrator state
        tool_states: Optional[Dict[str, Any]] = None, # e.g., browser state
        subtask_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> Optional[UUID]:
        """
        Saves a new checkpoint to the database.

        Args:
            workflow_id: The ID of the workflow.
            reason: The reason for this checkpoint.
            agent_state: The current state of the agent (if applicable).
            flow_state: The current state of the workflow/planning (if applicable).
            tool_states: The current state of relevant tools (if applicable).
            subtask_id: Optional ID of the subtask this checkpoint relates to.
            agent_name: Optional name of the agent this checkpoint relates to.

        Returns:
            The UUID of the created checkpoint, or None if failed.
        """
        serialized_agent_data = await self._serialize_agent_state(agent_state)
        agent_memory_json = None
        agent_internal_state_json = None
        if serialized_agent_data:
            agent_memory_json = serialized_agent_data.get('memory_messages')
            agent_internal_state_json = serialized_agent_data.get('internal_state')

        checkpoint = Checkpoint(
            workflow_id=workflow_id,
            subtask_id=subtask_id,
            agent_name=agent_name,
            agent_memory_snapshot=agent_memory_json,
            agent_internal_state_snapshot=agent_internal_state_json,
            tool_states_snapshot=tool_states,
            planning_flow_snapshot=flow_state,
            reason=reason,
        )

        async with SessionLocal() as db:
            try:
                db.add(checkpoint)
                await db.commit()
                await db.refresh(checkpoint)
                logger.info(f"Checkpoint {checkpoint.checkpoint_id} saved for workflow {workflow_id}, reason: {reason}")

                # Publish WorkflowCheckpointEvent
                # checkpoint_event = WorkflowCheckpointEvent(
                #     source="PostgreSQLCheckpointer",
                #     task_id=str(workflow_id),
                #     checkpoint_id=str(checkpoint.checkpoint_id),
                #     reason=reason,
                #     state_snapshot_summary={"agent_name": agent_name, "subtask_id": subtask_id} # Basic summary
                # )
                # await event_bus_instance.publish("workflow_events", checkpoint_event.model_dump(mode='json'))

                return checkpoint.checkpoint_id
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to save checkpoint for workflow {workflow_id}: {e}", exc_info=True)
                return None

    async def load_checkpoint_data(self, checkpoint_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Loads checkpoint data from the database.
        This method returns the raw data, deserialization happens elsewhere.
        """
        async with SessionLocal() as db:
            try:
                result = await db.execute(
                    select(Checkpoint).where(Checkpoint.checkpoint_id == checkpoint_id)
                )
                checkpoint = result.scalars().first()
                if checkpoint:
                    logger.info(f"Checkpoint {checkpoint_id} loaded successfully.")
                    return {
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "workflow_id": checkpoint.workflow_id,
                        "subtask_id": checkpoint.subtask_id,
                        "agent_name": checkpoint.agent_name,
                        "agent_memory_snapshot": checkpoint.agent_memory_snapshot,
                        "agent_internal_state_snapshot": checkpoint.agent_internal_state_snapshot,
                        "tool_states_snapshot": checkpoint.tool_states_snapshot,
                        "planning_flow_snapshot": checkpoint.planning_flow_snapshot,
                        "reason": checkpoint.reason,
                        "created_at": checkpoint.created_at,
                    }
                else:
                    logger.warning(f"Checkpoint {checkpoint_id} not found.")
                    return None
            except Exception as e:
                logger.error(f"Failed to load checkpoint {checkpoint_id}: {e}", exc_info=True)
                return None

    async def load_latest_checkpoint_data(self, workflow_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Loads the most recent checkpoint data for a given workflow_id.
        """
        async with SessionLocal() as db:
            try:
                result = await db.execute(
                    select(Checkpoint)
                    .where(Checkpoint.workflow_id == workflow_id)
                    .order_by(Checkpoint.created_at.desc())
                    .limit(1)
                )
                checkpoint = result.scalars().first()
                if checkpoint:
                    logger.info(f"Latest checkpoint {checkpoint.checkpoint_id} for workflow {workflow_id} loaded.")
                    return {
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "workflow_id": checkpoint.workflow_id,
                        "subtask_id": checkpoint.subtask_id,
                        "agent_name": checkpoint.agent_name,
                        "agent_memory_snapshot": checkpoint.agent_memory_snapshot,
                        "agent_internal_state_snapshot": checkpoint.agent_internal_state_snapshot,
                        "tool_states_snapshot": checkpoint.tool_states_snapshot,
                        "planning_flow_snapshot": checkpoint.planning_flow_snapshot,
                        "reason": checkpoint.reason,
                        "created_at": checkpoint.created_at,
                    }
                else:
                    logger.info(f"No checkpoints found for workflow {workflow_id}.")
                    return None
            except Exception as e:
                logger.error(f"Failed to load latest checkpoint for workflow {workflow_id}: {e}", exc_info=True)
                return None

    # --- Workflow and Subtask Management ---
    async def create_workflow(self, user_prompt: str, initial_dag: Optional[Dict] = None) -> Optional[UUID]:
        workflow = Workflow(user_prompt=user_prompt, status="PENDING", current_dag_representation=initial_dag)
        async with SessionLocal() as db:
            try:
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                logger.info(f"Workflow {workflow.workflow_id} created.")
                return workflow.workflow_id
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to create workflow: {e}", exc_info=True)
                return None

    async def update_workflow_status(self, workflow_id: UUID, status: str, dag_representation: Optional[Dict] = None) -> bool:
        async with SessionLocal() as db:
            try:
                result = await db.execute(select(Workflow).where(Workflow.workflow_id == workflow_id))
                workflow = result.scalars().first()
                if workflow:
                    workflow.status = status
                    if dag_representation is not None:
                        workflow.current_dag_representation = dag_representation
                    workflow.updated_at = func.now() # Explicitly update timestamp
                    await db.commit()
                    logger.info(f"Workflow {workflow_id} status updated to {status}.")
                    return True
                logger.warning(f"Workflow {workflow_id} not found for status update.")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to update workflow {workflow_id} status: {e}", exc_info=True)
                return False

    async def add_subtask(self, workflow_id: UUID, subtask_id: str, name: str, depends_on: Optional[List[str]] = None) -> bool:
        subtask = Subtask(
            subtask_id=subtask_id,
            workflow_id=workflow_id,
            name=name,
            status="PENDING",
            depends_on=depends_on if depends_on else []
        )
        async with SessionLocal() as db:
            try:
                db.add(subtask)
                await db.commit()
                logger.info(f"Subtask {subtask_id} for workflow {workflow_id} added.")
                return True
            except Exception as e: # Could be IntegrityError if subtask_id is not unique for workflow
                await db.rollback()
                logger.error(f"Failed to add subtask {subtask_id} to workflow {workflow_id}: {e}", exc_info=True)
                return False

    async def update_subtask(
        self,
        subtask_id: str,
        workflow_id: UUID, # Needed to ensure we update the correct subtask if IDs are not globally unique
        status: Optional[str] = None,
        result: Optional[Any] = None,
        error_message: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> bool:
        async with SessionLocal() as db:
            try:
                result_proxy = await db.execute(
                    select(Subtask).where(Subtask.subtask_id == subtask_id, Subtask.workflow_id == workflow_id)
                )
                subtask = result_proxy.scalars().first()
                if subtask:
                    updated = False
                    if status is not None:
                        subtask.status = status
                        updated = True
                    if result is not None:
                        subtask.result = result # Assume result is JSON serializable
                        updated = True
                    if error_message is not None:
                        subtask.error_message = error_message
                        updated = True
                    if agent_name is not None:
                        subtask.agent_name = agent_name
                        updated = True

                    if updated:
                        subtask.updated_at = func.now()
                        await db.commit()
                        logger.info(f"Subtask {subtask_id} (workflow {workflow_id}) updated. Status: {status}, Agent: {agent_name}")
                    else:
                        logger.info(f"No updates provided for subtask {subtask_id} (workflow {workflow_id}).")
                    return True
                logger.warning(f"Subtask {subtask_id} for workflow {workflow_id} not found for update.")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to update subtask {subtask_id} for workflow {workflow_id}: {e}", exc_info=True)
                return False

    async def get_workflow_with_subtasks(self, workflow_id: UUID) -> Optional[Dict]:
        async with SessionLocal() as db:
            try:
                result = await db.execute(
                    select(Workflow)
                    .where(Workflow.workflow_id == workflow_id)
                    .options(selectinload(Workflow.subtasks)) # Eager load subtasks
                )
                workflow = result.scalars().first()
                if workflow:
                    return {
                        "workflow_id": workflow.workflow_id,
                        "user_prompt": workflow.user_prompt,
                        "status": workflow.status,
                        "current_dag_representation": workflow.current_dag_representation,
                        "created_at": workflow.created_at,
                        "updated_at": workflow.updated_at,
                        "subtasks": [
                            {
                                "subtask_id": st.subtask_id,
                                "name": st.name,
                                "status": st.status,
                                "agent_name": st.agent_name,
                                "depends_on": st.depends_on,
                                "result": st.result,
                                "error_message": st.error_message,
                                "created_at": st.created_at,
                                "updated_at": st.updated_at,
                            } for st in workflow.subtasks
                        ]
                    }
                return None
            except Exception as e:
                logger.error(f"Error fetching workflow {workflow_id} with subtasks: {e}", exc_info=True)
                return None

    async def invalidate_subsequent_work(self, workflow_id: UUID, checkpoint_created_at: Any) -> bool:
        """
        Marks subtasks and checkpoints created after a specific checkpoint's creation time as 'INVALIDATED' or 'ARCHIVED'.
        For simplicity, we'll update subtask statuses to 'PENDING' or a new 'INVALIDATED' status,
        and for checkpoints, we might just log or add a status if the model supports it.
        Alternatively, delete them if strict rollback is required. For now, let's focus on subtasks.

        Args:
            workflow_id: The ID of the workflow.
            checkpoint_created_at: The creation timestamp of the checkpoint to roll back to.
                                   Work after this time will be invalidated.

        Returns:
            True if invalidation was successful (or no work needed invalidation), False otherwise.
        """
        async with SessionLocal() as db:
            try:
                # Invalidate Subtasks: Set status to PENDING for those not COMPLETED or FAILED before the checkpoint.
                # More complex logic might be needed if subtasks could be re-executed vs. truly invalidated.
                # For now, let's assume we are resetting them to PENDING if they were RUNNING or WAITING.
                # Or, if a subtask was COMPLETED *after* checkpoint_created_at, it should be reset.

                # Find subtasks of this workflow modified AFTER the checkpoint time
                subtasks_to_reset = await db.execute(
                    select(Subtask).where(
                        Subtask.workflow_id == workflow_id,
                        Subtask.updated_at > checkpoint_created_at
                        # Add more conditions if needed, e.g., only reset if status is RUNNING, etc.
                    )
                )
                subtasks_to_reset_list = subtasks_to_reset.scalars().all()

                for subtask in subtasks_to_reset_list:
                    logger.info(f"Rolling back subtask {subtask.subtask_id} (status: {subtask.status}) for workflow {workflow_id} due to rollback.")
                    # Reset status to PENDING. If it was created after the checkpoint, it might be deleted or marked differently.
                    # For simplicity, we'll reset its status. The DAG representation in Workflow should be the source of truth for structure.
                    subtask.status = "PENDING"
                    subtask.result = None
                    subtask.error_message = None
                    # updated_at will be set by onupdate

                # Invalidate Checkpoints: Delete checkpoints created after the rollback point.
                checkpoints_to_delete_stmt = Checkpoint.__table__.delete().where(
                    Checkpoint.workflow_id == workflow_id,
                    Checkpoint.created_at > checkpoint_created_at
                )
                delete_result = await db.execute(checkpoints_to_delete_stmt)

                await db.commit()
                logger.info(f"Invalidated {len(subtasks_to_reset_list)} subtasks and deleted {delete_result.rowcount} checkpoints after {checkpoint_created_at} for workflow {workflow_id}.")
                return True
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to invalidate subsequent work for workflow {workflow_id} after checkpoint at {checkpoint_created_at}: {e}", exc_info=True)
                return False


# Example usage:
# async def example_checkpointing():
#     checkpointer = PostgreSQLCheckpointer()
#
#     # Create a workflow
#     wf_id = await checkpointer.create_workflow("Test prompt")
#     if not wf_id: return
#
#     # Add subtasks
#     await checkpointer.add_subtask(wf_id, "st1", "Analyze data", [])
#     await checkpointer.add_subtask(wf_id, "st2", "Generate report", ["st1"])
#
#     # Simulate agent state
#     class MockAgent:
#         def __init__(self):
#             self.memory = type('obj', (object,), {'messages': [{'role': 'user', 'content': 'hello'}]})()
#             self.current_step = 5
#             self._autonomous_mode = False
#
#     agent = MockAgent()
#     agent_state_snapshot = await checkpointer._serialize_agent_state(agent)
#
#     # Save a checkpoint
#     chkpt_id = await checkpointer.save_checkpoint(
#         workflow_id=wf_id,
#         reason="Initial setup",
#         agent_state=agent, # Pass the agent instance
#         flow_state={"current_plan_step": 0},
#         subtask_id="st1",
#         agent_name="Manus"
#     )
#     if not chkpt_id: return
#
#     # Load the checkpoint data
#     loaded_data = await checkpointer.load_checkpoint_data(chkpt_id)
#     if loaded_data:
#         print("Loaded checkpoint data:", loaded_data)
#         # Example of deserializing state back to an agent (simplified)
#         new_agent = MockAgent() # Fresh agent instance
#         await checkpointer._deserialize_agent_state(
#             new_agent,
#             loaded_data.get('agent_memory_snapshot'),
#             loaded_data.get('agent_internal_state_snapshot')
#         )
#         print("Restored agent memory:", [msg.content for msg in new_agent.memory.messages])
#         print("Restored agent current_step:", new_agent.current_step)
#
# if __name__ == "__main__":
#     # This requires PostgreSQL running and configured in config.toml
#     # Also, app.database.init_db() should have been run once to create tables.
#     asyncio.run(example_checkpointing())
