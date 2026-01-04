"""FreEco.AI Agent Framework

Integrates function calling with Tasks, Settings, and Knowledge Base.
"""

import asyncio
from typing import Optional

from .function_calling import MinimaxFunctionCaller, ToolParameter
from .knowledge_base import KnowledgeBaseManager
from .settings import SettingsManager
from .tasks import TaskManager


class FreEcoAgent:
    """FreEco.AI Agent with integrated tools and reasoning."""

    def __init__(self):
        """Initialize FreEco agent."""
        self.tasks = TaskManager()
        self.settings = SettingsManager()
        self.knowledge_base = KnowledgeBaseManager()

        # Initialize function caller
        settings_obj = self.settings.get_settings()
        if not settings_obj.minimax.api_key:
            raise ValueError("Minimax API key not configured")

        self.caller = MinimaxFunctionCaller(
            api_key=settings_obj.minimax.api_key,
            model="MiniMax-M2",
        )

        # Register all tools
        self._register_tools()

    def _register_tools(self):
        """Register all available tools."""
        # Task management tools
        self.caller.register_function(
            "create_task",
            "Create a new task with title, description, and priority",
            {
                "title": ToolParameter("title", "string", "Task title", required=True),
                "description": ToolParameter(
                    "description", "string", "Task description", required=True
                ),
                "priority": ToolParameter(
                    "priority",
                    "string",
                    "Task priority",
                    required=False,
                    enum=["low", "medium", "high", "critical"],
                ),
            },
            self._create_task,
        )

        self.caller.register_function(
            "list_tasks",
            "List all tasks with optional filtering",
            {
                "status": ToolParameter(
                    "status",
                    "string",
                    "Filter by status",
                    required=False,
                    enum=["pending", "in_progress", "completed", "cancelled"],
                ),
                "priority": ToolParameter(
                    "priority",
                    "string",
                    "Filter by priority",
                    required=False,
                    enum=["low", "medium", "high", "critical"],
                ),
            },
            self._list_tasks,
        )

        self.caller.register_function(
            "update_task",
            "Update task status",
            {
                "task_id": ToolParameter("task_id", "string", "Task ID", required=True),
                "status": ToolParameter(
                    "status",
                    "string",
                    "New status",
                    required=True,
                    enum=["pending", "in_progress", "completed", "cancelled"],
                ),
            },
            self._update_task,
        )

        # Knowledge base tools
        self.caller.register_function(
            "add_document",
            "Add a document to the knowledge base",
            {
                "title": ToolParameter(
                    "title", "string", "Document title", required=True
                ),
                "content": ToolParameter(
                    "content", "string", "Document content", required=True
                ),
                "category": ToolParameter(
                    "category",
                    "string",
                    "Document category",
                    required=False,
                    enum=["general", "research", "notes", "guides", "code", "other"],
                ),
            },
            self._add_document,
        )

        self.caller.register_function(
            "search_knowledge_base",
            "Search the knowledge base for documents",
            {
                "query": ToolParameter(
                    "query", "string", "Search query", required=True
                ),
            },
            self._search_knowledge_base,
        )

        self.caller.register_function(
            "list_documents",
            "List all documents in knowledge base",
            {
                "category": ToolParameter(
                    "category",
                    "string",
                    "Filter by category",
                    required=False,
                    enum=["general", "research", "notes", "guides", "code", "other"],
                ),
            },
            self._list_documents,
        )

        # Statistics tools
        self.caller.register_function(
            "get_task_stats",
            "Get task statistics",
            {},
            self._get_task_stats,
        )

        self.caller.register_function(
            "get_kb_stats",
            "Get knowledge base statistics",
            {},
            self._get_kb_stats,
        )

    # ===== TASK TOOLS =====

    async def _create_task(
        self, title: str, description: str, priority: str = "medium"
    ) -> str:
        """Create a task.

        Args:
            title: Task title.
            description: Task description.
            priority: Task priority.

        Returns:
            Task creation result.
        """
        import uuid

        task_id = str(uuid.uuid4())[:8]
        task = self.tasks.create_task(task_id, title, description, priority)
        return f"✅ Task created: {task.id} - {task.title}"

    async def _list_tasks(
        self, status: Optional[str] = None, priority: Optional[str] = None
    ) -> str:
        """List tasks.

        Args:
            status: Filter by status.
            priority: Filter by priority.

        Returns:
            Task list as formatted string.
        """
        tasks = self.tasks.list_tasks(status=status, priority=priority)
        if not tasks:
            return "📭 No tasks found."

        result = f"📋 Tasks ({len(tasks)}):\n"
        for task in tasks:
            result += f"  • [{task.id}] {task.title} ({task.priority.value}) - {task.status.value}\n"
        return result

    async def _update_task(self, task_id: str, status: str) -> str:
        """Update task status.

        Args:
            task_id: Task ID.
            status: New status.

        Returns:
            Update result.
        """
        task = self.tasks.update_task(task_id, status=status)
        if task:
            return f"✅ Task updated: {task.id} - {task.status.value}"
        return f"❌ Task not found: {task_id}"

    # ===== KNOWLEDGE BASE TOOLS =====

    async def _add_document(
        self, title: str, content: str, category: str = "general"
    ) -> str:
        """Add document to knowledge base.

        Args:
            title: Document title.
            content: Document content.
            category: Document category.

        Returns:
            Document creation result.
        """
        import uuid

        doc_id = str(uuid.uuid4())[:8]
        doc = self.knowledge_base.add_document(doc_id, title, content, category)
        return f"✅ Document added: {doc.id} - {doc.title} ({doc.size} bytes)"

    async def _search_knowledge_base(self, query: str) -> str:
        """Search knowledge base.

        Args:
            query: Search query.

        Returns:
            Search results as formatted string.
        """
        results = self.knowledge_base.search_documents(query)
        if not results:
            return f"❌ No documents found for: {query}"

        result = f"🔍 Search results for '{query}' ({len(results)} found):\n"
        for doc in results:
            result += f"  • {doc.title} ({doc.category.value}) - {doc.size} bytes\n"
        return result

    async def _list_documents(self, category: Optional[str] = None) -> str:
        """List documents.

        Args:
            category: Filter by category.

        Returns:
            Document list as formatted string.
        """
        docs = self.knowledge_base.list_documents(category=category)
        if not docs:
            return "📭 No documents found."

        result = f"📚 Documents ({len(docs)}):\n"
        for doc in docs:
            result += f"  • {doc.title} ({doc.category.value}) - {doc.size} bytes\n"
        return result

    # ===== STATISTICS TOOLS =====

    async def _get_task_stats(self) -> str:
        """Get task statistics.

        Returns:
            Statistics as formatted string.
        """
        stats = self.tasks.get_statistics()
        result = "📊 Task Statistics:\n"
        for key, value in stats.items():
            result += f"  • {key}: {value}\n"
        return result

    async def _get_kb_stats(self) -> str:
        """Get knowledge base statistics.

        Returns:
            Statistics as formatted string.
        """
        stats = self.knowledge_base.get_statistics()
        result = "📊 Knowledge Base Statistics:\n"
        result += f"  • Total Documents: {stats['total_documents']}\n"
        result += f"  • Total Size: {stats['total_size_mb']} MB\n"
        result += f"  • Categories: {stats['categories']}\n"
        return result

    async def run(self, user_input: str) -> str:
        """Run agent with user input.

        Args:
            user_input: User message.

        Returns:
            Agent response.
        """
        print(f"\n👤 User: {user_input}")
        response = await self.caller.call_with_tools(user_input)
        print(f"\n🤖 Agent: {response}")
        return response

    def clear_history(self):
        """Clear conversation history."""
        self.caller.clear_history()


async def run_agent_demo():
    """Run agent demo."""
    print("🌿 FreEco.AI Agent - Function Calling Demo")
    print("=" * 50)

    try:
        agent = FreEcoAgent()
        print("✅ Agent initialized successfully\n")

        # Demo interactions
        demos = [
            "Create a task to learn about Minimax M2 function calling",
            "List all my tasks",
            "Add a document about ecological principles to the knowledge base",
            "Search for documents about ecology",
            "Show me task statistics",
        ]

        for demo in demos:
            await agent.run(demo)
            print("-" * 50)

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(run_agent_demo())
