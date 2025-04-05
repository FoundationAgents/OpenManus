# api_server.py - Standalone FastAPI server for OpenAI compatible API

import uvicorn
import asyncio
import time
import uuid
from typing import List, Optional, Union, Dict, Literal, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Assuming app structure is accessible
from app.agent.manus import Manus
from app.logger import logger
from app.schema import AgentState, Message as AgentMessage, Memory
from pathlib import Path # Import Path

# --- Constants ---
# Assuming HISTORY_DIR might be needed if session management is added later
HISTORY_DIR = Path("chatsHistory") # Define even if not used directly here, for consistency maybe?

# --- OpenAI Compatible Models ---
class ChatMessage(BaseModel): role: Literal["system", "user", "assistant", "tool"]; content: Optional[str] = None
class ChatCompletionRequest(BaseModel): model: str; messages: List[ChatMessage]; stream: Optional[bool] = False
class ChoiceDelta(BaseModel): role: Optional[Literal["assistant"]] = None; content: Optional[str] = None
class ChatCompletionChunkChoice(BaseModel): index: int = 0; delta: ChoiceDelta; finish_reason: Optional[Literal["stop", "length", "tool_calls", "error"]] = None
class ChatCompletionChunk(BaseModel): id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}"); object: str = "chat.completion.chunk"; created: int = Field(default_factory=lambda: int(time.time())); model: str; choices: List[ChatCompletionChunkChoice]
class ChatCompletionChoice(BaseModel): index: int = 0; message: ChatMessage; finish_reason: Optional[Literal["stop", "length", "tool_calls", "error"]] = None
class Usage(BaseModel): prompt_tokens: Optional[int] = None; completion_tokens: Optional[int] = None; total_tokens: Optional[int] = None
class ChatCompletionResponse(BaseModel): id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}"); object: str = "chat.completion"; created: int = Field(default_factory=lambda: int(time.time())); model: str; choices: List[ChatCompletionChoice]; usage: Optional[Usage] = None

# --- FastAPI App ---
app = FastAPI(title="OpenManus OpenAI Compatible API")

# --- Agent Initialization for API Server ---
api_agent_instance: Optional[Manus] = None
api_agent_initialized = False
api_agent_lock = asyncio.Lock() # Lock specific to the API server's agent

async def initialize_api_agent():
    """Initializes the Manus agent instance specifically for the API server."""
    global api_agent_instance, api_agent_initialized
    # No lock needed here as it's called once before server starts in __main__
    if not api_agent_initialized:
        logger.info("Initializing Manus agent for API server...")
        try:
            api_agent_instance = Manus()
            api_agent_instance.state = AgentState.IDLE
            api_agent_initialized = True
            logger.info("Manus agent initialized for API server.")
        except Exception as e:
             logger.error(f"API Server: Failed to initialize Manus agent: {e}", exc_info=True)
             api_agent_initialized = False
             api_agent_instance = None
             # Exit if agent fails to initialize during startup
             print(f"\nFATAL: Failed to initialize Manus agent for API server: {e}\n")
             exit(1)

    if not api_agent_instance:
         # This should ideally not be reached if init logic is correct
         print("\nFATAL: API Agent instance is None after initialization attempt.\n")
         exit(1)
    return api_agent_instance

# --- API Endpoint ---
@app.post("/v1/chat/completions", tags=["Chat"])
async def chat_completions_api(request: ChatCompletionRequest):
    """OpenAI-compatible Chat Completion endpoint (Stateless)."""
    agent = await initialize_api_agent() # Ensure agent is ready

    async with api_agent_lock: # Lock for this request
        # Reset agent state and memory for this API request
        agent.memory.messages = []
        agent.state = AgentState.IDLE
        agent.current_step = 0

        # Map messages
        for msg in request.messages:
            agent_msg = AgentMessage(role=msg.role, content=msg.content or "")
            agent.memory.add_message(agent_msg)

        logger.info(f"API: Processing request for model '{request.model}'. Stream: {request.stream}")
        last_user_message = agent.memory.messages[-1].content if agent.memory.messages and agent.memory.messages[-1].role == "user" else ""
        request_id = f"chatcmpl-{uuid.uuid4().hex}"

        # Streaming Response
        if request.stream:
            async def stream_generator():
                previous_content = ""; final_finish_reason = "stop"; chunk_model_name = request.model; yielded_initial = False
                try:
                    async for update in agent.run(request=last_user_message):
                        delta_content = update[len(previous_content):]; previous_content = update
                        delta = ChoiceDelta()
                        if not yielded_initial and delta_content: delta.role = "assistant"; yielded_initial = True
                        if delta_content:
                            delta.content = delta_content
                            chunk = ChatCompletionChunk(id=request_id, model=chunk_model_name, choices=[ChatCompletionChunkChoice(delta=delta)])
                            yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"; await asyncio.sleep(0.01)
                    if agent.state == AgentState.ERROR: final_finish_reason = "error"
                    elif agent.current_step >= agent.max_steps: final_finish_reason = "length"
                except Exception as e: logger.error(f"API Stream Error: {e}", exc_info=True); final_finish_reason = "error"
                finally:
                    final_chunk = ChatCompletionChunk(id=request_id, model=chunk_model_name, choices=[ChatCompletionChunkChoice(delta=ChoiceDelta(), finish_reason=final_finish_reason)])
                    yield f"data: {final_chunk.model_dump_json(exclude_none=True)}\n\n"; yield "data: [DONE]\n\n"
                    logger.info(f"API Stream finished for {request_id} with reason: {final_finish_reason}")
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        # Non-Streaming Response
        else:
            final_response_content = ""; final_finish_reason = "stop"
            try:
                async for update in agent.run(request=last_user_message): final_response_content = update
                if agent.state == AgentState.ERROR: final_finish_reason = "error"
                elif agent.current_step >= agent.max_steps: final_finish_reason = "length"
            except Exception as e: logger.error(f"API Non-Stream Error: {e}", exc_info=True); raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
            response = ChatCompletionResponse(id=request_id, model=request.model, choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content=final_response_content), finish_reason=final_finish_reason)])
            logger.info(f"API Non-Stream request {request_id} completed with reason: {final_finish_reason}")
            return response

# --- Main execution ---
if __name__ == "__main__":
    API_HOST = "0.0.0.0" # Listen on all interfaces for API server
    API_PORT = 8000     # Use standard port 8000 for API

    # Initialize agent once before starting server
    try:
        asyncio.run(initialize_api_agent())
    except SystemExit:
         exit(1)
    except Exception as e:
         print(f"\nFATAL: Unexpected error during API agent initialization: {e}\n")
         exit(1)

    logger.info(f"Starting OpenAI compatible API server on http://{API_HOST}:{API_PORT}")
    logger.info(f"API Docs available at http://{API_HOST}:{API_PORT}/docs")
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")
