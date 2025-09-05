class CriticAgent:
    """
    Você é um Agente de Monitoramento e Refinamento de Horizonte Temporal, com o objetivo principal de otimizar a eficácia e a confiabilidade da execução de tarefas de longo horizonte para outros agentes de IA ou fluxos de trabalho complexos.

    Seu Propósito Principal: Sua função é fornecer feedback crítico, identificar desvios e redirecionar a execução de tarefas para aumentar o horizonte temporal de sucesso, visando especialmente o alcance do Horizonte de Tempo de Conclusão de Tarefa de 50% (T50). O T50 é definido como a duração da tarefa (medida em tempo de um especialista humano qualificado) que o agente consegue concluir com 50% de confiabilidade.

    Monitoramento e Avaliação Crítica: Para cada tarefa em execução, você deve monitorar ativamente o progresso, as ações (utilizando o padrão ReAct: 'pensar' e 'agir') e o consumo de recursos. Sua avaliação crítica deve focar em:
    •
    Progresso em relação ao T50: Estimar se o ritmo de execução e a qualidade dos passos indicam que o T50 será alcançado.
    •
    Identificação de Erros e Loops: Detectar falhas repetitivas, ineficiências, desvios do plano original ou situações onde o agente executor está preso em ciclos de repetição (loops infinitos).
    •
    Qualidade do Raciocínio e Uso de Ferramentas: Avaliar se o agente está utilizando as ferramentas de forma eficaz e se seu raciocínio está se aprofundando ou se deteriorando com a complexidade da tarefa.

    Mecanismo de Feedback e Redirecionamento (Crítico): Se sua análise indicar que o T50 da tarefa não está sendo eficientemente alcançado, ou se houver sinais de falha iminente ou persistente, você deve intervir. Sua intervenção inclui:
    •
    Feedback Direto e Construtivo: Comunicar claramente o problema identificado ao agente executor (ou ao sistema de orquestração), destacando a causa percebida do desvio ou da ineficiência.
    •
    Sugestão de Plano de Ação Alternativo: Propor uma estratégia de correção, que pode envolver:
    ◦
    Modificação do plano de execução atual (ex: redefinir subtarefas ou prioridades).
    ◦
    A ativação de um sub-agente especializado para uma etapa específica (em sistemas multiagentes).
    ◦
    A solicitação de informações adicionais (se for o caso, simulando uma interação "human-in-the-loop" para clareza, como a ferramenta AskHuman).
    •
    Redirecionamento da Execução na Mesma Tarefa: Crucialmente, seu objetivo é redirecionar a execução dentro da mesma tarefa em andamento, permitindo que o agente executor ajuste seu curso sem reiniciar o trabalho do zero. Preserve o contexto acumulado e o progresso já realizado, visto que a arquitetura do agente gerencia uma lista de mensagens (self.messages) contendo as trocas de sistema, usuário e assistente, e variáveis como resultados de ferramentas são inseridas nessa lista para que o LLM considere na próxima iteração de raciocínio.

    Contexto e Ferramentas: Você terá acesso completo ao estado interno do agente executor, incluindo o histórico de mensagens, o plano atual ({PlanoAtual}), os resultados de ferramentas e a memória de curto e, se disponível, de longo prazo. Utilize essa informação para fundamentar suas análises e decisões, visando a autocorreção e a adaptação do sistema para um horizonte temporal mais longo e confiável.
    """

import re
from collections import Counter
from typing import Optional, Tuple, List, Dict, Any # Melhorando type hints

# Classe CriticAgent movida para baixo para que o type hint CriticAgent possa ser usado em ToolCallAgent
# se importado diretamente, mas como está em arquivos separados, isso não é um problema.

class CriticAgent:
    """Você é um Agente de Monitoramento e Refinamento de Horizonte Temporal, com o objetivo principal de otimizar a eficácia e a confiabilidade da execução de tarefas de longo horizonte para outros agentes de IA ou fluxos de trabalho complexos. Seu Propósito Principal: Sua função é fornecer feedback crítico, identificar desvios e redirecionar a execução de tarefas para aumentar o horizonte temporal de sucesso, visando especialmente o alcance do Horizonte de Tempo de Conclusão de Tarefa de 50% (T50) – a duração da tarefa (medida em tempo de um especialista humano qualificado) que o agente consegue concluir com 50% de confiabilidade.
    Monitoramento e Avaliação Crítica: Para cada tarefa em execução, você deve monitorar ativamente o progresso, as ações (utilizando o padrão ReAct: 'pensar' e 'agir') e o consumo de recursos. Sua ativação ocorrerá a cada 5 etapas da execução do agente principal. Sua avaliação crítica deve focar em:
    •
    Progresso em relação ao T50: Estimar se o ritmo de execução e a qualidade dos passos indicam que o T50 será alcançado.
    •
    Identificação de Erros e Loops: Detectar falhas repetitivas, ineficiências, desvios do plano ORIGINAL e da INTENÇÃO do usuário (abordando a falha de má interpretação do prompt inicial), ou situações onde o agente executor está preso em ciclos de repetição (loops infinitos ou estagnação). Considere também a auto-bias, onde o agente pode não reconhecer seus próprios erros.
    •
    Qualidade do Raciocínio e Uso de Ferramentas: Avaliar se o agente está utilizando as ferramentas de forma eficaz e se seu raciocínio está se aprofundando ou se deteriorando com a complexidade da tarefa. Investigue a causa raiz de falhas de ferramenta (ex: "empty text parameter", erros de sandbox, formato incorreto de API) e forneça diagnósticos específicos.
    •
    Discernimento: Seja crítico, porém realista e pragmático. Saiba reconhecer quando um processo está fluindo bem e quando não está, evitando intervenções desnecessárias.
    Mecanismo de Feedback e Redirecionamento (Crítico): Se sua análise indicar que o T50 da tarefa não está sendo eficientemente alcançado, ou se houver sinais de falha iminente ou persistente, você deve intervir. Sua intervenção inclui:
    •
    Feedback Direto e Construtivo: Comunicar claramente o problema identificado ao agente executor (ou ao sistema de orquestração), destacando a causa percebida do desvio ou da ineficiência e, se possível, a natureza do erro técnico (ex: "Erro de parsing na ferramenta X", "Problema de sequência de mensagens na API do LLM").
    •
    Sugestão de Plano de Ação Alternativo: Propor uma estratégia de correção detalhada, que pode envolver:
    ◦
    Modificação do plano de execução atual (ex: redefinir subtarefas ou prioridades), especialmente se houver um desalinhamento com a intenção inicial do usuário.
    ◦
    A ativação de um sub-agente especializado para uma etapa específica (em sistemas multiagentes, como um agente de depuração ou um especialista em validação de código).
    ◦
    A solicitação de informações adicionais (se for o caso, simulando uma interação "human-in-the-loop" para clareza, possivelmente invocando uma ferramenta AskHuman ou similar para feedback/aprovação humana em pontos críticos ou de alto risco).
    ◦
    Para falhas de ferramenta: Sugerir retentativas adaptativas, sanitização de entradas/saídas do LLM, ou o uso de ferramentas alternativas (considerando fixToolCallAgent e sanitizers).
    •
    Redirecionamento da Execução na Mesma Tarefa: Crucialmente, seu objetivo é redirecionar a execução dentro da mesma tarefa em andamento, permitindo que o agente executor ajuste seu curso sem reiniciar o trabalho do zero. Preserve o contexto acumulado e o progresso já realizado, visto que a arquitetura do agente gerencia uma lista de mensagens (self.messages) contendo as trocas de sistema, usuário e assistente, e variáveis como resultados de ferramentas são inseridas nessa lista para que o LLM considere na próxima iteração de raciocínio.
    •
    Alinhamento com Aprendizado por Reforço (RL): Suas sugestões e o sucesso da auto-correção devem idealmente servir como sinais de recompensa para o OpenManus-RL, contribuindo para o fine-tuning do agente em trajetórias de interação agêntica, aprimorando sua capacidade de ser um "bom agente" em cenários complexos.
    Contexto e Ferramentas: Você terá acesso completo ao estado interno do agente executor, incluindo o histórico de mensagens, o plano atual ({PlanoAtual}), os resultados de ferramentas e a memória de curto e, se disponível, de longo prazo. Utilize essa informação para fundamentar suas análises e decisões, visando a autocorreção e a adaptação do sistema para um horizonte temporal mais longo e confiável. Você deve considerar as limitações de contexto do LLM e, quando apropriado, sugerir técnicas de truncamento ou sumarização para otimizar o uso da memória. Integre-se com as funcionalidades de logging e observabilidade para facilitar a depuração e o monitoramento do seu próprio desempenho e do agente executor.
    """

    def __init__(self, llm_client: Any): # llm_client pode ser uma mock ou real LLM client
        """
        Inicializa o CriticAgent.

        Args:
            llm_client: Cliente LLM para usar para análises mais profundas (atualmente não usado ativamente para gerar feedback).
        """
        self.llm_client = llm_client
        self.error_history: Counter[str] = Counter() # Rastreia a frequência de assinaturas de erro.
        self.max_error_frequency: int = 3      # Limite para um erro ser considerado excessivamente repetitivo.
        self.stagnation_step_threshold: int = 10 # Nº de passos de revisão do crítico sem progresso no checklist para sinalizar estagnação.
        # Guarda o número de tarefas concluídas na última revisão para detectar estagnação real.
        self.last_review_completed_tasks: Optional[int] = None

    def _parse_checklist_progress(self, checklist_markdown: str) -> Tuple[int, int]:
        """
        Parseia o markdown do checklist para contar tarefas totais e concluídas.
        Espera-se que as tarefas sigam o formato GFM: "- [x] Tarefa Concluída" ou "- [ ] Tarefa Pendente".
        Linhas que não correspondem a este padrão são ignoradas.

        Args:
            checklist_markdown: String contendo o checklist em formato markdown.

        Returns:
            Uma tupla (total_tasks, completed_tasks).
        """
        if not isinstance(checklist_markdown, str):
            return 0, 0

        total_tasks = 0
        completed_tasks = 0
        lines = checklist_markdown.splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("- ["):
                total_tasks += 1
                if line.startswith("- [x]") or line.startswith("- [X]"):
                    completed_tasks += 1
        return total_tasks, completed_tasks

    def review_plan_and_progress(self,
                                 current_plan_markdown: str,
                                 initial_user_prompt: Optional[str],
                                 messages: List[Dict[str, Any]],
                                 tool_results: List[Dict[str, Any]],
                                 current_step: int,
                                 steps_since_last_review: int) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Analisa o plano atual, histórico de mensagens e resultados de ferramentas para fornecer feedback
        e, se necessário, sugerir redirecionamentos com base em heurísticas de T50.

        Args:
            current_plan_markdown: String markdown do checklist/plano atual.
            initial_user_prompt: O prompt inicial do usuário para a tarefa corrente.
            messages: Lista de mensagens recentes (histórico da conversa).
            tool_results: Lista de resultados recentes de ferramentas.
            current_step: O número total de passos de execução do agente principal.
            steps_since_last_review: Número de passos do agente principal desde a última revisão do crítico.

        Returns:
            Uma tupla contendo:
                - feedback (str): O feedback textual do crítico.
                - sugestao_redirecionamento (Optional[dict]): Um dicionário com a sugestão de ação
                  ou None se nenhuma sugestão crítica for feita.
        """

        total_checklist_tasks, completed_checklist_tasks_now = self._parse_checklist_progress(current_plan_markdown)
        t50_concerns: List[str] = []
        sugestao_redirecionamento: Optional[Dict[str, Any]] = None # Inicializa aqui

        # 0. Análise de Desvio da Intenção Original
        if initial_user_prompt:
            prompt_summary = initial_user_prompt[:100] + "..."
            # Heurística: se o prompt inicial é substancial, mas o checklist atual é muito pequeno ou
            # parece ser de uma tarefa anterior (muitas tarefas concluídas sem relação com o novo prompt).
            # Esta é uma heurística simplificada e pode precisar de ajuste.
            # Uma análise semântica real do LLM seria mais robusta.
            if len(initial_user_prompt) > 50 and total_checklist_tasks > 0:
                # Verifica se a maioria das tarefas está concluída, o que pode indicar um checklist antigo.
                if completed_checklist_tasks_now > total_checklist_tasks * 0.7:
                    concern_msg = (
                        f"Desalinhamento Potencial da Intenção: Um novo prompt ('{prompt_summary}') foi recebido, "
                        f"mas o checklist atual ({completed_checklist_tasks_now}/{total_checklist_tasks} concluídas) "
                        "parece ser de uma tarefa anterior. O plano pode não refletir a intenção atual do usuário."
                    )
                    t50_concerns.append(concern_msg)
                    # Sugestão de alta prioridade para limpar o checklist
                    sugestao_redirecionamento = {
                        "action_type": "MODIFY_PLAN", # Ou talvez um novo tipo "RESET_CHECKLIST_FOR_NEW_TASK"
                        "details": {
                            "task_description": "Resetar o checklist para alinhar com o novo prompt do usuário.",
                            "priority": "altíssima" # Sinaliza que isso deve ser tratado antes de outros problemas
                        },
                        "clarification": (
                            "Detectado um novo prompt de usuário, mas o checklist existente parece pertencer a uma tarefa anterior. "
                            "Sugiro resetar o checklist e criar um novo baseado no prompt atual: "
                            f"'{initial_user_prompt}'. Isso pode exigir uma confirmação do usuário via 'ask_human' "
                            "pelo agente principal antes de deletar o checklist existente."
                        )
                    }
                    # Se um desalinhamento forte for detectado, podemos retornar cedo ou priorizar esta sugestão.
                    # Por enquanto, vamos permitir que outras análises ocorram, mas esta sugestão terá prioridade se gerada.

        # 1. Análise de Estagnação do Checklist (Só executa se não houver sugestão de desalinhamento forte)
        # Verifica se houve progresso real no checklist desde a última revisão.
        if self.last_review_completed_tasks is not None and \
           steps_since_last_review >= self.stagnation_step_threshold and \
           total_checklist_tasks > 0 and \
           completed_checklist_tasks_now == self.last_review_completed_tasks and \
           completed_checklist_tasks_now < total_checklist_tasks: # Garante que não está apenas "preso" no final
            t50_concerns.append(
                f"Estagnação do Checklist: {steps_since_last_review} etapas se passaram desde a última revisão "
                f"sem que novas tarefas do checklist fossem concluídas. "
                f"Progresso atual: {completed_checklist_tasks_now}/{total_checklist_tasks}."
            )
        # Atualiza o número de tarefas concluídas para a próxima revisão.
        self.last_review_completed_tasks = completed_checklist_tasks_now

        # Se for a primeira revisão (last_review_completed_tasks is None) e já passou o threshold de passos,
        # mas há tarefas pendentes, também pode ser um sinal inicial de lentidão.
        if self.last_review_completed_tasks is None and \
           steps_since_last_review >= self.stagnation_step_threshold and \
           total_checklist_tasks > 0 and \
           completed_checklist_tasks_now < total_checklist_tasks:
            t50_concerns.append(
                f"Progresso Lento Inicial: {steps_since_last_review} etapas se passaram na primeira fase de revisão "
                f"e o checklist ainda não foi totalmente concluído ({completed_checklist_tasks_now}/{total_checklist_tasks})."
            )


        # 2. Análise de Erros Repetitivos
        # `tool_results` é uma lista de dicts: {'name': str, 'content': str, 'tool_call_id': str}
        for result in tool_results:
            if isinstance(result, dict):
                tool_name = result.get("name", "unknown_tool")
                # O conteúdo do resultado da ferramenta já é uma string de observação formatada por ToolCallAgent.execute_tool
                # Ex: "Observed output of cmd `tool_name` executed:\nError: some error message"
                tool_content_str = str(result.get("content", "")).lower()

                error_signature: Optional[str] = None
                # Verifica se a observação indica um erro.
                if tool_content_str.startswith("observed output") and "error:" in tool_content_str:
                    # Tenta extrair a mensagem de erro específica.
                    match = re.search(r"error: (.*)", tool_content_str, re.IGNORECASE)
                    if match:
                        error_message_full = match.group(1).strip()
                        # Identificar tipos específicos de erro aqui
                        if "empty text parameter" in error_message_full or \
                           "missing required parameter" in error_message_full or \
                           "required parameter" in error_message_full: # Adicionado para cobrir mais casos
                            error_signature = f"tool_error_{tool_name}_missing_param"
                        elif (tool_name.lower() == "pythonexecute" or tool_name.lower() == "sandboxpythonexecutor") and \
                             ("execution error" in error_message_full or "failed to execute" in error_message_full or "syntaxerror" in error_message_full or "indentationerror" in error_message_full):
                            error_signature = f"tool_error_{tool_name}_sandbox_execution_error"
                        # Adicionar outras detecções específicas de erro aqui (ex: API LLM)
                        # else if "api key" in error_message_full and "llm" in tool_name.lower():
                        #    error_signature = f"tool_error_{tool_name}_llm_api_key_issue"
                        else:
                            error_message_part = error_message_full[:75].strip() # Assinatura genérica se não for específica
                            error_signature = f"tool_error_{tool_name}_{error_message_part}"
                elif "traceback (most recent call last)" in tool_content_str: # Caso genérico de traceback
                     error_signature = f"traceback_{tool_name}"
                # Adicionar aqui a detecção de erros de API do LLM que podem não seguir o padrão "Error: "
                # Ex: se o resultado da ferramenta for um JSON de erro da API OpenAI/Anthropic
                # Isso é mais complexo e pode ser um TODO para análise baseada em LLM se a heurística for insuficiente.

                if error_signature:
                    self.error_history[error_signature] += 1
                    if self.error_history[error_signature] >= self.max_error_frequency:
                        t50_concerns.append(
                            f"Erro Repetitivo: A ferramenta '{tool_name}' parece estar falhando consistentemente. "
                            f"O erro (ou similar) ocorreu {self.error_history[error_signature]} vezes. "
                            f"Assinatura do erro: '{error_signature.split('_', 2)[-1]}'."
                        )
                        # Não resetar aqui; resetar apenas se uma sugestão de correção for explicitamente feita
                        # e o agente principal tentar essa correção.

        # --- Geração de Feedback e Sugestões com base nas preocupações T50 ---
        feedback: str = "Análise do Crítico:\n"
        sugestao_redirecionamento: Optional[Dict[str, Any]] = None

        if not t50_concerns:
            feedback += "O progresso parece razoável. Nenhuma preocupação crítica de T50 identificada nesta revisão.\n"
        else:
            feedback += "Foram identificadas as seguintes preocupações que podem afetar o T50 (progresso eficiente e confiável):\n"
            for concern in t50_concerns:
                feedback += f"- {concern}\n"

            # Priorizar sugestões: Erros repetitivos são geralmente mais críticos
            if any("Erro Repetitivo" in concern for concern in t50_concerns):
                most_frequent_error_sig: Optional[str] = None
                max_freq = 0
                # Encontra o erro mais frequente que ATINGIU o threshold para a sugestão
                for sig, freq in self.error_history.items():
                    if freq >= self.max_error_frequency and freq > max_freq:
                        max_freq = freq
                        most_frequent_error_sig = sig

                failed_tool_name_from_sig = "desconhecida"
                error_details_from_sig = "não especificado"
                specific_error_type_for_clarification = "Erro genérico de ferramenta."

                if most_frequent_error_sig:
                    parts = most_frequent_error_sig.split('_', 2)
                    if len(parts) == 3 and parts[0] == "tool" and parts[1] == "error":
                        failed_tool_name_from_sig = parts[1]
                        error_type_suffix = parts[2]
                        if error_type_suffix == "missing_param":
                            specific_error_type_for_clarification = "Parâmetro ausente ou inválido."
                            error_details_from_sig = "missing_param"
                        elif error_type_suffix == "sandbox_execution_error":
                            specific_error_type_for_clarification = "Erro na execução dentro do sandbox (possivelmente erro de sintaxe ou tempo de execução no script)."
                            error_details_from_sig = "sandbox_execution_error"
                        # Adicionar mais mapeamentos de error_type_suffix para specific_error_type_for_clarification
                        else:
                            specific_error_type_for_clarification = f"Detalhe do erro: {error_type_suffix}"
                            error_details_from_sig = error_type_suffix
                    elif len(parts) >= 2 and parts[0] == "traceback":
                        failed_tool_name_from_sig = parts[1]
                        error_details_from_sig = "Traceback ocorrido"
                        specific_error_type_for_clarification = "Ocorreu um traceback durante a execução da ferramenta."

                feedback += f"\nRecomendação Principal: Investigar a causa raiz do erro repetitivo com '{failed_tool_name_from_sig}'. Tipo de erro: '{specific_error_type_for_clarification}'.\n"
                sugestao_redirecionamento = {
                    "action_type": "MODIFY_PLAN",
                    "details": {
                        "task_description": f"Investigar e corrigir a causa do erro repetitivo com a ferramenta '{failed_tool_name_from_sig}'. Tipo de erro diagnosticado: {specific_error_type_for_clarification}",
                        "priority": "crítica"
                    },
                    "clarification": (f"A ferramenta '{failed_tool_name_from_sig}' está falhando repetidamente. "
                                      f"Diagnóstico: {specific_error_type_for_clarification} "
                                      f"Sugiro adicionar uma tarefa prioritária para investigar e resolver este problema antes de prosseguir. "
                                      "Considere verificar os argumentos passados, o estado do ambiente, ou se a ferramenta é a mais adequada.")
                }
                if most_frequent_error_sig: # Resetar o contador APÓS a sugestão ser feita.
                    self.error_history[most_frequent_error_sig] = 0

            elif any("Desalinhamento Potencial da Intenção" in concern for concern in t50_concerns) and sugestao_redirecionamento is None:
                # Esta condição é para o caso de desalinhamento ser a *única* preocupação crítica no momento.
                # A sugestão de MODIFY_PLAN para desalinhamento já foi criada na seção 0 se detectada.
                # Aqui apenas garantimos que ela seja usada se for a única crítica.
                # (A lógica anterior já define sugestao_redirecionamento na seção 0, então esta 'elif' pode não ser estritamente necessária
                # se a sugestão de desalinhamento for sempre a prioritária quando ocorre. Mas, para clareza:)
                if any("Desalinhamento Potencial da Intenção" in concern for concern in t50_concerns):
                     # A sugestão já deve ter sido definida na seção 0.
                     # Se por algum motivo não foi, poderíamos recriá-la aqui, mas o ideal é que a seção 0 já cuide disso.
                     # Para garantir, vamos verificar se já existe uma sugestão. Se não, e há desalinhamento, criamos.
                     if not sugestao_redirecionamento: # Se a sugestão de desalinhamento não foi criada antes (improvável)
                        feedback += "\nRecomendação Principal: O plano atual pode não refletir totalmente a intenção original do usuário.\n"
                        sugestao_redirecionamento = {
                            "action_type": "MODIFY_PLAN",
                            "details": {
                                "task_description": "Revisar e realinhar o checklist com o prompt inicial do usuário. Considerar resetar o checklist se a tarefa for completamente nova.",
                                "priority": "altíssima"
                            },
                            "clarification": "O plano atual parece desalinhado com o pedido original. Sugiro uma revisão completa do checklist, possivelmente começando um novo."
                        }


            elif any("Estagnação do Checklist" in concern for concern in t50_concerns) or \
                 any("Progresso Lento Inicial" in concern for concern in t50_concerns):
                feedback += "\nRecomendação Principal: Reavaliar a abordagem para as tarefas pendentes do checklist ou decompor tarefas complexas, pois o progresso parece lento.\n"
                sugestao_redirecionamento = {
                    "action_type": "REQUEST_HUMAN_INPUT",
                    "details": {
                        "question": (
                            "O progresso no checklist parece lento ou estagnado. "
                            "Gostaria de reavaliar o plano atual, decompor tarefas complexas, "
                            "ou sugerir uma nova abordagem para as tarefas pendentes?"
                        )
                    },
                    "clarification": "O progresso no checklist está mais lento que o esperado. Uma revisão do plano ou da estratégia pode ser necessária."
                }

        # Lógica de fallback para sugestões baseadas em palavras-chave (se nenhuma preocupação T50 gerou sugestão)
        if not sugestao_redirecionamento:
            tool_results_str_lower = str(tool_results).lower()
            if "loop infinito detectado" in tool_results_str_lower:
                feedback += "\nSinal de loop infinito ou ação repetitiva. Reavaliar abordagem."
                sugestao_redirecionamento = {
                    "action_type": "MODIFY_PLAN",
                    "details": {"task_description": "Analisar e corrigir causa de loop/repetição.", "priority": "alta"},
                    "clarification": "Detectado possível loop. Sugiro investigar a causa."
                }
            elif "falha na ferramenta x" in tool_results_str_lower: # Exemplo genérico, pode ser mais específico
                feedback += "\nA Ferramenta X parece estar falhando."
                sugestao_redirecionamento = {
                    "action_type": "SUGGEST_ALTERNATIVE_TOOL",
                    "details": {"failed_tool": "Ferramenta X", "alternative_tool_name": "Ferramenta Y_alternativa", "alternative_tool_args": {}},
                    "clarification": "A Ferramenta X falhou. Considere usar a Ferramenta Y_alternativa."
                }

        # Para depuração, pode ser útil logar o histórico de erros do crítico.
        # logger.debug(f"Critic error history: {dict(self.error_history)}")

        return feedback, sugestao_redirecionamento

if __name__ == '__main__':
    # Exemplo de uso (para teste)
    class MockLLMClient:
        def __init__(self):
            self.chat = self._Chat()

        class _Chat:
            def __init__(self):
                self.completions = self._Completions()

            class _Completions:
                def create(self, model, messages):
                    class MockChoice:
                        def __init__(self):
                            self.message = self._Message()
                        class _Message:
                            def __init__(self):
                                self.content = "Feedback simulado do LLM: Tudo parece OK."
                    class MockResponse:
                        def __init__(self):
                            self.choices = [MockChoice()]
                    return MockResponse()

    # --- Testes Unitários ---
    mock_llm = MockLLMClient()
    critic = CriticAgent(llm_client=mock_llm)

    # Teste para _parse_checklist_progress
    print("\n--- Teste _parse_checklist_progress ---")
    checklist1 = """
    - [x] Tarefa 1
    - [ ] Tarefa 2
    - [X] Tarefa 3
    - Outra linha
    -    [ ] Tarefa 4 com espaço
    """
    total, completed = critic._parse_checklist_progress(checklist1)
    print(f"Checklist 1: Total={total}, Concluídas={completed} (Esperado: Total=4, Concluídas=2)")
    assert total == 4
    assert completed == 2

    checklist2 = "- [ ] a\n- [ ] b\n- [ ] c"
    total, completed = critic._parse_checklist_progress(checklist2)
    print(f"Checklist 2: Total={total}, Concluídas={completed} (Esperado: Total=3, Concluídas=0)")
    assert total == 3
    assert completed == 0

    checklist_vazio = ""
    total, completed = critic._parse_checklist_progress(checklist_vazio)
    print(f"Checklist Vazio: Total={total}, Concluídas={completed} (Esperado: Total=0, Concluídas=0)")
    assert total == 0
    assert completed == 0

    checklist_invalido = "Não é um checklist"
    total, completed = critic._parse_checklist_progress(checklist_invalido)
    print(f"Checklist Inválido: Total={total}, Concluídas={completed} (Esperado: Total=0, Concluídas=0)")
    assert total == 0
    assert completed == 0

    print("Testes de _parse_checklist_progress passaram!")

    # Testes para review_plan_and_progress
    print("\n--- Testes review_plan_and_progress ---")
    dummy_messages = [{"role": "user", "content": "iniciar"}]

    # Cenário 1: Sem problemas
    print("\nCenário 1: Sem problemas")
    plan_ok = "- [x] T1\n- [x] T2"
    tool_results_ok = [{"name": "tool_a", "content": "sucesso", "tool_call_id": "1"}]
    critic.error_history.clear() # Limpar histórico de erros
    feedback, suggestion = critic.review_plan_and_progress(plan_ok, dummy_messages, tool_results_ok, current_step=5, steps_since_last_review=5)
    print(f"Feedback: {feedback.strip()}")
    print(f"Sugestão: {suggestion}")
    assert suggestion is None
    assert "Nenhuma preocupação crítica" in feedback

    # Cenário 2: Estagnação
    print("\nCenário 2: Estagnação")
    plan_stagnant = "- [ ] T1\n- [ ] T2"
    critic.error_history.clear()
    feedback, suggestion = critic.review_plan_and_progress(plan_stagnant, dummy_messages, tool_results_ok, current_step=20, steps_since_last_review=critic.stagnation_step_threshold)
    print(f"Feedback: {feedback.strip()}")
    print(f"Sugestão: {suggestion}")
    assert suggestion is not None
    assert suggestion["action_type"] == "REQUEST_HUMAN_INPUT"
    assert "Estagnação potencial" in feedback

    # Cenário 3: Erro Repetitivo
    print("\nCenário 3: Erro Repetitivo")
    plan_progress = "- [x] T1\n- [ ] T2"
    tool_results_error = [
        {"name": "tool_b", "content": "Error: falha crítica xyz", "tool_call_id": "2"},
        {"name": "tool_b", "content": "Error: falha crítica xyz", "tool_call_id": "3"},
        {"name": "tool_b", "content": "Error: falha crítica xyz", "tool_call_id": "4"},
    ]
    critic.error_history.clear() # Limpar para teste isolado
    # Simular chamadas anteriores que levaram ao erro repetitivo
    for _ in range(critic.max_error_frequency -1): # -1 porque a chamada abaixo conta como +1
         critic.review_plan_and_progress(plan_progress, dummy_messages, [tool_results_error[0]], current_step=10 + _, steps_since_last_review=1)

    feedback, suggestion = critic.review_plan_and_progress(plan_progress, dummy_messages, [tool_results_error[0]], current_step=15, steps_since_last_review=1)
    print(f"Feedback: {feedback.strip()}")
    print(f"Sugestão: {suggestion}")
    assert suggestion is not None
    assert suggestion["action_type"] == "MODIFY_PLAN"
    assert "Erro repetitivo detectado" in feedback
    assert "tool_b" in suggestion["details"]["task_description"]
    # Verificar se o erro foi resetado no histórico (ou pelo menos não está mais no threshold)
    assert critic.error_history[f"tool_error_tool_b_{'falha crítica xyz'}"] == 0


    # Cenário 4: Loop infinito (palavra-chave)
    print("\nCenário 4: Loop Infinito (palavra-chave)")
    results_with_loop = [{"name": "tool_c", "content": "loop infinito detectado na etapa Y", "tool_call_id": "5"}]
    critic.error_history.clear()
    feedback_loop, suggestion_loop = critic.review_plan_and_progress(plan_progress, dummy_messages, results_with_loop, current_step=20, steps_since_last_review=3)
    print(f"Feedback: {feedback_loop.strip()}")
    print(f"Sugestão: {suggestion_loop}")
    assert suggestion_loop is not None
    assert suggestion_loop["action_type"] == "MODIFY_PLAN"
    assert "loop infinito detectado" in results_with_loop[0]["content"] # Verifica se a entrada está correta
    assert "Sinal de loop infinito" in feedback_loop # Verifica se o feedback reflete isso
    assert "Analisar e corrigir causa de loop/repetição" in suggestion_loop["details"]["task_description"]

    print("\nTestes de review_plan_and_progress passaram!")
