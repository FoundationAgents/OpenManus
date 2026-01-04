"""
FreEco.AI GUI Server - FastAPI backend with Minimax M2 integration.
"""

from datetime import datetime
from pathlib import Path

import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.features.agent import FreEcoAgent
from app.features.knowledge_base import KnowledgeBaseManager
from app.features.settings import SettingsManager
from app.features.tasks import TaskManager


# ===== MINIMAX M2 API CONFIG =====
# Using OpenAI-compatible API endpoint (https://api.minimax.io/v1)
MINIMAX_API_KEY = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiJGcmVlIEVjbyAoZnJlLmVjbykiLCJVc2VyTmFtZSI6IkZyZWUgRWNvIChmcmUuZWNvKSIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxOTg2NzY0NjA1NDYzOTk0OTEzIiwiUGhvbmUiOiIiLCJHcm91cElEIjoiMTk4Njc2NDYwNTQ1OTc5NjUxMyIsIlBhZ2VOYW1lIjoiIiwiTWFpbCI6ImZyZWVjby5jaEBnbWFpbC5jb20iLCJDcmVhdGVUaW1lIjoiMjAyNS0xMS0wNyAyMzowMzozNyIsIlRva2VuVHlwZSI6MSwiaXNzIjoibWluaW1heCJ9.PgIBGBmudjF2qPmTKPgzr_yEfibgsF26iPPWN2JIA3-MBm-KqiDmsHL0u-EkB1CCbEY2ioib24mul1okxyVPkJoODY0Cp3CaVrYFGzQXkD9VH_M0x8dTChDsZxM4NyHzkEYz5K169OlhQ1j9boW7EwAQ1z4meDJNYKhnxUGOjsSdo__AKcrOJA2Gq65a4hshLsOy7Tt2iztBNZ0zESpW7dgtr0_2VGV4Qav6uLyVQi0ZawiUsIEXwLmSJlbNpKaMIpZa7FxyxTQTZfu0x9-qLgGTDV8qAfpwmKBttNo75JL0VhdFLIzal9mhs-2ob4rcBC2YggV_l8w8a3YF6xMJ6A"
MINIMAX_MODEL = "MiniMax-M2"
MINIMAX_API_URL = "https://api.minimax.io/v1/chat/completions"

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

    api_key: str
    model: str
    temperature: float
    max_tokens: int


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str


# ===== FASTAPI APP =====

app = FastAPI(title="FreEco.AI GUI Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
task_manager = TaskManager()
kb_manager = KnowledgeBaseManager()
settings_manager = SettingsManager()
agent = FreEcoAgent()

# ===== STATIC FILES =====

gui_path = Path(__file__).parent / "gui"
if gui_path.exists():
    app.mount("/static", StaticFiles(directory=gui_path), name="static")


# ===== ROOT ROUTE =====


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the GUI HTML file."""
    html_file = Path(__file__).parent / "gui" / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return "<h1>FreEco.AI GUI</h1>"


@app.get("/style.css")
async def get_css():
    """Serve CSS file."""
    css_file = Path(__file__).parent / "gui" / "style.css"
    if css_file.exists():
        return FileResponse(css_file, media_type="text/css")
    return ""


@app.get("/app.js")
async def get_js():
    """Serve JavaScript file."""
    js_file = Path(__file__).parent / "gui" / "app.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    return ""


# ===== HEALTH CHECK =====


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "agent_initialized": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ===== CHAT WITH MINIMAX M2 =====


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint using Minimax M2 API (OpenAI-compatible)."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": MINIMAX_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful ecological AI assistant.",
                    },
                    {"role": "user", "content": request.message},
                ],
                "temperature": 0.7,
                "max_tokens": 1024,
            }

            async with session.post(
                MINIMAX_API_URL, headers=headers, json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # OpenAI-compatible response format
                    if "choices" in data and len(data["choices"]) > 0:
                        response_text = data["choices"][0]["message"]["content"]
                        return {"response": response_text}
                    else:
                        return {"response": "No response from Minimax"}
                else:
                    error_text = await resp.text()
                    return {"response": f"API Error: {resp.status} - {error_text}"}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}


# ===== TASKS =====


@app.post("/api/tasks")
async def create_task(task: TaskCreate):
    """Create a new task."""
    try:
        task_id = task_manager.create_task(task.title, task.description, task.priority)
        return {"id": task_id, "message": "Task created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks")
async def list_tasks():
    """List all tasks."""
    try:
        tasks = task_manager.list_tasks()
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, update: TaskUpdate):
    """Update task status."""
    try:
        task_manager.update_task(task_id, update.status)
        return {"message": "Task updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    try:
        task_manager.delete_task(task_id)
        return {"message": "Task deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== KNOWLEDGE BASE =====


@app.post("/api/documents")
async def create_document(doc: DocumentCreate):
    """Create a new document."""
    try:
        doc_id = kb_manager.add_document(doc.title, doc.content, doc.category)
        return {"id": doc_id, "message": "Document created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def list_documents():
    """List all documents."""
    try:
        docs = kb_manager.list_documents()
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/search")
async def search_documents(q: str):
    """Search documents."""
    try:
        results = kb_manager.search(q)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document."""
    try:
        kb_manager.delete_document(doc_id)
        return {"message": "Document deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== SETTINGS =====


@app.get("/api/settings")
async def get_settings():
    """Get settings."""
    try:
        settings = settings_manager.get_settings()
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings")
async def save_settings(settings: SettingsUpdate):
    """Save settings."""
    try:
        settings_manager.save_settings(
            settings.api_key,
            settings.model,
            settings.temperature,
            settings.max_tokens,
        )
        return {"message": "Settings saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== AGENT FEATURES =====


@app.get("/api/agent/status")
async def agent_status():
    """Get agent status."""
    return {
        "status": "ready",
        "agent_type": "FreEco.AI",
        "features": [
            "ethics",
            "security",
            "stability",
            "performance",
            "ux",
            "evaluation",
            "testing",
        ],
    }


@app.post("/api/agent/execute")
async def execute_agent(request: ChatRequest):
    """Execute agent with function calling."""
    try:
        result = await agent.execute_with_tools(request.message)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
