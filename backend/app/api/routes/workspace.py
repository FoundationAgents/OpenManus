"""
Workspace file management API routes
"""

import mimetypes
import os
import tempfile
import zipfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.config import config
from app.logger import logger

router = APIRouter(prefix="/workspace", tags=["workspace"])


class FileItem(BaseModel):
    name: str
    path: str
    type: str  # 'file' or 'directory'
    size: int = None
    modified: str = None


class BrowseResponse(BaseModel):
    files: List[FileItem]
    current_path: str


def get_safe_path(relative_path: str, session_id: str = None) -> Path:
    """
    获取安全的文件路径，确保不会访问workspace外的文件
    支持会话隔离，每个会话有自己的工作目录
    """
    workspace_root = Path(config.workspace_root).resolve()

    # 如果提供了session_id，使用会话隔离目录
    if session_id:
        session_workspace = workspace_root / session_id
        # 确保会话目录存在
        session_workspace.mkdir(parents=True, exist_ok=True)
        workspace_root = session_workspace

    # 处理空路径
    if not relative_path or relative_path == "/" or relative_path == session_id:
        return workspace_root

    # 如果路径以session_id开头，移除它（因为我们已经在session目录中了）
    if session_id and relative_path.startswith(session_id):
        relative_path = relative_path[len(session_id) :].lstrip("/")
        if not relative_path:
            return workspace_root

    # 移除开头的斜杠
    relative_path = relative_path.lstrip("/")

    # 构建完整路径
    full_path = (workspace_root / relative_path).resolve()

    # 确保路径在workspace内
    try:
        full_path.relative_to(workspace_root)
    except ValueError:
        raise HTTPException(
            status_code=403, detail="Access denied: Path outside workspace"
        )

    return full_path


def get_file_type(path: Path) -> str:
    """判断文件类型"""
    if path.is_dir():
        return "directory"
    return "file"


def format_file_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


@router.get("/browse", response_model=BrowseResponse)
async def browse_files(
    path: str = Query("", description="Relative path from session workspace root"),
    session_id: str = Query(None, description="Session ID for workspace isolation"),
):
    """
    浏览workspace中的文件和文件夹，支持会话隔离
    """
    try:
        target_path = get_safe_path(path, session_id)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        if not target_path.is_dir():
            # 不记录错误日志，这是正常的文件vs目录判断
            raise HTTPException(status_code=400, detail="Path is not a directory")

        files = []

        # 获取会话workspace根目录
        session_workspace_root = Path(config.workspace_root)
        if session_id:
            session_workspace_root = session_workspace_root / session_id

        # 遍历目录内容
        for item in sorted(
            target_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())
        ):
            try:
                # 获取相对于会话workspace的路径
                relative_path = item.relative_to(session_workspace_root)

                file_item = FileItem(
                    name=item.name,
                    path=str(relative_path).replace("\\", "/"),  # 统一使用正斜杠
                    type=get_file_type(item),
                )

                # 如果是文件，添加大小和修改时间信息
                if item.is_file():
                    stat = item.stat()
                    file_item.size = stat.st_size
                    file_item.modified = str(int(stat.st_mtime))

                files.append(file_item)

            except (OSError, ValueError) as e:
                logger.warning(f"Error processing file {item}: {e}")
                continue

        return BrowseResponse(files=files, current_path=path)

    except HTTPException:
        # 重新抛出HTTP异常，不记录错误日志（如400错误是正常的）
        raise
    except Exception as e:
        logger.error(
            f"Error browsing files at path '{path}' for session '{session_id}': {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def get_file(
    path: str = Query(..., description="Relative path from session workspace root"),
    session_id: str = Query(None, description="Session ID for workspace isolation"),
    download: bool = Query(False, description="Force download instead of preview"),
):
    """
    获取workspace中的文件内容，支持会话隔离
    """
    try:
        target_path = get_safe_path(path, session_id)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="File or directory not found")

        # 处理文件夹下载 - 创建ZIP压缩包
        if target_path.is_dir():
            if not download:
                raise HTTPException(
                    status_code=400,
                    detail="Directory preview not supported, use download=true",
                )

            # 检查文件夹是否为空
            if not any(target_path.iterdir()):
                raise HTTPException(
                    status_code=400, detail="Cannot download empty directory"
                )

            # 创建临时ZIP文件
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            temp_zip_path = temp_zip.name
            temp_zip.close()  # 关闭文件句柄，避免Windows锁定问题

            try:
                with zipfile.ZipFile(temp_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in target_path.rglob("*"):
                        if file_path.is_file():
                            # 计算相对路径
                            arcname = file_path.relative_to(target_path)
                            zipf.write(file_path, arcname)

                # 返回ZIP文件，不使用background清理（避免异步问题）
                zip_filename = f"{target_path.name}.zip"

                # 创建一个简单的响应，让系统自动处理临时文件
                response = FileResponse(
                    path=temp_zip_path,
                    filename=zip_filename,
                    media_type="application/zip",
                )

                # 注册一个延迟清理任务（可选）
                import threading
                import time

                def delayed_cleanup():
                    time.sleep(2)  # 等待2秒确保下载完成
                    max_attempts = 5
                    for attempt in range(max_attempts):
                        try:
                            if os.path.exists(temp_zip_path):
                                os.unlink(temp_zip_path)
                                logger.debug(
                                    f"Successfully deleted temporary file: {temp_zip_path}"
                                )
                            break
                        except PermissionError:
                            if attempt < max_attempts - 1:
                                time.sleep(0.5)
                            else:
                                logger.warning(
                                    f"Failed to delete temporary file: {temp_zip_path}"
                                )
                        except Exception as e:
                            logger.error(f"Error deleting temporary file: {e}")
                            break

                # 在后台线程中执行清理
                cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
                cleanup_thread.start()

                return response
            except Exception as e:
                # 清理临时文件
                try:
                    if os.path.exists(temp_zip_path):
                        os.unlink(temp_zip_path)
                except PermissionError:
                    logger.warning(
                        f"Failed to cleanup temporary file on error: {temp_zip_path}"
                    )
                raise e

        # 处理单个文件
        if not target_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(str(target_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        # 如果是下载请求或者是二进制文件，返回文件下载
        if download:
            return FileResponse(
                path=target_path, filename=target_path.name, media_type=mime_type
            )

        # 对于文本文件，可以直接返回内容
        if mime_type.startswith("text/") or mime_type in [
            "application/json",
            "application/xml",
            "application/javascript",
            "application/x-python-code",
        ]:
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return Response(content=content, media_type=mime_type)
            except UnicodeDecodeError:
                # 如果无法以UTF-8解码，则作为二进制文件处理
                pass

        # 对于图片、视频、音频等媒体文件，返回文件流
        def iterfile():
            with open(target_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk

        return StreamingResponse(
            iterfile(),
            media_type=mime_type,
            headers={"Content-Disposition": f"inline; filename={target_path.name}"},
        )

    except Exception as e:
        logger.error(f"Error serving file '{path}' for session '{session_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_workspace_info():
    """
    获取workspace信息
    """
    try:
        workspace_root = Path(config.workspace_root)

        if not workspace_root.exists():
            raise HTTPException(status_code=404, detail="Workspace not found")

        # 统计文件数量和总大小
        total_files = 0
        total_size = 0

        for root, dirs, files in os.walk(workspace_root):
            total_files += len(files)
            for file in files:
                try:
                    file_path = Path(root) / file
                    total_size += file_path.stat().st_size
                except (OSError, ValueError):
                    continue

        return {
            "workspace_root": str(workspace_root),
            "total_files": total_files,
            "total_size": total_size,
            "total_size_formatted": format_file_size(total_size),
            "exists": workspace_root.exists(),
            "is_directory": workspace_root.is_dir(),
        }

    except Exception as e:
        logger.error(f"Error getting workspace info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-directory")
async def create_directory(
    path: str = Query(..., description="Relative path for new directory")
):
    """
    在workspace中创建新目录
    """
    try:
        target_path = get_safe_path(path)

        if target_path.exists():
            raise HTTPException(status_code=400, detail="Directory already exists")

        target_path.mkdir(parents=True, exist_ok=True)

        return {"message": f"Directory created: {path}"}

    except Exception as e:
        logger.error(f"Error creating directory '{path}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_file_or_directory(
    path: str = Query(..., description="Relative path to delete")
):
    """
    删除workspace中的文件或目录
    """
    try:
        target_path = get_safe_path(path)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="File or directory not found")

        if target_path.is_dir():
            import shutil

            shutil.rmtree(target_path)
            return {"message": f"Directory deleted: {path}"}
        else:
            target_path.unlink()
            return {"message": f"File deleted: {path}"}

    except Exception as e:
        logger.error(f"Error deleting '{path}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
