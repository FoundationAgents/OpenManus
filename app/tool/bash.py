import asyncio
import os
from typing import Optional

from app.config import config
from app.exceptions import ToolError
from app.tool.base import BaseTool, CLIResult
from app.logger import logger # ADDED


_BASH_DESCRIPTION = '''Execute a bash command in the terminal.
* working_directory: Optional. The working directory from which to run the command. If not specified, uses the agent's current working directory. This directory is set when the session (re)starts.
* Long running commands: For commands that may run indefinitely, it should be run in the background and the output should be redirected to a file, e.g. command = `python3 app.py > server.log 2>&1 &`.
* Interactive: If a bash command returns exit code `-1`, this means the process is not yet finished. The assistant must then send a second call to terminal with an empty `command` (which will retrieve any additional logs), or it can send additional text (set `command` to the text) to STDIN of the running process, or it can send command=`ctrl+c` to interrupt the process.
* Timeout: If a command execution result says "Command timed out. Sending SIGINT to the process", the assistant should retry running the command in the background.'''


class _BashSession:
    """A session of a bash shell."""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "/bin/bash"
    _output_delay: float = 0.2  # segundos
    _timeout: float = 86400.0  # segundos (24 horas)
    _sentinel: str = "<<exit>>"

    def __init__(self):
        self._started = False
        self._timed_out = False

    async def start(self, working_directory: Optional[str] = None): # Adicionar parâmetro
        if self._started:
            return

        self._process = await asyncio.create_subprocess_shell(
            self.command,
            # preexec_fn=os.setsid, # Esta linha já deve estar removida/comentada
            shell=True,
            bufsize=0,
            cwd=working_directory, # Adicionar este parâmetro
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._started = True

    def stop(self): # Renomear para indicar que é síncrono e apenas tenta terminar
        """Tenta encerrar o processo do shell bash."""
        if not self._started or not hasattr(self, '_process') or self._process.returncode is not None: # Adicionado hasattr
            return
        try:
            self._process.terminate()
            logger.info("Processo Bash encerrado.")
        except ProcessLookupError: 
            logger.info("Processo Bash já encerrado.")
        except Exception as e: 
            logger.error(f"Erro ao encerrar processo bash: {e}")

    async def close_async(self): # Novo método assíncrono para limpeza completa
        """Fecha stdin, encerra o processo e espera que ele saia."""
        logger.info("_BashSession.close_async: Iniciando...")
        if not self._started or not hasattr(self, '_process') or self._process.returncode is not None:
            logger.info("_BashSession.close_async: Sessão já fechada ou não iniciada.")
            return

        logger.info("_BashSession.close_async: Fechando sessão bash assincronamente...")
        try:
            if self._process.stdin and hasattr(self._process.stdin, 'is_closing') and not self._process.stdin.is_closing():
                try:
                    logger.info("_BashSession.close_async: Tentando escrever EOF para stdin.")
                    self._process.stdin.write_eof()
                    await self._process.stdin.drain() 
                    logger.info("_BashSession.close_async: EOF do stdin do Bash enviado e drenado.")
                except (ConnectionResetError, BrokenPipeError, AttributeError) as e: 
                    logger.warning(f"_BashSession.close_async: Erro ao enviar EOF para stdin do bash (pode já estar fechado): {e}")
                except Exception as e:
                    logger.error(f"_BashSession.close_async: Erro inesperado ao fechar stdin do bash: {e}")
                finally:
                    if self._process.stdin and hasattr(self._process.stdin, 'close') and hasattr(self._process.stdin, 'is_closing') and not self._process.stdin.is_closing(): # Checagens extras
                        self._process.stdin.close()

            if self._process.returncode is None: 
                logger.info("_BashSession.close_async: Tentando encerrar processo.")
                self._process.terminate()
                logger.info("_BashSession.close_async: SIGTERM enviado para o processo bash.")
                try:
                    logger.info("_BashSession.close_async: Aguardando processo sair após encerrar...")
                    await asyncio.wait_for(self._process.wait(), timeout=5.0) 
                    logger.info(f"_BashSession.close_async: Processo Bash saiu com código {self._process.returncode}.")
                except asyncio.TimeoutError:
                    logger.warning("_BashSession.close_async: Processo Bash não encerrou graciosamente após 5s, enviando SIGKILL.")
                    if self._process.returncode is None: 
                        logger.info("_BashSession.close_async: Processo não encerrou, tentando matar.")
                        self._process.kill()
                        await self._process.wait() 
                        logger.info(f"_BashSession.close_async: Processo Bash morto. Código de saída {self._process.returncode}.")
                except ProcessLookupError:
                    logger.info("_BashSession.close_async: Processo Bash já havia saído antes de aguardar.")
                except Exception as e: 
                    logger.error(f"_BashSession.close_async: Erro durante a espera do processo bash: {e}")
        except ProcessLookupError: 
            logger.info("_BashSession.close_async: Processo Bash não existe (já limpo).")
        except Exception as e:
            logger.error(f"_BashSession.close_async: Erro durante close_async da sessão bash: {e}")
        finally:
            logger.info("_BashSession.close_async: Definindo self._started para False.")
            self._started = False 
            if hasattr(self, '_process'): # Garantir que _process existe
                logger.info(f"close_async da sessão Bash concluído. Código de retorno final do processo: {self._process.returncode}")
            else:
                logger.info("close_async da sessão Bash concluído (atributo de processo ausente).")

    async def run(self, command: str):
        """Executa um comando no shell bash."""
        if not self._started:
            raise ToolError("A sessão não foi iniciada.")
        if self._process.returncode is not None:
            return CLIResult(
                system="a ferramenta precisa ser reiniciada",
                error=f"bash saiu com código de retorno {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"tempo esgotado: bash não retornou em {self._timeout} segundos e precisa ser reiniciado",
            )

        # sabemos que estes não são None porque criamos o processo com PIPEs
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr

        # envia comando para o processo
        self._process.stdin.write(
            command.encode() + f"; echo '{self._sentinel}'\n".encode()
        )
        await self._process.stdin.drain()

        # lê a saída do processo, até que o sentinela seja encontrado
        async def _read_output_with_sentinel():
            while True:
                await asyncio.sleep(self._output_delay)
                # se lermos diretamente de stdout/stderr, ele esperará para sempre por
                # EOF. use o buffer StreamReader diretamente.
                output_val = ( # Renomeado para output_val para evitar conflito com 'output' do escopo externo
                    self._process.stdout._buffer.decode()
                )  # pyright: ignore[reportAttributeAccessIssue]
                if self._sentinel in output_val:
                    # remove o sentinela e quebra
                    output_val = output_val[: output_val.index(self._sentinel)]
                    return output_val # Retorna a saída quando o sentinela é encontrado
                # Verifica se o processo saiu inesperadamente para evitar loop infinito.
                if self._process.returncode is not None:
                    logger.warning("_BashSession._read_output_with_sentinel: Processo saiu prematuramente.")
                    # Tenta obter qualquer saída restante, pode não conter o sentinela
                    return self._process.stdout._buffer.decode() # pyright: ignore[reportAttributeAccessIssue]
        
        output = "" # Inicializa output para garantir que esteja definido
        try:
            output = await asyncio.wait_for(_read_output_with_sentinel(), timeout=self._timeout)
        except asyncio.TimeoutError:
            self._timed_out = True
            # logger.error(f"Comando atingiu o tempo limite após {self._timeout}s em _BashSession.run") # Logger disponível
            raise ToolError(
                f"tempo esgotado: bash não retornou em {self._timeout} segundos e precisa ser reiniciado",
            ) from None

        if output and output.endswith("\n"): # Verifica se output não é None
            output = output[:-1]

        error = (
            self._process.stderr._buffer.decode()
        )  # pyright: ignore[reportAttributeAccessIssue]
        if error.endswith("\n"):
            error = error[:-1]

        # limpa os buffers para que a próxima saída possa ser lida corretamente
        self._process.stdout._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]
        self._process.stderr._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]

        return CLIResult(output=output, error=error)


class Bash(BaseTool):
    """Uma ferramenta para executar comandos bash"""

    name: str = "bash"
    description: str = _BASH_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "O comando bash a ser executado. Pode estar vazio para visualizar logs adicionais quando o código de saída anterior for `-1`. Pode ser `ctrl+c` para interromper o processo em execução no momento.",
            },
            "working_directory": { # Novo parâmetro
                "type": "string",
                "description": "Opcional. O diretório de trabalho a partir do qual executar o comando. Assume o diretório de trabalho atual do agente se não especificado. Este diretório é definido quando a sessão (re)inicia.",
                "nullable": True 
            }
        },
        "required": ["command"],
    }

    _session: Optional[_BashSession] = None

    async def execute(
        self, command: str | None = None, restart: bool = False, working_directory: Optional[str] = None, **kwargs # Adicionar parâmetro
    ) -> CLIResult:
        if restart:
            if self._session:
                await self._session.close_async() # MUDAR AQUI
            self._session = _BashSession()
            # Usar config.workspace_root como padrão para working_directory
            effective_working_directory = working_directory if working_directory is not None else str(config.workspace_root)
            await self._session.start(working_directory=effective_working_directory)
            return CLIResult(system="a ferramenta foi reiniciada.")

        if self._session is None:
            self._session = _BashSession()
            # Usar config.workspace_root como padrão para working_directory
            effective_working_directory = working_directory if working_directory is not None else str(config.workspace_root)
            await self._session.start(working_directory=effective_working_directory)

        if command is not None:
            # Nota: working_directory é definido no início da sessão. 
            # Se for necessário mudar por comando, o próprio comando 'cd' deve ser usado.
            return await self._session.run(command)

        raise ToolError("nenhum comando fornecido.")

    async def cleanup(self):
        """Limpa a sessão bash se ela existir."""
        logger.info("Bash.cleanup: Iniciando...")
        if self._session:
            logger.info("Bash.cleanup: Prester a chamar self._session.close_async()")
            await self._session.close_async()
            logger.info("Bash.cleanup: self._session.close_async() concluído.")
            self._session = None
            logger.info("Bash.cleanup: self._session definido como None.")
        else:
            logger.info("Bash.cleanup: Nenhuma sessão ativa da ferramenta Bash para limpar.")
        logger.info("Bash.cleanup: Finalizado.")


if __name__ == "__main__":
    bash = Bash()
    rst = asyncio.run(bash.execute("ls -l"))
    print(rst)
