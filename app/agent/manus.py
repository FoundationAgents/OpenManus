import os
import uuid
from typing import Dict, List, Optional, Any
from uuid import UUID as UUID_TYPE # Para type hinting do workflow_id

from pydantic import Field, model_validator, PrivateAttr

import json
import re
import ast
from app.agent.browser import BrowserContextHelper
from app.agent.toolcall import ToolCallAgent, ToolCall
from app.config import config
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import AgentState, Message, Role, Function as FunctionCall
from app.tool import Terminate, ToolCollection
from app.exceptions import ToolError
from app.tool.ask_human import AskHuman
from app.tool.bash import Bash
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.mcp import MCPClients, MCPClientTool
from app.tool.python_execute import PythonExecute
from app.tool.sandbox_python_executor import SandboxPythonExecutor
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.code_formatter import FormatPythonCode
from app.tool.code_editor_tools import ReplaceCodeBlock, ApplyDiffPatch, ASTRefactorTool
from app.tool.file_operators import LocalFileOperator
from app.tool.read_file_content import ReadFileContentTool
from app.tool.checklist_tools import ViewChecklistTool, AddChecklistTaskTool, UpdateChecklistTaskTool, ResetCurrentTaskChecklistTool
from app.tool.file_system_tools import CheckFileExistenceTool, ListFilesTool
from app.agent.checklist_manager import ChecklistManager
from .regex_patterns import re_subprocess
from app.tool.background_process_tools import ExecuteBackgroundProcessTool, CheckProcessStatusTool, GetProcessOutputTool

from app.event_bus.redis_bus import RedisEventBus


INTERNAL_SELF_ANALYSIS_PROMPT_TEMPLATE = """... (template como antes) ..."""
TOOL_CORRECTION_PROMPT_TEMPLATE = """... (template como antes) ..."""

PROMPT_CLASSIFY_USER_DIRECTIVE_TEMPLATE = """
Você é um assistente que ajuda a classificar a intenção de uma nova diretiva do usuário em relação a uma tarefa em andamento.
Dada a tarefa atual (representada pelo checklist), o histórico recente da conversa e a nova diretiva do usuário, classifique a diretiva como:

(A) TAREFA NOVA: A diretiva representa uma tarefa completamente nova e não relacionada com o checklist atual.
(B) MODIFICAÇÃO/CONTINUAÇÃO: A diretiva é uma modificação, adição, ou continuação da tarefa representada pelo checklist atual.
(C) ESCLARECIMENTO/PERGUNTA: A diretiva é uma pergunta ou pedido de esclarecimento que não altera fundamentalmente o plano de tarefas.

Contexto:
Checklist Atual:
{checklist_content}

Histórico Recente da Conversa (últimas ~3 mensagens):
{conversation_history}

Nova Diretiva do Usuário:
"{user_directive}"

Responda APENAS com a letra da classificação (A, B ou C).
Se for (A) ou (B) e a nova diretiva for clara, opcionalmente, após a letra e um hífen, forneça um resumo muito breve da nova tarefa ou da modificação.
Exemplos de resposta:
A - Gerar relatório de vendas trimestral.
B - Adicionar coluna de 'total' à tabela de dados.
C
"""


class Manus(ToolCallAgent):
    name: str = "Manus"
    description: str = "Um agente versátil que pode resolver várias tarefas usando múltiplas ferramentas, incluindo ferramentas baseadas em MCP"
    system_prompt: str = SYSTEM_PROMPT

    _mcp_clients: Optional[MCPClients] = PrivateAttr(default=None)
    _checklist_manager: ChecklistManager = PrivateAttr(default_factory=ChecklistManager)
    _monitoring_background_task: bool = PrivateAttr(default=False)
    _background_task_log_file: Optional[str] = PrivateAttr(default=None)
    _background_task_expected_artifact: Optional[str] = PrivateAttr(default=None)
    _background_task_artifact_path: Optional[str] = PrivateAttr(default=None)
    _background_task_description: Optional[str] = PrivateAttr(default=None)
    _background_task_last_log_size: int = PrivateAttr(default=0)
    _background_task_no_change_count: int = PrivateAttr(default=0)
    _MAX_LOG_NO_CHANGE_TURNS: int = PrivateAttr(default=3)

    _just_resumed_from_feedback_internal: bool = PrivateAttr(default=False) # Para lógica interna do Manus
    _trigger_failure_check_in_internal: bool = PrivateAttr(default=False)

    _pending_script_after_dependency: Optional[str] = PrivateAttr(default=None)
    _original_tool_call_for_pending_script: Optional[ToolCall] = PrivateAttr(default=None)
    _workspace_script_analysis_cache: Optional[Dict[str, Dict[str, Any]]] = PrivateAttr(default=None)
    _current_sandbox_pid: Optional[int] = PrivateAttr(default=None)
    _current_sandbox_pid_file: Optional[str] = PrivateAttr(default=None)
    _current_script_tool_call_id: Optional[str] = PrivateAttr(default=None)
    _fallback_attempted_for_tool_call_id: Optional[str] = PrivateAttr(default=None)
    _pending_fallback_tool_call: Optional[ToolCall] = PrivateAttr(default=None)
    _last_ask_human_for_fallback_id: Optional[str] = PrivateAttr(default=None)
    _autonomous_mode: bool = PrivateAttr(default=False)
    _reset_initiated_by_new_directive: bool = PrivateAttr(default=False)
    _pending_feedback_question: Optional[str] = PrivateAttr(default=None)

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name.lower(), AskHuman().name.lower()])
    browser_context_helper: Optional[BrowserContextHelper] = None

    def handle_tool_result(self, *args, **kwargs):
        pass

    async def step(self):
        # Lógica padrão: pensar e agir se métodos existirem
        if hasattr(self, "think") and hasattr(self, "act"):
            should_act = await self.think()
            if not should_act:
                return "Thinking complete - no action needed"
            return await self.act()
        return "No step logic implemented"

    async def should_request_feedback(self, *args, **kwargs):
        """Determine if a periodic check-in with the user should happen."""
        if self.max_steps > 0 and self.current_step >= self.max_steps:
            await self.periodic_user_check_in()
            return True
        return False

    def __init__(self, event_bus: RedisEventBus, **data):
        data['event_bus'] = event_bus
        super().__init__(**data)
        self.current_step = 0
        self._mcp_clients = MCPClients()
        self._checklist_manager = ChecklistManager(
            checklist_filename=f"manus_internal_checklist_{self.current_subtask_id or 'default'}.md"
        )
        self.available_tools = ToolCollection()  # começar vazio e depois adicionar
        self.available_tools.add_tools(
            PythonExecute(),
            BrowserUseTool(),
            StrReplaceEditor(),
            AskHuman(),
            Terminate(),
            Bash(),
            SandboxPythonExecutor(),
            ReadFileContentTool(),
            ViewChecklistTool(),
            AddChecklistTaskTool(),
            UpdateChecklistTaskTool(),
            ResetCurrentTaskChecklistTool(),
            CheckFileExistenceTool(),
            ListFilesTool(),
            ExecuteBackgroundProcessTool(),
            CheckProcessStatusTool(),
            GetProcessOutputTool(),
            FormatPythonCode(),
            ReplaceCodeBlock(),
            ApplyDiffPatch(),
            ASTRefactorTool(),
        )
        self._initialized = False

async def _classify_user_directive(
    self,
    user_directive: str,
    checklist_content: str,
    conversation_history: str,
) -> tuple[str, Optional[str]]:
    """
    Consulta o LLM para classificar a diretiva do usuário.
    Retorna uma tupla: (classificação (A, B ou C), resumo opcional).
    """
    if not self.llm:
        logger.error("LLM não disponível para _classify_user_directive.")
        return "B", "LLM indisponível, assumindo modificação da tarefa atual."

    prompt = PROMPT_CLASSIFY_USER_DIRECTIVE_TEMPLATE.format(
        checklist_content=checklist_content,
        conversation_history=conversation_history,
        user_directive=user_directive,
    )
    messages_for_llm = [Message.user_message(prompt)]

    try:
        response_text = await self.llm.ask(messages=messages_for_llm, stream=False)
        response_text = response_text.strip()

        classification = "C"  # padrão: necessidade de esclarecimento
        summary = None

        if response_text:
            parts = response_text.split("-", 1)
            classification_char = parts[0].strip().upper()
            if classification_char in ["A", "B", "C"]:
                classification = classification_char

            if len(parts) > 1:
                summary = parts[1].strip()

        logger.info(
            f"Diretiva do usuário classificada como '{classification}' com resumo: '{summary if summary else 'N/A'}'"
        )
        return classification, summary
    except Exception as e:
        logger.error(f"Erro ao classificar diretiva do usuário via LLM: {e}")
        return "B", f"Erro na classificação, assumindo modificação. Detalhe: {e}"


    def __getstate__(self):
        state = super().__getstate__()
        state.pop('_mcp_clients', None)
        state.pop('_checklist_manager', None)
        state.pop('browser_context_helper', None)
        # available_tools é recriado em __setstate__
        return state

    def __setstate__(self, state):
        super().__setstate__(state)
        self._mcp_clients = MCPClients()
        # O nome do arquivo do checklist pode precisar ser ajustado com base no current_subtask_id,
        # que pode não estar disponível diretamente ao desserializar.
        # Uma solução seria o Orchestrator passar o subtask_id ao restaurar.
        self._checklist_manager = ChecklistManager(checklist_filename=f"manus_internal_checklist_{self.current_subtask_id or 'default_restored'}.md")
        self.browser_context_helper = BrowserContextHelper(self)
        
        self.available_tools = ToolCollection(
            PythonExecute(), BrowserUseTool(), StrReplaceEditor(), AskHuman(), Terminate(),
            Bash(), SandboxPythonExecutor(), ReadFileContentTool(),
            ViewChecklistTool(), AddChecklistTaskTool(), UpdateChecklistTaskTool(), ResetCurrentTaskChecklistTool(),
            CheckFileExistenceTool(), ListFilesTool(),
            ExecuteBackgroundProcessTool(), CheckProcessStatusTool(), GetProcessOutputTool(),
            FormatPythonCode(), ReplaceCodeBlock(), ApplyDiffPatch(), ASTRefactorTool()
        )
        self._initialized = False
        # self.connected_servers é restaurado por super()

    @model_validator(mode="after")
    def initialize_manus_specific_helpers(self) -> "Manus":
        if not self.browser_context_helper:
            self.browser_context_helper = BrowserContextHelper(self)
        return self

    @classmethod
    async def create(cls, event_bus: RedisEventBus, **kwargs) -> "Manus":
        initial_messages = kwargs.pop('memory_messages', None)
        instance = cls(event_bus=event_bus, **kwargs)
        if initial_messages:
            instance.memory.add_messages(initial_messages)
        logger.info(f"Agente Manus criado. System prompt (primeiros 200 chars): {instance.system_prompt[:200]}")
        # ... (lógica de recuperação de tarefas em background como antes, se mantida) ...
        await instance.initialize_mcp_servers()
        instance._initialized = True
        return instance

    async def initialize_mcp_servers(self) -> None: # Implementação como antes
        pass
    async def connect_mcp_server(self, server_url: str, server_id: str = "", use_stdio: bool = False, stdio_args: List[str] = None) -> None:
        pass
    async def disconnect_mcp_server(self, server_id: str = "") -> None:
        pass

    def _can_self_reflect_on_failure(self) -> bool:
        return True

    async def _self_reflection_on_tool_failure(
        self, original_command: ToolCall, failure_observation: str, task_context: str
    ) -> Optional[ToolCall]:
        # ... (implementação como definida anteriormente, usando TOOL_CORRECTION_PROMPT_TEMPLATE) ...
        logger.info(f"Manus: Iniciando auto-reflexão para falha da ferramenta '{original_command.function.name}'.")
        recent_messages_str = "\n".join(
            [f"  - {msg.role}: {msg.content[:150]}..." for msg in self.memory.messages[-3:] if msg.content]
        )
        tool_args_str = original_command.function.arguments
        try:
            parsed_args = json.loads(tool_args_str)
            tool_args_str_for_prompt = json.dumps(parsed_args, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            tool_args_str_for_prompt = tool_args_str
        prompt_for_correction = TOOL_CORRECTION_PROMPT_TEMPLATE.format(
            task_context=task_context, tool_name=original_command.function.name,
            tool_args=tool_args_str_for_prompt, failure_observation=failure_observation,
            recent_messages=recent_messages_str
        )
        try:
            correction_system_prompt = ("Você é um assistente de IA especialista em depurar e corrigir falhas na execução de ferramentas. "
                                        "Analise a falha e forneça uma sugestão de correção no formato JSON especificado.")
            llm_response_str = await self.llm.ask(
                messages=[Message.user_message(content=prompt_for_correction)],
                system_msgs=[Message.system_message(content=correction_system_prompt)],
                temperature=0.1
            )
            suggestion_json_str = self._extract_json_from_response(llm_response_str)
            if suggestion_json_str:
                # ... (lógica de parse do JSON e retorno de ToolCall ou None como antes) ...
                pass # Implementação completa omitida para brevidade, mas segue o já definido
        except Exception as e:
            logger.error(f"Erro durante o ciclo de auto-reflexão do LLM: {e}", exc_info=True)
        return None # Fallback

    async def think(self) -> bool:
        # Adicionar estado do checklist interno ao contexto, se houver
        await self._checklist_manager._load_checklist() # Garante que o checklist interno está carregado
        internal_checklist_tasks = self._checklist_manager.get_tasks()
        if internal_checklist_tasks:
            formatted_checklist = ["Checklist Interno da Subtarefa Atual:"]
            for task in internal_checklist_tasks:
                agent_display = f" [Agente: {task.get('agent')}]" if task.get("agent") else ""
                formatted_checklist.append(f"- [{task.get('status', 'N/A')}]" + agent_display + f" {task.get('description', 'Sem descrição')}")
            self.memory.add_message(Message.system_message("\n".join(formatted_checklist)))

        # Lógica para lidar com _new_task_directive_received para o checklist *interno*
        if self._reset_initiated_by_new_directive: # Esta flag agora seria para o checklist interno
            logger.info(f"Manus: Resetando checklist interno para subtarefa {self.current_subtask_id} devido a nova diretiva.")
            await self._checklist_manager.add_task("Decompor nova diretiva da subtarefa e popular checklist interno.") # Tarefa inicial
            self._reset_initiated_by_new_directive = False
            # O `think` de ToolCallAgent será chamado e provavelmente usará `ViewChecklistTool` ou `AddChecklistTaskTool`
            # para o checklist interno.

        # Lógica do BrowserContextHelper (se este Manus for um agente de navegador)
        # if self.browser_context_helper and "browser" in self.name.lower(): # Melhorar esta verificação
        #    browser_state_prompt = await self.browser_context_helper.format_next_step_prompt()
        #    self.memory.add_message(Message.system_message(f"Contexto do Navegador Atual:\n{browser_state_prompt}"))

        return await super().think() # Chama o think de ToolCallAgent

    async def handle_tool_result(self, tool_name: str, tool_call_id: str, tool_observation: str, subtask_id: str, workflow_id: str) -> None:
        await super().handle_tool_result(tool_name, tool_call_id, tool_observation, subtask_id, workflow_id)

        # Se super().handle_tool_result já decidiu falhar a subtarefa (e.g., após auto-correção falhar), não fazer mais nada.
        # Precisamos de uma forma de verificar isso. Por enquanto, se tool_calls não foi preenchido por uma correção:
        if not self.tool_calls and not tool_observation.startswith("Error:"): # Se não houve erro ou foi corrigido

            is_manus_checklist_complete = await self._is_internal_checklist_complete_for_subtask()
            ask_human_planned_tool_call: Optional[ToolCall] = None

            if is_manus_checklist_complete:
                logger.info(f"Manus: Checklist interno para subtarefa {self.current_subtask_id} completo.")
                if not self._autonomous_mode:
                    ask_human_planned_tool_call = await self.periodic_user_check_in(is_final_check=True)
                else:
                    logger.info(f"Manus: Modo autônomo. Marcando subtarefa {self.current_subtask_id} como concluída.")
                    await self._publish_subtask_completed(result={"response": f"Subtarefa {self.current_subtask_id} concluída autonomamente."})
                    return

            elif not self._autonomous_mode and self.current_step > 0 and \
                 self.max_steps_per_subtask > 0 and \
                 self.current_step % (self.max_steps_per_subtask // 2) == 0 and \
                 self.current_step < self.max_steps_per_subtask: # Check-in no meio da subtarefa
                ask_human_planned_tool_call = await self.periodic_user_check_in(is_final_check=False, is_failure_scenario=False)

            if ask_human_planned_tool_call:
                self.tool_calls = [ask_human_planned_tool_call]
                await self.act()
                return

            if not is_manus_checklist_complete:
                logger.info(f"Manus: Subtarefa {self.current_subtask_id} não concluída e sem input humano pendente. Novo ciclo de think.")
                await self._process_current_subtask_iteration() # Continua a subtarefa
            elif self._autonomous_mode and is_manus_checklist_complete:
                 await self._publish_subtask_completed(result={"response": f"Subtarefa {self.current_subtask_id} concluída autonomamente."})
            else: # Checklist completo, não autônomo, mas sem AskHuman (talvez periodic_user_check_in retornou None)
                logger.warning(f"Manus: Checklist interno completo para {self.current_subtask_id}, mas sem AskHuman final. Concluindo subtarefa.")
                await self._publish_subtask_completed(result={"response": f"Subtarefa {self.current_subtask_id} concluída."})


    async def _is_internal_checklist_complete_for_subtask(self) -> bool:
        await self._checklist_manager._load_checklist()
        if not self._checklist_manager.get_tasks():
            # Se o prompt da subtarefa for muito simples, pode não precisar de checklist interno.
            # Considerar o prompt da subtarefa atual (self.current_subtask_prompt) para decidir.
            # Por agora, se não há checklist interno, consideramos "não aplicável" ou "completo" para não bloquear.
            # Isso precisa de uma heurística melhor. Se o SYSTEM_PROMPT sempre instrui a criar, então
            # um checklist vazio após o primeiro `think` pode significar que a subtarefa é trivial.
            # Vamos assumir que se o checklist está vazio, a parte gerenciada pelo Manus está "completa".
            if self.current_step > 1: # Se já passou do primeiro passo de think
                 logger.info(f"Manus: Checklist interno para subtarefa {self.current_subtask_id} está vazio após o passo inicial. Considerando completo.")
                 return True
            return False # No primeiro passo, um checklist vazio significa que precisa ser populado.
        return self._checklist_manager.are_all_tasks_complete()

    async def periodic_user_check_in(self, is_final_check: bool = False, is_failure_scenario: bool = False) -> Optional[ToolCall]:
        # ... (lógica adaptada como antes para construir a pergunta) ...
        # Esta lógica precisa ser robusta. Usar o INTERNAL_SELF_ANALYSIS_PROMPT_TEMPLATE
        # para gerar o `relatorio_autoanalise` como antes.
        # Por enquanto, uma pergunta placeholder:
        question_for_human = "Este é um check-in. Como devo proceder com a subtarefa?"
        if is_final_check:
            question_for_human = f"O checklist interno para a subtarefa '{self.current_subtask_id}' parece completo. Deseja marcar esta subtarefa como concluída?"
        if is_failure_scenario:
            # Aqui, o `relatorio_autoanalise` seria sobre a falha da subtarefa do Manus.
            question_for_human = f"Encontrei um problema com a subtarefa '{self.current_subtask_id}'. [Relatório de Análise da Falha da Subtarefa aqui]. Como devo proceder?"

        logger.info(f"Manus: Planejando AskHuman para check-in na subtarefa {self.current_subtask_id}: {question_for_human[:100]}")

        # Obter o ID do último checkpoint relevante. O Orchestrator pode precisar passar isso para o agente.
        # Ou o agente pode precisar de acesso ao checkpointer para encontrar o último checkpoint para este workflow/subtarefa.
        # Por agora, deixaremos como None.
        relevant_checkpoint_id = None
        # Se o agente tivesse acesso ao checkpointer:
        # if self.checkpointer and self.current_workflow_id:
        #    latest_chkpt_data = await self.checkpointer.load_latest_checkpoint_data(self.current_workflow_id)
        #    if latest_chkpt_data: relevant_checkpoint_id = str(latest_chkpt_data["checkpoint_id"])

        ask_human_args = {
            "inquire": question_for_human,
            "workflow_id": str(self.current_workflow_id) if self.current_workflow_id else "unknown_workflow",
            "subtask_id": self.current_subtask_id or "unknown_subtask",
            "relevant_checkpoint_id": relevant_checkpoint_id
        }
        return ToolCall(
            id=f"ask_human_manus_{uuid.uuid4().hex[:4]}",
            function=FunctionCall(name=AskHuman().name, arguments=json.dumps(ask_human_args))
        )

    async def cleanup(self): # Sobrescreve cleanup de ToolCallAgent
        logger.info(f"Manus ({self.name}) cleanup starting.")
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()
        if self._mcp_clients and self._initialized:
            await self.disconnect_mcp_server()
            self._initialized = False
        await super().cleanup() # Chama ToolCallAgent.cleanup() que chama BaseAgent.cleanup()
        logger.info(f"Manus ({self.name}) cleanup complete.")

    # Métodos auxiliares mantidos
    def _sanitize_text_for_file(self, text_content: str) -> str: # ... (como antes) ...
        if not isinstance(text_content, str): return text_content
        return text_content.replace('\u0000', '')
    def _extract_python_code(self, text: str) -> str: # ... (como antes) ...
        if "```python" in text: return text.split("```python")[1].split("```")[0].strip()
        if "```" in text: return text.split("```")[1].split("```")[0].strip()
        return text.strip()
    async def _execute_self_coding_cycle(self, task_prompt_for_llm: str, max_attempts: int = 3) -> Dict[str, Any]: # ... (como antes, mas usando self.available_tools.get_tool) ...
        logger.info(f"Iniciando ciclo de auto-codificação para tarefa: {task_prompt_for_llm}")
        # ... (implementação completa omitida para brevidade, mas deve usar self.available_tools.get_tool)
        return {"success": False, "message": "Self-coding cycle not fully implemented in this refactor."}
    def _extract_json_from_response(self, llm_response: str) -> Optional[str]: # ... (como antes) ...
        logger.debug(f"Tentando extrair JSON da resposta do LLM: '{llm_response[:500]}...'")
        match = re.search(r"```json\s*([\s\S]+?)\s*```", llm_response)
        if match: return match.group(1).strip()
        response_stripped = llm_response.strip()
        if response_stripped.startswith("{") and response_stripped.endswith("}"): return response_stripped
        logger.warning("Nenhum bloco de código JSON encontrado na resposta do LLM para extração.")
        return None


    def _build_targeted_analysis_prompt(self, script_content: str, stdout: str, stderr: str, original_task: str) -> str:
        """Constrói o prompt para o LLM analisar e sugerir uma correção baseada em ferramenta."""
        ANALYSIS_PROMPT_TEMPLATE = """Você é um "Python Code Analyzer and Corrector".
Sua tarefa é analisar um script Python que falhou, juntamente com sua saída padrão (stdout) e erro padrão (stderr).
Você DEVE retornar um objeto JSON especificando uma única ferramenta para aplicar a correção e os parâmetros para essa ferramenta.

**Ferramentas Disponíveis para Correção:**
1.  **`replace_code_block`**:
    *   Descrição: Substitui um bloco de código entre `start_line` e `end_line` (inclusive, 1-indexado) com `new_content`.
    *   Parâmetros: `path` (string, caminho do arquivo - **NÃO INCLUA ESTE PARÂMETRO, será adicionado automaticamente**), `start_line` (integer), `end_line` (integer), `new_content` (string).
    *   Uso: Ideal para substituir funções inteiras, blocos lógicos, ou seções maiores de código.
2.  **`apply_diff_patch`**:
    *   Descrição: Aplica um patch no formato unified diff ao arquivo.
    *   Parâmetros: `path` (string, caminho do arquivo - **NÃO INCLUA ESTE PARÂMETRO**), `patch_content` (string, conteúdo do diff).
    *   Uso: Bom para múltiplas pequenas alterações, alterações não contíguas, ou quando a lógica do diff é mais fácil de expressar. O diff deve ser gerado em relação ao script original fornecido.
3.  **`ast_refactor`**:
    *   Descrição: Realiza refatorações baseadas em AST. Operação inicial: `replace_function_body`.
    *   Parâmetros para `replace_function_body`: `path` (string - **NÃO INCLUA ESTE PARÂMETRO**), `operation` (string, fixo: "replace_function_body"), `target_node_name` (string, nome da função), `new_code_snippet` (string, novo corpo da função, sem o `def ...`).
    *   Uso: Mais seguro para refatorações estruturais, como substituir o corpo de uma função sem afetar sua assinatura ou o restante do arquivo.
4.  **`format_python_code`**:
    *   Descrição: Formata o código Python usando Ruff/Black. Pode corrigir erros de sintaxe/indentação simples.
    *   Parâmetros: `code` (string, o código completo a ser formatado - **IMPORTANTE: para esta ferramenta, em vez de "path", forneça o conteúdo do script no parâmetro "code" dentro de "tool_params"**).
    *   Uso: Tente esta ferramenta PRIMEIRO para erros de SyntaxError ou IndentationError. Se o LLM for solicitado após uma falha do formatador, não sugira `format_python_code` novamente.

**Formato JSON Obrigatório para a Resposta:**
A resposta DEVE ser uma string JSON que possa ser parseada, contendo um objeto com as seguintes chaves:
- "tool_to_use": string, o nome da ferramenta escolhida (e.g., "replace_code_block", "apply_diff_patch", "ast_refactor", "format_python_code").
- "tool_params": object, um dicionário contendo os parâmetros específicos para a ferramenta escolhida (NÃO inclua "path" aqui, exceto para "format_python_code" onde "code" é usado em vez de "path").
- "comment": string, uma breve explicação do erro e da correção que você está aplicando.

**Exemplos de Resposta JSON:**

Para `replace_code_block`:
```json
{
  "tool_to_use": "replace_code_block",
  "tool_params": {
    "start_line": 10,
    "end_line": 15,
    "new_content": "def minha_funcao_corrigida():\\n    return 'corrigido'"
  },
  "comment": "A função 'minha_funcao' original tinha um erro de lógica. Substituindo-a completamente."
}
```

Para `apply_diff_patch`:
```json
{
  "tool_to_use": "apply_diff_patch",
  "tool_params": {
    "patch_content": "--- a/script_original.py\\n+++ b/script_corrigido.py\\n@@ -1,3 +1,3 @@\\n- linha_com_erro\\n+ linha_corrigida\\n  outra_linha\\n"
  },
  "comment": "Corrigido um typo na linha 1 e ajustada uma variável na linha 5 (exemplo de diff)."
}
```

Para `ast_refactor` (operação `replace_function_body`):
```json
{
  "tool_to_use": "ast_refactor",
  "tool_params": {
    "operation": "replace_function_body",
    "target_node_name": "minha_funcao_com_erro",
    "new_code_snippet": "  # Novo corpo da função\\n  resultado = calcula_algo()\\n  return resultado"
  },
  "comment": "O corpo da função 'minha_funcao_com_erro' foi reescrito para corrigir um bug de cálculo."
}
```

Para `format_python_code` (se for um erro de sintaxe e o formatador automático ainda não foi tentado):
```json
{
  "tool_to_use": "format_python_code",
  "tool_params": {
    "code": "# Conteúdo completo do script aqui...\nprint('hello') # Exemplo"
  },
  "comment": "Tentando corrigir possível erro de sintaxe/indentação simples com o formatador."
}
```

**Importante:**
- Escolha APENAS UMA ferramenta.
- Forneça as correções no formato JSON EXATO especificado acima.
- Se o script estiver fundamentalmente errado e precisar de uma reescrita completa que não se encaixe bem em uma única chamada de ferramenta, ou se nenhuma correção for óbvia, você PODE retornar um JSON com `tool_to_use": null` e um comentário explicando. Ex: `{"tool_to_use": null, "tool_params": {}, "comment": "O script está muito quebrado, sugiro reescrevê-lo com base na tarefa original."}`.
- Analise o `stderr` cuidadosamente para identificar a causa raiz do erro.
- O objetivo é fazer a correção mais apropriada usando a ferramenta mais adequada.
- **NÃO inclua o parâmetro "path" em "tool_params" para `replace_code_block`, `apply_diff_patch`, `ast_refactor`. Ele será adicionado automaticamente. Para `format_python_code`, use o parâmetro "code" em `tool_params` para passar o conteúdo do script.**

**Script Original com Erro:**
```python
{script_content}
```

**Saída Padrão (stdout) da Execução Falha:**
```
{stdout}
```

**Erro Padrão (stderr) da Execução Falha:**
```
{stderr}
```

**Tarefa Original que o Script Tentava Realizar:**
{original_task}

Agora, forneça sua análise e a sugestão de ferramenta e parâmetros no formato JSON especificado.
"""
        return ANALYSIS_PROMPT_TEMPLATE.format(
            script_content=script_content,
            stdout=stdout,
            stderr=stderr,
            original_task=original_task
        )

    async def think(self) -> bool:
        self.planned_tool_calls = []
        if not self._initialized:
            await self.initialize_mcp_servers()
            self._initialized = True

        # --- Lógica para Nova Diretiva de Tarefa Recebida ---
        if hasattr(self, '_new_task_directive_received') and self._new_task_directive_received:
            logger.info("Nova diretiva de tarefa recebida detectada. Planejando reset do checklist e reinício da contagem de passos.")
            self.tool_calls = [
                ToolCall(
                    id=str(uuid.uuid4()),
                    function=FunctionCall(
                        name=ResetCurrentTaskChecklistTool().name,
                        arguments=json.dumps({})
                    )
                )
            ]
            self.memory.add_message(Message.from_tool_calls(
                tool_calls=self.tool_calls,
                content="Uma nova diretiva de tarefa foi recebida. Resetando o checklist para iniciar a nova tarefa."
            ))
            self.current_step = 0
            self._new_task_directive_received = False
            self._reset_initiated_by_new_directive = True # SINALIZAR que o reset foi por nova diretiva
            return True

        # --- Lógica de Verificação Inicial e Reset Automático do Checklist ---
        # --- Lógica de Edição Manual do Checklist ---
        # Esta lógica será acionada se for o início de uma nova interação principal (novo prompt do usuário)
        # ou se _new_task_directive_received foi setado por periodic_user_check_in.
        # A flag _reset_initiated_by_new_directive ajuda a coordenar isso.

        # Se um novo prompt de usuário foi recebido e ainda não processamos a edição do checklist para ele.
        # self.current_step == 1 é um bom indicador de um novo ciclo de 'run' principal.
        # _new_task_directive_received seria True se periodic_user_check_in classificou como TAREFA NOVA.

        # Condição para invocar o editor de checklist:
        # 1. É o primeiro passo de pensamento para o prompt atual do usuário.
        # 2. Ou, _new_task_directive_received foi explicitamente definido como True (vindo de periodic_user_check_in).
        # A flag _just_resumed_from_feedback_internal é usada para evitar re-editar o checklist
        # imediatamente após o usuário responder a um periodic_user_check_in que *não* era para uma nova tarefa.

        # Heurística: se a última mensagem não for do assistente (ou seja, é do usuário ou sistema),
        # e não acabamos de resumir de um feedback que não era uma nova tarefa,
        # então provavelmente é um novo input do usuário que precisa de edição do checklist.
        last_msg_role = self.memory.messages[-1].role if self.memory.messages else None

        # Invocaremos o editor do checklist se:
        # - For o primeiro passo (novo prompt principal).
        # - Ou se uma nova diretiva de tarefa foi sinalizada (vindo de periodic_user_check_in).
        # - E não acabamos de voltar de um feedback que era apenas uma continuação.
        needs_checklist_edit = False
        if self.current_step == 1 and not self._just_resumed_from_feedback_internal:
            needs_checklist_edit = True
            logger.info("Manus.think: current_step == 1 e não resumindo de feedback de continuação. Edição de checklist necessária.")
        elif hasattr(self, '_new_task_directive_received') and self._new_task_directive_received:
            needs_checklist_edit = True
            logger.info("Manus.think: _new_task_directive_received é True. Edição de checklist necessária.")

        if needs_checklist_edit:
            edited_successfully = await self._handle_checklist_editing_cycle()
            # Resetar a flag _new_task_directive_received após a tentativa de edição.
            if hasattr(self, '_new_task_directive_received') and self._new_task_directive_received:
                self._new_task_directive_received = False # Consumir a flag

            if not edited_successfully:
                logger.error("Manus.think: Ciclo de edição do checklist falhou ou não produziu um checklist válido. O agente pode não conseguir prosseguir corretamente.")
            else:
                logger.info("Manus.think: Checklist editado com sucesso. Prosseguindo com o `super().think()`.")

        self._just_resumed_from_feedback_internal = False
        # --- Fim da Lógica de Edição Manual do Checklist ---


        # Check for autonomous mode trigger in initial user prompt
        # Esta verificação só faz sentido no primeiro ciclo real de `think` para um novo prompt do usuário.
        # `self.current_step == 1` e `not self._autonomous_mode` é uma boa condição.
        if self.current_step == 1 and not self._autonomous_mode:
            # Encontra a última mensagem do usuário para verificar o comando de modo autônomo.
            # Isso é mais robusto do que assumir que a primeira mensagem na memória é o prompt atual.
            last_user_message_for_autonomy_check = None
            for msg_idx in range(len(self.memory.messages) -1, -1, -1):
                if self.memory.messages[msg_idx].role == Role.USER:
                    last_user_message_for_autonomy_check = self.memory.messages[msg_idx]
                    break

            if last_user_message_for_autonomy_check and last_user_message_for_autonomy_check.content:
                prompt_content = last_user_message_for_autonomy_check.content.strip().lower()
                if prompt_content.startswith("execute em modo autônomo:") or prompt_content.startswith("modo autônomo:"):
                    self._autonomous_mode = True
                    logger.info("Modo autônomo ativado por prompt do usuário.")
                    self.memory.add_message(Message.assistant_message("Modo autônomo ativado. Não pedirei permissão para continuar a cada ciclo de etapas."))
                    # Opcional: Remover a frase gatilho do prompt para não confundir o LLM depois
                    # No entanto, isso pode ser complexo se a mensagem do usuário já foi usada para edição do checklist.
                    # É mais seguro apenas adicionar a mensagem do assistente e deixar o LLM ignorar a frase gatilho.

        last_message = self.memory.messages[-1] if self.memory.messages else None
        # Etapa A: Detectar falha do SandboxPythonExecutor e perguntar ao usuário
        if (
            last_message
            and last_message.role == Role.TOOL
            and hasattr(last_message, 'name') and last_message.name == SandboxPythonExecutor().name
            and hasattr(last_message, 'tool_call_id') # Garantir que tool_call_id existe
        ):
            tool_call_id_from_message = last_message.tool_call_id
            if tool_call_id_from_message != self._fallback_attempted_for_tool_call_id: # Evitar processar o mesmo erro múltiplas vezes
                try:
                    # last_message.content é a string de observação, formatada por ToolCallAgent.act()
                    # Ex: "Observed output of cmd `sandbox_python_executor` executed (converted from <class 'dict'>):\n{'stdout': '', 'stderr': \"ToolError: {...}\", 'exit_code': -2}"
                    # Precisamos extrair o dicionário principal.
                    tool_result_content = None
                    # Tenta encontrar um dicionário JSON na string.
                    # Esta regex busca por algo que comece com '{' e termine com '}' e seja o último na string,
                    # ou o único JSON na string.
                    # É um pouco frágil; o ideal seria que ToolCallAgent.act formatasse de uma maneira mais parseável
                    # ou que SandboxPythonExecutor retornasse ToolResult e o erro fosse processado de forma estruturada.
                    match = re.search(r"(\{[\s\S]*\})\s*$", last_message.content)
                    if match:
                        python_dict_like_str = match.group(1)
                        try:
                            # Usar ast.literal_eval para converter a string em um dicionário Python
                            tool_result_content = ast.literal_eval(python_dict_like_str)
                            logger.info(f"Dicionário de resultado da ferramenta (via ast.literal_eval) extraído para fallback: {tool_result_content}")
                        except (ValueError, SyntaxError) as e:
                            logger.error(f"Falha ao parsear string com ast.literal_eval: '{python_dict_like_str}'. Erro: {e}. Conteúdo original: {last_message.content}")
                            tool_result_content = None # Garante que não prossiga se o parse falhar
                    else:
                        logger.warning(f"Não foi possível extrair um dicionário (formato Python) da observação para fallback: {last_message.content}")
                        tool_result_content = None

                    if isinstance(tool_result_content, dict) and tool_result_content.get("exit_code") == -2:
                        # A mensagem de erro detalhada está em tool_result_content.get("stderr")
                        # Esta string pode conter ela mesma uma representação de dicionário.
                        # Ex: "ToolError: {'success': false, 'error_type': 'environment', ...}"
                        error_detail_str = tool_result_content.get("stderr", "")

                        # Tentar extrair a mensagem mais interna do ToolError se presente
                        tool_error_message = error_detail_str # Default to the whole stderr string
                        if error_detail_str.startswith("ToolError: "):
                            try:
                                inner_error_dict_str = error_detail_str.replace("ToolError: ", "", 1)
                                inner_error_dict = ast.literal_eval(inner_error_dict_str)
                                if isinstance(inner_error_dict, dict) and "message" in inner_error_dict:
                                    tool_error_message = inner_error_dict["message"]
                            except (ValueError, SyntaxError) as e_inner:
                                logger.warning(f"Não foi possível parsear o conteúdo detalhado do ToolError em stderr: '{error_detail_str}'. Erro: {e_inner}. Usando stderr completo.")

                        logger.warning(
                            f"SandboxPythonExecutor falhou com exit_code -2 (erro de criação do sandbox) para tool_call_id {tool_call_id_from_message}. "
                            f"Mensagem de erro principal: '{tool_error_message}' (Extraído de stderr: '{error_detail_str}')"
                            "Iniciando lógica de fallback."
                        )

                        # Encontrar a ToolCall original que invocou o SandboxPythonExecutor
                        original_tool_call_for_sandbox = None
                        for msg_idx in range(len(self.memory.messages) - 2, -1, -1):
                            prev_msg = self.memory.messages[msg_idx]
                            if prev_msg.role == Role.ASSISTANT and prev_msg.tool_calls:
                                for tc in prev_msg.tool_calls:
                                    if tc.id == tool_call_id_from_message:
                                        original_tool_call_for_sandbox = tc
                                        break
                                if original_tool_call_for_sandbox:
                                    break

                        if original_tool_call_for_sandbox:
                            self._pending_fallback_tool_call = original_tool_call_for_sandbox

                            # tool_error_message foi definida algumas linhas acima com o erro específico do sandbox
                            ask_human_question = (
                                f"A execução segura no sandbox falhou com o seguinte erro: '{tool_error_message}'.\n"
                                "Deseja tentar executar o script diretamente na máquina do agente? \n"
                                "ATENÇÃO: Isso pode ser um risco de segurança se o script for desconhecido ou malicioso. \n"
                                "Responda 'sim' para executar diretamente ou 'não' para cancelar."
                            )
                            self.memory.add_message(Message.assistant_message(
                                "Alerta: Problema ao executar script em ambiente seguro (sandbox)."
                            )) # Mensagem curta antes de AskHuman

                            ask_human_tool_call_id = str(uuid.uuid4())
                            self._last_ask_human_for_fallback_id = ask_human_tool_call_id
                            self.tool_calls = [
                                ToolCall(
                                    id=ask_human_tool_call_id,
                                    function=FunctionCall(
                                        name=AskHuman().name,
                                        arguments=json.dumps({"inquire": ask_human_question})
                                    )
                                )
                            ]
                            logger.info(f"Solicitando permissão do usuário para fallback da tool_call {tool_call_id_from_message} para PythonExecute.")
                            return True # Retorna para executar AskHuman
                        else:
                            logger.error(f"Não foi possível encontrar a ToolCall original do assistente para o tool_call_id {tool_call_id_from_message} que falhou no sandbox.")

                except json.JSONDecodeError as e:
                    logger.error(f"Falha ao parsear o conteúdo do resultado da ferramenta para lógica de fallback (Sandbox): {last_message.content}. Erro: {e}")
                except Exception as e_fallback_init:
                    logger.error(f"Erro inesperado durante a inicialização do fallback do sandbox: {e_fallback_init}", exc_info=True)

        # Etapa B: Processar resposta do usuário para fallback
        if (
            last_message
            and last_message.role == Role.USER
            and self._pending_fallback_tool_call # Havia uma pergunta pendente
            # Verifica se a mensagem do usuário é uma resposta à pergunta de fallback
            # Isso pode ser melhorado se AskHuman ToolCall/ToolMessage tiverem IDs que possam ser rastreados.
            # Por enquanto, confiamos que a última mensagem do usuário após _pending_fallback_tool_call ser setado é a resposta.
            # Adicionamos _last_ask_human_for_fallback_id para uma verificação mais robusta se a mensagem anterior foi o AskHuman
        ):
            is_direct_fallback_response = False
            if len(self.memory.messages) >= 2:
                prev_message = self.memory.messages[-2] # A mensagem da ferramenta AskHuman
                if prev_message.role == Role.TOOL and hasattr(prev_message, 'name') and prev_message.name == AskHuman().name and \
                   hasattr(prev_message, 'tool_call_id') and prev_message.tool_call_id == self._last_ask_human_for_fallback_id:
                    is_direct_fallback_response = True

            if not is_direct_fallback_response:
                logger.info("A última mensagem do usuário não é uma resposta direta à pergunta de fallback do sandbox. Ignorando para fins de fallback.")
            else:
                user_response_text = last_message.content.strip().lower()
                original_failed_tool_call = self._pending_fallback_tool_call
                # Reset pending state immediately, regardless of outcome, to prevent reprocessing.
                self._pending_fallback_tool_call = None
                self._last_ask_human_for_fallback_id = None

                if user_response_text == "sim":
                    logger.info(f"Usuário aprovou fallback para PythonExecute para a tool_call original ID: {original_failed_tool_call.id}")
                    self._fallback_attempted_for_tool_call_id = original_failed_tool_call.id
                    try:
                        original_args = json.loads(original_failed_tool_call.function.arguments)
                        fallback_args = {}
                        fallback_tool_name = PythonExecute().name
                        assistant_message_on_fallback = ""

                        if "file_path" in original_args and original_args["file_path"]:
                            script_file_path = original_args["file_path"]
                            fallback_args["file_path_to_execute"] = script_file_path
                            # Define working_directory como o diretório do script, se não especificado de outra forma.
                            # A ferramenta PythonExecute já tem lógica para isso se WD não for passado.
                            # Para ser explícito aqui:
                            fallback_args["working_directory"] = os.path.dirname(script_file_path)
                            assistant_message_on_fallback = (
                                f"Ok, tentando executar o script '{os.path.basename(script_file_path)}' "
                                f"diretamente usando '{fallback_tool_name}' no diretório '{fallback_args['working_directory']}'. "
                                "Lembre-se dos riscos de segurança."
                            )
                            logger.info(f"Preparando fallback para executar arquivo '{script_file_path}' com PythonExecute.")

                        elif "code" in original_args and original_args["code"]:
                            fallback_args["code"] = original_args["code"]
                            # working_directory pode ser herdado ou deixado como None se não houver contexto de arquivo.
                            # Se original_args tivesse um working_directory, poderíamos usá-lo.
                            if "working_directory" in original_args:
                                fallback_args["working_directory"] = original_args["working_directory"]
                            assistant_message_on_fallback = (
                                f"Ok, tentando executar o código fornecido diretamente usando '{fallback_tool_name}'. "
                                "Lembre-se dos riscos de segurança."
                            )
                            logger.info("Preparando fallback para executar código string com PythonExecute.")
                        else:
                            logger.error(f"Não foi possível realizar fallback para PythonExecute: 'code' ou 'file_path' não encontrado nos args originais: {original_args}")
                            self.memory.add_message(Message.assistant_message("Erro interno: não foi possível encontrar o código ou caminho do arquivo para a execução de fallback."))
                            self.tool_calls = []
                            return True # Let LLM re-evaluate.

                        original_timeout = original_args.get("timeout")
                        if original_timeout is not None:
                            fallback_args["timeout"] = original_timeout

                        new_fallback_tool_call = ToolCall(
                            id=str(uuid.uuid4()), # New ID for the fallback attempt
                            function=FunctionCall(
                                name=fallback_tool_name, # Use a variável
                                arguments=json.dumps(fallback_args)
                            )
                        )
                        self.tool_calls = [new_fallback_tool_call]
                        self.memory.add_message(Message.assistant_message(assistant_message_on_fallback))
                        logger.info(f"ToolCall de fallback planejada para {fallback_tool_name}: {new_fallback_tool_call}")

                    except json.JSONDecodeError as e:
                        logger.error(f"Falha ao parsear argumentos da tool_call original durante o fallback: {original_failed_tool_call.function.arguments}. Erro: {e}")
                        self.memory.add_message(Message.assistant_message("Erro interno ao preparar a execução de fallback. Não é possível continuar com esta tentativa."))
                        self.tool_calls = [] # Clear any planned calls
                    except Exception as e_fallback_exec:
                        logger.error(f"Erro inesperado durante a preparação ou execução do fallback para PythonExecute: {e_fallback_exec}", exc_info=True)
                        self.memory.add_message(Message.assistant_message(f"Erro inesperado ao tentar fallback: {e_fallback_exec}"))
                        self.tool_calls = [] # Clear any planned calls

                    return True # Execute the planned fallback tool_call (or let LLM re-evaluate if errors occurred)

                elif user_response_text == "não":
                    self.tool_calls = [new_fallback_tool_call]
                    self.memory.add_message(Message.assistant_message(
                        f"Ok, tentando executar o código diretamente usando '{PythonExecute().name}'. "
                        "Lembre-se dos riscos de segurança."
                    ))
                    logger.info(f"ToolCall de fallback planejada para PythonExecute: {new_fallback_tool_call}")
                    return True # Execute the planned fallback tool_call (or let LLM re-evaluate if errors occurred)

                elif user_response_text == "não":
                    logger.info(f"Usuário negou fallback para PythonExecute para a tool_call original ID: {original_failed_tool_call.id}")
                    self.memory.add_message(Message.assistant_message(
                        "Entendido. A execução do script foi cancelada conforme sua solicitação."
                    ))
                    self.tool_calls = [] # No further action on this script
                    self._fallback_attempted_for_tool_call_id = original_failed_tool_call.id # Mark as handled
                    return True # Let LLM decide what to do next.

                else: # Unrecognized response
                    logger.info(f"Resposta não reconhecida do usuário ('{user_response_text}') para a pergunta de fallback. Tratando como 'não'.")
                    self.memory.add_message(Message.assistant_message(
                        f"Resposta '{last_message.content}' não reconhecida. Assumindo 'não' para a execução direta. A execução do script foi cancelada."
                    ))
                    self.tool_calls = [] # No further action on this script
                    self._fallback_attempted_for_tool_call_id = original_failed_tool_call.id # Mark as handled
                    return True # Let LLM decide what to do next.

        # --- Fim da Lógica de Fallback ---

        user_prompt_message = next((msg for msg in reversed(self.memory.messages) if msg.role == Role.USER), None)
        user_prompt_content = user_prompt_message.content if user_prompt_message else ""
        SELF_CODING_TRIGGER = "execute self coding cycle: "
        if user_prompt_content.startswith(SELF_CODING_TRIGGER):
            if self._monitoring_background_task:
                logger.info("Novo ciclo de auto-codificação iniciado, parando monitoramento de tarefa em background anterior.")
                self._monitoring_background_task = False
                self._background_task_log_file = None
                self._background_task_expected_artifact = None
                self._background_task_artifact_path = None
                self._background_task_description = None
                self._background_task_last_log_size = 0
                self._background_task_no_change_count = 0
            task_description = user_prompt_content[len(SELF_CODING_TRIGGER):].strip()
            if not task_description:
                self.memory.add_message(Message.assistant_message("Por favor, forneça uma descrição da tarefa para o ciclo de auto-codificação."))
                self.tool_calls = []
                return True
            logger.info(f"Acionando ciclo de auto-codificação para a tarefa: {task_description}")
            self.memory.add_message(Message.assistant_message(f"Iniciando ciclo de auto-codificação para: {task_description}. Vou relatar o resultado."))
            cycle_result = await self._execute_self_coding_cycle(task_description)
            if cycle_result.get("status_code") == "SANDBOX_CREATION_FAILED":
                self.memory.add_message(Message.assistant_message(
                    f"Falha ao executar o ciclo de auto-codificação para '{task_description}'.\n"
                    f"Motivo: Não foi possível criar o ambiente seguro (sandbox) para execução do código.\n"
                    f"Detalhes: {cycle_result.get('details', 'Erro desconhecido na criação do sandbox.')}\n"
                    f"Por favor, verifique se o Docker está em execução e se a imagem '{config.sandbox.image_name}' está disponível ou pode ser baixada."
                ))
            elif cycle_result.get("status_code") == "SANDBOX_COPY_FAILED":
                self.memory.add_message(Message.assistant_message(
                    f"Falha ao executar o ciclo de auto-codificação para '{task_description}'.\n"
                    f"Motivo: Não foi possível copiar o script para o ambiente seguro (sandbox).\n"
                    f"Detalhes: {cycle_result.get('message', 'Erro desconhecido na cópia para o sandbox.')}"
                ))
            elif cycle_result.get("success"):
                success_message = f"Ciclo de auto-codificação concluído com sucesso para '{task_description}'.\n\n"
                success_message += f"Saída (stdout) do script:\n{cycle_result.get('stdout', 'Sem saída stdout.')}\n"
                if cycle_result.get("workspace_listing"):
                    success_message += f"\nConteúdo atual do diretório de trabalho principal ({config.workspace_root}):\n{cycle_result.get('workspace_listing')}\n"
                success_message += f"\nQuaisquer arquivos mencionados como 'salvos' ou 'gerados' pelo script (e copiados de /tmp do sandbox, se aplicável) devem estar visíveis acima ou diretamente no diretório {config.workspace_root}."
                self.memory.add_message(Message.assistant_message(success_message))
            else:
                error_details = cycle_result.get('stderr', cycle_result.get('last_execution_result', {}).get('stderr', 'Sem saída stderr.'))
                self.memory.add_message(Message.assistant_message(
                    f"Ciclo de auto-codificação falhou para '{task_description}'.\n"
                    f"Motivo: {cycle_result.get('message', 'Erro desconhecido.')}\n"
                    f"Última saída de erro (stderr):\n{error_details}"
                ))
            self.tool_calls = []
            return True

        original_prompt = self.next_step_prompt
        recent_messages_for_browser = self.memory.messages[-3:] if self.memory.messages else []
        browser_in_use = any(
            tc.function.name == BrowserUseTool().name
            for msg in recent_messages_for_browser # Nome da variável corrigido
            if msg.tool_calls
            for tc in msg.tool_calls
        )
        if browser_in_use:
            if self.browser_context_helper:
                self.next_step_prompt = (
                    await self.browser_context_helper.format_next_step_prompt()
                )
            else:
                logger.warning("BrowserContextHelper não inicializado, não é possível formatar next_step_prompt para o navegador.")

        result = await super().think()
        self.next_step_prompt = original_prompt

        # Sobrescrever chamadas PythonExecute que executam scripts externos para usar SandboxPythonExecutor
        if self.tool_calls:
            new_tool_calls = []
            for tool_call in self.tool_calls:
                # Linha original onde o erro ocorre:
                if tool_call.function.name == "python_execute":
                    try:
                        args = json.loads(tool_call.function.arguments)
                        code_to_execute = args.get("code")
                        original_timeout = args.get("timeout")

                        if isinstance(code_to_execute, str) and code_to_execute:
                            script_path_match = None
                            # Regex para subprocess.run(['python3', 'script.py', ...])
                            # Permite variações como "python", "python3", "python3.x"
                            # Captura o caminho do script ('([^']+\.py)')
                            # Usando o padrão regex externalizado
                            # re_subprocess agora é importado diretamente
                            # Regex para os.system('python3 script.py ...')
                            # Nota: Este regex para os.system pode precisar de externalização semelhante se se tornar complexo ou causar problemas.
                            re_os_system = r"os\.system\s*\(\s*['\"](?:python|python3)(?:\.[\d]+)?\s+([^'\" ]+\.py)['\"].*?\)"

                            match_subprocess = re.search(re_subprocess, code_to_execute) # re_subprocess é agora o padrão compilado
                            if match_subprocess:
                                script_path_match = match_subprocess.group(1)
                            else:
                                match_os_system = re.search(re_os_system, code_to_execute)
                                if match_os_system:
                                    script_path_match = match_os_system.group(1)

                            if script_path_match:
                                resolved_script_path = ""
                                if os.path.isabs(script_path_match):
                                    resolved_script_path = os.path.normpath(script_path_match)
                                else:
                                    resolved_script_path = str(config.workspace_root / script_path_match)

                                # Verificação de segurança: Garante que o caminho resolvido está dentro do workspace
                                if os.path.abspath(resolved_script_path).startswith(str(config.workspace_root)):
                                    logger.info(f"Sobrescrevendo chamada PythonExecute para script '{script_path_match}' para SandboxPythonExecutor com caminho '{resolved_script_path}'.")
                                    new_arguments = {"file_path": resolved_script_path}
                                    if original_timeout is not None:
                                        new_arguments["timeout"] = original_timeout

                                    # Cria um novo objeto ToolCall para a sobrescrita
                                    overridden_tool_call = ToolCall(
                                        id=tool_call.id, # Mantém o mesmo ID
                                        function=Function(
                                            name=SandboxPythonExecutor.name,
                                            arguments=json.dumps(new_arguments)
                                        )
                                    )
                                    new_tool_calls.append(overridden_tool_call)
                                    continue # Passa para a próxima tool_call
                                else:
                                    logger.warning(f"Chamada PythonExecute para script '{script_path_match}' resolvida para '{resolved_script_path}', que está fora do workspace. Não sobrescrevendo.")
                            else:
                                logger.info(f"Chamada PythonExecute com código não correspondeu a padrões de execução de script. Código: {code_to_execute[:100]}...")
                        else:
                            logger.warning("Chamada PythonExecute não tinha argumento 'code' válido.")
                    except json.JSONDecodeError:
                        logger.warning(f"Falha ao parsear argumentos para PythonExecute: {tool_call.function.arguments}. Usando chamada de ferramenta original.")
                    except Exception as e:
                        logger.error(f"Erro durante lógica de sobrescrita de PythonExecute: {e}. Usando chamada de ferramenta original.")

                new_tool_calls.append(tool_call) # Adiciona tool_call original ou não-PythonExecute
            self.tool_calls = new_tool_calls

        if self.tool_calls and self.tool_calls[0].function.name == Bash().name: # Verifica a primeira chamada de ferramenta
            try:
                args = json.loads(self.tool_calls[0].function.arguments)
                command_str = args.get("command", "")
                log_file_pattern = re.escape(str(config.workspace_root)) + r"/[^\s]+\.log"
                match = re.match(r"^\s*(.+?)\s*>\s*(" + log_file_pattern + r")\s*2>&1\s*&\s*$", command_str)
                if match:
                    actual_command = match.group(1).strip()
                    log_file = match.group(2).strip()
                    self._monitoring_background_task = True
                    self._background_task_log_file = log_file
                    self._background_task_description = f"Execução do comando: {actual_command}"
                    self._background_task_last_log_size = 0
                    self._background_task_no_change_count = 0
                    actual_command_lower = actual_command.lower()
                    script_name_match = re.search(r"python\d*\s+([^\s]+\.py)", actual_command)
                    if script_name_match:
                        script_path_in_command = script_name_match.group(1)
                        base_script_name = os.path.basename(script_path_in_command).replace(".py", "")
                        if "csv" in self._background_task_description.lower() or "csv" in actual_command_lower:
                            self._background_task_expected_artifact = f"{base_script_name}.csv"
                        elif "report" in self._background_task_description.lower() or "report" in actual_command_lower:
                            self._background_task_expected_artifact = f"{base_script_name}_report.txt"
                        else:
                            self._background_task_expected_artifact = f"{base_script_name}_output.txt"
                    else:
                        command_parts = actual_command.split()
                        first_part = os.path.basename(command_parts[0]) if command_parts else "command"
                        self._background_task_expected_artifact = f"{first_part}_artifact.out"
                    self._background_task_artifact_path = str(config.workspace_root / self._background_task_expected_artifact)
                    logger.info(f"Artefato esperado definido como: {self._background_task_artifact_path} (Arquivo de log: {log_file})")
                    self.memory.add_message(Message.assistant_message(
                        f"Comando '{actual_command}' iniciado em background. "
                        f"Logs serão enviados para '{os.path.basename(log_file)}' (localizado em {config.workspace_root}). "
                        f"Procurando pelo artefato esperado '{self._background_task_expected_artifact}' em '{config.workspace_root}'. "
                        "Vou monitorar o progresso."
                    ))
            except json.JSONDecodeError:
                logger.error("Erro ao decodificar argumentos JSON para Bash ao tentar iniciar monitoramento.")
            except Exception as e_parse:
                logger.error(f"Erro ao processar comando bash para monitoramento: {e_parse}")

        if self.tool_calls:
            new_tool_calls = []
            terminate_failure_detected = False
            for tc in self.tool_calls:
                if tc.function.name == Terminate().name:
                    try:
                        args = json.loads(tc.function.arguments)
                        if args.get("status") == "failure":
                            logger.info(f"Interceptada ToolCall para Terminate com status 'failure'. Argumentos: {args}")
                            terminate_failure_detected = True
                        else:
                            new_tool_calls.append(tc)
                    except json.JSONDecodeError:
                        logger.warning(f"Erro ao decodificar argumentos JSON para Terminate ToolCall: {tc.function.arguments}. Mantendo a chamada.")
                        new_tool_calls.append(tc)
                    except Exception as e_json_parse:
                        logger.warning(f"Erro inesperado ao analisar argumentos de Terminate: {e_json_parse}. Mantendo a chamada.")
                        new_tool_calls.append(tc)
                else:
                    new_tool_calls.append(tc)

            if terminate_failure_detected:
                logger.info("Sinalizando para _trigger_failure_check_in devido à interceptação de terminate(failure).")
                self._trigger_failure_check_in = True
                self.tool_calls = new_tool_calls
                self.memory.add_message(Message.system_message(
                    "Nota interna: Uma tentativa de finalizar a tarefa devido a uma falha foi interceptada. "
                    "O usuário será consultado antes da finalização."
                ))
                if not self.tool_calls:
                     logger.info("Nenhuma outra ferramenta planejada além do terminate(failure) interceptado. Indo para o feedback de falha.")
                else:
                     logger.warning("Outras ferramentas foram planejadas junto com terminate(failure). Isso é inesperado. O feedback de falha ocorrerá após estas ferramentas.")

        if self._pending_script_after_dependency and self.tool_calls:
            last_tool_response = next((msg for msg in reversed(self.memory.messages) if msg.role == Role.TOOL and msg.tool_call_id == self.tool_calls[0].id), None)
            dependency_succeeded_and_file_generated = False
            expected_generated_file_name = None
            if self._original_tool_call_for_pending_script:
                try:
                    original_args = json.loads(self._original_tool_call_for_pending_script.function.arguments)
                    original_script_path = original_args.get("file_path")
                    if original_script_path:
                        original_script_analysis = await self._analyze_python_script(original_script_path)
                        if original_script_analysis.get("inputs"):
                            expected_generated_file_name = original_script_analysis["inputs"][0]
                except Exception as e_inner_analysis:
                    logger.error(f"Erro ao reanalisar script original para nome de arquivo esperado: {e_inner_analysis}")

            if last_tool_response and isinstance(last_tool_response.content, str) and \
               any(err_keyword in last_tool_response.content.lower() for err_keyword in ["error", "traceback", "failed", "exception"]):
                logger.warning(f"Script de dependência parece ter falhado. Resposta: {last_tool_response.content}")
                self.memory.add_message(Message.assistant_message(
                    f"O script que tentei executar como dependência ('{self.tool_calls[0].function.name}') parece ter falhado em gerar o arquivo necessário para '{os.path.basename(self._pending_script_after_dependency)}'. Detalhes do erro: {last_tool_response.content}. Não tentarei executar o script pendente."
                ))
            elif not expected_generated_file_name:
                logger.warning("Não foi possível determinar o nome do arquivo esperado da dependência. Assumindo falha na geração.")
                self.memory.add_message(Message.assistant_message(
                    f"Não consegui determinar qual arquivo o script de dependência deveria gerar para '{os.path.basename(self._pending_script_after_dependency)}'. Não tentarei executar o script pendente."
                ))
            else:
                try:
                    expected_file_path = str(config.workspace_root / expected_generated_file_name)
                    editor = self.available_tools.get_tool(StrReplaceEditor().name)
                    await editor.execute(command="view", path=expected_file_path)
                    logger.info(f"Arquivo esperado '{expected_generated_file_name}' gerado com sucesso pela dependência.")
                    dependency_succeeded_and_file_generated = True
                except ToolError:
                    logger.warning(f"Script de dependência executado, mas o arquivo esperado '{expected_generated_file_name}' NÃO foi encontrado.")
                    self.memory.add_message(Message.assistant_message(
                        f"O script de dependência foi executado, mas o arquivo esperado '{expected_generated_file_name}' para '{os.path.basename(self._pending_script_after_dependency)}' não foi encontrado. Não tentarei executar o script pendente."
                    ))
                except Exception as e_check:
                    logger.error(f"Erro ao verificar arquivo gerado pela dependência '{expected_generated_file_name}': {e_check}")
                    self.memory.add_message(Message.assistant_message(
                        f"Ocorreu um erro ao verificar se o arquivo esperado '{expected_generated_file_name}' foi gerado. Não tentarei executar o script pendente."
                    ))

            if dependency_succeeded_and_file_generated:
                logger.info(f"Script de dependência concluído e arquivo gerado. Tentando executar o script pendente: {self._pending_script_after_dependency}")
                self.memory.add_message(Message.assistant_message(
                    f"A execução do script de dependência e a geração do arquivo '{expected_generated_file_name}' parecem ter sido bem-sucedidas. Agora vou tentar executar o script original: {os.path.basename(self._pending_script_after_dependency)}."
                ))
                if self._original_tool_call_for_pending_script:
                    self.tool_calls = [self._original_tool_call_for_pending_script]
                else:
                    logger.error("Não foi possível encontrar a tool_call original para o script pendente.")
                    self.tool_calls = []
                self._pending_script_after_dependency = None
                self._original_tool_call_for_pending_script = None
            else:
                self._pending_script_after_dependency = None
                self._original_tool_call_for_pending_script = None
                self.tool_calls = []

        if self.tool_calls and not self._pending_script_after_dependency:
            tool_call_to_check = self.tool_calls[0]
            required_file = None
            script_to_run_if_dependency_succeeds = None

            if tool_call_to_check.function.name in [SandboxPythonExecutor().name, PythonExecute().name] or \
               (tool_call_to_check.function.name == Bash().name and "python" in tool_call_to_check.function.arguments):
                try:
                    args = json.loads(tool_call_to_check.function.arguments)
                    script_path_from_args = args.get("file_path")
                    if not script_path_from_args and tool_call_to_check.function.name == Bash().name:
                        command_str = args.get("command", "")
                        match = re.search(r"python\d*\s+([^\s]+\.py)", command_str)
                        if match: script_path_from_args = match.group(1)
                        if script_path_from_args and not os.path.isabs(script_path_from_args):
                            script_path_from_args = str(config.workspace_root / script_path_from_args)

                    script_to_run_if_dependency_succeeds = script_path_from_args
                    if script_to_run_if_dependency_succeeds:
                        logger.info(f"Analisando inputs para o script planejado: {script_to_run_if_dependency_succeeds}")
                        script_analysis = await self._analyze_python_script(script_path_from_args)
                        if script_analysis.get("inputs"):
                            for inp_file_name in script_analysis["inputs"]:
                                expected_input_path = str(config.workspace_root / inp_file_name)
                                try:
                                    editor = self.available_tools.get_tool(StrReplaceEditor().name)
                                    await editor.execute(command="view", path=expected_input_path)
                                    logger.info(f"Arquivo de input '{expected_input_path}' para '{script_to_run_if_dependency_succeeds}' encontrado.")
                                except ToolError:
                                    logger.info(f"Arquivo de input '{expected_input_path}' para '{script_to_run_if_dependency_succeeds}' NÃO encontrado. Iniciando análise de dependência.")
                                    required_file = inp_file_name
                                    break
                        else:
                            logger.info(f"Nenhum input declarado encontrado para {script_to_run_if_dependency_succeeds} na análise.")
                except Exception as e:
                    logger.error(f"Erro ao analisar argumentos da tool call para dependências: {e}")

            if required_file and script_to_run_if_dependency_succeeds:
                logger.info(f"Arquivo '{required_file}' necessário para '{script_to_run_if_dependency_succeeds}' está faltando. Analisando workspace...")
                workspace_analysis = await self._analyze_workspace()
                found_generating_script = None
                for gen_script_name, analysis_info in workspace_analysis.items():
                    if required_file in analysis_info.get("outputs", []):
                        if os.path.basename(gen_script_name) == os.path.basename(script_to_run_if_dependency_succeeds):
                            logger.info(f"Script '{gen_script_name}' parece gerar seu próprio input '{required_file}'. Não considerar como dependência.")
                            continue
                        found_generating_script = gen_script_name
                        break
                if found_generating_script:
                    self.memory.add_message(Message.assistant_message(
                        f"O arquivo '{required_file}' necessário para '{os.path.basename(script_to_run_if_dependency_succeeds)}' não foi encontrado. "
                        f"Verifiquei que '{os.path.basename(found_generating_script)}' pode gerá-lo. Tentarei executar '{os.path.basename(found_generating_script)}' primeiro."
                    ))
                    self._pending_script_after_dependency = script_to_run_if_dependency_succeeds
                    self._original_tool_call_for_pending_script = tool_call_to_check
                    new_tool_call_args = {"file_path": str(config.workspace_root / found_generating_script)}
                    self.tool_calls = [ToolCall(
                        id=str(uuid.uuid4()),
                        function=FunctionCall(name=SandboxPythonExecutor().name, arguments=json.dumps(new_tool_call_args))
                    )]
                    logger.info(f"Execução de '{os.path.basename(script_to_run_if_dependency_succeeds)}' adiada. Executando dependência '{os.path.basename(found_generating_script)}' primeiro.")
                else:
                    self.memory.add_message(Message.assistant_message(
                        f"O arquivo '{required_file}' necessário para '{os.path.basename(script_to_run_if_dependency_succeeds)}' não foi encontrado, e não identifiquei um script no workspace que o gere. "
                        "Vou precisar que você forneça este arquivo ou um script para gerá-lo."
                    ))
                    self.tool_calls = []
                    logger.info(f"Nenhum script gerador encontrado para '{required_file}'. O LLM deverá usar AskHuman.")
        return result

    async def _analyze_python_script(self, script_path: str, script_content: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Analisando script Python: {script_path}")
        analysis = {"inputs": [], "outputs": [], "libraries": []}

        if not script_content:
            try:
                editor_tool = self.available_tools.get_tool(StrReplaceEditor().name)
                if not editor_tool:
                    logger.error("Ferramenta StrReplaceEditor não encontrada para _analyze_python_script.")
                    return analysis
                script_content_result = await editor_tool.execute(command="view", path=script_path)
                if isinstance(script_content_result, str):
                    script_content = script_content_result
                else:
                    logger.error(f"Falha ao ler o conteúdo de {script_path} para análise: {script_content_result}")
                    return analysis
            except ToolError as e:
                logger.error(f"ToolError ao ler {script_path} para análise: {e}")
                return analysis
            except Exception as e:
                logger.error(f"Erro inesperado ao ler {script_path} para análise: {e}")
                return analysis

        if not script_content:
            return analysis

        input_patterns = [
            r"pd\.read_csv\s*\(\s*['\"]([^'\"]+)['\"]",
            r"pd\.read_excel\s*\(\s*['\"]([^'\"]+)['\"]",
            r"open\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]r[^'\"]*['\"]",
            r"json\.load\s*\(\s*open\s*\(\s*['\"]([^'\"]+)['\"]",
            r"np\.load\s*\(\s*['\"]([^'\"]+)['\"]",
        ]
        for pattern in input_patterns:
            for match in re.finditer(pattern, script_content):
                analysis["inputs"].append(os.path.basename(match.group(1)))

        output_patterns = [
            r"df\.to_csv\s*\(\s*['\"]([^'\"]+)['\"]",
            r"df\.to_excel\s*\(\s*['\"]([^'\"]+)['\"]",
            r"open\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]w[^'\"]*['\"]",
            r"open\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]a[^'\"]*['\"]",
            r"json\.dump\s*\(.*,\s*open\s*\(\s*['\"]([^'\"]+)['\"]",
            r"plt\.savefig\s*\(\s*['\"]([^'\"]+)['\"]",
            r"np\.save\s*\(\s*['\"]([^'\"]+)['\"]",
        ]
        for pattern in output_patterns:
            for match in re.finditer(pattern, script_content):
                analysis["outputs"].append(os.path.basename(match.group(1)))

        library_patterns = [
            r"^\s*import\s+([a-zA-Z0-9_]+)",
            r"^\s*from\s+([a-zA-Z0-9_]+)\s+import"
        ]
        for pattern in library_patterns:
            for match in re.finditer(pattern, script_content, re.MULTILINE):
                lib_name = match.group(1)
                if lib_name not in analysis["libraries"]:
                    analysis["libraries"].append(lib_name)

        analysis["inputs"] = sorted(list(set(analysis["inputs"])))
        analysis["outputs"] = sorted(list(set(analysis["outputs"])))
        analysis["libraries"] = sorted(list(set(analysis["libraries"])))

        logger.info(f"Análise de {script_path}: Inputs: {analysis['inputs']}, Outputs: {analysis['outputs']}, Bibliotecas: {analysis['libraries']}")
        return analysis

    async def _analyze_workspace(self) -> Dict[str, Dict[str, Any]]:
        logger.info("Analisando scripts Python no workspace...")
        if self._workspace_script_analysis_cache:
             logger.info("Retornando análise de workspace do cache.")
             return self._workspace_script_analysis_cache

        workspace_scripts_analysis: Dict[str, Dict[str, Any]] = {}
        editor_tool = self.available_tools.get_tool(StrReplaceEditor().name)
        if not editor_tool:
            logger.error("Ferramenta StrReplaceEditor não encontrada para _analyze_workspace.")
            return workspace_scripts_analysis

        try:
            workspace_path_str = str(config.workspace_root)
            dir_listing_result = await editor_tool.execute(command="view", path=workspace_path_str)

            if isinstance(dir_listing_result, str):
                python_files = [line.strip() for line in dir_listing_result.splitlines() if line.strip().endswith(".py")]
                logger.info(f"Scripts Python encontrados no workspace ({workspace_path_str}): {python_files}")
                for script_name in python_files:
                    full_script_path = str(config.workspace_root / script_name)
                    workspace_scripts_analysis[script_name] = await self._analyze_python_script(full_script_path)
            else:
                logger.error(f"Falha ao listar arquivos do workspace para análise: {dir_listing_result}")

        except ToolError as e:
            logger.error(f"ToolError ao listar arquivos do workspace para análise: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao analisar workspace: {e}")

        self._workspace_script_analysis_cache = workspace_scripts_analysis
        return workspace_scripts_analysis

    async def _initiate_sandbox_script_cancellation(self):
        """Tenta ler um PID do arquivo de PID rastreado e enviar um sinal SIGTERM para ele no sandbox."""
        if not self._current_sandbox_pid_file:
            logger.warning("_initiate_sandbox_script_cancellation chamado sem _current_sandbox_pid_file definido.")
            return

        if self._current_sandbox_pid is None:
            try:
                pid_str = await SANDBOX_CLIENT.read_file(self._current_sandbox_pid_file)
                pid = int(pid_str.strip())
                self._current_sandbox_pid = pid
                logger.info(f"PID {pid} lido com sucesso de {self._current_sandbox_pid_file}")
            except FileNotFoundError:
                logger.warning(f"Arquivo PID {self._current_sandbox_pid_file} não encontrado. O script pode já ter terminado.")
                self.memory.add_message(Message.assistant_message("Não foi possível encontrar o arquivo de PID para cancelamento; o script pode já ter terminado."))
                # Tenta limpar o registro do arquivo PID inexistente chamando o helper de limpeza existente
                # Isso também limpará os atributos relacionados se o ID da chamada de ferramenta atual corresponder.
                # No entanto, neste estágio, a chamada de ferramenta ainda não "terminou", então a limpeza direta é melhor.
                if hasattr(self, '_cleanup_sandbox_file') and callable(getattr(self, '_cleanup_sandbox_file')):
                    # Chama a limpeza principal para este caminho de arquivo que também deve limpar atributos
                     await self._cleanup_sandbox_file(self._current_sandbox_pid_file) # Isso registrará seu próprio sucesso/falha
                # Limpa explicitamente os atributos aqui porque o script é considerado desaparecido ou seu estado desconhecido.
                self._current_sandbox_pid_file = None
                self._current_script_tool_call_id = None
                self._current_sandbox_pid = None
                return
            except (ValueError, TypeError) as e:
                logger.error(f"Conteúdo inválido no arquivo PID {self._current_sandbox_pid_file}: {pid_str if 'pid_str' in locals() else 'conteúdo desconhecido'}. Erro: {e}")
                self.memory.add_message(Message.assistant_message(f"Conteúdo inválido no arquivo de PID ({self._current_sandbox_pid_file}). Não é possível cancelar."))
                if hasattr(self, '_cleanup_sandbox_file') and callable(getattr(self, '_cleanup_sandbox_file')):
                     await self._cleanup_sandbox_file(self._current_sandbox_pid_file)
                self._current_sandbox_pid_file = None
                self._current_script_tool_call_id = None
                self._current_sandbox_pid = None
                return
            except Exception as e: # Captura outros erros do SANDBOX_CLIENT como problemas de permissão ou sandbox inativo
                logger.error(f"Erro ao ler arquivo PID {self._current_sandbox_pid_file}: {e}")
                self.memory.add_message(Message.assistant_message(f"Erro ao ler o arquivo de PID para cancelamento: {e}"))
                # Não limpe _current_sandbox_pid_file aqui, pois o arquivo ainda pode existir, apenas ilegível temporariamente.
                # A chamada de ferramenta original ainda pode ser concluída e acionar a limpeza adequada através do bloco finally de execute_tool.
                return

        if self._current_sandbox_pid is not None:
            try:
                kill_command = f"kill -SIGTERM {self._current_sandbox_pid}"
                logger.info(f"Tentando executar comando kill no sandbox: {kill_command}")
                # Adiciona mensagem antes de enviar kill, para que o usuário veja mesmo se o agente/sandbox tiver problemas durante o comando
                self.memory.add_message(Message.assistant_message(f"Enviando sinal de cancelamento (SIGTERM) para o processo {self._current_sandbox_pid} no sandbox..."))
                result = await SANDBOX_CLIENT.run_command(kill_command, timeout=10) # Usando SIGTERM

                if result.get("exit_code") == 0:
                    logger.info(f"SIGTERM enviado com sucesso para PID {self._current_sandbox_pid}. Saída stdout do comando kill: '{result.get('stdout','').strip()}', stderr: '{result.get('stderr','').strip()}'")
                    # Mensagem do usuário para envio de sinal bem-sucedido já foi adicionada.
                else:
                    # Isso pode acontecer se o processo já terminou entre a leitura do PID e o comando kill.
                    logger.warning(f"Comando kill para PID {self._current_sandbox_pid} falhou ou PID não encontrado. Código de saída: {result.get('exit_code')}. Stderr: '{result.get('stderr','').strip()}'")
                    # self.memory.add_message(Message.assistant_message(f"Falha ao enviar sinal de cancelamento para o script (PID: {self._current_sandbox_pid}), ou o script já havia terminado. Detalhes: {result.get('stderr','').strip()}"))
                    # Não há necessidade de outra mensagem se a anterior indicou uma tentativa. O log é suficiente.
            except Exception as e:
                logger.error(f"Exceção ao tentar matar PID {self._current_sandbox_pid}: {e}")
                self.memory.add_message(Message.assistant_message(f"Erro ao tentar cancelar o script (PID: {self._current_sandbox_pid}): {e}"))
        # Conforme o plano, não limpe as informações do PID aqui; isso é tratado pelo bloco finally de ToolCallAgent.execute_tool.

    async def _cleanup_sandbox_file(self, file_path_in_sandbox: str):
        """Auxiliar para remover um arquivo do sandbox."""
        if not file_path_in_sandbox:
            return
        try:
            logger.info(f"Tentando limpar arquivo do sandbox: {file_path_in_sandbox}")
            # Garante que SANDBOX_CLIENT está disponível e run_command é awaitable
            cleanup_result = await SANDBOX_CLIENT.run_command(f"rm -f {file_path_in_sandbox}", timeout=10)
            if cleanup_result.get("exit_code") != 0:
                logger.warning(f"Falha ao limpar arquivo do sandbox '{file_path_in_sandbox}'. Erro: {cleanup_result.get('stderr')}")
            else:
                logger.info(f"Arquivo do sandbox limpo com sucesso: {file_path_in_sandbox}")
        except Exception as e:
            logger.error(f"Exceção durante a limpeza do arquivo do sandbox para '{file_path_in_sandbox}': {e}")

    async def periodic_user_check_in(self, is_final_check: bool = False, is_failure_scenario: bool = False) -> bool:
        user_interaction_tool_name = AskHuman().name
        if user_interaction_tool_name not in self.available_tools.tool_map:
            logger.warning(f"Ferramenta de interação com o usuário '{user_interaction_tool_name}' não disponível. Continuando execução.")
            self.memory.add_message(Message.system_message(f"Interação periódica com usuário pulada: ferramenta '{user_interaction_tool_name}' não encontrada."))
            return True

        checklist_content_str = "Checklist não encontrado ou vazio."
        checklist_path = str(config.workspace_root / "checklist_principal_tarefa.md")
        local_file_op = LocalFileOperator()
        try:
            checklist_content_str = await local_file_op.read_file(checklist_path)
            if not checklist_content_str.strip():
                checklist_content_str = "Checklist encontrado, mas está vazio."
            logger.info(f"Conteúdo do checklist lido localmente para autoanálise: {checklist_content_str[:200]}...")
        except ToolError as e_tool_error:
            logger.info(f"Checklist '{checklist_path}' não encontrado (ou erro ao ler localmente) para autoanálise: {str(e_tool_error)}. Usando mensagem padrão.")
        except Exception as e_checklist:
            logger.error(f"Erro inesperado ao ler checklist localmente para autoanálise: {str(e_checklist)}")
            checklist_content_str = f"Erro inesperado ao ler checklist: {str(e_checklist)}"

        prompt_messages_list = [Message(role=Role.SYSTEM, content=self.system_prompt)]
        num_messages_for_context = 7
        mensagens_recentes_raw = self.memory.messages[-num_messages_for_context:]
        
        present_tool_response_ids = set()
        for msg_scan_tool_responses in mensagens_recentes_raw:
            if msg_scan_tool_responses.role == Role.TOOL and hasattr(msg_scan_tool_responses, 'tool_call_id') and msg_scan_tool_responses.tool_call_id:
                present_tool_response_ids.add(msg_scan_tool_responses.tool_call_id)

        final_filtered_messages: List[Message] = []
        assistant_tool_call_map: Dict[str, int] = {}
        for i, msg_map_assistant in enumerate(mensagens_recentes_raw):
            if msg_map_assistant.role == Role.ASSISTANT and msg_map_assistant.tool_calls:
                for tc_map in msg_map_assistant.tool_calls:
                    assistant_tool_call_map[tc_map.id] = i

        for i, msg_original in enumerate(mensagens_recentes_raw):
            msg = msg_original.model_copy(deep=True)

            if msg.role == Role.ASSISTANT and msg.tool_calls:
                all_tool_calls_have_responses = True
                temp_tool_calls_for_current_assistant_msg = []

                for tc_assistant in msg.tool_calls:
                    if tc_assistant.id not in present_tool_response_ids:
                        all_tool_calls_have_responses = False
                    else:
                        temp_tool_calls_for_current_assistant_msg.append(tc_assistant)

                if not all_tool_calls_have_responses:
                    msg.tool_calls = None
                elif not temp_tool_calls_for_current_assistant_msg:
                    msg.tool_calls = None
            elif msg.role == Role.TOOL:
                if not (hasattr(msg, 'tool_call_id') and msg.tool_call_id and msg.tool_call_id in assistant_tool_call_map):
                    continue
            final_filtered_messages.append(msg)
        
        prompt_messages_list.extend(final_filtered_messages)
        
        internal_prompt_text = INTERNAL_SELF_ANALYSIS_PROMPT_TEMPLATE.format(
            X=num_messages_for_context, 
            checklist_content=checklist_content_str
        )
        prompt_messages_list.append(Message(role=Role.USER, content=internal_prompt_text))

        relatorio_autoanalise = "Não foi possível gerar o relatório de autoanálise devido a um erro interno."
        try:
            logger.info("Iniciando chamada LLM interna para autoanálise...")
            if hasattr(self, 'llm') and self.llm:
                 relatorio_autoanalise = await self.llm.ask(messages=prompt_messages_list, stream=False) 
                 logger.info(f"Relatório de autoanálise recebido do LLM: {relatorio_autoanalise[:300]}...")
            else:
                logger.error("Instância LLM (self.llm) não disponível para autoanálise.")
                # Define um relatório padrão se o LLM não estiver disponível, para não quebrar o fluxo
                relatorio_autoanalise = "Autoanálise não disponível (LLM offline). Progresso conforme o último ciclo."
        except Exception as e_llm_call:
            logger.error(f"Erro durante chamada LLM interna para autoanálise: {e_llm_call}")
            relatorio_autoanalise = f"Não foi possível gerar o relatório de autoanálise devido a um erro: {e_llm_call}"
        
        pergunta = ""
        if is_failure_scenario:
            last_llm_thought = ""
            if self.memory.messages and self.memory.messages[-1].role == Role.ASSISTANT:
                last_llm_thought = self.memory.messages[-1].content
            error_details_for_prompt = f"Detalhes do erro (conforme meu último pensamento): {last_llm_thought}" if last_llm_thought else "Não consegui obter detalhes específicos do erro do meu processamento interno."
            pergunta = (
                f"Encontrei um problema que me impede de continuar a tarefa como planejado.\n"
                f"Relatório de Autoanálise (sobre a falha):\n{relatorio_autoanalise}\n\n"
                f"{error_details_for_prompt}\n\n"
                f"Você gostaria que eu finalizasse a tarefa agora devido a esta dificuldade?\n\n"
                f"Por favor, responda com:\n"
                f"- 'sim, finalizar' (para encerrar a tarefa com falha)\n"
                f"- 'não, tentar outra abordagem: [suas instruções]' (se você tiver uma sugestão ou quiser que eu tente algo diferente)"
            )
        elif is_final_check:
            pergunta = (
                f"Todos os itens do checklist foram concluídos. Aqui está meu relatório de autoanálise final:\n{relatorio_autoanalise}\n\n"
                f"Você está satisfeito com o resultado e deseja que eu finalize a tarefa?\n\n"
                f"Por favor, responda com:\n"
                f"- 'sim' (para finalizar a tarefa com sucesso)\n"
                f"- 'revisar: [suas instruções para revisão]' (se algo precisa ser ajustado antes de finalizar)"
            )
        else:
            pergunta = (
                f"Aqui está meu relatório de autoanálise e planejamento:\n{relatorio_autoanalise}\n\n"
                f"Considerando isso, completei um ciclo de {self.max_steps} etapas (total de etapas realizadas: {self.current_step}).\n"
                f"Você quer que eu continue por mais {self.max_steps} etapas (possivelmente seguindo o plano sugerido, se houver)? Ou você prefere parar ou me dar novas instruções?\n\n"
                f"Por favor, responda com:\n"
                f"- 'continuar' (para prosseguir por mais {self.max_steps} etapas)\n"
                f"- 'parar' (para encerrar a tarefa atual)\n"
                f"- 'mudar: [suas novas instruções]' (para fornecer uma nova direção)"
            )
        
        # Verifica script cancelável antes de pedir entrada do usuário no caso geral
        if not is_failure_scenario and not is_final_check:
            if hasattr(self, '_current_sandbox_pid_file') and self._current_sandbox_pid_file:
                logger.info(f"Pausa solicitada pelo usuário. Script atualmente em execução com arquivo PID: {self._current_sandbox_pid_file}. Tentando cancelamento.")
                # Assumindo que _initiate_sandbox_script_cancellation será um método assíncrono
                # Idealmente, também deveria adicionar uma mensagem à memória sobre seu resultado.
                # Por enquanto, adicionamos uma mensagem genérica aqui.
                self.memory.add_message(Message.assistant_message("Tentativa de cancelamento do script em execução no sandbox devido à solicitação de pausa..."))
                if hasattr(self, '_initiate_sandbox_script_cancellation') and callable(getattr(self, '_initiate_sandbox_script_cancellation')):
                    await self._initiate_sandbox_script_cancellation()
                else:
                    logger.warning("Método _initiate_sandbox_script_cancellation não encontrado, não é possível cancelar script.")
                    self.memory.add_message(Message.assistant_message("AVISO: Funcionalidade de cancelamento de script não implementada neste agente."))

        logger.info(f"Manus: Solicitando feedback do usuário com prompt: {pergunta[:500]}...")
        self.memory.add_message(Message.assistant_message(content=pergunta))
        self._pending_feedback_question = pergunta
        self.current_step = 0
        return True

