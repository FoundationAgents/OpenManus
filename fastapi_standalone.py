#!/usr/bin/env python3
"""
FastAPI Standalone - Interface web simples para demonstrar os sandbox adapters
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Config
from app.sandbox.adapters.factory import SandboxFactory
from app.sandbox.adapters.unified_client import UnifiedSandboxClient

app = FastAPI(title="OpenManus Sandbox Demo", version="1.0.0")


# Models
class CommandRequest(BaseModel):
    command: str
    sandbox_id: Optional[str] = None


class CommandResponse(BaseModel):
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    sandbox_id: str


class SandboxInfo(BaseModel):
    id: str
    backend: str
    available_backends: list
    status: str


# Global state
active_clients = {}
sandbox_clients = {}


@app.get("/", response_class=HTMLResponse)
async def get_home():
    """Página inicial com interface simples."""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>OpenManus Sandbox Demo</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
        }
        .content {
            padding: 20px;
        }
        .terminal {
            background: #1e1e1e;
            color: #00ff00;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            height: 400px;
            overflow-y: auto;
            margin-bottom: 15px;
            border: 2px solid #444;
        }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        #commandInput {
            flex: 1;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            font-family: 'Courier New', monospace;
        }
        button {
            padding: 10px 20px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: background 0.3s;
        }
        button:hover {
            background: #2980b9;
        }
        button:disabled {
            background: #bdc3c7;
            cursor: not-allowed;
        }
        .status {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            margin-bottom: 15px;
            font-size: 14px;
        }
        .examples {
            background: #f0f8ff;
            padding: 15px;
            border-radius: 5px;
            margin-top: 15px;
            border-left: 4px solid #3498db;
        }
        .examples h3 {
            margin-top: 0;
            color: #2c3e50;
        }
        .examples code {
            background: #e8e8e8;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        .loading {
            display: none;
            color: #f39c12;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 OpenManus Sandbox Demo</h1>
            <p>Sistema de Sandbox Open Source</p>
        </div>

        <div class="content">
            <div class="status">
                <div>
                    <strong>Status:</strong> <span id="status">Conectando...</span>
                </div>
                <div>
                    <strong>Backend:</strong> <span id="backend">-</span>
                </div>
                <div>
                    <strong>Sandbox:</strong> <span id="sandboxId">-</span>
                </div>
            </div>

            <div id="terminal" class="terminal">
                <div>🔄 Inicializando sandbox...</div>
            </div>

            <div class="input-group">
                <input type="text" id="commandInput" placeholder="Digite seu comando (ex: ls -la, python3 --version)" disabled>
                <button id="sendButton" onclick="sendCommand()" disabled>Executar</button>
                <button onclick="clearTerminal()">Limpar</button>
            </div>

            <div class="examples">
                <h3>📝 Comandos de Exemplo:</h3>
                <p><code>ls -la</code> - Listar arquivos</p>
                <p><code>python3 --version</code> - Versão do Python</p>
                <p><code>echo "Hello OpenManus" > /tmp/test.txt</code> - Criar arquivo</p>
                <p><code>cat /tmp/test.txt</code> - Ler arquivo</p>
                <p><code>pip list</code> - Pacotes Python instalados</p>
                <p><code>curl -s https://httpbin.org/json</code> - Teste de rede</p>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let sandboxId = null;
        let isConnected = false;

        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            ws = new WebSocket(wsUrl);

            ws.onopen = function(event) {
                console.log('WebSocket conectado');
                addToTerminal('✅ Conectado ao servidor');
                document.getElementById('status').textContent = 'Conectado';

                // Inicializar sandbox
                ws.send(JSON.stringify({type: 'init'}));
            };

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);

                if (data.type === 'sandbox_created') {
                    sandboxId = data.sandbox_id;
                    document.getElementById('sandboxId').textContent = sandboxId.substring(0, 8) + '...';
                    document.getElementById('backend').textContent = data.backend;
                    document.getElementById('status').textContent = 'Sandbox Ativo';
                    document.getElementById('commandInput').disabled = false;
                    document.getElementById('sendButton').disabled = false;
                    addToTerminal(`🎯 Sandbox ${data.backend} criado: ${sandboxId.substring(0, 12)}...`);
                    addToTerminal('💡 Digite comandos para executar no sandbox!');
                } else if (data.type === 'command_result') {
                    const result = data.result;
                    addToTerminal(`💻 Comando: ${data.command}`);
                    if (result.stdout) {
                        addToTerminal(result.stdout);
                    }
                    if (result.stderr) {
                        addToTerminal(`❌ Erro: ${result.stderr}`, 'error');
                    }
                    addToTerminal(`⏱️ Executado em ${result.execution_time.toFixed(2)}s`);
                    addToTerminal(''); // Linha em branco
                } else if (data.type === 'error') {
                    addToTerminal(`❌ Erro: ${data.message}`, 'error');
                }

                hideLoading();
            };

            ws.onclose = function(event) {
                console.log('WebSocket desconectado');
                addToTerminal('❌ Conexão perdida');
                document.getElementById('status').textContent = 'Desconectado';
                document.getElementById('commandInput').disabled = true;
                document.getElementById('sendButton').disabled = true;
                isConnected = false;

                // Tentar reconectar após 3 segundos
                setTimeout(connect, 3000);
            };

            ws.onerror = function(error) {
                console.log('Erro WebSocket:', error);
                addToTerminal('❌ Erro de conexão');
            };
        }

        function addToTerminal(message, type = 'normal') {
            const terminal = document.getElementById('terminal');
            const div = document.createElement('div');

            if (type === 'error') {
                div.style.color = '#ff6b6b';
            } else if (type === 'success') {
                div.style.color = '#51cf66';
            }

            div.textContent = message;
            terminal.appendChild(div);
            terminal.scrollTop = terminal.scrollHeight;
        }

        function sendCommand() {
            const input = document.getElementById('commandInput');
            const command = input.value.trim();

            if (!command || !ws || ws.readyState !== WebSocket.OPEN) {
                return;
            }

            showLoading();
            ws.send(JSON.stringify({
                type: 'command',
                command: command,
                sandbox_id: sandboxId
            }));

            input.value = '';
        }

        function clearTerminal() {
            document.getElementById('terminal').innerHTML = '';
        }

        function showLoading() {
            document.getElementById('sendButton').disabled = true;
            document.getElementById('sendButton').textContent = 'Executando...';
        }

        function hideLoading() {
            document.getElementById('sendButton').disabled = false;
            document.getElementById('sendButton').textContent = 'Executar';
        }

        // Event listeners
        document.getElementById('commandInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendCommand();
            }
        });

        // Conectar ao carregar a página
        connect();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para comunicação em tempo real."""
    await websocket.accept()
    client_id = id(websocket)
    active_clients[client_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "init":
                # Inicializar sandbox
                try:
                    config_obj = Config()
                    backend = config_obj.sandbox.backend or "docker"

                    client = UnifiedSandboxClient(backend)
                    sandbox_id = await client.create_sandbox()

                    sandbox_clients[client_id] = {
                        "client": client,
                        "sandbox_id": sandbox_id,
                        "backend": backend,
                    }

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "sandbox_created",
                                "sandbox_id": sandbox_id,
                                "backend": backend,
                            }
                        )
                    )

                except Exception as e:
                    await websocket.send_text(
                        json.dumps(
                            {"type": "error", "message": f"Erro criando sandbox: {e}"}
                        )
                    )

            elif message["type"] == "command":
                # Executar comando
                if client_id not in sandbox_clients:
                    await websocket.send_text(
                        json.dumps(
                            {"type": "error", "message": "Sandbox não inicializado"}
                        )
                    )
                    continue

                try:
                    sandbox_info = sandbox_clients[client_id]
                    client = sandbox_info["client"]
                    sandbox_id = sandbox_info["sandbox_id"]
                    command = message["command"]

                    result = await client.execute(sandbox_id, command)

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "command_result",
                                "command": command,
                                "result": {
                                    "stdout": result.stdout,
                                    "stderr": result.stderr,
                                    "exit_code": result.exit_code,
                                    "execution_time": result.execution_time,
                                },
                            }
                        )
                    )

                except Exception as e:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "message": f"Erro executando comando: {e}",
                            }
                        )
                    )

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup
        if client_id in active_clients:
            del active_clients[client_id]

        if client_id in sandbox_clients:
            try:
                sandbox_info = sandbox_clients[client_id]
                await sandbox_info["client"].destroy_sandbox(sandbox_info["sandbox_id"])
            except Exception as e:
                print(f"Erro limpando sandbox: {e}")
            finally:
                del sandbox_clients[client_id]


@app.get("/api/status")
async def get_status():
    """Status da API."""
    available_backends = SandboxFactory.get_available_adapters()
    best_backend = SandboxFactory.auto_detect_backend()

    return {
        "status": "running",
        "available_backends": available_backends,
        "recommended_backend": best_backend,
        "active_clients": len(active_clients),
        "active_sandboxes": len(sandbox_clients),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "service": "OpenManus FastAPI",
        "version": "1.0.0",
    }


@app.get("/readiness")
async def readiness_check():
    """Readiness check endpoint to verify service is ready to accept traffic."""
    try:
        # Check if we can create a config instance
        config = Config()
        return {
            "status": "ready",
            "message": "Service is ready to accept requests",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenManus FastAPI Sandbox Demo")
    parser.add_argument("--host", default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8001, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    print(f"🌐 Iniciando OpenManus Web Demo em http://{args.host}:{args.port}")
    print("🔧 Sistema de sandbox open source carregado")
    print("📱 Acesse pelo navegador para usar a interface web")

    uvicorn.run(
        "fastapi_standalone:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
