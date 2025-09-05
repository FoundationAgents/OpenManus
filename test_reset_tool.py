import asyncio
from app.tool.checklist_tools import ResetCurrentTaskChecklistTool
from app.config import config
import os

async def main():
    # Ensure workspace exists (though it should from previous steps)
    os.makedirs(config.workspace_root, exist_ok=True)

    tool = ResetCurrentTaskChecklistTool()
    print(f"Executing ResetCurrentTaskChecklistTool...")
    result = await tool.execute()
    print(f"Tool execution result: {result.output if result else 'No result'}")

    # Verify file content
    checklist_path = config.workspace_root / "checklist_principal_tarefa.md"
    if os.path.exists(checklist_path):
        with open(checklist_path, 'r') as f:
            content = f.read()
            print(f"Content of checklist_principal_tarefa.md after reset:\n'''{content}'''")
            if content == "":
                print("Test Passed: Checklist file is empty after reset.")
            else:
                print("Test Failed: Checklist file is NOT empty after reset.")
    else:
        print("Test Failed: Checklist file does not exist after reset.")

if __name__ == "__main__":
    asyncio.run(main())
