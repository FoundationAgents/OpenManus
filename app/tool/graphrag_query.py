import asyncio
import os

from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class GraphRAGQuery(BaseTool):
    """GraphRAG query tool for knowledge base search."""

    name: str = "graphrag_query"
    description: str = "Query GraphRAG knowledge base using global or local search methods"
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The query string to search in the knowledge base"},
            "method": {
                "type": "string",
                "enum": ["global", "local", "drift", "basic"],
                "description": "Search method to use (global, local, drift, or basic)",
                "default": "global",
            },
            "root_path": {
                "type": "string",
                "description": "Root path to the GraphRAG directory",
                "default": "./yh_rag",
            },
            "community_level": {
                "type": "integer",
                "description": "Community level for global search (0-4)",
                "default": 2,
            },
            "response_type": {
                "type": "string",
                "enum": [
                    "Multiple Paragraphs",
                    "Single Paragraph",
                    "Single Sentence",
                    "List of 3-7 Points",
                    "Real Time",
                ],
                "description": "Response format type",
                "default": "Multiple Paragraphs",
            },
        },
        "required": ["query"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute GraphRAG query."""
        try:
            query = kwargs.get("query")
            method = kwargs.get("method", "global")
            root_path = kwargs.get("root_path", "./yh_rag")
            community_level = kwargs.get("community_level", 2)
            response_type = kwargs.get("response_type", "Multiple Paragraphs")

            if not query:
                return ToolResult(error="Query parameter is required")

            # Validate method
            valid_methods = ["global", "local", "drift", "basic"]
            if method not in valid_methods:
                return ToolResult(error=f"Invalid method. Must be one of: {valid_methods}")

            # Build command
            cmd = ["python", "-m", "graphrag", "query", "--root", root_path, "--method", method, "--query", query]

            # Add method-specific parameters
            if method == "global":
                cmd.extend(["--community_level", str(community_level)])
                cmd.extend(["--response_type", response_type])

            logger.info(f"Executing GraphRAG query: {' '.join(cmd)}")

            # Execute command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=os.getcwd()
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8") if stderr else "Unknown error occurred"
                logger.error(f"GraphRAG query failed: {error_msg}")
                return ToolResult(error=f"GraphRAG query failed: {error_msg}")

            result = stdout.decode("utf-8").strip()

            if not result:
                return ToolResult(output="No results found for the query")

            logger.info("GraphRAG query completed successfully")
            return ToolResult(output=result)

        except Exception as e:
            logger.error(f"Error executing GraphRAG query: {str(e)}")
            return ToolResult(error=f"Error executing GraphRAG query: {str(e)}")

    async def validate_setup(self) -> bool:
        """Validate that GraphRAG is properly set up."""
        try:
            # Check if graphrag module is available
            process = await asyncio.create_subprocess_exec(
                "python", "-m", "graphrag", "--help", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False
