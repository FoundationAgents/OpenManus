# app_ui.py - Standalone Gradio UI Server

import gradio as gr
import asyncio
import datetime
import os
import json
import re
import webbrowser
import threading
from pathlib import Path
from typing import Dict, List, Optional

# Assuming app structure is accessible
from app.agent.manus import Manus
from app.logger import logger
from app.schema import AgentState, Message as AgentMessage, Memory

# --- Constants ---
HISTORY_DIR = Path("chatsHistory")
UI_HOST = "127.0.0.1" # Use 127.0.0.1 for local access by default
UI_PORT = 7860
UI_BASE_URL = f"http://{UI_HOST}:{UI_PORT}"

# --- Agent Initialization for UI Server ---
ui_agent_instance: Optional[Manus] = None
ui_agent_initialized = False
# UI might not need a lock if Gradio handles sessions properly,
# but agent execution itself might still benefit from it if agent is complex.
# Let's keep it for now for consistency with previous logic.
ui_agent_lock = asyncio.Lock()

async def initialize_ui_agent():
    """Initializes the Manus agent instance specifically for the UI server."""
    global ui_agent_instance, ui_agent_initialized
    # No lock needed here as it's called once before server starts
    if not ui_agent_initialized:
        logger.info("Initializing Manus agent for UI server...")
        try:
            ui_agent_instance = Manus()
            ui_agent_instance.state = AgentState.IDLE
            ui_agent_initialized = True
            logger.info("Manus agent initialized for UI server.")
        except Exception as e:
             logger.error(f"UI Server: Failed to initialize Manus agent: {e}", exc_info=True)
             print(f"\nFATAL: Failed to initialize Manus agent for UI server: {e}\n")
             exit(1)

    if not ui_agent_instance:
         print("\nFATAL: UI Agent instance is None after initialization attempt.\n")
         exit(1)
    return ui_agent_instance

# --- File Persistence Helper Functions ---
def sanitize_filename(name: str) -> str:
    name = re.sub(r'[^\w\s-]', '', name).strip()
    name = re.sub(r'[\s-]+', '_', name)
    if not name: name = "untitled_chat"
    return name

def save_session_file(session_id: str, messages: List[AgentMessage]):
    try:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        filename = sanitize_filename(session_id) + ".json"
        filepath = HISTORY_DIR / filename
        messages_as_dicts = [msg.model_dump(mode='json') for msg in messages] # Use mode='json' for datetime etc.
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(messages_as_dicts, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved session '{session_id}' to {filepath}")
    except Exception as e: logger.error(f"Error saving session '{session_id}' to file: {e}", exc_info=True); gr.Warning(f"Failed to save session '{session_id}': {e}")

def load_session_data() -> Dict[str, List[AgentMessage]]:
    sessions = {}
    HISTORY_DIR.mkdir(parents=True, exist_ok=True) # Ensure directory exists before reading
    try:
        def sort_key(p: Path):
            name = p.stem
            if name.startswith("Chat ") and len(name.split(" ")) > 1 and name.split(" ")[1].isdigit():
                try: return (0, int(name.split(" ")[1])) # Prioritize "Chat X" numerically
                except ValueError: return (1, name) # Fallback for malformed "Chat X"
            return (1, name) # Sort others alphabetically
        session_files = sorted(HISTORY_DIR.glob("*.json"), key=sort_key)
        for filepath in session_files:
            session_id_from_filename = filepath.stem
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    messages_data_str = f.read()
                    if not messages_data_str.strip(): messages = []
                    else:
                         messages_data = json.loads(messages_data_str)
                         # Use model_validate for each dict in the list
                         messages = [AgentMessage.model_validate(msg_data) for msg_data in messages_data]
                    sessions[session_id_from_filename] = messages
                logger.debug(f"Loaded session '{session_id_from_filename}' from {filepath}")
            except Exception as e: logger.error(f"Error loading session file {filepath}: {e}", exc_info=True)
    except Exception as e: logger.error(f"Error reading history directory '{HISTORY_DIR}': {e}", exc_info=True)
    if not sessions:
        logger.info("No chat history found. Starting with 'Chat 1'.")
        default_session_id = "Chat 1"; sessions[default_session_id] = []; save_session_file(default_session_id, [])
    logger.info(f"Loaded {len(sessions)} sessions.")
    return sessions

def delete_session_file(session_id: str):
    try:
        filename = sanitize_filename(session_id) + ".json"; filepath = HISTORY_DIR / filename
        if filepath.exists(): filepath.unlink(); logger.info(f"Deleted session file: {filepath}")
        else: logger.warning(f"Attempted to delete non-existent session file: {filepath}")
    except Exception as e: logger.error(f"Error deleting session file for '{session_id}': {e}", exc_info=True); gr.Error(f"Failed to delete session file for '{session_id}': {e}")

def rename_session_file(old_session_id: str, new_session_id: str):
    try:
        old_filename = sanitize_filename(old_session_id) + ".json"; new_filename = sanitize_filename(new_session_id) + ".json"
        old_filepath = HISTORY_DIR / old_filename; new_filepath = HISTORY_DIR / new_filename
        if old_filepath.exists():
            if not new_filepath.exists(): old_filepath.rename(new_filepath); logger.info(f"Renamed session file from {old_filename} to {new_filename}")
            else: logger.error(f"Rename failed: Target file '{new_filename}' already exists."); gr.Error(f"Rename failed: File for '{new_session_id}' already exists.")
        else: logger.warning(f"Attempted to rename non-existent session file: {old_filepath}"); gr.Warning(f"Could not find file for '{old_session_id}' to rename.")
    except Exception as e: logger.error(f"Error renaming session file from '{old_session_id}' to '{new_session_id}': {e}", exc_info=True); gr.Error(f"Failed to rename session file for '{old_session_id}': {e}")


# --- UI Helper Function ---
def format_history_for_chatbot(messages: list[AgentMessage]) -> list[list[str | None]]:
    chatbot_history = []; user_msg_content = None; assistant_msg_parts = []
    for msg in messages:
        if msg.role == "user":
            if assistant_msg_parts:
                 if user_msg_content is not None: chatbot_history.append([user_msg_content, "\n\n".join(assistant_msg_parts)])
                 else: logger.warning("Found assistant messages without preceding user message."); chatbot_history.append([None, "\n\n".join(assistant_msg_parts)])
                 assistant_msg_parts = []
            user_msg_content = msg.content
        elif msg.role == "assistant":
             thought_prefix = "**Assistant Thoughts/Plan:**\n" if msg.content else ""
             tool_calls_str = ""
             if msg.tool_calls: tool_calls_str = "\n**Requesting Tools:**\n" + "\n".join([f"- `{tc.function.name}`(`{tc.function.arguments or '{}'}`)" for tc in msg.tool_calls])
             assistant_msg_parts.append(f"{thought_prefix}{msg.content or ''}{tool_calls_str}")
        elif msg.role == "tool":
             tool_content = str(msg.content); is_code = "```" in tool_content or "\n" in tool_content.strip(); formatted_content = f"```\n{tool_content}\n```" if is_code else tool_content
             if len(tool_content) > 500 and "..." not in tool_content[-10:]: formatted_content = formatted_content[:500] + "..."
             assistant_msg_parts.append(f"**Tool Result (`{msg.name}`):**\n{formatted_content}")
        elif msg.role == "system": assistant_msg_parts.append(f"**System Note:**\n{msg.content}")
    if user_msg_content is not None: chatbot_history.append([user_msg_content, "\n\n".join(assistant_msg_parts) if assistant_msg_parts else None])
    elif assistant_msg_parts: chatbot_history.append([None, "\n\n".join(assistant_msg_parts)])
    return chatbot_history

# --- Gradio Session Management Functions ---
def rename_chat_session_ui(session_id: str, new_name: str, session_data: dict):
    if not session_id or session_id not in session_data: gr.Warning(f"Session '{session_id}' not found!"); return session_id, session_data, gr.Radio(choices=list(session_data.keys()), value=session_id), gr.Textbox(value="")
    if not new_name or not new_name.strip(): gr.Warning("New name cannot be empty!"); return session_id, session_data, gr.Radio(choices=list(session_data.keys()), value=session_id), gr.Textbox(value="")
    new_name = new_name.strip()
    if new_name == session_id: return session_id, session_data, gr.Radio(choices=list(session_data.keys()), value=session_id), gr.Textbox(value="")
    if new_name in session_data: gr.Warning(f"Name '{new_name}' already exists!"); return session_id, session_data, gr.Radio(choices=list(session_data.keys()), value=session_id), gr.Textbox(value="")
    logger.info(f"Renaming session '{session_id}' to '{new_name}'")
    rename_session_file(session_id, new_name); session_data[new_name] = session_data.pop(session_id)
    updated_choices = list(session_data.keys()); updated_choices.sort(key=lambda x: int(x.split(" ")[1]) if x.startswith("Chat ") and len(x.split(" ")) > 1 and x.split(" ")[1].isdigit() else float('inf'))
    return new_name, session_data, gr.Radio(choices=updated_choices, value=new_name), gr.Textbox(value="")

def delete_chat_session_ui(session_id: str, session_data: dict):
    if not session_id or session_id not in session_data: gr.Warning(f"Session '{session_id}' not found!"); return session_id, session_data, gr.Radio(choices=list(session_data.keys()), value=session_id), []
    if len(session_data) <= 1: gr.Warning("Cannot delete the last chat session!"); return session_id, session_data, gr.Radio(choices=list(session_data.keys()), value=session_id), format_history_for_chatbot(session_data.get(session_id, []))
    logger.info(f"Deleting session '{session_id}'")
    delete_session_file(session_id); del session_data[session_id]
    updated_choices = list(session_data.keys()); updated_choices.sort(key=lambda x: int(x.split(" ")[1]) if x.startswith("Chat ") and len(x.split(" ")) > 1 and x.split(" ")[1].isdigit() else float('inf'))
    new_active_session_id = updated_choices[-1] if updated_choices else None
    new_chatbot_history = format_history_for_chatbot(session_data.get(new_active_session_id, [])) if new_active_session_id else []
    return new_active_session_id, session_data, gr.Radio(choices=updated_choices, value=new_active_session_id), new_chatbot_history

def start_new_chat_session_ui(session_data: dict):
    max_num = 0
    for key in session_data.keys():
        if key.startswith("Chat "):
            try:
                parts = key.split(" ")
                if len(parts) > 1 and parts[1].isdigit():
                    num = int(parts[1])
                    if num > max_num:
                        max_num = num
            except ValueError:
                continue # Ignore keys not matching the pattern
    new_session_id = f"Chat {max_num + 1}"
    session_data[new_session_id] = []; save_session_file(new_session_id, [])
    logger.info(f"Started and saved new chat session: {new_session_id}")
    updated_choices = list(session_data.keys()); updated_choices.sort(key=lambda x: int(x.split(" ")[1]) if x.startswith("Chat ") and len(x.split(" ")) > 1 and x.split(" ")[1].isdigit() else float('inf'))
    return new_session_id, session_data, [], gr.Radio(choices=updated_choices, value=new_session_id)

def load_chat_session_ui(session_id: str, session_data: dict):
    if not session_id or session_id not in session_data:
        logger.warning(f"Attempted to load invalid session ID: {session_id}")
        if session_data:
             sorted_keys = list(session_data.keys()); sorted_keys.sort(key=lambda x: int(x.split(" ")[1]) if x.startswith("Chat ") and len(x.split(" ")) > 1 and x.split(" ")[1].isdigit() else float('inf'))
             latest_session_id = sorted_keys[-1] if sorted_keys else None
             if latest_session_id: logger.warning(f"Falling back to latest session: {latest_session_id}"); return format_history_for_chatbot(session_data.get(latest_session_id, [])), latest_session_id, gr.Radio(value=latest_session_id)
        return [], None, gr.Radio(value=None)
    logger.info(f"Loading chat session: {session_id}")
    history_messages = session_data.get(session_id, [])
    formatted_history = format_history_for_chatbot(history_messages)
    return formatted_history, session_id, gr.Radio(value=session_id)

# --- Gradio Chat Execution Logic ---
async def run_chat_ui(message: str, chat_history_formatted: list[list[str | None]], active_session_id: str, session_data: dict):
    if not active_session_id: yield chat_history_formatted + [[message, "Error: No active session selected."]], session_data; return
    agent = await initialize_ui_agent() # Use UI specific agent init
    if not agent: yield chat_history_formatted + [[message, "Error: Agent not initialized"]], session_data; return

    async with ui_agent_lock: # Use UI specific lock
        current_history_messages = session_data.get(active_session_id, [])
        agent.memory.messages = current_history_messages.copy()
        agent.state = AgentState.IDLE; agent.current_step = 0
        logger.info(f"UI: Loaded {len(agent.memory.messages)} messages for session {active_session_id}.")

        chat_history_formatted.append([message, None])
        yield chat_history_formatted, session_data

        assistant_response_stream = ""
        try:
            async for update in agent.run(request=message):
                assistant_response_stream = update
                if chat_history_formatted: chat_history_formatted[-1][1] = assistant_response_stream
                yield chat_history_formatted, session_data
            if agent.state == AgentState.FINISHED:
                success_message = "<br><br><span style='color:green; font-weight:bold;'>✅ Succeed / 完成</span>"
                if chat_history_formatted: chat_history_formatted[-1][1] = (chat_history_formatted[-1][1] or "") + success_message
                logger.info("UI: Appended success message.")
                yield chat_history_formatted, session_data
        except Exception as e:
            logger.error(f"UI: Error during agent run for session {active_session_id}: {e}", exc_info=True)
            error_msg = f"An error occurred: {str(e)}"
            if chat_history_formatted: chat_history_formatted[-1][1] = (chat_history_formatted[-1][1] or "") + f"\n\n**Error:** {error_msg}"
            if agent: agent.state = AgentState.ERROR
            yield chat_history_formatted, session_data
        finally:
            if agent and agent.memory:
                 if active_session_id in session_data:
                      session_data[active_session_id] = agent.memory.messages.copy()
                      save_session_file(active_session_id, session_data[active_session_id])
                      logger.info(f"UI: Saved final state for session {active_session_id}")
                 else: logger.warning(f"UI: Session '{active_session_id}' was deleted during run, cannot save.")
            else: logger.error("UI: Agent or memory not available for saving.")
            yield chat_history_formatted, session_data

# --- Build Gradio UI ---
initial_session_data = load_session_data()
initial_session_ids = list(initial_session_data.keys())
initial_session_ids.sort(key=lambda x: int(x.split(" ")[1]) if x.startswith("Chat ") and len(x.split(" ")) > 1 and x.split(" ")[1].isdigit() else float('inf'))
active_session_id_on_load = initial_session_ids[-1] if initial_session_ids else "Chat 1"

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    session_state = gr.State(initial_session_data)
    active_session_id_state = gr.State(active_session_id_on_load)
    with gr.Row():
        with gr.Column(scale=1, min_width=250):
            gr.Markdown("## Chat History")
            new_chat_btn = gr.Button("➕ New Chat")
            history_radio = gr.Radio(label="Sessions", choices=initial_session_ids, value=active_session_id_on_load, type="value")
            gr.Markdown("### Manage Selected Session")
            rename_textbox = gr.Textbox(label="New Name", placeholder="Enter new name...", scale=3, show_label=False)
            with gr.Row(): rename_btn = gr.Button("Rename", scale=1); delete_btn = gr.Button("Delete", scale=1, variant="stop")
        with gr.Column(scale=4):
            initial_chatbot_history = format_history_for_chatbot(initial_session_data.get(active_session_id_on_load, []))
            chatbot = gr.Chatbot(label="OpenManus Agent", value=initial_chatbot_history, render_markdown=True, height=700, show_label=False, bubble_full_width=False)
            with gr.Row(): msg_textbox = gr.Textbox(placeholder="Enter your request...", scale=7, container=False, show_label=False); send_btn = gr.Button("Send", scale=1, variant="primary", min_width=100)
    # --- Define Gradio Interactions ---
    submit_event = msg_textbox.submit(fn=run_chat_ui, inputs=[msg_textbox, chatbot, active_session_id_state, session_state], outputs=[chatbot, session_state])
    submit_event.then(lambda: gr.Textbox(value=""), outputs=[msg_textbox])
    click_event = send_btn.click(fn=run_chat_ui, inputs=[msg_textbox, chatbot, active_session_id_state, session_state], outputs=[chatbot, session_state])
    click_event.then(lambda: gr.Textbox(value=""), outputs=[msg_textbox])
    new_chat_btn.click(fn=start_new_chat_session_ui, inputs=[session_state], outputs=[active_session_id_state, session_state, chatbot, history_radio])
    history_radio.change(fn=load_chat_session_ui, inputs=[history_radio, session_state], outputs=[chatbot, active_session_id_state, history_radio])
    rename_btn.click(fn=rename_chat_session_ui, inputs=[active_session_id_state, rename_textbox, session_state], outputs=[active_session_id_state, session_state, history_radio, rename_textbox])
    delete_btn.click(fn=delete_chat_session_ui, inputs=[active_session_id_state, session_state], outputs=[active_session_id_state, session_state, history_radio, chatbot])

# --- Function to Open Browser ---
def open_browser():
    """Opens the browser to the Gradio UI."""
    try:
        logger.info(f"Attempting to open browser at {UI_BASE_URL}")
        webbrowser.open(UI_BASE_URL)
        logger.info(f"Browser open command issued for {UI_BASE_URL}")
    except Exception as e:
        logger.error(f"Failed to open browser automatically: {e}")
        print(f"\nCould not open browser automatically. Please navigate to {UI_BASE_URL}\n")

# --- Main Execution ---
if __name__ == "__main__":
    # Initialize agent before starting server
    try:
        asyncio.run(initialize_ui_agent()) # Use UI specific init
    except SystemExit: exit(1)
    except Exception as e: print(f"\nFATAL: Unexpected error during UI agent initialization: {e}\n"); exit(1)

    # Use threading.Timer to open browser after a delay
    threading.Timer(1.5, open_browser).start()

    logger.info(f"Starting Gradio UI server on {UI_BASE_URL}")
    # Launch Gradio app directly (not mounting on FastAPI anymore)
    demo.launch(server_name=UI_HOST, server_port=UI_PORT)
