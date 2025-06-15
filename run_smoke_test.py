import asyncio
import logging
import os

# Configurar o logging para capturar saídas do agente e das ferramentas
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Adicionar o diretório 'app' ao PYTHONPATH para permitir importações diretas
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app.agent.manus import Manus
from app.config import Config, SearchConfig, BrowserConfig, ProxyConfig, MCPConfig
from app.memory.base import Message
from app.tool.web_search import WebSearch, SearchResponse
# from app.tool.browser_use_tool import BrowserUseTool # Removido para este teste
from app.tool.base import ToolResult
from app.exceptions import ToolError

async def main():
    logger.info("Iniciando script de teste de fumaça (foco em WebSearch).")

    from app.config import config as app_config
    if not hasattr(app_config, 'search_config') or app_config.search_config is None:
        app_config.search_config = SearchConfig()
    if not hasattr(app_config, 'browser_config') or app_config.browser_config is None:
        # Mesmo que não usemos a ferramenta, a config pode ser acessada em algum lugar
        app_config.browser_config = BrowserConfig()
    if not hasattr(app_config, 'mcp_config') or app_config.mcp_config is None:
        app_config.mcp_config = MCPConfig(servers={})

    try:
        agent = Manus(name="SmokeTestAgent", system_prompt="Test", next_step_prompt="Test")
        logger.info("Instância de Manus criada para o teste.")

        # Modificar temporariamente o método think para o teste de fumaça
        original_think = agent.think
        async def smoke_test_think():
            logger.info("INICIANDO TESTE DE FUMAÇA DO MÉTODO THINK (MODIFICADO)")
            agent.planned_tool_calls = [] # Resetar planned_tool_calls
            test_summary_lines = ["Resumo do Teste de Fumaça (WebSearch Apenas):"]
            tasks = []
            test_queries = [
                "o que é inteligência artificial?",
                "python non_existent_library_for_error_test",
                "latest news on climate change"
            ]
            # url_for_timeout_test = "http://localhost:12345/nonexistent" # Removido

            web_search_tool = agent.available_tools.get_tool('web_search')
            # browser_use_tool = agent.available_tools.get_tool('browser_use_tool') # Removido

            if web_search_tool:
                for query in test_queries:
                    tasks.append(
                        web_search_tool.execute(query=query, fetch_content=True, num_results=1)
                    )
            else:
                test_summary_lines.append("- Ferramenta web_search não encontrada.")
                logger.error("SMOKE TEST: web_search tool not found.")

            # if browser_use_tool: # Removido
            #     tasks.append(
            #         browser_use_tool.execute(action="go_to_url", url=url_for_timeout_test)
            #     )
            # else:
            #    test_summary_lines.append("- Ferramenta browser_use_tool não pôde ser testada (dependência de versão Python).")
            #    logger.warning("SMOKE TEST: browser_use_tool não incluída no teste devido a dependência de versão Python.")

            if not tasks and web_search_tool: # Adicionado web_search_tool para clareza
                 test_summary_lines.append("- Nenhuma tarefa de web_search para executar.")
                 logger.info("SMOKE TEST: Nenhuma tarefa de web_search para executar.")
            elif not tasks:
                 test_summary_lines.append("- Nenhuma tarefa para executar (web_search não encontrada).")
                 logger.error("SMOKE TEST: Nenhuma tarefa para executar (web_search não encontrada).")


            if tasks:
                logger.info(f"SMOKE TEST: Executando {len(tasks)} tarefas com asyncio.gather...")
                all_results = await asyncio.gather(*tasks, return_exceptions=True)
                logger.info("SMOKE TEST: Coleta de dados assíncrona do teste concluída.")

                for i, result_or_exc in enumerate(all_results):
                    original_input = f"WebSearch Query: '{test_queries[i]}'" # Ajustado, pois só há web_search agora

                    line = f"Resultado para [{original_input}]: "
                    if isinstance(result_or_exc, Exception):
                        line += f"FALHA. Erro: {type(result_or_exc).__name__} - {str(result_or_exc)}"
                        logger.error(f"SMOKE TEST RESULT: {original_input} -> FALHA. Erro: {type(result_or_exc).__name__} - {str(result_or_exc)}")
                    elif hasattr(result_or_exc, 'error') and result_or_exc.error:
                        line += f"FALHA. Erro da Ferramenta: {result_or_exc.error}"
                        logger.warning(f"SMOKE TEST RESULT: {original_input} -> FALHA. Erro da Ferramenta: {result_or_exc.error}")
                    elif hasattr(result_or_exc, 'output'):
                        line += f"SUCESSO. Output: {result_or_exc.output[:100]}..."
                        logger.info(f"SMOKE TEST RESULT: {original_input} -> SUCESSO. Output: {result_or_exc.output[:100]}...")
                        if hasattr(result_or_exc, 'results') and isinstance(result_or_exc.results, list) and result_or_exc.results:
                            first_res = result_or_exc.results[0]
                            logger.info(f"  -> Detalhe WebSearch: Título: {first_res.title}, URL: {first_res.url}, Conteúdo Raw: {str(first_res.raw_content)[:100]}...")
                    else:
                        line += f"STATUS DESCONHECIDO. Resultado: {str(result_or_exc)[:100]}..."
                        logger.warning(f"SMOKE TEST RESULT: {original_input} -> STATUS DESCONHECIDO. Resultado: {str(result_or_exc)[:100]}...")
                    test_summary_lines.append(line)

            test_summary_lines.append("- Ferramenta browser_use_tool não foi testada devido a incompatibilidade da versão do Python com a dependência 'browser-use'.")

            final_summary = "\n".join(test_summary_lines)
            agent.memory.add_message(Message(role="assistant", content=final_summary)) # Usando objeto Message
            logger.info("SMOKE TEST: Teste de fumaça do método think concluído.")
            logger.info(f"SMOKE TEST: Resumo final adicionado à memória:\n{final_summary}")

            agent.tool_calls = []
            return True

        agent.think = smoke_test_think # Substitui o método think original pelo de teste

        logger.info("Chamando o método think() modificado para o teste...")
        await agent.think()
        logger.info("Método think() do teste concluído.")

        summary_message_obj = None
        if agent.memory.messages:
            for msg in reversed(agent.memory.messages):
                if msg.role == "assistant":
                    summary_message_obj = msg
                    break

        if summary_message_obj:
            logger.info("Resumo do teste recuperado da memória do agente:")
            print("--- INÍCIO DO RESUMO DO TESTE ---")
            print(summary_message_obj.content)
            print("--- FIM DO RESUMO DO TESTE ---")
        else:
            logger.warning("Nenhuma mensagem de resumo encontrada na memória do agente.")
            print("Nenhuma mensagem de resumo encontrada na memória do agente.")

        # Restaurar o método think original (opcional, pois o agente é descartado)
        agent.think = original_think
        logger.info("Método think original restaurado (simbolicamente).")

        logger.info("Executando limpeza do agente...")
        await agent.cleanup() # Cleanup ainda é importante
        logger.info("Limpeza do agente concluída.")

    except Exception as e:
        logger.error(f"Erro durante a execução do script de teste de fumaça: {e}", exc_info=True)
        print(f"ERRO NO TESTE DE FUMAÇA: {e}")

if __name__ == "__main__":
    asyncio.run(main())
