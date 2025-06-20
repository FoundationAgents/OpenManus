import re
from typing import Dict, List, Optional

from app.config import config
from app.exceptions import ToolError
from app.logger import logger
from app.tool.file_operators import LocalFileOperator


class ChecklistManager:
    """
    Manages a checklist stored in a markdown file.
    Provides functionalities to load, add, update tasks, and check their status.
    """

    def __init__(self, checklist_filename: str = "checklist_principal_tarefa.md"):
        """
        Initializes the ChecklistManager.

        Args:
            checklist_filename: The name of the markdown file for the checklist.
        """
        self.checklist_path = config.workspace_root / checklist_filename
        logger.info(f"ChecklistManager initialized for: {self.checklist_path}")
        self.tasks: List[
            Dict[str, str]
        ] = (
            []
        )  # e.g., [{'description': 'Do X', 'status': 'Pendente', 'agent': 'Manus'}]
        self.file_operator = LocalFileOperator()
        # _load_checklist will be called explicitly by the tool after instantiation if needed.

    def _normalize_description(self, description: str) -> str:
        """
        Normalizes a task description for comparison.
        - Converts to lowercase.
        - Strips leading/trailing whitespace.
        - Removes agent tags like "[Agente: ...]" for matching purposes.
        """
        # Remove agent tag if present, e.g., "[Agente: Manus] "
        # This regex matches "[Agente: any_non_bracket_chars] " (note the trailing space)
        # and also handles cases where there might not be a space after the tag.
        normalized_desc = re.sub(r"\[Agente:\s*[^\]]+\]\s*", "", description, flags=re.IGNORECASE)
        return normalized_desc.strip().lower()

    async def _load_checklist(self):
        """
        Loads tasks from the checklist file.
        If the file doesn't exist, logs it specifically and initializes an empty task list.
        If the file is empty, also initializes an empty task list.
        Parses content line by line and populates self.tasks.
        """
        logger.info(f"Attempting to load checklist from: {self.checklist_path}")
        try:
            content = await self.file_operator.read_file(str(self.checklist_path))
            # No specific check for "File not found" in content needed here,
            # as FileNotFoundError will be caught below if read_file raises it.

            if not content:  # Handles empty file content
                logger.info(
                    f"Checklist file at {self.checklist_path} is empty. Initializing with empty task list."
                )
                self.tasks = []
                return

            self.tasks = []  # Reset tasks before loading
            # Pattern to match: - [Status] [Agent: NAME] Description (agent part optional)
            # Status can be Pendente, Em Andamento, Concluído, Bloqueado (case insensitive)
            task_pattern = re.compile(
                r"-\s*\[(Pendente|Em Andamento|Concluído|Bloqueado)\]\s*(?:\[Agente:\s*(?P<agent>[^\]]+)\]\s*)?(?P<desc>.+)",
                re.IGNORECASE,
            )
            for line_number, line in enumerate(content.splitlines()):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                match = task_pattern.match(line)
                if match:
                    status = match.group(1).capitalize()  # Normalize status
                    agent = match.group("agent")
                    description = match.group("desc").strip()
                    task_entry = {
                        "description": description,
                        "status": status,
                        "agent": agent.strip() if agent else None,
                    }
                    self.tasks.append(task_entry)
                else:
                    # Log lines that don't match the expected format
                    logger.warning(
                        f"Could not parse checklist line: '{line}' in file {self.checklist_path} at line {line_number + 1}. Skipping."
                    )

            logger.info(f"Loaded {len(self.tasks)} tasks from {self.checklist_path}.")

        except ToolError as e:
            # Assuming ToolError from LocalFileOperator wraps FileNotFoundError or similar
            # The LocalFileOperator.read_file should ideally raise a specific FileNotFoundError
            # that can be caught, or its ToolError should clearly indicate "file not found".
            # For now, we check the string representation as before, but ideally,
            # LocalFileOperator().read_file would raise FileNotFoundError directly
            # if app.exceptions.ToolError is a wrapper.
            # If LocalFileOperator can raise FileNotFoundError directly (e.g. if it's not caught and wrapped by ToolError):
            # except FileNotFoundError:
            #    logger.info(f"Arquivo de checklist '{self.checklist_path}' não encontrado. Iniciando com uma checklist vazia.")
            #    self.tasks = []
            #
            # Given the current structure (ToolError wrapping), we stick to string checking for "File not found"
            if "File not found" in str(e) or "No such file or directory" in str(e):
                # This is the specific log message requested by the issue for FileNotFoundError
                logger.info(
                    f"Arquivo de checklist '{self.checklist_path}' não encontrado. Iniciando com uma checklist vazia."
                )
            else:
                # Log other ToolErrors
                logger.error(
                    f"ToolError occurred while reading checklist file {self.checklist_path}: {e}"
                )
            self.tasks = []  # Initialize with empty list for any ToolError

        except Exception as e:
            # Catch any other unexpected errors during loading/parsing
            logger.error(
                f"Unexpected error while loading checklist {self.checklist_path}: {e}"
            )
            self.tasks = []  # Initialize with empty list for safety

    async def _rewrite_checklist_file(self):
        """
        Rewrites the checklist file with the current tasks.
        """
        logger.info(
            f"Rewriting checklist file at: {self.checklist_path} with {len(self.tasks)} tasks."
        )
        content_to_write_list = []
        if self.tasks: # Only write tasks if there are any
            for task in self.tasks:
                agent_part = f" [Agente: {task['agent']}]" if task.get("agent") else ""
                content_to_write_list.append(
                    f"- [{task['status']}]" + agent_part + f" {task['description']}"
                )
            content_final = "\n".join(content_to_write_list) + "\n"
        else:
            # If there are no tasks (e.g., after a reset), write an empty file
            # or a file with just a header, depending on how _load_checklist handles it.
            # For simplicity and robustness, writing an empty string for an empty checklist.
            content_final = "" # Empty content for an empty checklist

        try:
            await self.file_operator.write_file(
                str(self.checklist_path), content_final
            )
            # Success log is now part of the calling logger.info line
        except ToolError as e:
            logger.error(f"Error writing checklist file {self.checklist_path}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error writing checklist file {self.checklist_path}: {e}"
            )

    async def reset_checklist(self):
        """Resets the checklist to an empty state."""
        logger.info(f"Resetting checklist at {self.checklist_path}.")
        self.tasks = []
        await self._rewrite_checklist_file() # This will now write an empty file

    def get_tasks(self) -> List[Dict[str, str]]:
        """
        Returns a copy of the current tasks.
        """
        return [task.copy() for task in self.tasks]

    async def add_task(
        self,
        task_description: str,
        status: str = "Pendente",
        assigned_agent: Optional[str] = None,
    ) -> bool:
        """
        Adds a new task to the checklist.

        Args:
            task_description: The description of the task.
            status: The initial status of the task (default: "Pendente").
            assigned_agent: Optional name of the agent responsible for this task.

        Returns:
            True if the task was added, False if a task with the same description already exists.
        """
        normalized_description = self._normalize_description(task_description)
        task_desc_stripped = task_description.strip()
        if self.get_task_by_description(normalized_description):
            logger.warning(f"Task '{task_desc_stripped}' already exists. Not adding.")
            return False

        new_task = {
            "description": task_desc_stripped,
            "status": status,
            "agent": assigned_agent,
        }
        self.tasks.append(new_task)
        logger.info(f"Adding task: '{task_desc_stripped}' with status '{status}'")
        await self._rewrite_checklist_file()
        return True

    async def update_task_status(self, task_description: str, new_status: str) -> bool:
        """
        Updates the status of an existing task.

        Args:
            task_description: The description of the task to update.
            new_status: The new status for the task.

        Returns:
            True if the task was found and updated, False otherwise.
        """
        normalized_description_to_find = self._normalize_description(task_description)
        for task in self.tasks:
            if (
                self._normalize_description(task["description"])
                == normalized_description_to_find
            ):
                if task["status"] == new_status:
                    logger.info(
                        f"Task '{task_description.strip()}' already has status '{new_status}'. No update needed."
                    )
                    return True
                task["status"] = new_status
                logger.info(
                    f"Updating task status: '{normalized_description_to_find}' to '{new_status}'"
                )
                await self._rewrite_checklist_file()
                return True

        logger.warning(f"Task not found for update: '{normalized_description_to_find}'")
        return False

    async def update_task_agent(self, task_description: str, new_agent: str) -> bool:
        """Updates the assigned agent for an existing task."""
        normalized_description_to_find = self._normalize_description(task_description)
        for task in self.tasks:
            if (
                self._normalize_description(task["description"])
                == normalized_description_to_find
            ):
                if task.get("agent") == new_agent:
                    logger.info(
                        f"Task '{task_description.strip()}' already assigned to '{new_agent}'. No update needed."
                    )
                    return True
                task["agent"] = new_agent
                logger.info(
                    f"Updating task agent: '{normalized_description_to_find}' to '{new_agent}'"
                )
                await self._rewrite_checklist_file()
                return True
        logger.warning(
            f"Task not found for agent update: '{normalized_description_to_find}'"
        )
        return False

    def get_task_by_description(
        self, task_description: str
    ) -> Optional[Dict[str, str]]:
        """
        Finds a task by its description (case-insensitive, whitespace-normalized).

        Args:
            task_description: The description of the task to find.

        Returns:
            The task dictionary if found, None otherwise.
        """
        normalized_description_to_find = self._normalize_description(task_description)
        for task in self.tasks:
            if (
                self._normalize_description(task["description"])
                == normalized_description_to_find
            ):
                return task.copy()  # Return a copy
        return None

    def is_task_complete(self, task_description: str) -> bool:
        """
        Checks if a specific task is marked as "Concluído".

        Args:
            task_description: The description of the task.

        Returns:
            True if the task is found and complete, False otherwise.
        """
        task = self.get_task_by_description(task_description)
        if task:
            return task["status"] == "Concluído"
        return False

    def are_all_tasks_complete(self) -> bool:
        """
        Checks if all tasks in the checklist are marked as "Concluído".

        Returns:
            True if all tasks are "Concluído", or if there are no tasks.
            False if any task is not "Concluído".
        """
        if not self.tasks:
            logger.info(
                "are_all_tasks_complete: No tasks in checklist, returning False."
            )
            return False  # No tasks means not complete
        for task in self.tasks:
            if (
                task.get("status", "").lower() != "concluído"
            ):  # Use .lower() for case-insensitivity
                logger.info(
                    f"are_all_tasks_complete: Task '{task.get('description')}' is not 'Concluído'. Status: '{task.get('status')}'. Returning False."
                )
                return False
        logger.info(
            "are_all_tasks_complete: All tasks are 'Concluído', returning True."
        )
        return True


if __name__ == "__main__":
    # Example Usage (for testing purposes)
    # Ensure workspace_root is set correctly in your config for this to run standalone
    # from app.config import Config # Assuming Config class can set workspace_root
    # config.workspace_root = Path(".") # Example: current directory as workspace

    logger.info(f"ChecklistManager example using workspace: {config.workspace_root}")

    manager = ChecklistManager(checklist_filename="test_checklist.md")

    # Clean up previous test file if exists
    if manager.checklist_path.exists():
        manager.checklist_path.unlink()
        logger.info(f"Removed old test_checklist.md for fresh test.")
        manager = ChecklistManager(
            checklist_filename="test_checklist.md"
        )  # Re-init with no file

    print(f"Initial tasks: {manager.get_tasks()}")

    manager.add_task("  Tarefa Inicial 1  ")
    manager.add_task("Tarefa Inicial 2", status="Em Andamento")
    manager.add_task("Tarefa já existente para teste de duplicidade")
    manager.add_task(
        "Tarefa já existente para teste de duplicidade"
    )  # Try adding duplicate

    print(f"Tasks after additions: {manager.get_tasks()}")

    manager.update_task_status("Tarefa Inicial 1", "Concluído")
    manager.update_task_status("tarefa inicial 2  ", "Concluído")  # Test normalization
    manager.update_task_status("Tarefa Inexistente", "Concluído")

    print(f"Tasks after updates: {manager.get_tasks()}")
    print(
        f"Is 'Tarefa Inicial 1' complete? {manager.is_task_complete('Tarefa Inicial 1')}"
    )
    print(f"Are all tasks complete? {manager.are_all_tasks_complete()}")

    manager.add_task("Tarefa Pendente Final", "Pendente")
    print(
        f"Are all tasks complete (after adding a pending one)? {manager.are_all_tasks_complete()}"
    )

    # Test loading from existing file
    print("\n--- Testing loading from existing file ---")
    manager_reloaded = ChecklistManager(checklist_filename="test_checklist.md")
    print(f"Tasks reloaded: {manager_reloaded.get_tasks()}")
    manager_reloaded.update_task_status("Tarefa Pendente Final", "Concluído")
    print(
        f"Are all tasks complete (reloaded manager)? {manager_reloaded.are_all_tasks_complete()}"
    )

    # Test empty file scenario
    print("\n--- Testing empty file scenario ---")
    empty_manager = ChecklistManager(checklist_filename="empty_test_checklist.md")
    if empty_manager.checklist_path.exists():
        empty_manager.checklist_path.unlink()
    empty_manager.file_operator.write_file(
        str(empty_manager.checklist_path), ""
    )  # create empty file
    empty_manager._load_checklist()  # force reload
    print(f"Tasks from empty file: {empty_manager.get_tasks()}")
    print(f"All complete from empty: {empty_manager.are_all_tasks_complete()}")

    # Test non-existent file scenario (after ensuring it's deleted)
    print("\n--- Testing non-existent file scenario ---")
    non_existent_manager = ChecklistManager(checklist_filename="non_existent_test.md")
    if non_existent_manager.checklist_path.exists():
        non_existent_manager.checklist_path.unlink()
    non_existent_manager._load_checklist()  # force reload after ensuring it's gone
    print(f"Tasks from non-existent file: {non_existent_manager.get_tasks()}")
    print(
        f"All complete from non-existent: {non_existent_manager.are_all_tasks_complete()}"
    )

    logger.info("ChecklistManager example finished.")
    # For cleanup, you might want to delete test_checklist.md
    # if manager.checklist_path.exists():
    #     manager.checklist_path.unlink()
    # if empty_manager.checklist_path.exists():
    #     empty_manager.checklist_path.unlink()
    # if non_existent_manager.checklist_path.exists():
    #     non_existent_manager.checklist_path.unlink()

"""
Note on `if __name__ == '__main__':` block:
This block is for basic testing. For it to run correctly standalone:
1. The `app.config.config.workspace_root` must be set.
   You might need to uncomment and adjust:
   # from app.config import Config
   # config.workspace_root = Path(".")
2. This script should be run from a context where `app.logger` and `app.exceptions` are accessible.
   Typically, this means running from the project root or having the PYTHONPATH set up correctly.
The example usage includes creating a test checklist file, adding/updating tasks, and checking completion statuses.
It also demonstrates reloading the checklist from the file.
"""
