import asyncio
from app.tool.checklist_tools import UpdateChecklistTaskTool, ViewChecklistTool
from app.config import config
import os

async def main():
    os.makedirs(config.workspace_root, exist_ok=True)

    update_tool = UpdateChecklistTaskTool()
    view_tool = ViewChecklistTool()

    task_to_update_variations = [
        "Minha Tarefa De Teste Com Tag De Agente", # Exact description LLM might use (without agent tag)
        " minha tarefa de teste com tag de agente ", # With spaces and different case
        "[Agente: TestAgent] Minha Tarefa De Teste Com Tag De Agente" # With agent tag (less likely from LLM but good to test)
    ]
    new_status = "Em Andamento"

    print("Initial checklist state:")
    initial_view_result = await view_tool.execute()
    print(initial_view_result.output if initial_view_result else "Could not view checklist")
    print("-" * 30)

    for i, desc_variation in enumerate(task_to_update_variations):
        print(f"Attempting to update task using description variation {i+1}: '{desc_variation}' to status '{new_status}'")
        result = await update_tool.execute(task_description=desc_variation, new_status=new_status)
        print(f"Update Result {i+1}: {result.output if result and result.output else result.error if result else 'No result'}")

        print(f"Checklist state after attempt {i+1}:")
        current_view_result = await view_tool.execute()
        print(current_view_result.output if current_view_result else "Could not view checklist")
        print("-" * 30)

        # Check if the specific task was updated
        # This requires parsing the view_tool output or using ChecklistManager directly
        # For simplicity in this script, we'll rely on the tool's output message for success indication.
        if result and result.output and "atualizado para" in result.output:
            print(f"Test Variation {i+1} Passed: Task update reported success.")
            # Reset for next variation test if needed, or break if one success is enough
            # For this test, we want to see if it *can* be updated. If it's updated once, subsequent variations
            # might report "already has status" if we don't change new_status.
            # Let's change the status for the next attempt to ensure we're testing the match, not just "already set".
            new_status = "Concluído" if new_status == "Em Andamento" else "Em Andamento"
        elif result and result.error:
             print(f"Test Variation {i+1} Failed: Task update reported error: {result.error}")
        elif result and "Tarefa não encontrada" in result.output:
             print(f"Test Variation {i+1} Failed: Task update reported 'Tarefa não encontrada'.")
        else:
            print(f"Test Variation {i+1} Ambiguous: Tool output: {result.output if result else 'No result'}")


    # Test updating the second task as a control
    print("Attempting to update 'Outra Tarefa Sem Tag De Agente' to 'Concluído'")
    control_result = await update_tool.execute(task_description="Outra Tarefa Sem Tag De Agente", new_status="Concluído")
    print(f"Control Update Result: {control_result.output if control_result and control_result.output else control_result.error if control_result else 'No result'}")
    print(f"Final checklist state:")
    final_view_result = await view_tool.execute()
    print(final_view_result.output if final_view_result else "Could not view checklist")


if __name__ == "__main__":
    asyncio.run(main())
