"""
Web UI module for the iXlinx Agent framework.
Provides a modern web interface using FastAPI and WebSockets.
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
    from fastapi.responses import HTMLResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    
    # Create dummy classes for when FastAPI is not available
    class FastAPI:
        def __init__(self, *args, **kwargs):
            pass
        def add_middleware(self, *args, **kwargs):
            pass
        def get(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def websocket(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def run(self, *args, **kwargs):
            logger.error("FastAPI is not installed. Web UI is not available.")
            logger.info("To install FastAPI, run: pip install fastapi uvicorn")

from app.config import config
from app.logger import logger
from app.agent.manus import Manus
from app.flow.flow_factory import FlowFactory, FlowType
from app.cli_tool import cli_tool
from app.local_service import local_service
from app.resources.catalog import (
    ResourceMetadata,
    ResourceRequirements,
    ResourceType,
    resource_catalog,
)


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")
        
    def disconnect(self, client_id: str):
        """Disconnect a WebSocket client."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")
            
    async def send_message(self, client_id: str, message: dict):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
                
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected_clients = []
        
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
                
        for client_id in disconnected_clients:
            self.disconnect(client_id)


class WebUI:
    """Main Web UI application."""
    
    def __init__(self):
        self.app = FastAPI(title="OpenManus Web UI", version="1.0.0")
        self.manager = ConnectionManager()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        self.setup_middleware()
        self.setup_routes()
        
    def setup_middleware(self):
        """Setup FastAPI middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
    def setup_routes(self):
        """Setup FastAPI routes."""
        
        def serialize_resource(resource: ResourceMetadata) -> Dict[str, Any]:
            data = resource.dict()
            data["resource_type"] = resource.resource_type.value
            if resource.first_seen:
                data["first_seen"] = resource.first_seen.isoformat()
            if resource.last_seen:
                data["last_seen"] = resource.last_seen.isoformat()
            return data
        
        @self.app.get("/", response_class=HTMLResponse)
        async def get_index():
            """Serve the main HTML page."""
            return self.get_html_template()
            
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """WebSocket endpoint for real-time communication."""
            await self.manager.connect(websocket, client_id)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self.handle_message(client_id, message)
            except WebSocketDisconnect:
                self.manager.disconnect(client_id)
            except Exception as e:
                logger.error(f"WebSocket error for {client_id}: {e}")
                self.manager.disconnect(client_id)
                
        @self.app.get("/api/status")
        async def get_status():
            """Get system status."""
            return {
                "status": "running",
                "connected_clients": len(self.manager.active_connections),
                "active_tasks": len(self.active_tasks),
                "system_info": cli_tool.get_system_info()
            }
            
        @self.app.get("/api/processes")
        async def get_processes():
            """Get running processes."""
            return {"processes": local_service.list_processes()}
            
        @self.app.post("/api/processes/{process_id}/terminate")
        async def terminate_process(process_id: str):
            """Terminate a process."""
            success = await local_service.terminate_process(process_id)
            return {"success": success}
            
        @self.app.get("/api/files")
        async def get_files(directory: str = "."):
            """Get files in directory."""
            return {"files": local_service.list_files(directory)}
            
        @self.app.get("/api/files/{file_path:path}")
        async def get_file_content(file_path: str):
            """Get file content."""
            content = await local_service.read_file(file_path)
            if content is None:
                raise HTTPException(status_code=404, detail="File not found")
            return {"content": content}
            
        @self.app.post("/api/files/{file_path:path}")
        async def save_file_content(file_path: str, content: dict):
            """Save file content."""
            success = await local_service.write_file(file_path, content.get("content", ""))
            return {"success": success}
            
        @self.app.post("/api/execute")
        async def execute_command(request: dict):
            """Execute a command."""
            command = request.get("command")
            shell_type = request.get("shell_type", "default")
            cwd = request.get("cwd")
            
            result = await cli_tool.execute_command(
                command=command,
                shell_type=shell_type,
                cwd=cwd
            )
            return result
            
        @self.app.get("/api/config")
        async def get_config():
            """Get current configuration."""
            return {
                "llm_models": list(config.llm.keys()),
                "ui_config": {
                    "theme": config.ui.theme,
                    "auto_save": config.ui.auto_save
                },
                "local_service": {
                    "workspace_directory": config.local_service.workspace_directory,
                    "allowed_commands": config.local_service.allowed_commands
                }
            }
        
        @self.app.get("/api/resources")
        async def list_resources(
            resource_type: Optional[str] = None,
            capability: Optional[str] = None,
            name: Optional[str] = None,
            available_only: bool = True,
        ):
            normalized_type = resource_type.lower() if resource_type else None
            normalized_capability = capability.lower() if capability else None
            resources = await resource_catalog.get_resources(
                resource_type=normalized_type,
                capability=normalized_capability,
                name=name,
                available_only=available_only,
            )
            return {"resources": [serialize_resource(res) for res in resources]}

        @self.app.get("/api/resources/{resource_name}")
        async def get_resource_detail(resource_name: str):
            try:
                resource = await resource_catalog.get_resource(resource_name)
            except ValueError:
                raise HTTPException(status_code=404, detail="Resource not found")
            return serialize_resource(resource)

        @self.app.post("/api/resources/refresh")
        async def refresh_resources():
            result = await resource_catalog.refresh(force=True)
            return result

        @self.app.post("/api/resources")
        async def register_resource(payload: Dict[str, Any]):
            try:
                resource_type_value = ResourceType(payload["resource_type"])
                name = payload["name"]
            except KeyError as exc:
                raise HTTPException(status_code=400, detail=f"Missing field: {exc.args[0]}")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid resource_type")

            min_requirements = payload.get("min_requirements")
            max_requirements = payload.get("max_requirements")

            metadata = ResourceMetadata(
                name=name,
                resource_type=resource_type_value,
                version=payload.get("version"),
                install_path=payload.get("install_path"),
                dependencies=payload.get("dependencies") or [],
                min_requirements=ResourceRequirements(**min_requirements) if min_requirements else None,
                max_requirements=ResourceRequirements(**max_requirements) if max_requirements else None,
                capability_tags=payload.get("capability_tags") or [],
                discovery_source=payload.get("discovery_source", "manual"),
                metadata=payload.get("metadata") or {},
            )

            await resource_catalog.register_custom_resource(
                metadata, override=payload.get("override", True)
            )

            stored_resources = await resource_catalog.get_resources(
                name=name,
                available_only=False,
            )
            stored = next(
                (
                    item
                    for item in stored_resources
                    if item.install_path == metadata.install_path
                ),
                stored_resources[0] if stored_resources else metadata,
            )
            return serialize_resource(stored)
        
    async def handle_message(self, client_id: str, message: dict):
        """Handle incoming WebSocket messages."""
        message_type = message.get("type")
        
        if message_type == "chat":
            await self.handle_chat_message(client_id, message)
        elif message_type == "command":
            await self.handle_command_message(client_id, message)
        elif message_type == "get_processes":
            await self.send_processes_update(client_id)
        elif message_type == "get_files":
            await self.send_files_update(client_id, message.get("directory", "."))
        else:
            await self.manager.send_message(client_id, {
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            })
            
    async def handle_chat_message(self, client_id: str, message: dict):
        """Handle chat messages."""
        prompt = message.get("prompt", "")
        mode = message.get("mode", "chat")
        
        if not prompt.strip():
            await self.manager.send_message(client_id, {
                "type": "error",
                "message": "Empty prompt"
            })
            return
            
        # Create task for agent execution
        task_id = str(uuid.uuid4())
        task = asyncio.create_task(self.execute_agent_task(client_id, task_id, prompt, mode))
        self.active_tasks[task_id] = task
        
        try:
            await task
        except Exception as e:
            logger.error(f"Agent task error: {e}")
            await self.manager.send_message(client_id, {
                "type": "error",
                "message": f"Agent error: {str(e)}"
            })
        finally:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                
    async def execute_agent_task(self, client_id: str, task_id: str, prompt: str, mode: str):
        """Execute an agent task."""
        # Send status update
        await self.manager.send_message(client_id, {
            "type": "status",
            "message": f"Starting {mode} execution...",
            "task_id": task_id
        })
        
        try:
            if mode == "chat":
                agent = await Manus.create()
                try:
                    result = await agent.run(prompt)
                    response_text = str(result)
                finally:
                    await agent.cleanup()
            elif mode in ["agent_flow", "ade"]:
                from app.agent.manus import Manus
                from app.agent.data_analysis import DataAnalysis
                
                agents = {"manus": await Manus.create()}
                if config.run_flow_config.use_data_analysis_agent:
                    agents["data_analysis"] = DataAnalysis()
                    
                flow = FlowFactory.create_flow(
                    flow_type=FlowType.PLANNING,
                    agents=agents,
                )
                
                result = await flow.execute(prompt)
                response_text = str(result)
            else:
                raise ValueError(f"Unknown mode: {mode}")
                
            # Send response
            await self.manager.send_message(client_id, {
                "type": "response",
                "message": response_text,
                "task_id": task_id,
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            await self.manager.send_message(client_id, {
                "type": "error",
                "message": f"Execution error: {str(e)}",
                "task_id": task_id
            })
            
    async def handle_command_message(self, client_id: str, message: dict):
        """Handle command execution messages."""
        command = message.get("command", "")
        shell_type = message.get("shell_type", "default")
        cwd = message.get("cwd")
        
        if not command.strip():
            await self.manager.send_message(client_id, {
                "type": "error",
                "message": "Empty command"
            })
            return
            
        result = await cli_tool.execute_command(
            command=command,
            shell_type=shell_type,
            cwd=cwd
        )
        
        await self.manager.send_message(client_id, {
            "type": "command_result",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    async def send_processes_update(self, client_id: str):
        """Send processes update to client."""
        processes = local_service.list_processes()
        await self.manager.send_message(client_id, {
            "type": "processes_update",
            "processes": processes
        })
        
    async def send_files_update(self, client_id: str, directory: str):
        """Send files update to client."""
        files = local_service.list_files(directory)
        await self.manager.send_message(client_id, {
            "type": "files_update",
            "files": files,
            "directory": directory
        })
        
    def get_html_template(self) -> str:
        """Get the HTML template for the web UI."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenManus Web UI</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
            height: 70vh;
        }
        
        .chat-section {
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
        }
        
        .chat-header {
            padding: 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .mode-selector {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background: white;
        }
        
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 10px;
            max-width: 80%;
        }
        
        .message.user {
            background: #007bff;
            color: white;
            margin-left: auto;
        }
        
        .message.agent {
            background: #f1f3f4;
            color: #333;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
        }
        
        .message.system {
            background: #d1ecf1;
            color: #0c5460;
            font-style: italic;
        }
        
        .chat-input {
            padding: 15px;
            border-top: 1px solid #eee;
            display: flex;
            gap: 10px;
        }
        
        .chat-input input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        
        .chat-input button {
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        
        .chat-input button:hover {
            background: #0056b3;
        }
        
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .panel {
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .panel-header {
            padding: 15px;
            background: #f8f9fa;
            border-bottom: 1px solid #eee;
            font-weight: bold;
        }
        
        .panel-content {
            padding: 15px;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .process-item, .file-item {
            padding: 8px;
            border-bottom: 1px solid #f0f0f0;
            cursor: pointer;
        }
        
        .process-item:hover, .file-item:hover {
            background: #f8f9fa;
        }
        
        .command-input {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .command-input input {
            flex: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        
        .command-input button {
            padding: 8px 15px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        
        .command-output {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            max-height: 150px;
            overflow-y: auto;
        }
        
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .status-indicator.connected {
            background: #28a745;
        }
        
        .status-indicator.disconnected {
            background: #dc3545;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
                height: auto;
            }
            
            .sidebar {
                order: -1;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>OpenManus Web UI</h1>
            <p>Advanced Agent Framework with Multi-Modal Capabilities</p>
            <div>
                <span class="status-indicator" id="statusIndicator"></span>
                <span id="statusText">Connecting...</span>
            </div>
        </div>
        
        <div class="main-content">
            <div class="chat-section">
                <div class="chat-header">
                    <h3>Agent Chat</h3>
                    <select class="mode-selector" id="modeSelector">
                        <option value="chat">Chat Mode</option>
                        <option value="agent_flow">Agent Flow</option>
                        <option value="ade">ADE Mode</option>
                    </select>
                </div>
                
                <div class="chat-messages" id="chatMessages">
                    <div class="message system">
                        Welcome to OpenManus! Select a mode and start chatting with the agent.
                    </div>
                </div>
                
                <div class="chat-input">
                    <input type="text" id="messageInput" placeholder="Enter your message..." />
                    <button onclick="sendMessage()">Send</button>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="panel">
                    <div class="panel-header">Command Terminal</div>
                    <div class="panel-content">
                        <div class="command-input">
                            <input type="text" id="commandInput" placeholder="Enter command..." />
                            <button onclick="executeCommand()">Run</button>
                        </div>
                        <div class="command-output" id="commandOutput"></div>
                    </div>
                </div>
                
                <div class="panel">
                    <div class="panel-header">Processes</div>
                    <div class="panel-content" id="processesList">
                        <div class="process-item">Loading...</div>
                    </div>
                </div>
                
                <div class="panel">
                    <div class="panel-header">Files</div>
                    <div class="panel-content" id="filesList">
                        <div class="file-item">Loading...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let clientId = 'client_' + Math.random().toString(36).substr(2, 9);
        let ws;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/${clientId}`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                updateStatus(true);
                addMessage('system', 'Connected to iXlinx Agent server');
                loadProcesses();
                loadFiles();
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            ws.onclose = function() {
                updateStatus(false);
                addMessage('system', 'Disconnected from server');
                // Try to reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateStatus(false);
            };
        }
        
        function updateStatus(connected) {
            const indicator = document.getElementById('statusIndicator');
            const statusText = document.getElementById('statusText');
            
            if (connected) {
                indicator.className = 'status-indicator connected';
                statusText.textContent = 'Connected';
            } else {
                indicator.className = 'status-indicator disconnected';
                statusText.textContent = 'Disconnected';
            }
        }
        
        function handleMessage(data) {
            switch(data.type) {
                case 'response':
                    addMessage('agent', data.message);
                    break;
                case 'error':
                    addMessage('error', data.message);
                    break;
                case 'status':
                    addMessage('system', data.message);
                    break;
                case 'command_result':
                    displayCommandResult(data.result);
                    break;
                case 'processes_update':
                    displayProcesses(data.processes);
                    break;
                case 'files_update':
                    displayFiles(data.files);
                    break;
            }
        }
        
        function addMessage(type, content) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            
            const timestamp = new Date().toLocaleTimeString();
            messageDiv.innerHTML = `<strong>${type} [${timestamp}]:</strong><br>${content}`;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            const mode = document.getElementById('modeSelector').value;
            
            addMessage('user', message);
            
            ws.send(JSON.stringify({
                type: 'chat',
                prompt: message,
                mode: mode
            }));
            
            input.value = '';
        }
        
        function executeCommand() {
            const input = document.getElementById('commandInput');
            const command = input.value.trim();
            
            if (!command) return;
            
            ws.send(JSON.stringify({
                type: 'command',
                command: command,
                shell_type: 'default'
            }));
            
            input.value = '';
        }
        
        function displayCommandResult(result) {
            const output = document.getElementById('commandOutput');
            const timestamp = new Date().toLocaleTimeString();
            
            let displayText = `[${timestamp}] $ ${result.command_display || 'command'}\\n`;
            
            if (result.stdout) {
                displayText += result.stdout;
            }
            
            if (result.stderr) {
                displayText += `\\nSTDERR: ${result.stderr}`;
            }
            
            displayText += `\\nExit code: ${result.exit_code}\\n`;
            
            output.textContent = displayText;
            output.scrollTop = output.scrollHeight;
        }
        
        function loadProcesses() {
            ws.send(JSON.stringify({ type: 'get_processes' }));
        }
        
        function loadFiles(directory = '.') {
            ws.send(JSON.stringify({ 
                type: 'get_files', 
                directory: directory 
            }));
        }
        
        function displayProcesses(processes) {
            const list = document.getElementById('processesList');
            list.innerHTML = '';
            
            if (processes.length === 0) {
                list.innerHTML = '<div class="process-item">No processes running</div>';
                return;
            }
            
            processes.forEach(proc => {
                const item = document.createElement('div');
                item.className = 'process-item';
                item.innerHTML = `
                    <strong>${proc.process_id.substring(0, 8)}</strong><br>
                    <small>${proc.command.substring(0, 50)}...</small><br>
                    <small>PID: ${proc.pid} | ${proc.is_running ? 'Running' : 'Stopped'}</small>
                `;
                list.appendChild(item);
            });
        }
        
        function displayFiles(files) {
            const list = document.getElementById('filesList');
            list.innerHTML = '';
            
            if (files.length === 0) {
                list.innerHTML = '<div class="file-item">No files found</div>';
                return;
            }
            
            files.forEach(file => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.textContent = file;
                item.onclick = () => {
                    if (file.endsWith('/')) {
                        // Navigate to directory
                        const currentDir = document.getElementById('filesList').dataset.currentDir || '.';
                        const newDir = currentDir === '.' ? file : `${currentDir}/${file}`;
                        loadFiles(newDir);
                    }
                };
                list.appendChild(item);
            });
        }
        
        // Event listeners
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        document.getElementById('commandInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                executeCommand();
            }
        });
        
        // Auto-refresh processes and files
        setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                loadProcesses();
                loadFiles();
            }
        }, 10000); // Refresh every 10 seconds
        
        // Initialize connection
        connectWebSocket();
    </script>
</body>
</html>
        """
        
        if not FASTAPI_AVAILABLE:
            logger.error("FastAPI is not installed. Web UI is not available.")
            logger.info("To install FastAPI, run: pip install fastapi uvicorn")
            return

    def run(self, host: str = None, port: int = None):
        """Run the web UI server."""
        host = host or config.ui.webui_host
        port = port or config.ui.webui_port
        
        logger.info(f"Starting Web UI on http://{host}:{port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )


# Global instance
web_ui = WebUI()