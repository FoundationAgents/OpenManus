import asyncio
import os
import json

from app.agent.manus import Manus
from app.schema import Message, Role, Function as FunctionCall, ToolCall # Corrected import
from app.tool.checklist_tools import AddChecklistTaskTool, UpdateChecklistTaskTool, ViewChecklistTool, ResetCurrentTaskChecklistTool
from app.config import config
from app.logger import logger

async def setup_agent_for_improvisation_test():
    logger.info("Setting up agent state for improvisation test...")
    agent = await Manus.create()
    agent.current_step = 5 # Simulate a few steps have passed

    # 1. Initial User Prompt
    agent.memory.add_message(Message.user_message("crie dados sinteticos que depois podem ser usados pra simular machine learning com aleatoriedade... gere uma boa amostra de dados"))

    # Simulate initial checklist reset and decomposition by LLM
    # (as per the new automatic reset logic, checklist should be empty initially)
    # Then LLM adds initial tasks.

    # Simulate reset_current_task_checklist call and its effect (empty checklist)
    # In a real run, Manus.think() would call this. Here we manually ensure state.
    reset_tool = ResetCurrentTaskChecklistTool()
    await reset_tool.execute()
    logger.info("Simulated: Checklist reset.")

    # Simulate LLM adding initial tasks
    add_tool = AddChecklistTaskTool()
    task1_desc = "Definir os requisitos e características dos dados sintéticos a serem gerados para simulação de machine learning."
    task2_desc = "Implementar a geração de dados sintéticos com aleatoriedade em Python, atendendo aos requisitos definidos."
    task3_desc = "Testar a geração dos dados sintéticos e validar a amostra gerada."

    await add_tool.execute(task_description=task1_desc)
    await add_tool.execute(task_description=task2_desc)
    await add_tool.execute(task_description=task3_desc)
    logger.info("Simulated: Initial tasks added to checklist by LLM.")

    # Simulate agent deciding to ask for parameters for task1
    agent.memory.add_message(Message.assistant_message(content=f"Vou começar definindo os requisitos para a tarefa: '{task1_desc}'."))

    # Simulate agent marking task1 as 'Em Andamento'
    update_tool = UpdateChecklistTaskTool()
    await update_tool.execute(task_description=task1_desc, new_status="Em Andamento")
    logger.info(f"Simulated: Task '{task1_desc}' marked as 'Em Andamento'.")

    # 2. Agent asks for parameters (AskHuman)
    ask_human_question = (
        "Para prosseguir com a geração dos dados sintéticos para simulação de machine learning, preciso que você me informe os requisitos básicos:\n\n"
        "1. Tipo de problema de machine learning (ex: classificação binária, multi-classe, regressão, clustering).\n"
        "2. Quantidade aproximada de amostras (linhas).\n"
        "3. Quantidade e tipos de variáveis (numéricas, categóricas, booleanas etc.).\n"
        "4. Deseja correlação entre variáveis?\n"
        "5. Características especiais (ruído, outliers, desbalanceamento, etc.).\n"
        "6. Deseja variável alvo (target) para treino supervisionado?\n\n"
        "Por favor, forneça essas informações para que eu possa criar um perfil adequado para os dados sintéticos."
    )
    ask_human_tool_call_id = "ask_human_for_params_123"
    agent.memory.add_message(
        Message.from_tool_calls(
            tool_calls=[
                ToolCall(id=ask_human_tool_call_id, function=FunctionCall(name="AskHuman", arguments=json.dumps({"inquire": ask_human_question})))
            ],
            content="Preciso de mais detalhes para definir os requisitos dos dados."
        )
    )
    logger.info("Simulated: Agent planned AskHuman for data parameters.")

    # Simulate AskHuman tool result
    agent.memory.add_message(
        Message(role=Role.TOOL, name="AskHuman", tool_call_id=ask_human_tool_call_id, content=ask_human_question) # The tool echoes the question in its result for context
    )

    # 3. User responds with "tanto faz..."
    user_improvisation_response = "tanto fas tudo isso, capriche e improvite, o que eu quero saber mesmo é o T50"
    agent.memory.add_message(Message.user_message(user_improvisation_response))
    logger.info(f"Simulated: User response: '{user_improvisation_response}'")

    # 4. Agent marks task1 as Bloqueado (as seen in logs)
    # This happened in the log because the agent didn't know how to proceed with "tanto faz"
    # Our new prompt should prevent this, but we set it to reflect the state *before* the new prompt takes effect.
    await update_tool.execute(task_description=task1_desc, new_status="Bloqueado")
    agent.memory.add_message(Message.assistant_message(content=f"Tarefa '{task1_desc}' marcada como Bloqueado devido à falta de especificações claras."))
    logger.info(f"Simulated: Task '{task1_desc}' marked as 'Bloqueado'.")

    logger.info("Agent state setup complete. Current memory:")
    for i, msg in enumerate(agent.memory.messages):
        content_summary = str(msg.content)[:100] + "..." if msg.content and len(str(msg.content)) > 100 else str(msg.content)
        tc_summary = f", TC: {len(msg.tool_calls)}" if msg.tool_calls else ""
        logger.info(f"  Msg {i}: Role={msg.role}, Content='{content_summary}'{tc_summary}")

    # Save agent state to a file to be loaded by the next script
    # For simplicity, we'll just re-run this setup if needed, or pass agent instance if possible.
    # For this test, the next step will re-instantiate and replay messages.
    # This script's main purpose is to verify the setup and messages.

    # View final checklist state
    logger.info("Final checklist state after setup:")
    view_tool = ViewChecklistTool()
    final_checklist_view = await view_tool.execute()
    logger.info(final_checklist_view.output if final_checklist_view else "Could not view final checklist")

    await agent.cleanup() # Clean up agent resources like browser if they were implicitly started by tools.
    logger.info("Setup script finished.")

if __name__ == "__main__":
    asyncio.run(setup_agent_for_improvisation_test())
