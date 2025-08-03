"""文件系统监听服务

监听workspace文件变化并发布相应事件
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config import config
from app.event import (
    DirectoryCreatedEvent,
    DirectoryDeletedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    bus,
)
from app.logger import logger


class WorkspaceFileSystemEventHandler(FileSystemEventHandler):
    """Workspace文件系统事件处理器"""

    def __init__(self, session_id: str, workspace_root: Path):
        super().__init__()
        self.session_id = session_id
        self.workspace_root = workspace_root
        self.loop = None

    def set_event_loop(self, loop):
        """设置事件循环"""
        self.loop = loop

    def _get_relative_path(self, path: str) -> str:
        """获取相对于workspace根目录的路径"""
        try:
            abs_path = Path(path)
            return str(abs_path.relative_to(self.workspace_root)).replace("\\", "/")
        except ValueError:
            # 如果路径不在workspace内，返回原路径
            return path

    def _is_hidden_or_temp(self, path: str) -> bool:
        """检查是否为隐藏文件或临时文件"""
        path_obj = Path(path)
        # 跳过隐藏文件、临时文件、缓存文件等
        skip_patterns = {".git", "__pycache__", ".DS_Store", "Thumbs.db", ".tmp"}
        return any(
            part.startswith(".") or part in skip_patterns for part in path_obj.parts
        )

    def _schedule_event_publish(self, event_instance):
        """调度事件发布到异步事件循环"""
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(bus.publish(event_instance), self.loop)

    def on_created(self, event: FileSystemEvent):
        """文件/目录创建事件"""
        if self._is_hidden_or_temp(event.src_path):
            return

        relative_path = self._get_relative_path(event.src_path)

        try:
            if event.is_directory:
                fs_event = DirectoryCreatedEvent(
                    session_id=self.session_id, path=relative_path
                )
                logger.info(
                    f"📁 Directory created: {relative_path} (session: {self.session_id})"
                )
            else:
                # 获取文件大小
                file_size = None
                try:
                    file_size = os.path.getsize(event.src_path)
                except OSError:
                    pass

                fs_event = FileCreatedEvent(
                    session_id=self.session_id,
                    path=relative_path,
                    file_type="file",
                    size=file_size,
                )
                logger.info(
                    f"📄 File created: {relative_path} (session: {self.session_id})"
                )

            self._schedule_event_publish(fs_event)
        except Exception as e:
            logger.error(f"Error handling file creation event: {e}")

    def on_modified(self, event: FileSystemEvent):
        """文件修改事件"""
        if event.is_directory or self._is_hidden_or_temp(event.src_path):
            return

        relative_path = self._get_relative_path(event.src_path)

        try:
            # 获取文件大小
            file_size = None
            try:
                file_size = os.path.getsize(event.src_path)
            except OSError:
                pass

            fs_event = FileModifiedEvent(
                session_id=self.session_id,
                path=relative_path,
                file_type="file",
                size=file_size,
            )
            logger.info(
                f"✏️ File modified: {relative_path} (session: {self.session_id})"
            )
            self._schedule_event_publish(fs_event)
        except Exception as e:
            logger.error(f"Error handling file modification event: {e}")

    def on_deleted(self, event: FileSystemEvent):
        """文件/目录删除事件"""
        if self._is_hidden_or_temp(event.src_path):
            return

        relative_path = self._get_relative_path(event.src_path)

        try:
            if event.is_directory:
                fs_event = DirectoryDeletedEvent(
                    session_id=self.session_id, path=relative_path
                )
                logger.info(
                    f"🗑️ Directory deleted: {relative_path} (session: {self.session_id})"
                )
            else:
                fs_event = FileDeletedEvent(
                    session_id=self.session_id, path=relative_path, file_type="file"
                )
                logger.info(
                    f"🗑️ File deleted: {relative_path} (session: {self.session_id})"
                )

            self._schedule_event_publish(fs_event)
        except Exception as e:
            logger.error(f"Error handling file deletion event: {e}")

    def on_moved(self, event: FileSystemEvent):
        """文件/目录移动/重命名事件"""
        if self._is_hidden_or_temp(event.src_path) or self._is_hidden_or_temp(
            event.dest_path
        ):
            return

        old_relative_path = self._get_relative_path(event.src_path)
        new_relative_path = self._get_relative_path(event.dest_path)

        try:
            fs_event = FileMovedEvent(
                session_id=self.session_id,
                old_path=old_relative_path,
                new_path=new_relative_path,
                file_type="directory" if event.is_directory else "file",
            )
            logger.info(
                f"📦 {'Directory' if event.is_directory else 'File'} moved: {old_relative_path} -> {new_relative_path} (session: {self.session_id})"
            )
            self._schedule_event_publish(fs_event)
        except Exception as e:
            logger.error(f"Error handling file move event: {e}")


class FileSystemWatcherService:
    """文件系统监听服务"""

    def __init__(self):
        self.observers: Dict[str, Observer] = {}
        self.handlers: Dict[str, WorkspaceFileSystemEventHandler] = {}
        self.workspace_root = Path(config.workspace_root)

    def start_watching_session(self, session_id: str) -> bool:
        """开始监听指定会话的workspace"""
        if session_id in self.observers:
            logger.warning(f"Already watching session: {session_id}")
            return True

        try:
            # 确定会话的workspace路径
            session_workspace = self.workspace_root / session_id

            # 如果目录不存在，创建它
            session_workspace.mkdir(parents=True, exist_ok=True)

            # 创建事件处理器
            handler = WorkspaceFileSystemEventHandler(session_id, session_workspace)
            handler.set_event_loop(asyncio.get_event_loop())

            # 创建观察者
            observer = Observer()
            observer.schedule(handler, str(session_workspace), recursive=True)
            observer.start()

            # 保存引用
            self.observers[session_id] = observer
            self.handlers[session_id] = handler

            logger.info(
                f"🔍 Started watching filesystem for session: {session_id} at {session_workspace}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start watching session {session_id}: {e}")
            return False

    def stop_watching_session(self, session_id: str) -> bool:
        """停止监听指定会话的workspace"""
        if session_id not in self.observers:
            logger.warning(f"Not watching session: {session_id}")
            return True

        try:
            observer = self.observers[session_id]
            observer.stop()
            observer.join(timeout=5.0)  # 等待最多5秒

            # 清理引用
            del self.observers[session_id]
            del self.handlers[session_id]

            logger.info(f"🛑 Stopped watching filesystem for session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop watching session {session_id}: {e}")
            return False

    def stop_all(self):
        """停止所有文件系统监听"""
        session_ids = list(self.observers.keys())
        for session_id in session_ids:
            self.stop_watching_session(session_id)

    def get_watching_sessions(self) -> Set[str]:
        """获取当前正在监听的会话列表"""
        return set(self.observers.keys())


# 全局文件系统监听服务实例
filesystem_watcher = FileSystemWatcherService()
