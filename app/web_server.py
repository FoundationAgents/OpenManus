from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
import json
import uuid
import re
from pathlib import Path
import uvicorn
import logging
from functools import partial
import subprocess

from app.agent.manus import Manus
from app.logger import logger

app = FastAPI(title="OpenManus Web界面")

# 获取项目根目录路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 获取模板和静态文件目录
TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "web", "static")

# 确保目录存在
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# 配置静态文件
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 确保workspace文件夹存在
workspace_dir = Path(BASE_DIR) / "workspace"
workspace_dir.mkdir(parents=True, exist_ok=True)

# 配置workspace文件夹的静态文件访问
app.mount("/workspace", StaticFiles(directory=workspace_dir), name="workspace")

# 配置模板
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 存储活跃的WebSocket连接
active_connections = {}

# 首页路由
@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 自定义日志处理器，将日志发送到WebSocket
class WebSocketLogHandler(logging.Handler):
    def __init__(self, websocket):
        super().__init__()
        self.websocket = websocket
        self.next_thought_id = 1    # 用于标记思考的顺序
        self.next_step_id = 1       # 用于标记执行步骤的ID
        self.current_step_logs = [] # 当前步骤的日志累积
        self.step_pattern = re.compile(r"Executing step (\d+)/(\d+)")
        self.token_pattern = re.compile(r"Token usage:")
        self.tool_pattern = re.compile(r"Activating tool:")
        self.connection_closed = False  # 标记连接状态

    async def send_message(self, record):
        if not self.websocket or self.connection_closed:
            return

        try:
            message = self.format(record)

            # 捕获"Manus's thoughts"内容
            if "✨ Manus's thoughts:" in message:
                # 如果有累积的日志，先发送
                if self.current_step_logs:
                    await self.send_accumulated_logs()

                # 提取思考内容
                thoughts = message.split("✨ Manus's thoughts:")[1].strip()

                # 清理思考内容
                cleaned_thought = thoughts

                # 如果包含tool_call，只保留前面的内容
                if "<tool_call>" in cleaned_thought:
                    cleaned_thought = cleaned_thought.split("<tool_call>")[0].strip()

                # 确保有实际内容
                if cleaned_thought and len(cleaned_thought) > 5:
                    # 发送思考内容
                    if not self.connection_closed:
                        try:
                            await self.websocket.send_json({
                                "status": "thinking",
                                "message": cleaned_thought,
                                "id": self.next_thought_id
                            })
                            self.next_thought_id += 1
                        except RuntimeError:
                            # 连接可能已关闭
                            self.connection_closed = True
                            logger.warning("WebSocket连接已关闭，无法发送思考内容")
                return  # 如果是思考内容，就不再处理为日志消息

            # 过滤掉DEBUG级别和思考内容相关的日志
            if "DEBUG" in message or "Manus's thoughts" in message:
                return

            # 检查是否是新的执行步骤开始、Token使用信息或工具激活
            step_match = self.step_pattern.search(message)
            token_match = self.token_pattern.search(message)
            tool_match = self.tool_pattern.search(message)

            if step_match:
                # 如果有累积的日志，先发送
                if self.current_step_logs:
                    await self.send_accumulated_logs()

                # 开始新的日志累积
                self.current_step_logs.append(message)
            elif token_match or tool_match:
                # 将token使用信息或工具激活信息添加到当前步骤
                if not self.current_step_logs:
                    self.current_step_logs = [message]
                else:
                    self.current_step_logs.append(message)

                # 完成一个逻辑步骤，发送日志
                await self.send_accumulated_logs()
            else:
                # 累积其他日志
                if not self.current_step_logs:
                    self.current_step_logs = [message]
                else:
                    self.current_step_logs.append(message)

                # 如果累积太多行，发送日志
                if len(self.current_step_logs) >= 3:
                    await self.send_accumulated_logs()

        except Exception as e:
            if "Unexpected ASGI message" in str(e) or "WebSocket is closed" in str(e):
                # 将连接标记为已关闭
                self.connection_closed = True
                logger.warning(f"WebSocket连接已关闭: {str(e)}")
            else:
                print(f"发送消息失败: {str(e)}")

    async def send_accumulated_logs(self):
        """发送累积的日志消息"""
        if self.current_step_logs and not self.connection_closed:
            combined_log = "\n".join(self.current_step_logs)
            try:
                await self.websocket.send_json({
                    "status": "log",
                    "message": combined_log,
                    "id": self.next_step_id
                })
                self.next_step_id += 1
                self.current_step_logs = []  # 清空累积的日志
            except Exception as e:
                if "Unexpected ASGI message" in str(e) or "WebSocket is closed" in str(e):
                    # 将连接标记为已关闭
                    self.connection_closed = True
                    logger.warning(f"WebSocket连接已关闭，无法发送累积的日志: {str(e)}")
                else:
                    print(f"发送累积日志失败: {str(e)}")

    def close_connection(self):
        """标记连接为已关闭"""
        self.connection_closed = True

    def emit(self, record):
        asyncio.create_task(self.send_message(record))

# WebSocket连接处理
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    # 如果是新的客户端ID，创建一个新的Manus实例
    if client_id not in active_connections:
        active_connections[client_id] = {
            "websocket": websocket,
            "manus": Manus()
        }
    else:
        active_connections[client_id]["websocket"] = websocket

    # 设置自定义日志处理器
    log_handler = WebSocketLogHandler(websocket)
    handler_id = logger.add(log_handler)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                # 解析客户端发送的JSON数据
                message = json.loads(data)
                prompt = message.get("prompt", "")

                if not prompt.strip():
                    await websocket.send_json({"status": "error", "message": "提示不能为空"})
                    continue

                # 发送正在处理的状态
                await websocket.send_json({"status": "processing", "message": "正在处理您的请求..."})

                # 调用Manus处理请求
                manus_instance = active_connections[client_id]["manus"]

                # 创建一个任务来运行Manus
                async def run_manus():
                    try:
                        result = await manus_instance.run(prompt)

                        # 确保发送所有累积的日志
                        if not log_handler.connection_closed and hasattr(log_handler, 'current_step_logs') and log_handler.current_step_logs:
                            await log_handler.send_accumulated_logs()

                        # 检查连接是否仍然打开
                        if not log_handler.connection_closed:
                            try:
                                await websocket.send_json({"status": "complete", "result": result})
                            except RuntimeError:
                                # 连接可能已关闭
                                log_handler.connection_closed = True
                                logger.warning("WebSocket连接已关闭，无法发送完成结果")
                    except Exception as e:
                        logger.error(f"处理请求时出错: {str(e)}")
                        if not log_handler.connection_closed:
                            try:
                                await websocket.send_json({"status": "error", "message": f"处理请求时出错: {str(e)}"})
                            except RuntimeError:
                                # 连接可能已关闭
                                log_handler.connection_closed = True
                                logger.warning("WebSocket连接已关闭，无法发送错误消息")

                # 使用asyncio.create_task来运行Manus处理，不阻塞WebSocket
                asyncio.create_task(run_manus())

            except Exception as e:
                logger.error(f"处理请求时出错: {str(e)}")
                if not log_handler.connection_closed:
                    try:
                        await websocket.send_json({"status": "error", "message": f"处理请求时出错: {str(e)}"})
                    except RuntimeError:
                        # 连接可能已关闭
                        log_handler.connection_closed = True
                        logger.warning("WebSocket连接已关闭，无法发送错误消息")

    except WebSocketDisconnect:
        # 客户端断开连接，但保留Manus实例一段时间以备重新连接
        logger.info("connection closed")

        # 标记连接为已关闭
        log_handler.close_connection()

        # 发送任何剩余的日志
        if not log_handler.connection_closed and hasattr(log_handler, 'current_step_logs') and log_handler.current_step_logs:
            try:
                await log_handler.send_accumulated_logs()
            except Exception:
                pass  # 忽略关闭连接时的发送错误

        # 移除日志处理器 - 使用正确的ID
        try:
            logger.remove(handler_id)
        except Exception as e:
            logger.warning(f"移除日志处理器时出错: {str(e)}")

@app.get("/new-session")
async def create_new_session():
    """创建一个新的会话ID"""
    return {"session_id": str(uuid.uuid4())}

@app.get("/workspace-files")
async def get_workspace_files():
    """获取workspace文件夹中的文件列表"""
    # 列出所有文件
    files = []
    for file_path in workspace_dir.rglob("*"):
        if file_path.is_file():
            # 获取相对于workspace目录的路径
            rel_path = file_path.relative_to(workspace_dir)
            files.append({
                "name": str(rel_path),
                "path": str(rel_path),
                "size": file_path.stat().st_size,
                "last_modified": file_path.stat().st_mtime
            })

    return {"files": files}

@app.get("/workspace-file/{file_path:path}")
async def get_workspace_file(file_path: str):
    """获取workspace文件夹中的文件内容"""
    file_full_path = workspace_dir / file_path

    # 检查文件是否存在
    if not file_full_path.exists() or not file_full_path.is_file():
        return {"status": "error", "message": "文件不存在"}

    # 获取文件内容
    try:
        content = file_full_path.read_text(errors='replace')
        return {"status": "success", "content": content, "name": file_path}
    except Exception as e:
        return {"status": "error", "message": f"读取文件失败: {str(e)}"}

@app.get("/open-workspace-folder")
async def open_workspace_folder():
    """打开workspace文件夹"""
    try:
        # 根据操作系统打开文件夹
        if os.name == 'nt':  # Windows
            os.startfile(str(workspace_dir))
        elif os.name == 'posix':  # macOS 或 Linux
            if os.uname().sysname == 'Darwin':  # macOS
                subprocess.run(['open', str(workspace_dir)])
            else:  # Linux
                subprocess.run(['xdg-open', str(workspace_dir)])
        return {"status": "success", "message": "已打开workspace文件夹"}
    except Exception as e:
        return {"status": "error", "message": f"打开文件夹失败: {str(e)}"}

def run_server(host="0.0.0.0", port=8000):
    """运行Web服务器"""
    uvicorn.run("app.web_server:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    run_server()
