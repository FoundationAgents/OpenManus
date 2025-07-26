import subprocess
import os
from app.config import config, LLMSettings
from app.logger import logger

# Try to import docker, but don't fail if it's not there,
# as the check should handle its absence.
try:
    import docker
    from docker.errors import DockerException
except ImportError:
    docker = None
    DockerException = None # type: ignore

# Try to import openai and anthropic for API key validation
try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None


class EnvironmentValidator:
    """
    Valida pré-requisitos ambientais críticos para a execução do agente.
    """

    def __init__(self, agent_name: str = "default"):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.agent_name = agent_name # Nome do agente para buscar config LLM específica

    async def check_docker_connectivity(self) -> bool:
        """
        Verifica a conectividade com o serviço Docker.
        Tenta listar os containers em execução.
        """
        logger.info("Verificando conectividade com o Docker...")
        if not config.sandbox.use_sandbox:
            msg = "Uso do Sandbox está desabilitado na configuração (config.sandbox.use_sandbox=False). Pulando verificação de Docker."
            logger.info(msg)
            self.warnings.append(msg)
            return True # Não é um erro se o sandbox não for usado

        if docker is None or DockerException is None:
            msg = "Biblioteca Docker (python-docker) não instalada, mas o sandbox está habilitado. Não é possível verificar a conectividade com o Docker. Instale com 'pip install docker'."
            logger.error(msg) # Erro porque o sandbox está habilitado
            self.errors.append(msg)
            return False

        try:
            client = docker.from_env()
            client.ping() # Verifica se o daemon Docker está respondendo
            logger.info("Conexão com o Docker bem-sucedida (ping).")
            # Tentar uma operação mais complexa como listar containers
            client.containers.list(limit=1)
            logger.info("Listagem de containers Docker (limit=1) bem-sucedida.")
            return True
        except DockerException as e:
            msg = (
                "Falha ao conectar ao serviço Docker ou executar operações básicas. Verifique se o Docker está em execução "
                "e se o usuário atual tem permissão para acessá-lo. "
                f"Erro: {e}"
            )
            logger.error(msg)
            self.errors.append(msg)
            return False
        except Exception as e:
            msg = f"Erro inesperado ao verificar a conectividade com o Docker: {e}"
            logger.error(msg)
            self.errors.append(msg)
            return False

    async def _validate_openai_key(self, llm_settings: LLMSettings):
        api_key = llm_settings.api_key
        base_url = llm_settings.base_url
        api_type = llm_settings.api_type
        api_version = llm_settings.api_version

        if not api_key:
            msg = f"Chave da API OpenAI/Azure (config: {self.agent_name}, tipo: {api_type}) não configurada."
            logger.error(msg)
            self.errors.append(msg)
            return False

        if len(api_key) < 10: # Heurística
            msg = f"Chave da API OpenAI/Azure (config: {self.agent_name}, tipo: {api_type}) parece muito curta."
            logger.error(msg)
            self.errors.append(msg)
            return False

        if openai is None:
            msg = "Biblioteca OpenAI (python-openai) não instalada. Não é possível validar a chave da API com uma chamada real."
            logger.warning(msg)
            self.warnings.append(msg)
            return True # Não é um erro de chave, mas de ferramenta de validação

        logger.info(f"Validando chave API para {api_type} (config: {self.agent_name}) com uma chamada de teste...")
        try:
            if api_type == "azure":
                client = openai.AsyncAzureOpenAI(
                    api_key=api_key, azure_endpoint=base_url, api_version=api_version
                )
            else: # openai
                client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url if base_url else None)

            await client.models.list(timeout=10.0) # Chamada leve para testar a chave/conectividade
            logger.info(f"Chave da API OpenAI/Azure (config: {self.agent_name}, tipo: {api_type}) validada com sucesso.")
            return True
        except openai.AuthenticationError as e:
            msg = f"Erro de autenticação ao validar a chave da API OpenAI/Azure (config: {self.agent_name}, tipo: {api_type}). Chave inválida ou permissões incorretas. Erro: {e}"
            logger.error(msg)
            self.errors.append(msg)
            return False
        except openai.APIConnectionError as e:
            msg = f"Erro de conexão ao tentar validar a chave da API OpenAI/Azure (config: {self.agent_name}, tipo: {api_type}). Verifique base_url/endpoint e conectividade. Erro: {e}"
            logger.error(msg)
            self.errors.append(msg)
            return False
        except Exception as e:
            msg = f"Erro inesperado ao validar a chave da API OpenAI/Azure (config: {self.agent_name}, tipo: {api_type}): {e}"
            logger.error(msg)
            self.errors.append(msg)
            return False

    async def _validate_anthropic_key(self, llm_settings: LLMSettings):
        api_key = llm_settings.api_key
        if not api_key:
            msg = f"Chave da API Anthropic (config: {self.agent_name}) não configurada."
            logger.error(msg)
            self.errors.append(msg)
            return False

        if len(api_key) < 10:  # Heurística
            msg = f"Chave da API Anthropic (config: {self.agent_name}) parece muito curta."
            logger.error(msg)
            self.errors.append(msg)
            return False

        if anthropic is None:
            msg = "Biblioteca Anthropic (python-anthropic) não instalada. Não é possível validar a chave da API com uma chamada real."
            logger.warning(msg)
            self.warnings.append(msg)
            return True # Não é um erro de chave, mas de ferramenta de validação

        logger.info(f"Validando chave API Anthropic (config: {self.agent_name}) com uma chamada de teste...")
        try:
            # A biblioteca Anthropic não tem um método async fácil para `models.list` no construtor síncrono.
            # Para uma verificação simples, podemos instanciar e assumir que falhará no construtor ou na primeira chamada se a chave for ruim.
            # Uma verificação mais robusta exigiria uma chamada async real se disponível ou rodar a síncrona em um executor.
            # Por simplicidade, vamos apenas instanciar.
            # sync_client = anthropic.Anthropic(api_key=api_key)
            # Idealmente, faríamos uma chamada leve, mas a SDK pode não ter um `count_tokens` síncrono fácil ou `models.list` sem ser async.
            # O SDK atual da Anthropic (0.20+) usa `AsyncAnthropic` para chamadas async.
            async_client = anthropic.AsyncAnthropic(api_key=api_key)
            # Não há um `models.list()` direto no cliente Anthropic.
            # Uma chamada leve poderia ser tentar contar tokens de uma string vazia,
            # mas isso pode não validar a chave tanto quanto uma chamada de API real.
            # Vamos tentar uma chamada de mensagem com poucos tokens.
            await async_client.messages.create(
                model="claude-3-haiku-20240307", # Modelo leve
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}]
            )
            logger.info(f"Chave da API Anthropic (config: {self.agent_name}) validada com sucesso.")
            return True
        except anthropic.AuthenticationError as e:
            msg = f"Erro de autenticação ao validar a chave da API Anthropic (config: {self.agent_name}). Chave inválida? Erro: {e}"
            logger.error(msg)
            self.errors.append(msg)
            return False
        except anthropic.APIConnectionError as e:
            msg = f"Erro de conexão ao tentar validar a chave da API Anthropic (config: {self.agent_name}). Verifique conectividade. Erro: {e}"
            logger.error(msg)
            self.errors.append(msg)
            return False
        except Exception as e:
            msg = f"Erro inesperado ao validar a chave da API Anthropic (config: {self.agent_name}): {e}"
            logger.error(msg)
            self.errors.append(msg)
            return False

    async def check_api_keys(self) -> bool:
        """
        Verifica a validade das chaves de API necessárias com base na configuração do agente.
        """
        logger.info(f"Verificando chaves de API para configuração do agente: '{self.agent_name}'...")

        if not hasattr(config, 'llm') or not config.llm:
            msg = "Configuração LLM (config.llm) não encontrada ou vazia."
            logger.error(msg)
            self.errors.append(msg)
            return False

        llm_settings_for_agent = config.llm.get(self.agent_name.lower())
        if not llm_settings_for_agent:
            logger.info(f"Nenhuma configuração LLM específica para '{self.agent_name}'. Usando configuração 'default'.")
            llm_settings_for_agent = config.llm.get("default")
            if not llm_settings_for_agent:
                msg = "Configuração LLM 'default' não encontrada."
                logger.error(msg)
                self.errors.append(msg)
                return False

        api_type = getattr(llm_settings_for_agent, 'api_type', '').lower()
        base_url = getattr(llm_settings_for_agent, 'base_url', '').lower()
        key_valid = False

        if api_type == "openai" or api_type == "azure":
            key_valid = await self._validate_openai_key(llm_settings_for_agent)
        elif api_type == "anthropic" or "anthropic.com" in base_url:
            key_valid = await self._validate_anthropic_key(llm_settings_for_agent)
        elif api_type == "aws":
            # Placeholder para validação de Bedrock/AWS
            logger.info(f"Validação de API para AWS (Bedrock) (config: {self.agent_name}) não implementada ainda. Assumindo OK se chave estiver presente.")
            if not llm_settings_for_agent.api_key: # AWS pode não usar api_key diretamente assim
                 msg = f"Configuração de API para AWS (config: {self.agent_name}) parece incompleta (sem api_key, pode usar roles IAM)."
                 self.warnings.append(msg)
            key_valid = True # Simplificação por agora
        else:
            msg = f"Tipo de API desconhecido ou não suportado para validação: '{api_type}' (config: {self.agent_name}). Pulando validação de chave."
            logger.warning(msg)
            self.warnings.append(msg)
            key_valid = True # Não podemos validar, então não falhamos

        if key_valid and not self.errors:
             logger.info(f"Verificação de chaves de API para '{self.agent_name}' concluída sem erros críticos detectados.")
        return key_valid and not self.errors


    async def run_all_checks(self) -> tuple[bool, list[str]]:
        """
        Executa todas as verificações de ambiente.

        Returns:
            tuple[bool, list[str]]: (True se tudo OK, False se houver erros), lista de mensagens de erro/aviso.
        """
        self.errors = []
        self.warnings = []

        docker_ok = await self.check_docker_connectivity()
        keys_ok = await self.check_api_keys()

        # Adicionar outras chamadas de verificação aqui
        # example_service_ok = await self.check_example_service()

        # Consolidar mensagens de erro e aviso
        all_messages = []
        if self.errors:
            all_messages.extend([f"[ERRO] {e}" for e in self.errors])
        if self.warnings:
            all_messages.extend([f"[AVISO] {w}" for w in self.warnings])

        if not self.errors: # Somente se não houver erros, consideramos sucesso
            logger.info("Validação de pré-execução do ambiente concluída com sucesso.")
            return True, all_messages
        else:
            logger.error(f"Validação de pré-execução do ambiente falhou com {len(self.errors)} erro(s).")
            return False, all_messages

if __name__ == '__main__':
    # Exemplo de uso (requer que app.config e app.logger sejam acessíveis)
    async def main():
        print("Executando EnvironmentValidator standalone...")
        validator = EnvironmentValidator()
        success, messages = await validator.run_all_checks()
        if success:
            print("Validação do ambiente: SUCESSO")
        else:
            print("Validação do ambiente: FALHA")
        for msg in messages:
            print(msg)

    # Para executar o main assíncrono:
    # import asyncio
    # asyncio.run(main())
    # No entanto, este script não é destinado a ser executado diretamente com frequência,
    # mas sim importado e usado pelo agente.
    pass
