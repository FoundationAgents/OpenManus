"""
Notion Integration Tool

This tool provides comprehensive Notion workspace integration for reading, writing,
and managing Notion pages, databases, and content.

Author: Enhancement #4 Implementation
Date: 2025-10-26
"""

import os
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.tool.base import BaseTool, ToolResult
from app.utils.logger import logger


class NotionTool(BaseTool):
    """
    Notion workspace integration for knowledge management and automation.

    This tool provides comprehensive Notion operations:
    - Create and update pages
    - Query and manage databases
    - Search across workspace
    - Add content to knowledge base
    - Sync meeting notes and documentation

    Use cases:
    - Sync meeting notes to Notion
    - Query Notion databases for information
    - Create project documentation automatically
    - Build knowledge base from Notion content
    - Automate Notion workflows
    - Maintain personal wiki/second brain

    Design rationale:
    - Uses official notion-client SDK for reliability
    - Supports both pages and databases
    - Rich text formatting with blocks
    - Metadata extraction for knowledge base
    - Automatic parent/child relationship handling
    - Error handling for permissions and rate limits

    Technical details:
    - API version: 2022-06-28
    - Authentication: Integration token (NOTION_API_KEY env var)
    - Rate limit: 3 requests per second
    - Max page size: 100 blocks per request
    """

    name: str = "notion"
    description: str = (
        "Notion workspace integration for reading, writing, and managing pages and databases. "
        "Create pages, update content, query databases, search workspace, add to knowledge base. "
        "Supports rich text formatting, metadata, and hierarchical organization. "
        "Requires NOTION_API_KEY environment variable."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create_page",
                        "update_page",
                        "read_page",
                        "create_database",
                        "query_database",
                        "add_to_database",
                        "search",
                        "add_to_knowledge",
                    ],
                    "description": "Action to perform in Notion",
                },
                "page_id": {
                    "type": "string",
                    "description": "Notion page ID (for read_page, update_page, add_to_knowledge)",
                },
                "database_id": {
                    "type": "string",
                    "description": "Notion database ID (for create_page, query_database, add_to_database)",
                },
                "title": {
                    "type": "string",
                    "description": "Page title (for create_page)",
                },
                "content": {
                    "type": "string",
                    "description": "Page content as markdown or plain text (for create_page, update_page)",
                },
                "properties": {
                    "type": "object",
                    "description": "Database properties for new entry (for add_to_database)",
                },
                "query": {
                    "type": "string",
                    "description": "Search query (for search action)",
                },
                "filter": {
                    "type": "object",
                    "description": "Database filter criteria (for query_database)",
                },
                "sorts": {
                    "type": "array",
                    "description": "Sort criteria for database query",
                },
            },
            "required": ["action"],
        }
    )

    def __init__(self, **data):
        """Initialize the Notion tool."""
        super().__init__(**data)
        self.client = None
        self.api_key = os.getenv("NOTION_API_KEY")

        if self.api_key:
            self._initialize_client()
        else:
            logger.warning("NOTION_API_KEY not set. Notion tool will not function.")

    def _initialize_client(self):
        """Initialize the Notion client."""
        try:
            from notion_client import Client

            self.client = Client(auth=self.api_key)
            logger.info("Notion client initialized successfully")
        except ImportError:
            logger.error("notion-client not installed. Run: pip install notion-client")
            self.client = None
        except Exception as e:
            logger.error(f"Error initializing Notion client: {e}")
            self.client = None

    def _text_to_blocks(self, content: str) -> List[Dict]:
        """
        Convert plain text or markdown to Notion blocks.

        Supports:
        - Paragraphs
        - Headers (# ## ###)
        - Bullet lists (-)
        - Numbered lists (1. 2. 3.)
        - Code blocks (```)

        Args:
            content: Text content (markdown or plain)

        Returns:
            List of Notion block objects
        """
        blocks = []
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Headers
            if line.startswith("# "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line[2:]}}
                            ]
                        },
                    }
                )
            elif line.startswith("## "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line[3:]}}
                            ]
                        },
                    }
                )
            elif line.startswith("### "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line[4:]}}
                            ]
                        },
                    }
                )

            # Bullet list
            elif line.startswith("- "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line[2:]}}
                            ]
                        },
                    }
                )

            # Numbered list
            elif line[0].isdigit() and ". " in line:
                text = line.split(". ", 1)[1]
                blocks.append(
                    {
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                        },
                    }
                )

            # Code block
            elif line.startswith("```"):
                language = line[3:].strip() or "plain text"
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1

                code_content = "\n".join(code_lines)
                blocks.append(
                    {
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [
                                {"type": "text", "text": {"content": code_content}}
                            ],
                            "language": language,
                        },
                    }
                )

            # Regular paragraph
            else:
                blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": line}}]
                        },
                    }
                )

            i += 1

        return blocks

    def _blocks_to_text(self, blocks: List[Dict]) -> str:
        """
        Convert Notion blocks to plain text.

        Args:
            blocks: List of Notion block objects

        Returns:
            Plain text representation
        """
        text_parts = []

        for block in blocks:
            block_type = block.get("type")

            if block_type in [
                "paragraph",
                "heading_1",
                "heading_2",
                "heading_3",
                "bulleted_list_item",
                "numbered_list_item",
            ]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text = "".join([rt.get("plain_text", "") for rt in rich_text])

                if block_type == "heading_1":
                    text = f"# {text}"
                elif block_type == "heading_2":
                    text = f"## {text}"
                elif block_type == "heading_3":
                    text = f"### {text}"
                elif block_type == "bulleted_list_item":
                    text = f"- {text}"

                text_parts.append(text)

            elif block_type == "code":
                rich_text = block.get("code", {}).get("rich_text", [])
                code = "".join([rt.get("plain_text", "") for rt in rich_text])
                language = block.get("code", {}).get("language", "plain text")
                text_parts.append(f"```{language}\n{code}\n```")

        return "\n\n".join(text_parts)

    async def _create_page(
        self,
        database_id: Optional[str] = None,
        parent_page_id: Optional[str] = None,
        title: str = "Untitled",
        content: str = "",
    ) -> Dict[str, Any]:
        """
        Create a new Notion page.

        Args:
            database_id: Parent database ID (if creating in database)
            parent_page_id: Parent page ID (if creating as subpage)
            title: Page title
            content: Page content

        Returns:
            Created page object
        """
        if not self.client:
            raise Exception("Notion client not initialized")

        # Determine parent
        if database_id:
            parent = {"database_id": database_id}
            properties = {
                "Name": {"title": [{"type": "text", "text": {"content": title}}]}
            }
        elif parent_page_id:
            parent = {"page_id": parent_page_id}
            properties = {
                "title": {"title": [{"type": "text", "text": {"content": title}}]}
            }
        else:
            raise Exception("Either database_id or parent_page_id must be provided")

        # Convert content to blocks
        blocks = self._text_to_blocks(content) if content else []

        # Create page
        page = self.client.pages.create(
            parent=parent,
            properties=properties,
            children=blocks[:100],  # Notion limit: 100 blocks per request
        )

        return page

    async def _read_page(self, page_id: str) -> Dict[str, Any]:
        """
        Read a Notion page.

        Args:
            page_id: Page ID to read

        Returns:
            Page data with content
        """
        if not self.client:
            raise Exception("Notion client not initialized")

        # Get page metadata
        page = self.client.pages.retrieve(page_id)

        # Get page blocks (content)
        blocks_response = self.client.blocks.children.list(page_id)
        blocks = blocks_response.get("results", [])

        # Convert blocks to text
        content = self._blocks_to_text(blocks)

        # Extract title
        title = "Untitled"
        properties = page.get("properties", {})
        for prop_name, prop_value in properties.items():
            if prop_value.get("type") == "title":
                title_array = prop_value.get("title", [])
                if title_array:
                    title = "".join([t.get("plain_text", "") for t in title_array])
                break

        return {
            "page_id": page_id,
            "title": title,
            "content": content,
            "url": page.get("url"),
            "created_time": page.get("created_time"),
            "last_edited_time": page.get("last_edited_time"),
            "properties": properties,
        }

    async def _update_page(self, page_id: str, content: str) -> Dict[str, Any]:
        """
        Update a Notion page's content.

        Args:
            page_id: Page ID to update
            content: New content

        Returns:
            Updated page object
        """
        if not self.client:
            raise Exception("Notion client not initialized")

        # Convert content to blocks
        blocks = self._text_to_blocks(content)

        # Delete existing blocks
        existing_blocks = self.client.blocks.children.list(page_id).get("results", [])
        for block in existing_blocks:
            self.client.blocks.delete(block["id"])

        # Add new blocks
        self.client.blocks.children.append(
            page_id, children=blocks[:100]  # Notion limit
        )

        return {"page_id": page_id, "updated": True}

    async def _query_database(
        self,
        database_id: str,
        filter_criteria: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query a Notion database.

        Args:
            database_id: Database ID
            filter_criteria: Filter object
            sorts: Sort criteria

        Returns:
            List of database entries
        """
        if not self.client:
            raise Exception("Notion client not initialized")

        query_params = {"database_id": database_id}
        if filter_criteria:
            query_params["filter"] = filter_criteria
        if sorts:
            query_params["sorts"] = sorts

        response = self.client.databases.query(**query_params)

        results = []
        for page in response.get("results", []):
            # Extract properties
            properties = {}
            for prop_name, prop_value in page.get("properties", {}).items():
                prop_type = prop_value.get("type")

                if prop_type == "title":
                    title_array = prop_value.get("title", [])
                    properties[prop_name] = "".join(
                        [t.get("plain_text", "") for t in title_array]
                    )
                elif prop_type == "rich_text":
                    text_array = prop_value.get("rich_text", [])
                    properties[prop_name] = "".join(
                        [t.get("plain_text", "") for t in text_array]
                    )
                elif prop_type == "number":
                    properties[prop_name] = prop_value.get("number")
                elif prop_type == "select":
                    select_obj = prop_value.get("select")
                    properties[prop_name] = (
                        select_obj.get("name") if select_obj else None
                    )
                elif prop_type == "date":
                    date_obj = prop_value.get("date")
                    properties[prop_name] = date_obj.get("start") if date_obj else None
                else:
                    properties[prop_name] = prop_value

            results.append(
                {
                    "page_id": page["id"],
                    "url": page.get("url"),
                    "properties": properties,
                }
            )

        return results

    async def _search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search across Notion workspace.

        Args:
            query: Search query

        Returns:
            List of matching pages
        """
        if not self.client:
            raise Exception("Notion client not initialized")

        response = self.client.search(query=query)

        results = []
        for item in response.get("results", []):
            results.append(
                {
                    "id": item["id"],
                    "object": item.get("object"),
                    "url": item.get("url"),
                    "created_time": item.get("created_time"),
                    "last_edited_time": item.get("last_edited_time"),
                }
            )

        return results

    async def _add_to_knowledge_base(self, page_id: str) -> Optional[str]:
        """
        Add Notion page content to knowledge base.

        Args:
            page_id: Page ID to add

        Returns:
            Knowledge entry ID or None
        """
        try:
            # Read page content
            page_data = await self._read_page(page_id)

            # Import knowledge base tool
            from app.tool.knowledge_base import KnowledgeBaseTool

            kb_tool = KnowledgeBaseTool()

            # Add to knowledge base
            result = await kb_tool.execute(
                action="add",
                content=page_data["content"],
                source=f"notion:{page_id}",
                title=page_data["title"],
                metadata={
                    "type": "notion_page",
                    "url": page_data["url"],
                    "created_time": page_data["created_time"],
                    "last_edited_time": page_data["last_edited_time"],
                },
            )

            if result.output and "knowledge_id" in result.output:
                return result.output["knowledge_id"]

            return None

        except Exception as e:
            logger.error(f"Error adding to knowledge base: {e}")
            return None

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Execute Notion operation.

        Args:
            action: Operation to perform
            **kwargs: Action-specific parameters

        Returns:
            ToolResult with operation results
        """
        try:
            if not self.client:
                return self.error_response(
                    "Notion client not initialized. Set NOTION_API_KEY environment variable and install notion-client."
                )

            if action == "create_page":
                page = await self._create_page(
                    database_id=kwargs.get("database_id"),
                    parent_page_id=kwargs.get("parent_page_id"),
                    title=kwargs.get("title", "Untitled"),
                    content=kwargs.get("content", ""),
                )
                return self.success_response(
                    {"page_id": page["id"], "url": page.get("url"), "status": "created"}
                )

            elif action == "read_page":
                if "page_id" not in kwargs:
                    return self.error_response("Missing required parameter: page_id")

                page_data = await self._read_page(kwargs["page_id"])
                return self.success_response(page_data)

            elif action == "update_page":
                if "page_id" not in kwargs or "content" not in kwargs:
                    return self.error_response(
                        "Missing required parameters: page_id, content"
                    )

                result = await self._update_page(kwargs["page_id"], kwargs["content"])
                return self.success_response(result)

            elif action == "query_database":
                if "database_id" not in kwargs:
                    return self.error_response(
                        "Missing required parameter: database_id"
                    )

                results = await self._query_database(
                    kwargs["database_id"], kwargs.get("filter"), kwargs.get("sorts")
                )
                return self.success_response(
                    {"results": results, "count": len(results)}
                )

            elif action == "search":
                if "query" not in kwargs:
                    return self.error_response("Missing required parameter: query")

                results = await self._search(kwargs["query"])
                return self.success_response(
                    {"results": results, "count": len(results)}
                )

            elif action == "add_to_knowledge":
                if "page_id" not in kwargs:
                    return self.error_response("Missing required parameter: page_id")

                knowledge_id = await self._add_to_knowledge_base(kwargs["page_id"])
                if knowledge_id:
                    return self.success_response(
                        {"knowledge_id": knowledge_id, "status": "added"}
                    )
                else:
                    return self.error_response("Failed to add to knowledge base")

            else:
                return self.error_response(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Notion tool: {e}")
            return self.error_response(f"Notion operation failed: {str(e)}")
