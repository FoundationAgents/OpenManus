"""CLI Commands for FreEco.AI Features

Provides command-line interface for Tasks, Settings, and Knowledge Base.
"""

import asyncio
from typing import Optional

from .knowledge_base import KnowledgeBaseManager
from .minimax_client import MinimaxClient, MinimaxMessage
from .settings import SettingsManager
from .tasks import TaskManager


class FreEcoCLI:
    """CLI interface for FreEco.AI features."""

    def __init__(self):
        """Initialize CLI."""
        self.tasks = TaskManager()
        self.settings = SettingsManager()
        self.knowledge_base = KnowledgeBaseManager()
        self.minimax: Optional[MinimaxClient] = None

    def initialize_minimax(self):
        """Initialize Minimax client from settings."""
        if self.settings.validate_minimax_config():
            config = self.settings.get_settings().minimax
            self.minimax = MinimaxClient(
                api_key=config.api_key,
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        else:
            print("❌ Minimax API key not configured. Run 'freeco settings minimax'")

    # ===== TASKS COMMANDS =====

    def task_create(
        self, title: str, description: str, priority: str = "medium"
    ) -> None:
        """Create a new task.

        Args:
            title: Task title.
            description: Task description.
            priority: Task priority (low, medium, high, critical).
        """
        import uuid

        task_id = str(uuid.uuid4())[:8]
        task = self.tasks.create_task(task_id, title, description, priority)
        print(f"✅ Task created: {task.id} - {task.title}")

    def task_list(
        self, status: Optional[str] = None, priority: Optional[str] = None
    ) -> None:
        """List tasks.

        Args:
            status: Filter by status (pending, in_progress, completed, cancelled).
            priority: Filter by priority (low, medium, high, critical).
        """
        tasks = self.tasks.list_tasks(status=status, priority=priority)
        if not tasks:
            print("📭 No tasks found.")
            return

        print(f"\n📋 Tasks ({len(tasks)}):")
        for task in tasks:
            status_icon = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "cancelled": "❌",
            }.get(task.status.value, "❓")

            print(
                f"  {status_icon} [{task.id}] {task.title} "
                f"({task.priority.value}) - {task.status.value}"
            )

    def task_update(self, task_id: str, status: Optional[str] = None) -> None:
        """Update task status.

        Args:
            task_id: Task ID.
            status: New status.
        """
        task = self.tasks.update_task(task_id, status=status)
        if task:
            print(f"✅ Task updated: {task.id} - {task.status.value}")
        else:
            print(f"❌ Task not found: {task_id}")

    def task_delete(self, task_id: str) -> None:
        """Delete a task.

        Args:
            task_id: Task ID.
        """
        if self.tasks.delete_task(task_id):
            print(f"✅ Task deleted: {task_id}")
        else:
            print(f"❌ Task not found: {task_id}")

    def task_stats(self) -> None:
        """Show task statistics."""
        stats = self.tasks.get_statistics()
        print("\n📊 Task Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    # ===== SETTINGS COMMANDS =====

    def settings_show(self) -> None:
        """Show current settings."""
        settings = self.settings.get_settings()
        print("\n⚙️  FreEco.AI Settings:")
        print(f"  Theme: {settings.theme.mode}")
        print(f"  Model: {settings.minimax.model}")
        print(f"  Temperature: {settings.minimax.temperature}")
        print(f"  Max Tokens: {settings.minimax.max_tokens}")
        print(f"  Auto-save: {settings.auto_save}")
        print(f"  Debug Mode: {settings.debug_mode}")

    def settings_minimax(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Configure Minimax settings.

        Args:
            api_key: Minimax API key.
            model: Model name.
            temperature: Temperature value.
            max_tokens: Max tokens value.
        """
        config = self.settings.update_minimax_config(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        print("✅ Minimax settings updated:")
        print(f"  Model: {config.model}")
        print(f"  Temperature: {config.temperature}")
        print(f"  Max Tokens: {config.max_tokens}")

    async def settings_test_minimax(self) -> None:
        """Test Minimax connection."""
        if not self.minimax:
            self.initialize_minimax()

        if not self.minimax:
            return

        print("🔍 Testing Minimax connection...")
        is_connected = await self.minimax.test_connection()
        if is_connected:
            print("✅ Minimax connection successful!")
        else:
            print("❌ Minimax connection failed. Check your API key.")

    # ===== KNOWLEDGE BASE COMMANDS =====

    def kb_add(
        self,
        title: str,
        content: str,
        category: str = "general",
        doc_type: str = "markdown",
    ) -> None:
        """Add document to knowledge base.

        Args:
            title: Document title.
            content: Document content.
            category: Document category.
            doc_type: Document type.
        """
        import uuid

        doc_id = str(uuid.uuid4())[:8]
        doc = self.knowledge_base.add_document(
            doc_id, title, content, category, doc_type
        )
        print(f"✅ Document added: {doc.id} - {doc.title}")

    def kb_list(self, category: Optional[str] = None) -> None:
        """List documents in knowledge base.

        Args:
            category: Filter by category.
        """
        docs = self.knowledge_base.list_documents(category=category)
        if not docs:
            print("📭 No documents found.")
            return

        print(f"\n📚 Knowledge Base ({len(docs)} documents):")
        for doc in docs:
            print(
                f"  📄 [{doc.id}] {doc.title} ({doc.category.value}) "
                f"- {doc.size} bytes"
            )

    def kb_search(self, query: str) -> None:
        """Search knowledge base.

        Args:
            query: Search query.
        """
        results = self.knowledge_base.search_documents(query)
        if not results:
            print(f"❌ No documents found for: {query}")
            return

        print(f"\n🔍 Search results for '{query}' ({len(results)} found):")
        for doc in results:
            print(f"  📄 {doc.title} ({doc.category.value})")

    def kb_delete(self, doc_id: str) -> None:
        """Delete document from knowledge base.

        Args:
            doc_id: Document ID.
        """
        if self.knowledge_base.delete_document(doc_id):
            print(f"✅ Document deleted: {doc_id}")
        else:
            print(f"❌ Document not found: {doc_id}")

    def kb_stats(self) -> None:
        """Show knowledge base statistics."""
        stats = self.knowledge_base.get_statistics()
        print("\n📊 Knowledge Base Statistics:")
        print(f"  Total Documents: {stats['total_documents']}")
        print(f"  Total Size: {stats['total_size_mb']} MB")
        print(f"  Average Doc Size: {stats['average_doc_size']} bytes")
        print(f"  Categories: {stats['categories']}")

    # ===== MINIMAX CHAT COMMANDS =====

    async def chat(self, prompt: str) -> None:
        """Chat with Minimax M2 Pro.

        Args:
            prompt: User prompt.
        """
        if not self.minimax:
            self.initialize_minimax()

        if not self.minimax:
            return

        print(f"\n💬 Sending to Minimax M2 Pro...")
        messages = [MinimaxMessage("user", prompt)]
        try:
            response = await self.minimax.chat(messages)
            print(f"\n🤖 Minimax Response:\n{response}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")

    async def chat_stream(self, prompt: str) -> None:
        """Stream chat with Minimax M2 Pro.

        Args:
            prompt: User prompt.
        """
        if not self.minimax:
            self.initialize_minimax()

        if not self.minimax:
            return

        print(f"\n💬 Streaming from Minimax M2 Pro...")
        messages = [MinimaxMessage("user", prompt)]
        try:
            print("\n🤖 Response: ", end="", flush=True)
            async for chunk in self.minimax.chat_stream(messages):
                print(chunk, end="", flush=True)
            print("\n")
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")


def run_cli():
    """Run CLI interface."""
    cli = FreEcoCLI()
    cli.initialize_minimax()

    print("🌿 FreEco.AI - Tasks, Settings & Knowledge Base")
    print("=" * 50)

    while True:
        try:
            command = input("\n> ").strip().split()
            if not command:
                continue

            cmd = command[0].lower()

            # Tasks commands
            if cmd == "task":
                if len(command) > 1:
                    subcmd = command[1].lower()
                    if subcmd == "create" and len(command) >= 4:
                        cli.task_create(command[2], " ".join(command[3:]))
                    elif subcmd == "list":
                        cli.task_list()
                    elif subcmd == "stats":
                        cli.task_stats()
                    else:
                        print("Usage: task [create|list|stats]")

            # Settings commands
            elif cmd == "settings":
                if len(command) > 1:
                    subcmd = command[1].lower()
                    if subcmd == "show":
                        cli.settings_show()
                    elif subcmd == "test":
                        asyncio.run(cli.settings_test_minimax())
                    else:
                        print("Usage: settings [show|test]")

            # Knowledge base commands
            elif cmd == "kb":
                if len(command) > 1:
                    subcmd = command[1].lower()
                    if subcmd == "list":
                        cli.kb_list()
                    elif subcmd == "search" and len(command) >= 3:
                        cli.kb_search(" ".join(command[2:]))
                    elif subcmd == "stats":
                        cli.kb_stats()
                    else:
                        print("Usage: kb [list|search|stats]")

            # Chat commands
            elif cmd == "chat" and len(command) >= 2:
                asyncio.run(cli.chat(" ".join(command[1:])))

            elif cmd == "exit":
                print("👋 Goodbye!")
                break

            else:
                print(
                    "Commands: task, settings, kb, chat, exit\n"
                    "Type 'help' for more information."
                )

        except KeyboardInterrupt:
            print("\n👋 Interrupted. Type 'exit' to quit.")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    run_cli()
