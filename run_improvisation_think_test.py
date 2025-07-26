import asyncio
import os
import json

from app.agent.manus import Manus
from app.schema import Message, Role, Function as FunctionCall, ToolCall
from app.tool.checklist_tools import AddChecklistTaskTool, UpdateChecklistTaskTool, ViewChecklistTool, ResetCurrentTaskChecklistTool
from app.config import config
from app.logger import logger

async def run_think_on_improv_state():
    logger.info("Re-setting up agent state for improvisation 'think' test...")
    agent = await Manus.create()
    agent.current_step = 5 # Simulate a few steps have passed (same as setup script)

    # 1. Initial User Prompt
    agent.memory.add_message(Message.user_message("crie dados sinteticos que depois podem ser usados pra simular machine learning com aleatoriedade... gere uma boa amostra de dados"))

    # Simulate initial checklist reset and decomposition by LLM
    reset_tool = ResetCurrentTaskChecklistTool()
    await reset_tool.execute()

    add_tool = AddChecklistTaskTool()
    task1_desc = "Definir os requisitos e características dos dados sintéticos a serem gerados para simulação de machine learning."
    task2_desc = "Implementar a geração de dados sintéticos com aleatoriedade em Python, atendendo aos requisitos definidos."
    task3_desc = "Testar a geração dos dados sintéticos e validar a amostra gerada."

    await add_tool.execute(task_description=task1_desc)
    await add_tool.execute(task_description=task2_desc)
    await add_tool.execute(task_description=task3_desc)

    agent.memory.add_message(Message.assistant_message(content=f"Vou começar definindo os requisitos para a tarefa: '{task1_desc}'."))

    update_tool = UpdateChecklistTaskTool()
    await update_tool.execute(task_description=task1_desc, new_status="Em Andamento")

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
    # Use from_tool_calls to correctly create the message
    agent.memory.add_message(
        Message.from_tool_calls(
            tool_calls=[
                ToolCall(id=ask_human_tool_call_id, function=FunctionCall(name="AskHuman", arguments=json.dumps({"inquire": ask_human_question})))
            ],
            content="Preciso de mais detalhes para definir os requisitos dos dados."
        )
    )
    # Simulate AskHuman tool result in memory
    agent.memory.add_message(
        Message(role=Role.TOOL, name="AskHuman", tool_call_id=ask_human_tool_call_id, content=ask_human_question)
    )

    # 3. User responds with "tanto faz..."
    user_improvisation_response = "tanto fas tudo isso, capriche e improvite, o que eu quero saber mesmo é o T50"
    agent.memory.add_message(Message.user_message(user_improvisation_response))

    # 4. Agent marks task1 as Bloqueado (as per original log, to set the stage for the new `think` call)
    await update_tool.execute(task_description=task1_desc, new_status="Bloqueado")
    agent.memory.add_message(Message.assistant_message(content=f"Tarefa '{task1_desc}' marcada como Bloqueado devido à falta de especificações claras."))

    logger.info("Agent state re-established. Calling agent.think() now...")

    # CRUCIAL STEP: Call think()
    await agent.think()

    logger.info("agent.think() executed. Analyzing results...")
    logger.info("Final agent memory:")
    for i, msg in enumerate(agent.memory.messages):
        content_summary = str(msg.content)[:200] + "..." if msg.content and len(str(msg.content)) > 200 else str(msg.content)
        tc_summary = ""
        if msg.tool_calls:
            tc_names = [tc.function.name for tc in msg.tool_calls]
            tc_summary = f", Planned TCs: {tc_names}"
        logger.info(f"  Msg {i}: Role={msg.role}, Content='{content_summary}'{tc_summary}")

    if agent.tool_calls:
        logger.info(f"Agent planned tool_calls: {[tc.function.name for tc in agent.tool_calls]}")
        if "AskHuman" in [tc.function.name for tc in agent.tool_calls]:
            logger.error("Test Failed: Agent is still planning to AskHuman for parameters.")
        else:
            logger.info("Test Observation: Agent did NOT plan AskHuman. This is good.")
            # Further checks could be if it planned to update checklist or generate code.
    else:
        logger.info("Test Observation: Agent did not plan any tool calls in this step.")
        # Check the last assistant message for explanation
        last_assistant_msg = next((m for m in reversed(agent.memory.messages) if m.role == Role.ASSISTANT), None)
        if last_assistant_msg and last_assistant_msg.content:
            logger.info(f"Last assistant thought: {last_assistant_msg.content}")
            if "parâmetros padrão" in last_assistant_msg.content.lower() or "vou assumir" in last_assistant_msg.content.lower():
                logger.info("Test Passed: Agent mentioned using default/assumed parameters.")
            else:
                logger.warning("Test Observation: Agent did not explicitly mention default parameters in its last thought, but did not ask again.")
        else:
            logger.error("Test Failed: Agent did not plan tools and left no clear explanation.")


    logger.info("Final checklist state after think call:")
    view_tool = ViewChecklistTool()
    final_checklist_view = await view_tool.execute()
    logger.info(final_checklist_view.output if final_checklist_view else "Could not view final checklist")

    await agent.cleanup()
    logger.info("Improvisation 'think' test finished.")

if __name__ == "__main__":
    asyncio.run(run_think_on_improv_state())
