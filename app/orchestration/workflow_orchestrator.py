import asyncio
from uuid import UUID
from typing import Dict, Optional

from app.event_bus.redis_bus import RedisEventBus
from app.event_bus.events import (
    TaskCreatedEvent,
    SubtaskCompletedEvent,
    SubtaskFailedEvent,
    AgentActionScheduledEvent,
    HumanInputProvidedEvent, # Adicionado
    # Potentially WorkflowCompletedEvent, WorkflowFailedEvent if defined
)
from app.checkpointing.postgresql_checkpointer import PostgreSQLCheckpointer
from app.database.models import Workflow as WorkflowDBModel, Checkpoint as CheckpointDBModel
from app.tool.planning import Plan, Subtask
from app.logger import logger
# from app.schema import Message # Para new_directive, se necessário no futuro


class WorkflowOrchestrator:
    def __init__(self, event_bus: RedisEventBus, checkpointer: PostgreSQLCheckpointer):
        self.event_bus = event_bus
        self.checkpointer = checkpointer
        # self.active_workflows: Dict[UUID, Plan] = {} # Cache em memória de planos ativos, opcional

    async def handle_task_created_event(self, event: TaskCreatedEvent, event_id_str: str, stream_name: str, group_name: str, consumer_name: str):
        logger.info(f"Orchestrator: Handling TaskCreatedEvent for task_id: {event.task_info.task_id}")

        workflow_uuid = UUID(event.task_info.task_id)

        existing_workflow_data = await self.checkpointer.get_workflow_with_subtasks(workflow_uuid)

        if existing_workflow_data:
            logger.info(f"Workflow {workflow_uuid} already exists. Updating or re-evaluating.")
            if existing_workflow_data['status'] not in ["PENDING", "RUNNING", "WAITING_HUMAN"]:
                await self.checkpointer.update_workflow_status(workflow_uuid, "PENDING", event.initial_plan)
        else:
            created_wf_id = await self.checkpointer.create_workflow(
                user_prompt=event.user_prompt,
                initial_dag=event.initial_plan
            )
            if not created_wf_id :
                 logger.error(f"Failed to create workflow {workflow_uuid} in DB from TaskCreatedEvent.")
                 return

        current_plan_dag_dict: Optional[Dict] = None
        if event.initial_plan and isinstance(event.initial_plan, dict) and "subtasks" in event.initial_plan:
            try:
                plan_obj = Plan(**event.initial_plan)
                current_plan_dag_dict = plan_obj.model_dump(mode='json')

                for subtask_id, subtask_obj in plan_obj.subtasks.items():
                    await self.checkpointer.add_subtask(
                        workflow_id=workflow_uuid,
                        subtask_id=subtask_obj.id,
                        name=subtask_obj.name,
                        depends_on=subtask_obj.depends_on
                    )
                logger.info(f"Subtasks from initial_plan processed for workflow {workflow_uuid}")
            except Exception as e:
                logger.error(f"Error processing initial_plan for workflow {workflow_uuid}: {e}", exc_info=True)
                await self.checkpointer.update_workflow_status(workflow_uuid, "FAILED", None)
                return

        await self.checkpointer.update_workflow_status(workflow_uuid, "PENDING", current_plan_dag_dict)
        await self.schedule_ready_subtasks(workflow_uuid)

    async def schedule_ready_subtasks(self, workflow_uuid: UUID):
        logger.info(f"Orchestrator: Checking and scheduling ready subtasks for workflow {workflow_uuid}")
        workflow_data = await self.checkpointer.get_workflow_with_subtasks(workflow_uuid)

        if not workflow_data:
            logger.warning(f"Workflow {workflow_uuid} not found in DB. Cannot schedule subtasks.")
            return

        dag_representation = workflow_data.get('current_dag_representation')
        if not dag_representation:
            logger.warning(f"Workflow {workflow_uuid} has no DAG representation in DB. Cannot schedule subtasks.")
            return

        try:
            plan = Plan(**dag_representation)
        except Exception as e:
            logger.error(f"Failed to load Plan object from DB representation for workflow {workflow_uuid}: {e}", exc_info=True)
            return

        ready_subtasks = plan.get_ready_subtasks()

        if not ready_subtasks and plan.are_all_subtasks_completed():
            logger.info(f"All subtasks completed for workflow {workflow_uuid}. Marking workflow as COMPLETED.")
            await self.checkpointer.update_workflow_status(workflow_uuid, "COMPLETED", plan.model_dump(mode='json'))
            # TODO: Publicar WorkflowCompletedEvent
            return

        for subtask in ready_subtasks:
            if subtask.status == "READY":
                logger.info(f"Scheduling subtask {subtask.id} ('{subtask.name}') for workflow {workflow_uuid}")
                db_update_success = await self.checkpointer.update_subtask(
                    workflow_id=workflow_uuid,
                    subtask_id=subtask.id,
                    status="RUNNING",
                    agent_name=subtask.agent_name
                )
                if not db_update_success:
                    logger.error(f"Failed to update subtask {subtask.id} to RUNNING in DB for workflow {workflow_uuid}. Skipping scheduling.")
                    continue

                action_event = AgentActionScheduledEvent(
                    source="WorkflowOrchestrator",
                    task_id=str(workflow_uuid),
                    subtask_id=subtask.id,
                    agent_name=subtask.agent_name or "Manus",
                    action_details={
                        "prompt": f"Execute subtask: {subtask.name}",
                        "tool_calls_spec": subtask.tool_calls_spec,
                        "plan_context": plan.model_dump(mode='json')
                    }
                )
                stream_for_agent = f"agent_actions_{subtask.agent_name or 'Manus'}"
                await self.event_bus.publish(stream_for_agent, action_event.model_dump(mode='json'))

        if not ready_subtasks and not plan.are_all_subtasks_completed():
            logger.info(f"No subtasks are currently ready for workflow {workflow_uuid}, but not all are completed. Workflow may be waiting or blocked.")

    async def handle_subtask_completed_event(self, event: SubtaskCompletedEvent, event_id_str: str, stream_name: str, group_name: str, consumer_name: str):
        logger.info(f"Orchestrator: Handling SubtaskCompletedEvent for subtask: {event.subtask_id} in workflow: {event.task_id}")
        workflow_uuid = UUID(event.task_id)

        await self.checkpointer.update_subtask(
            workflow_id=workflow_uuid,
            subtask_id=event.subtask_id,
            status="COMPLETED",
            result=event.result
        )
        await self.schedule_ready_subtasks(workflow_uuid)

    async def handle_subtask_failed_event(self, event: SubtaskFailedEvent, event_id_str: str, stream_name: str, group_name: str, consumer_name: str):
        logger.error(f"Orchestrator: Handling SubtaskFailedEvent for subtask: {event.subtask_id} in workflow: {event.task_id}. Error: {event.error_message}")
        workflow_uuid = UUID(event.task_id)

        await self.checkpointer.update_subtask(
            workflow_id=workflow_uuid,
            subtask_id=event.subtask_id,
            status="FAILED",
            error_message=event.error_message,
            result=event.details
        )

        logger.info(f"Marking workflow {workflow_uuid} as FAILED due to subtask {event.subtask_id} failure.")
        await self.checkpointer.update_workflow_status(workflow_uuid, "FAILED")
        # TODO: Publicar WorkflowFailedEvent

    async def handle_human_input_provided_event(self, event_data: dict, event_id_str: str, stream_name: str, group_name: str, consumer_name: str):
        # Primeiro, parsear o event_data para HumanInputProvidedEvent Pydantic model
        try:
            event = HumanInputProvidedEvent(**event_data)
        except Exception as e_parse:
            logger.error(f"Orchestrator: Failed to parse HumanInputProvidedEvent data: {event_data}. Error: {e_parse}")
            return

        logger.info(f"Orchestrator: Handling HumanInputProvidedEvent for subtask: {event.subtask_id} in workflow: {event.task_id}. Response: '{str(event.user_response)[:100]}...'")
        workflow_uuid = UUID(event.task_id)
        subtask_id_str = event.subtask_id

        subtask_updated = await self.checkpointer.update_subtask(
            workflow_id=workflow_uuid,
            subtask_id=subtask_id_str,
            status="PENDING"
        )
        if not subtask_updated:
            logger.error(f"Failed to update subtask {subtask_id_str} status after human input for workflow {workflow_uuid}.")
            return

        correlation_info = event.responder_info or {}
        # O HumanInputRequiredEvent original tinha um campo relevant_checkpoint_id.
        # O AskHuman o passou para o evento. O NotificationManager o colocou em responder_info.
        relevant_checkpoint_id_str = correlation_info.get("relevant_checkpoint_id")
        if not relevant_checkpoint_id_str and event_data.get("relevant_checkpoint_id"): # Fallback se estiver direto no event_data
             relevant_checkpoint_id_str = event_data.get("relevant_checkpoint_id")


        if relevant_checkpoint_id_str:
            logger.info(f"Relevant checkpoint ID {relevant_checkpoint_id_str} found for human input on subtask {subtask_id_str}.")
        else:
            logger.warning(f"No relevant_checkpoint_id found in HumanInputProvidedEvent for subtask {subtask_id_str}. Agent will resume with current state + user response in memory.")

        workflow_data = await self.checkpointer.get_workflow_with_subtasks(workflow_uuid)
        subtask_to_reschedule = None
        plan_for_context = None

        if workflow_data and workflow_data.get('current_dag_representation'):
            try:
                plan = Plan(**workflow_data['current_dag_representation'])
                plan_for_context = plan.model_dump(mode='json')
                subtask_to_reschedule = plan.get_subtask(subtask_id_str)
            except Exception as e:
                logger.error(f"Failed to load Plan object to find subtask {subtask_id_str} for rescheduling: {e}")

        if subtask_to_reschedule:
            logger.info(f"Re-scheduling subtask {subtask_id_str} ('{subtask_to_reschedule.name}') after human input for workflow {workflow_uuid}.")

            await self.checkpointer.update_subtask(
                workflow_id=workflow_uuid,
                subtask_id=subtask_id_str,
                status="RUNNING",
                agent_name=subtask_to_reschedule.agent_name
            )

            action_event = AgentActionScheduledEvent(
                source="WorkflowOrchestrator:HumanInputResume",
                task_id=str(workflow_uuid),
                subtask_id=subtask_id_str,
                agent_name=subtask_to_reschedule.agent_name or "Manus",
                action_details={
                    "prompt": f"Continue subtask: {subtask_to_reschedule.name}. Human input provided: '{event.user_response}'",
                    "tool_calls_spec": subtask_to_reschedule.tool_calls_spec,
                    "plan_context": plan_for_context,
                    "human_response": str(event.user_response),
                    "resuming_from_checkpoint_id": relevant_checkpoint_id_str
                }
            )
            stream_for_agent = f"agent_actions_{subtask_to_reschedule.agent_name or 'Manus'}"
            await self.event_bus.publish(stream_for_agent, action_event.model_dump(mode='json'))
        else:
            logger.warning(f"Could not find subtask {subtask_id_str} to reschedule after human input for workflow {workflow_uuid}. Will attempt general rescheduling.")
            await self.schedule_ready_subtasks(workflow_uuid)


    async def start(self):
        logger.info("WorkflowOrchestrator starting...")
        if not self.event_bus.redis_client or not self.event_bus.redis_client.is_connected:
            await self.event_bus.connect()

        await self.event_bus.subscribe(
            stream_name="task_creation_events",
            group_name="orchestrator_group",
            consumer_name="orchestrator_main",
            callback=self.handle_task_created_event
        )
        await self.event_bus.subscribe(
            stream_name="subtask_completion_events",
            group_name="orchestrator_group",
            consumer_name="orchestrator_main",
            callback=self.handle_subtask_completed_event
        )
        await self.event_bus.subscribe(
            stream_name="subtask_failure_events",
            group_name="orchestrator_group",
            consumer_name="orchestrator_main",
            callback=self.handle_subtask_failed_event
        )
        await self.event_bus.subscribe(
            stream_name="human_responses_events",
            group_name="orchestrator_group",
            consumer_name="orchestrator_main", # Usando o mesmo consumer para simplificar
            callback=self.handle_human_input_provided_event
        )

        logger.info("WorkflowOrchestrator started and subscribed to relevant events.")

    async def shutdown(self):
        logger.info("WorkflowOrchestrator shutting down...")
        # O shutdown do event_bus é geralmente tratado externamente
        logger.info("WorkflowOrchestrator shutdown complete.")

    async def trigger_rollback(self, workflow_id: UUID, checkpoint_id: UUID, new_directive: Optional[str] = None) -> bool:
        """
        Triggers a rollback to a specific checkpoint for a workflow.
        """
        logger.info(f"Orchestrator: Initiating rollback for workflow {workflow_id} to checkpoint {checkpoint_id}.")

        checkpoint_data = await self.checkpointer.load_checkpoint_data(checkpoint_id)
        if not checkpoint_data:
            logger.error(f"Rollback failed: Checkpoint {checkpoint_id} not found.")
            return False

        if str(checkpoint_data.get("workflow_id")) != str(workflow_id):
            logger.error(f"Rollback failed: Checkpoint {checkpoint_id} (wf: {checkpoint_data.get('workflow_id')}) does not belong to workflow {workflow_id}.")
            return False

        checkpoint_created_at = checkpoint_data.get("created_at")
        if not checkpoint_created_at:
             logger.error(f"Rollback failed: Checkpoint {checkpoint_id} for workflow {workflow_id} is missing 'created_at' timestamp.")
             return False

        invalidated = await self.checkpointer.invalidate_subsequent_work(workflow_id, checkpoint_created_at)
        if not invalidated:
            logger.error(f"Rollback failed: Could not invalidate subsequent work for workflow {workflow_id} using checkpoint {checkpoint_id} timestamp ({checkpoint_created_at}).")
            return False

        restored_dag_representation_json = checkpoint_data.get("planning_flow_snapshot")

        if restored_dag_representation_json is None:
            logger.warning(f"Checkpoint {checkpoint_id} for workflow {workflow_id} does not contain 'planning_flow_snapshot' (DAG). Attempting to use current DAG from DB.")
            current_workflow_data = await self.checkpointer.get_workflow_with_subtasks(workflow_id)
            if current_workflow_data and current_workflow_data.get('current_dag_representation'):
                restored_dag_representation_json = current_workflow_data['current_dag_representation']
                logger.info(f"DAG for workflow {workflow_id} taken from current DB record as it was not in checkpoint {checkpoint_id}.")
            else:
                logger.error(f"Critical error: No DAG found in checkpoint {checkpoint_id} nor in current workflow record for {workflow_id}. Cannot proceed with rollback logic.")
                return False

        new_workflow_status_after_rollback = "PENDING"

        status_updated = await self.checkpointer.update_workflow_status(
            workflow_id,
            new_workflow_status_after_rollback,
            dag_representation=restored_dag_representation_json
        )
        if not status_updated:
            logger.error(f"Rollback failed: Could not update workflow {workflow_id} status/DAG after invalidation and loading checkpoint {checkpoint_id}.")
            return False

        logger.info(f"Workflow {workflow_id} state (status and DAG) restored from checkpoint {checkpoint_id} or current DB state.")

        if new_directive:
            logger.info(f"New directive provided for workflow {workflow_id} after rollback: '{new_directive}'. This may need to be passed to the agent or planning mechanism.")
            # A lógica de aplicar a nova diretiva pode ser injetar uma mensagem no histórico do agente
            # ou modificar o DAG. Por enquanto, apenas logamos.
            # Se fosse para a memória do agente, o evento AgentActionScheduledEvent precisaria carregar isso.
            # Ex: Adicionar ao `action_details` do primeiro AgentActionScheduledEvent após rollback.
            # No entanto, o orchestrator não tem acesso direto à memória do agente.
            # Uma melhoria seria o `WorkflowOrchestrator` publicar um `NewDirectiveAvailableEvent`
            # que um agente de planejamento ou o agente principal da subtarefa possa consumir.
            # Por agora, a diretiva não é automaticamente aplicada ao estado do agente.
            pass

        logger.info(f"Re-scheduling subtasks for workflow {workflow_id} after rollback to checkpoint {checkpoint_id}.")
        await self.schedule_ready_subtasks(workflow_id)

        logger.info(f"Rollback to checkpoint {checkpoint_id} for workflow {workflow_id} initiated successfully.")
        return True

# Example usage (for standalone testing or integration)
# async def run_orchestrator_example():
#     from app.config import config
#     # Ensure config is loaded and set up (e.g., mock for testing if needed)
#     # ... (setup mock config if necessary) ...
#
#     event_bus = RedisEventBus()
#     await event_bus.connect()
#
#     checkpointer = PostgreSQLCheckpointer()
#     # Ensure DB is initialized if running standalone:
#     # from app.database.base import init_db
#     # await init_db()
#
#     orchestrator = WorkflowOrchestrator(event_bus, checkpointer)
#     await orchestrator.start()
#     event_bus.start_consuming()
#
#     try:
#         # Simulate publishing a TaskCreatedEvent
#         from app.event_bus.events import TaskInfo
#         import uuid
#         example_task_id = str(uuid.uuid4())
#         test_event = TaskCreatedEvent(
#             source="TestScript",
#             task_info=TaskInfo(task_id=example_task_id),
#             user_prompt="Process data and generate report.",
#             initial_plan={
#                 "plan_id": f"plan_orch_test_{example_task_id}",
#                 "title": "Data Processing Plan",
#                 "subtasks": {
#                     "st1": {"id": "st1", "name": "Load data", "depends_on": []},
#                     "st2": {"id": "st2", "name": "Process data", "depends_on": ["st1"]},
#                     "st3": {"id": "st3", "name": "Generate report", "depends_on": ["st2"]}
#                 }
#             }
#         )
#         await event_bus.publish("task_creation_events", test_event.model_dump(mode='json'))
#         logger.info(f"Published TaskCreatedEvent for workflow {example_task_id}")
#
#         # Keep alive for a bit to process events
#         await asyncio.sleep(30)
#
#     except KeyboardInterrupt:
#         logger.info("Orchestrator example interrupted by user.")
#     finally:
#         logger.info("Shutting down orchestrator example...")
#         await orchestrator.shutdown()
#         await event_bus.shutdown()
#
# if __name__ == "__main__":
#     import logging
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
#     # asyncio.run(run_orchestrator_example())
#     logger.info("Standalone orchestrator example finished (or commented out).")
