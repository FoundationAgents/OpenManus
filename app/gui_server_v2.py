"""FreEco.AI GUI Server v2 - With Static File Serving

FastAPI backend for the Manus-style GUI interface with proper static file serving.
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app.features.agent import FreEcoAgent
from app.features.knowledge_base import KnowledgeBaseManager
from app.features.settings import SettingsManager
from app.features.tasks import TaskManager


# ===== PYDANTIC MODELS =====


class TaskCreate(BaseModel):
    """Task creation model."""

    title: str
    description: str
    priority: str = "medium"


class TaskUpdate(BaseModel):
    """Task update model."""

    status: str


class DocumentCreate(BaseModel):
    """Document creation model."""

    title: str
    content: str
    category: str = "general"


class SettingsUpdate(BaseModel):
    """Settings update model."""

    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatMessage(BaseModel):
    """Chat message model."""

    message: str


# ===== FASTAPI APP =====

app = FastAPI(title="FreEco.AI GUI Server", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
tasks_manager = TaskManager()
settings_manager = SettingsManager()
kb_manager = KnowledgeBaseManager()
agent: Optional[FreEcoAgent] = None

# Get GUI directory
GUI_DIR = Path(__file__).parent / "gui"


# ===== INITIALIZATION =====


@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup."""
    global agent
    try:
        agent = FreEcoAgent()
        print("✅ FreEco Agent initialized")
    except Exception as e:
        print(f"⚠️  Agent initialization failed: {str(e)}")


# ===== STATIC FILES & ROOT =====


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main GUI HTML file."""
    html_file = GUI_DIR / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse(
        "<h1>FreEco.AI GUI</h1><p>GUI files not found. Please check installation.</p>"
    )


@app.get("/style.css")
async def serve_css():
    """Serve CSS file."""
    css_file = GUI_DIR / "style.css"
    if css_file.exists():
        return FileResponse(css_file, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS file not found")


@app.get("/app.js")
async def serve_js():
    """Serve JavaScript file."""
    js_file = GUI_DIR / "app.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JS file not found")


# ===== HEALTH CHECK =====


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "agent_initialized": agent is not None,
    }


# ===== TASKS ENDPOINTS =====


@app.post("/api/tasks")
async def create_task(task: TaskCreate):
    """Create a new task."""
    import uuid

    task_id = str(uuid.uuid4())[:8]
    created_task = tasks_manager.create_task(
        task_id, task.title, task.description, task.priority
    )
    return {
        "id": created_task.id,
        "title": created_task.title,
        "description": created_task.description,
        "priority": created_task.priority.value,
        "status": created_task.status.value,
        "created_at": created_task.created_at.isoformat(),
    }


@app.get("/api/tasks")
async def list_tasks(status: Optional[str] = None, priority: Optional[str] = None):
    """List all tasks."""
    tasks = tasks_manager.list_tasks(status=status, priority=priority)
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority.value,
            "status": t.status.value,
            "created_at": t.created_at.isoformat(),
        }
        for t in tasks
    ]


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, update: TaskUpdate):
    """Update task status."""
    task = tasks_manager.update_task(task_id, status=update.status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value,
        "updated_at": task.updated_at.isoformat(),
    }


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    if not tasks_manager.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}


@app.get("/api/tasks/stats")
async def get_task_stats():
    """Get task statistics."""
    return tasks_manager.get_statistics()


# ===== KNOWLEDGE BASE ENDPOINTS =====


@app.post("/api/documents")
async def add_document(doc: DocumentCreate):
    """Add document to knowledge base."""
    import uuid

    doc_id = str(uuid.uuid4())[:8]
    created_doc = kb_manager.add_document(doc_id, doc.title, doc.content, doc.category)
    return {
        "id": created_doc.id,
        "title": created_doc.title,
        "category": created_doc.category.value,
        "size": created_doc.size,
        "created_at": created_doc.created_at.isoformat(),
    }


@app.get("/api/documents")
async def list_documents(category: Optional[str] = None):
    """List documents."""
    docs = kb_manager.list_documents(category=category)
    return [
        {
            "id": d.id,
            "title": d.title,
            "category": d.category.value,
            "size": d.size,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@app.get("/api/documents/search")
async def search_documents(q: str):
    """Search documents."""
    results = kb_manager.search_documents(q)
    return [
        {
            "id": d.id,
            "title": d.title,
            "category": d.category.value,
            "size": d.size,
        }
        for d in results
    ]


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete document."""
    if not kb_manager.delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True}


@app.get("/api/documents/stats")
async def get_kb_stats():
    """Get knowledge base statistics."""
    return kb_manager.get_statistics()


# ===== SETTINGS ENDPOINTS =====


@app.get("/api/settings")
async def get_settings():
    """Get current settings."""
    settings = settings_manager.get_settings()
    return {
        "theme": settings.theme.mode,
        "minimax": {
            "model": settings.minimax.model,
            "temperature": settings.minimax.temperature,
            "max_tokens": settings.minimax.max_tokens,
        },
        "auto_save": settings.auto_save,
        "debug_mode": settings.debug_mode,
    }


@app.put("/api/settings")
async def update_settings(settings: SettingsUpdate):
    """Update settings."""
    config = settings_manager.update_minimax_config(
        api_key=settings.api_key,
        model=settings.model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )
    return {
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }


@app.post("/api/settings/test-minimax")
async def test_minimax_connection():
    """Test Minimax connection."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        is_connected = await agent.caller.caller.test_connection()
        return {"connected": is_connected}
    except Exception as e:
        return {"connected": False, "error": str(e)}


# ===== AGENT CHAT ENDPOINTS =====


@app.post("/api/chat")
async def chat(msg: ChatMessage):
    """Chat with agent."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        response = await agent.run(msg.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket chat endpoint for streaming."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            if not agent:
                await websocket.send_text("Error: Agent not initialized")
                continue

            try:
                response = await agent.run(data)
                await websocket.send_text(response)
            except Exception as e:
                await websocket.send_text(f"Error: {str(e)}")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
