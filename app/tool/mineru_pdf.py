# flake8: noqa: E501
import asyncio
import time
from enum import Enum
from typing import List, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config import config
from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class TaskState(str, Enum):
    """MinerU task processing states"""

    PENDING = "pending"
    RUNNING = "running"
    CONVERTING = "converting"
    DONE = "done"
    FAILED = "failed"


class ExportFormat(str, Enum):
    """Additional export formats for MinerU"""

    DOCX = "docx"
    HTML = "html"
    LATEX = "latex"


class ModelVersion(str, Enum):
    """MinerU model versions"""

    PIPELINE = "pipeline"
    VLM = "vlm"


class ExtractProgress(BaseModel):
    """Progress information for document extraction"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    extracted_pages: int = Field(description="Number of pages already extracted")
    total_pages: int = Field(description="Total number of pages in document")
    start_time: str = Field(description="Extraction start time")


class MinerUTaskResponse(BaseModel):
    """Response from MinerU task submission or query"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    task_id: str = Field(description="Task ID")
    data_id: Optional[str] = Field(default=None, description="Data ID if provided")
    state: TaskState = Field(description="Task processing state")
    full_zip_url: Optional[str] = Field(default=None, description="URL to download result zip file")
    err_msg: Optional[str] = Field(default=None, description="Error message if task failed")
    extract_progress: Optional[ExtractProgress] = Field(default=None, description="Extraction progress")


class MinerUPDFResult(ToolResult):
    """Structured response from MinerU PDF tool"""

    task_id: str = Field(description="Task ID")
    state: TaskState = Field(description="Task processing state")
    data_id: Optional[str] = Field(default=None, description="Data ID")
    full_zip_url: Optional[str] = Field(default=None, description="Download URL for results")
    extract_progress: Optional[ExtractProgress] = Field(default=None, description="Extraction progress")

    @model_validator(mode="after")
    def populate_output(self) -> "MinerUPDFResult":
        """Populate output or error fields based on task state"""
        if self.error:
            return self

        result_text = [f"MinerU PDF Task: {self.task_id}"]

        if self.data_id:
            result_text.append(f"Data ID: {self.data_id}")

        result_text.append(f"Status: {self.state.value}")

        if self.state == TaskState.PENDING:
            result_text.append("⏳ Task is queued and waiting to be processed")
        elif self.state == TaskState.RUNNING:
            if self.extract_progress:
                progress = self.extract_progress
                percentage = (progress.extracted_pages / progress.total_pages * 100) if progress.total_pages > 0 else 0
                result_text.append(
                    f"🔄 Extracting: {progress.extracted_pages}/{progress.total_pages} pages ({percentage:.1f}%)"
                )
                result_text.append(f"   Started at: {progress.start_time}")
        elif self.state == TaskState.CONVERTING:
            result_text.append("🔄 Converting to output formats...")
        elif self.state == TaskState.DONE:
            result_text.append("✅ Task completed successfully!")
            if self.full_zip_url:
                result_text.append(f"📦 Download results: {self.full_zip_url}")
        elif self.state == TaskState.FAILED:
            result_text.append(f"❌ Task failed: {self.error or 'Unknown error'}")

        self.output = "\n".join(result_text)
        return self


class MinerUPDFTool(BaseTool):
    """
    MinerU PDF parsing tool for extracting content from PDF and other document formats.

    This tool provides two main operations:
    1. submit_task: Submit a document for parsing
    2. query_task: Query the status and results of a parsing task
    """

    name: str = "mineru_pdf"
    description: str = """Parse PDF and other document formats (PDF, DOC, DOCX, PPT, PPTX, PNG, JPG, JPEG) using MinerU service.

    This tool supports two operations:
    - submit_task: Submit a document URL for parsing. Returns a task_id for tracking.
    - query_task: Query the parsing status and get results using task_id.

    The tool can extract text, formulas, tables, and images from documents with OCR support."""

    parameters: dict = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["submit_task", "query_task"],
                "description": "(required) Operation to perform: 'submit_task' to start parsing, 'query_task' to check status",
            },
            "url": {
                "type": "string",
                "description": "(required for submit_task) URL of the document to parse. Supports PDF, DOC, DOCX, PPT, PPTX, PNG, JPG, JPEG formats",
            },
            "task_id": {
                "type": "string",
                "description": "(required for query_task) Task ID returned from submit_task operation",
            },
            "is_ocr": {
                "type": "boolean",
                "description": "(optional) Enable OCR for image-based documents. Default: true",
                "default": True,
            },
            "enable_formula": {
                "type": "boolean",
                "description": "(optional) Enable formula recognition. Default: true",
                "default": True,
            },
            "enable_table": {
                "type": "boolean",
                "description": "(optional) Enable table recognition. Default: true",
                "default": True,
            },
            "language": {
                "type": "string",
                "description": "(optional) Document language code (e.g., 'ch' for Chinese, 'en' for English). Default: 'ch'",
                "default": "ch",
            },
            "data_id": {
                "type": "string",
                "description": "(optional) Custom data ID for tracking your business data (max 128 chars)",
            },
            "extra_formats": {
                "type": "array",
                "items": {"type": "string", "enum": ["docx", "html", "latex"]},
                "description": "(optional) Additional export formats. Markdown and JSON are exported by default",
            },
            "page_ranges": {
                "type": "string",
                "description": "(optional) Page ranges to extract (e.g., '2,4-6' or '2--2' for page 2 to second-to-last)",
            },
            "model_version": {
                "type": "string",
                "enum": ["pipeline", "vlm"],
                "description": "(optional) MinerU model version. Default: 'pipeline'",
                "default": "pipeline",
            },
            "wait_for_completion": {
                "type": "boolean",
                "description": "(optional for submit_task) Wait for task completion and return final results. Default: false",
                "default": False,
            },
            "poll_interval": {
                "type": "integer",
                "description": "(optional) Polling interval in seconds when waiting for completion. Default: 5",
                "default": 5,
            },
            "max_wait_time": {
                "type": "integer",
                "description": "(optional) Maximum wait time in seconds when waiting for completion. Default: 1200 (5 minutes)",
                "default": 1200,
            },
        },
        "required": ["operation"],
    }

    def __init__(self, **data):
        super().__init__(**data)
        self._base_url = "https://mineru.net/api/v4/extract"
        self._api_key = None

        # Load API key from config
        if hasattr(config, "mineru_config") and config.mineru_config:
            self._api_key = config.mineru_config.api_key
            if hasattr(config.mineru_config, "base_url"):
                self._base_url = config.mineru_config.base_url

    async def execute(
        self,
        operation: str,
        url: Optional[str] = None,
        task_id: Optional[str] = None,
        is_ocr: bool = True,
        enable_formula: bool = True,
        enable_table: bool = True,
        language: str = "ch",
        data_id: Optional[str] = None,
        extra_formats: Optional[List[str]] = None,
        page_ranges: Optional[str] = None,
        model_version: str = "pipeline",
        wait_for_completion: bool = False,
        poll_interval: int = 5,
        max_wait_time: int = 1200,
        **kwargs,
    ) -> MinerUPDFResult:
        """
        Execute MinerU PDF parsing operation.

        Args:
            operation: Operation to perform ('submit_task' or 'query_task')
            url: Document URL (required for submit_task)
            task_id: Task ID (required for query_task)
            is_ocr: Enable OCR
            enable_formula: Enable formula recognition
            enable_table: Enable table recognition
            language: Document language code
            data_id: Custom data ID
            extra_formats: Additional export formats
            page_ranges: Page ranges to extract
            model_version: MinerU model version
            wait_for_completion: Wait for task completion
            poll_interval: Polling interval in seconds
            max_wait_time: Maximum wait time in seconds

        Returns:
            MinerUPDFResult with task status and results
        """
        if not self._api_key:
            return MinerUPDFResult(
                task_id="",
                state=TaskState.FAILED,
                error="MinerU API key not configured. Please set mineru_config.api_key in config.toml",
            )

        try:
            if operation == "submit_task":
                if not url:
                    return MinerUPDFResult(
                        task_id="", state=TaskState.FAILED, error="URL is required for submit_task operation"
                    )

                result = await self._submit_task(
                    url=url,
                    is_ocr=is_ocr,
                    enable_formula=enable_formula,
                    enable_table=enable_table,
                    language=language,
                    data_id=data_id,
                    extra_formats=extra_formats,
                    page_ranges=page_ranges,
                    model_version=model_version,
                )

                # If wait_for_completion is True, poll until done
                if wait_for_completion and result.task_id:
                    logger.info(f"Waiting for task {result.task_id} to complete...")
                    result = await self._wait_for_completion(
                        result.task_id, poll_interval=poll_interval, max_wait_time=max_wait_time
                    )

                return result

            elif operation == "query_task":
                if not task_id:
                    return MinerUPDFResult(
                        task_id="", state=TaskState.FAILED, error="task_id is required for query_task operation"
                    )

                return await self._query_task(task_id)

            else:
                return MinerUPDFResult(
                    task_id="",
                    state=TaskState.FAILED,
                    error=f"Unknown operation: {operation}. Use 'submit_task' or 'query_task'",
                )

        except Exception as e:
            logger.error(f"MinerU PDF tool error: {e}", exc_info=True)
            return MinerUPDFResult(
                task_id=task_id or "", state=TaskState.FAILED, error=f"Error executing MinerU operation: {str(e)}"
            )

    async def _submit_task(
        self,
        url: str,
        is_ocr: bool,
        enable_formula: bool,
        enable_table: bool,
        language: str,
        data_id: Optional[str],
        extra_formats: Optional[List[str]],
        page_ranges: Optional[str],
        model_version: str,
    ) -> MinerUPDFResult:
        """Submit a document parsing task to MinerU"""

        # Build request payload
        payload = {
            "url": url,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula,
            "enable_table": enable_table,
            "language": language,
            "model_version": model_version,
        }

        if data_id:
            payload["data_id"] = data_id
        if extra_formats:
            payload["extra_formats"] = extra_formats
        if page_ranges:
            payload["page_ranges"] = page_ranges

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json", "Accept": "*/*"}

        logger.info(f"Submitting MinerU task for URL: {url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/task", json=payload, headers=headers)

            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to submit MinerU task: {error_msg}")
                return MinerUPDFResult(task_id="", state=TaskState.FAILED, error=error_msg)

            result = response.json()

            if result.get("code") != 0:
                error_msg = result.get("msg", "Unknown error")
                logger.error(f"MinerU API error: {error_msg}")
                return MinerUPDFResult(task_id="", state=TaskState.FAILED, error=error_msg)

            data = result.get("data", {})
            task_id = data.get("task_id", "")

            logger.info(f"✅ MinerU task submitted successfully: {task_id}")

            return MinerUPDFResult(task_id=task_id, state=TaskState.PENDING, data_id=data.get("data_id"))

    async def _query_task(self, task_id: str) -> MinerUPDFResult:
        """Query the status of a MinerU parsing task"""

        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "*/*"}

        logger.info(f"Querying MinerU task: {task_id}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self._base_url}/task/{task_id}", headers=headers)

            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to query MinerU task: {error_msg}")
                return MinerUPDFResult(task_id=task_id, state=TaskState.FAILED, error=error_msg)

            result = response.json()

            if result.get("code") != 0:
                error_msg = result.get("msg", "Unknown error")
                logger.error(f"MinerU API error: {error_msg}")
                return MinerUPDFResult(task_id=task_id, state=TaskState.FAILED, error=error_msg)

            data = result.get("data", {})
            state = TaskState(data.get("state", "failed"))

            # Build progress info if available
            extract_progress = None
            if "extract_progress" in data and data["extract_progress"]:
                prog = data["extract_progress"]
                extract_progress = ExtractProgress(
                    extracted_pages=prog.get("extracted_pages", 0),
                    total_pages=prog.get("total_pages", 0),
                    start_time=prog.get("start_time", ""),
                )

            return MinerUPDFResult(
                task_id=task_id,
                state=state,
                data_id=data.get("data_id"),
                full_zip_url=data.get("full_zip_url"),
                extract_progress=extract_progress,
                error=data.get("err_msg") if state == TaskState.FAILED else None,
            )

    async def _wait_for_completion(
        self, task_id: str, poll_interval: int = 5, max_wait_time: int = 1200
    ) -> MinerUPDFResult:
        """Wait for a task to complete by polling its status"""

        start_time = time.time()

        while True:
            # Check if we've exceeded max wait time
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                logger.warning(f"Task {task_id} exceeded max wait time of {max_wait_time}s")
                result = await self._query_task(task_id)
                result.error = f"Task exceeded maximum wait time of {max_wait_time} seconds"
                return result

            # Query task status
            result = await self._query_task(task_id)

            # Check if task is in terminal state
            if result.state in [TaskState.DONE, TaskState.FAILED]:
                return result

            # Log progress
            if result.state == TaskState.RUNNING and result.extract_progress:
                prog = result.extract_progress
                logger.info(f"Task {task_id}: {prog.extracted_pages}/{prog.total_pages} pages extracted")
            elif result.state == TaskState.CONVERTING:
                logger.info(f"Task {task_id}: Converting to output formats...")

            # Wait before next poll
            await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    # Example usage
    async def test_mineru():
        tool = MinerUPDFTool()

        # Submit a task
        result = await tool.execute(
            operation="submit_task",
            url="https://cdn-mineru.openxlab.org.cn/demo/example.pdf",
            is_ocr=True,
            enable_formula=True,
            wait_for_completion=True,
        )

        print(result.output)

        if result.state == TaskState.DONE:
            print(f"\n✅ Download results from: {result.full_zip_url}")

    asyncio.run(test_mineru())
