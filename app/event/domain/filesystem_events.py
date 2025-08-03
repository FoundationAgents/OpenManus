"""文件系统相关事件定义"""

import uuid
from typing import Optional

from app.event.core.base import BaseEvent


class FileSystemEvent(BaseEvent):
    """文件系统事件基类"""

    def __init__(self, session_id: str, path: str, **kwargs):
        super().__init__(
            event_type=f"filesystem.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "session_id": session_id,
                "path": path,
            },
            **kwargs,
        )
        self.session_id = session_id
        self.path = path


class FileCreatedEvent(FileSystemEvent):
    """文件创建事件"""

    def __init__(
        self,
        session_id: str,
        path: str,
        file_type: str = "file",
        size: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(session_id=session_id, path=path, **kwargs)
        self.data.update(
            {
                "action": "created",
                "file_type": file_type,
                "size": size,
                "event_id": str(uuid.uuid4()),
            }
        )


class FileModifiedEvent(FileSystemEvent):
    """文件修改事件"""

    def __init__(
        self,
        session_id: str,
        path: str,
        file_type: str = "file",
        size: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(session_id=session_id, path=path, **kwargs)
        self.data.update(
            {
                "action": "modified",
                "file_type": file_type,
                "size": size,
                "event_id": str(uuid.uuid4()),
            }
        )


class FileDeletedEvent(FileSystemEvent):
    """文件删除事件"""

    def __init__(
        self,
        session_id: str,
        path: str,
        file_type: str = "file",
        **kwargs,
    ):
        super().__init__(session_id=session_id, path=path, **kwargs)
        self.data.update(
            {
                "action": "deleted",
                "file_type": file_type,
                "event_id": str(uuid.uuid4()),
            }
        )


class FileMovedEvent(FileSystemEvent):
    """文件移动/重命名事件"""

    def __init__(
        self,
        session_id: str,
        old_path: str,
        new_path: str,
        file_type: str = "file",
        **kwargs,
    ):
        super().__init__(session_id=session_id, path=new_path, **kwargs)
        self.data.update(
            {
                "action": "moved",
                "old_path": old_path,
                "new_path": new_path,
                "file_type": file_type,
                "event_id": str(uuid.uuid4()),
            }
        )


class DirectoryCreatedEvent(FileSystemEvent):
    """目录创建事件"""

    def __init__(self, session_id: str, path: str, **kwargs):
        super().__init__(session_id=session_id, path=path, **kwargs)
        self.data.update(
            {
                "action": "created",
                "file_type": "directory",
                "event_id": str(uuid.uuid4()),
            }
        )


class DirectoryDeletedEvent(FileSystemEvent):
    """目录删除事件"""

    def __init__(self, session_id: str, path: str, **kwargs):
        super().__init__(session_id=session_id, path=path, **kwargs)
        self.data.update(
            {
                "action": "deleted",
                "file_type": "directory",
                "event_id": str(uuid.uuid4()),
            }
        )
