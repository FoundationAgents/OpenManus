import asyncio
from app.tool.str_replace_editor import StrReplaceEditor
from app.config import config
import os

async def main():
    os.makedirs(config.workspace_root, exist_ok=True)

    tool = StrReplaceEditor()
    checklist_content = """# Checklist Antigo
- [Concluído] Tarefa Velha 1
- [Pendente] Tarefa Velha 2 que não foi feita"""
    checklist_path = str(config.workspace_root / "checklist_principal_tarefa.md")

    print(f"Attempting to set initial checklist content at: {checklist_path}")
    result = await tool.execute(
        command="create", # Create implies overwrite if file_text is provided and overwrite=True
        path=checklist_path,
        file_text=checklist_content,
        overwrite=True
    )
    print(f"Tool execution result: {result.output if result and result.output else result.error if result else 'No result'}")

    # Verify file content
    if os.path.exists(checklist_path):
        with open(checklist_path, 'r') as f:
            content = f.read().strip()
            expected_content_stripped = checklist_content.strip()
            print(f"Content of checklist_principal_tarefa.md:\n'''{content}'''")
            if content == expected_content_stripped:
                print("Test Setup Succeeded: Checklist file content is as expected.")
            else:
                print(f"Test Setup Failed: Checklist file content mismatch.")
    else:
        print("Test Setup Failed: Checklist file does not exist.")

if __name__ == "__main__":
    asyncio.run(main())
