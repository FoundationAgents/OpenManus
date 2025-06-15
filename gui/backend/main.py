from fastapi import FastAPI, Request, Depends, HTTPException # Added HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from pydantic import BaseModel # Added BaseModel
import uvicorn
import asyncio
import json
from typing import List, Optional # Added Optional

from sqlalchemy import select, func # Added func

from gui.backend.log_streamer import get_log_queue
from gui.backend.database import create_db_and_tables, get_db, LogEntry, AsyncSession
# Import agent_manager components
from gui.backend import agent_manager # Import the module
from app.logger import logger # For logging errors in API endpoints

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()
    # Optionally initialize other resources if needed
    logger.info("Application startup complete. Database tables created.")

@app.get("/api/logs/executions")
async def get_log_executions(db: AsyncSession = Depends(get_db)):
    statement = (
        select(LogEntry.execution_id, func.min(LogEntry.timestamp).label("start_time"))
        .where(LogEntry.execution_id.isnot(None))
        .group_by(LogEntry.execution_id)
        .order_by(func.min(LogEntry.timestamp).desc())
    )
    results = await db.execute(statement)
    executions = results.all() # Fetches list of Row objects
    return [
        {"execution_id": exec_row.execution_id, "start_time": exec_row.start_time.isoformat()}
        for exec_row in executions
    ]

@app.get("/api/logs/stream")
async def read_log_stream(request: Request):
    log_queue = get_log_queue()
    async def event_generator():
        while True:
            try:
                # Wait for a new log message
                log_entry = await log_queue.get()
                # Check if client is still connected
                if await request.is_disconnected():
                    # Optional: Put the log back if you want to retry for other clients,
                    # or handle how many logs to buffer if clients disconnect often.
                    # For simplicity, we'll just break here.
                    print("Client disconnected from log stream.")
                    break
                
                yield f"data: {json.dumps(log_entry)}\n\n" # Ensure two newlines for SSE
                log_queue.task_done() # Important for queue management if needed elsewhere
            except asyncio.CancelledError:
                # This happens when the client disconnects
                print("Log stream task cancelled due to client disconnect.")
                break
            except Exception as e:
                # Log other errors if necessary
                print(f"Error in log stream: {e}")
                # Optionally send an error event to client if the connection is still alive
                # yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break # Or continue, depending on desired robustness
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/logs/history", response_model=List[dict]) # response_model already here
async def read_log_history(
    execution_id: str = None, # Optional filter by execution_id
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db) # Use AsyncSession from get_db
):
    statement = select(LogEntry).order_by(LogEntry.timestamp.desc())
    if execution_id:
        statement = statement.where(LogEntry.execution_id == execution_id)
    statement = statement.offset(skip).limit(limit)
    
    results = await db.execute(statement)
    log_entries = results.scalars().all()
    # Convert to dicts for JSON response
    return [
        {
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(), # Ensure datetime is imported in database.py
            "level": entry.level,
            "message": entry.message,
            "logger_name": entry.logger_name,
            "module": entry.module,
            "function": entry.function,
            "line": entry.line,
            "execution_id": entry.execution_id,
        }
        for entry in log_entries
    ]

# --- Agent Interaction Endpoints ---

class AgentRunRequest(BaseModel):
    prompt: str
    agent_type: str = "manus" # or "planning_flow"

@app.post("/api/agent/run")
async def api_run_agent(request: AgentRunRequest): # Use Pydantic model for request body
    try:
        execution_id = await agent_manager.start_new_agent_session(request.prompt, request.agent_type)
        return {"execution_id": execution_id, "message": "Agent session started."}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) # Conflict if already running
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) # Bad request for unknown agent type
    except Exception as e:
        logger.error(f"Error starting agent session from API: {e}")
        raise HTTPException(status_code=500, detail="Failed to start agent session.")

@app.get("/api/agent/status")
async def api_get_agent_status(): # Made async as per instruction
    return agent_manager.get_agent_status()

@app.get("/api/agent/plan")
async def api_get_agent_plan():
    plan = await agent_manager.get_agent_plan()
    if plan is None and agent_manager.current_agent_instance is not None : # Agent exists but not planning flow
         return {"message": "No active plan found or agent is not a planning agent."}
    if plan is None and agent_manager.current_agent_instance is None:
         return {"message": "No agent is currently active."}
    if plan and "error" in plan : # Check plan is not None before "error" in plan
         return JSONResponse(status_code=500, content=plan)
    return plan

class AgentInputRequest(BaseModel):
    user_input: str

@app.post("/api/agent/input")
async def api_provide_agent_input(request: AgentInputRequest):
    success = await agent_manager.provide_input_to_agent(request.user_input)
    if success:
        return {"message": "Input provided to agent."}
    else:
        raise HTTPException(status_code=400, detail="Agent not waiting for input or queue full.")

@app.get("/api/agent/tools")
async def api_get_agent_tools(): # Made async
    return agent_manager.get_available_tools()

@app.get("/api/agent/config")
async def api_get_agent_config(): # Made async
    return agent_manager.get_agent_config()

# --- End Agent Interaction Endpoints ---


@app.get("/", response_class=HTMLResponse)
async def get_test_page():
    return """
    <html>
        <head>
            <title>Log Stream Test</title>
        </head>
        <body>
            <h1>Log Stream</h1>
            <ul id="logs"></ul>
            <script>
                const logsList = document.getElementById('logs');
                const eventSource = new EventSource('/api/logs/stream');

                eventSource.onmessage = function(event) {
                    const logEntry = JSON.parse(event.data);
                    const listItem = document.createElement('li');
                    listItem.textContent = `[${logEntry.time.repr}] [${logEntry.level}] [${logEntry.name}:${logEntry.function}:${logEntry.line}] ${logEntry.text}`;
                    logsList.appendChild(listItem);
                };

                eventSource.onerror = function(err) {
                    console.error("EventSource failed:", err);
                    const listItem = document.createElement('li');
                    listItem.textContent = "Error connecting to log stream. Check console.";
                    logsList.appendChild(listItem);
                    eventSource.close();
                };
            </script>
        </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008)
