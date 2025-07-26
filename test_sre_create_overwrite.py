import asyncio
from app.tool.str_replace_editor import StrReplaceEditor
from app.config import config
import os

async def main():
    # Ensure workspace exists
    os.makedirs(config.workspace_root, exist_ok=True)

    tool = StrReplaceEditor()
    checklist_content = """- [Pendente] [Agente: TestAgent] Minha Tarefa De Teste Com Tag De Agente
- [Pendente] Outra Tarefa Sem Tag De Agente"""
    checklist_path = str(config.workspace_root / "checklist_principal_tarefa.md")

    print(f"Attempting to create/overwrite checklist file at: {checklist_path}")
    # Use the 'create' command with overwrite=True
    # The StrReplaceEditor's execute method expects keyword arguments matching its parameters.
    # The 'create' command uses 'path' and 'file_text'. 'overwrite' is also a parameter.
    result = await tool.execute(
        command="create",
        path=checklist_path,
        file_text=checklist_content,
        overwrite=True # Explicitly overwrite
    )
    print(f"Tool execution result: {result.output if result and result.output else result.error if result else 'No result'}")

    # Verify file content
    if os.path.exists(checklist_path):
        with open(checklist_path, 'r') as f:
            content = f.read().strip() # Use strip to remove potential trailing newline for comparison
            expected_content_stripped = checklist_content.strip()
            print(f"Content of checklist_principal_tarefa.md after SRE create/overwrite:\n'''{content}'''")
            if content == expected_content_stripped:
                print("Test Passed: Checklist file content is as expected after SRE create/overwrite.")
            else:
                print(f"Test Failed: Checklist file content mismatch.\nExpected:\n'''{expected_content_stripped}'''\nGot:\n'''{content}'''")
    else:
        print("Test Failed: Checklist file does not exist after SRE create/overwrite.")

if __name__ == "__main__":
    asyncio.run(main())
