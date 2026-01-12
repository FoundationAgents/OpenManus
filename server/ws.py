import asyncio
import json
import queue
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from core.task_registry import TaskRegistry

# Reuse registry from REST API if available; fallback to a local registry.
try:  # pragma: no cover - optional import
    from server.api import registry as api_registry

    registry = api_registry
except Exception:  # pragma: no cover - fallback
    registry = TaskRegistry()

app = FastAPI(title="OpenManus Task WS")


async def _get_event(task_queue: Any):
    """Await an event from either asyncio.Queue or queue.Queue."""
    if isinstance(task_queue, asyncio.Queue):
        return await task_queue.get()
    if isinstance(task_queue, queue.Queue):
        return await asyncio.to_thread(task_queue.get)
    return None


@app.websocket("/tasks/{task_id}/stream")
async def task_stream(websocket: WebSocket, task_id: str):
    await websocket.accept()
    task = registry.get_task(task_id)
    if not task:
        await websocket.send_text(json.dumps({"error": "Task not found"}))
        await websocket.close()
        return

    event_queue = task.event_queue

    try:
        while True:
            recv_task = asyncio.create_task(websocket.receive_text())
            event_task = asyncio.create_task(_get_event(event_queue))

            done, pending = await asyncio.wait(
                {recv_task, event_task}, return_when=asyncio.FIRST_COMPLETED
            )

            for p in pending:
                p.cancel()

            if recv_task in done:
                try:
                    message = recv_task.result()
                except WebSocketDisconnect:
                    return
                except Exception:
                    message = ""

                if isinstance(message, str):
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        data = {"command": message}
                    command = data.get("command")
                    if command == "interrupt":
                        registry.interrupt_task(task_id)
                        await websocket.send_text(
                            json.dumps({"type": "interrupt_ack", "id": task_id})
                        )

            if event_task in done:
                try:
                    event = event_task.result()
                except Exception:
                    event = None

                if event is None:
                    continue

                payload = event if isinstance(event, dict) else {"event": event}
                await websocket.send_text(json.dumps(payload))

    except WebSocketDisconnect:
        return


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
