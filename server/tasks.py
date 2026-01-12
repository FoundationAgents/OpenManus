import asyncio
from typing import Optional

from app.agent.manus import Manus
from core.task import TaskStatus
from core.task_registry import TaskRegistry
from server.celery_app import celery_app


registry = TaskRegistry()


@celery_app.task(name="run_task")
def run_task(task_id: str, prompt: Optional[str] = None):
    """Celery task wrapper to execute Manus agent and persist status/result."""
    task = registry.get_task(task_id)
    if task is None:
        return {"error": "task not found"}

    async def _run():
        agent = await Manus.create()
        result = await agent.run(task, prompt)
        return result

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run())
        task.status = "COMPLETED"
        registry.update_task(task, result={"output": result})
        return {"status": "COMPLETED", "result": result}
    except Exception as exc:  # pragma: no cover
        task.status = TaskStatus.FAILED
        registry.update_task(task, result={"error": str(exc)})
        return {"status": "FAILED", "error": str(exc)}
    finally:
        try:
            loop.close()
        except Exception:
            pass
