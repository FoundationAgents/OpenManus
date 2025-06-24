from typing import List

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.swe import SYSTEM_PROMPT
from app.tool import Bash, StrReplaceEditor, Terminate, ToolCollection
from app.tool.ask_human import AskHuman # Importação adicionada
from app.logger import logger # Importação adicionada
from app.schema import AgentState # Importação adicionada


class SWEAgent(ToolCallAgent):
    """Um agente que implementa o paradigma SWEAgent para executar código e conversas naturais."""

    name: str = "swe"
    description: str = "um programador de IA autônomo que interage diretamente com o computador para resolver tarefas."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = ""

    available_tools: ToolCollection = ToolCollection(
        Bash(), StrReplaceEditor(), Terminate(), AskHuman() # AskHuman adicionado
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    max_steps: int = 50 # max_steps aumentado

    async def should_request_feedback(self) -> bool:
        """Determina se o agente deve pausar e solicitar feedback do usuário.

        Este método implementa a lógica para decidir quando pedir feedback
        com base em critérios como estar preso, enfrentar ambiguidade ou falta de informações críticas.
        """
        # 1. Verificar se o agente está preso (usando mecanismo existente)
        if self.is_stuck():
            logger.info("Condição de feedback: Agente está preso (respostas duplicadas).")
            # Garantir que há uma pergunta a ser feita, talvez definindo um padrão ou usando o prompt de preso.
            # Por enquanto, assumimos que o LLM usará ask_human com base no prompt do sistema se estiver preso.
            # Podemos precisar de uma maneira mais direta de definir a pergunta para ask_human aqui.
            self.update_memory("system", "Você parece estar preso. Considere pedir orientação ao usuário usando a ferramenta 'ask_human' se não tiver certeza de como proceder.")
            return True

        # 2. Verificar palavras-chave que indicam ambiguidade ou falta de informações na memória recente
        # Olhar as últimas mensagens em busca de sinais reveladores.
        # Esta é uma heurística simples e pode ser expandida.
        recent_messages_to_check = 3
        keywords = ["não fornecido", "incerto", "chave de api ausente", "qual é o valor", "parâmetro desconhecido", "esclarecer", "não está claro"]
        
        for message in self.memory.messages[-recent_messages_to_check:]:
            if message.content: # Garantir que o conteúdo não é None
                for keyword in keywords:
                    if keyword in message.content.lower():
                        logger.info(f"Condição de feedback: Palavra-chave '{keyword}' encontrada nas mensagens recentes.")
                        # Solicitar ao LLM para fazer uma pergunta.
                        self.update_memory("system", f"Parece haver alguma incerteza (relacionada a '{keyword}'). Por favor, use a ferramenta 'ask_human' para pedir esclarecimentos ou informações ausentes ao usuário.")
                        return True
        
        # 3. Placeholder para verificar tentativas falhas repetidas
        # TODO: Implementar lógica para detectar execuções de ferramentas falhas repetidas ou falta de progresso em direção a um objetivo.
        # Isso pode envolver a análise dos resultados da execução da ferramenta ou outras métricas de progresso.
        # Por exemplo, se as últimas N chamadas de ferramenta resultaram em erros ou nenhuma mudança no estado.

        # 4. Verificar passos excessivos sem finalizar (como um fallback)
        # Esta é uma versão mais branda do antigo interaction_interval, mas mais uma verificação de "estamos demorando muito?".
        # Acionar apenas se um número significativo de passos tiver passado sem resolução.
        if self.current_step > (self.max_steps * 0.75) and self.state != AgentState.FINISHED:
             logger.info(f"Condição de feedback: Agente executou {self.current_step} passos sem finalizar.")
             self.update_memory("system", "Você executou um número significativo de passos. Se não estiver confiante no caminho atual, considere usar 'ask_human' para verificar com o usuário ou pedir orientação.")
             return True

        return False
