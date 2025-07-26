"""Interfaces e implementações de operações de arquivo para ambientes locais e sandbox."""

import asyncio
from pathlib import Path
from typing import Optional, Protocol, Tuple, Union, runtime_checkable

# Garantir que estes sejam importados apenas uma vez e corretamente
from app.config import SandboxSettings, config # Garantir que 'config' seja importado
from app.exceptions import ToolError
from app.sandbox.client import SANDBOX_CLIENT
from app.logger import logger # Garantir que logger seja importado

PathLike = Union[str, Path]


@runtime_checkable
class FileOperator(Protocol):
    """Interface para operações de arquivo em diferentes ambientes."""

    async def read_file(self, path: PathLike) -> str:
        """Lê o conteúdo de um arquivo."""
        ...

    async def write_file(self, path: PathLike, content: str) -> None:
        """Escreve conteúdo em um arquivo."""
        ...

    async def is_directory(self, path: PathLike) -> bool:
        """Verifica se o caminho aponta para um diretório."""
        ...

    async def exists(self, path: PathLike) -> bool:
        """Verifica se o caminho existe."""
        ...

    async def run_command(
        self, cmd: str, timeout: Optional[float] = 120.0
    ) -> Tuple[int, str, str]:
        """Executa um comando de shell e retorna (código_de_retorno, stdout, stderr)."""
        ...

    async def get_sandbox_path(self, host_path: PathLike) -> str:
        """Traduz um caminho do host para seu equivalente no sandbox, se aplicável."""
        raise NotImplementedError


class LocalFileOperator(FileOperator):
    """Implementação de operações de arquivo para o sistema de arquivos local."""

    encoding: str = "utf-8"

    async def read_file(self, path: PathLike) -> str:
        """Lê o conteúdo de um arquivo local."""
        try:
            content = Path(path).read_text(encoding=self.encoding)
            return content
        except Exception as e:
            raise ToolError(f"Falha ao ler {path}: {str(e)}") from None

    async def write_file(self, path: PathLike, content: str) -> None:
        """Escreve conteúdo em um arquivo local."""
        try:
            Path(path).write_text(content, encoding=self.encoding)
        except Exception as e:
            raise ToolError(f"Falha ao escrever em {path}: {str(e)}") from None

    async def is_directory(self, path: PathLike) -> bool:
        """Verifica se o caminho aponta para um diretório."""
        result = Path(path).is_dir()
        return result

    async def exists(self, path: PathLike) -> bool:
        """Verifica se o caminho existe."""
        result = Path(path).exists()
        return result

    async def run_command(
        self, cmd: str, timeout: Optional[float] = 120.0
    ) -> Tuple[int, str, str]:
        """Executa um comando de shell localmente."""
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return (
                process.returncode or 0,
                stdout.decode(),
                stderr.decode(),
            )
        except asyncio.TimeoutError as exc:
            try:
                process.kill()
            except ProcessLookupError:
                pass # Processo já encerrado
            raise TimeoutError(
                f"Comando '{cmd}' excedeu o tempo limite após {timeout} segundos"
            ) from exc
        
    async def get_sandbox_path(self, host_path: PathLike) -> str:
        """Operador local não traduz para caminhos do sandbox, retorna o original."""
        return str(host_path)

    async def delete_file(self, path: PathLike) -> None:
        """Deleta um arquivo local."""
        try:
            Path(path).unlink(missing_ok=True) # missing_ok=True para não dar erro se já não existir
            logger.info(f"Arquivo local {path} deletado (ou já não existia).")
        except Exception as e:
            raise ToolError(f"Falha ao deletar arquivo local {path}: {str(e)}")


class SandboxFileOperator(FileOperator):
    """Implementação de operações de arquivo para o ambiente sandbox."""

    SANDBOX_WORKSPACE_PATH = "/workspace" # Workspace padrão do sandbox

    def __init__(self):
        self.sandbox_client = SANDBOX_CLIENT
        self.host_workspace_root = Path(config.workspace_root).resolve()

    def _translate_to_sandbox_path(self, host_path: PathLike) -> str:
        """Traduz um caminho absoluto do host para seu caminho correspondente no sandbox."""
        resolved_host_path = Path(host_path).resolve()
        try:
            relative_path = resolved_host_path.relative_to(self.host_workspace_root)
        except ValueError as e:
            raise ToolError(
                f"O caminho '{host_path}' não está dentro do workspace do host configurado "
                f"'{self.host_workspace_root}'. Não é possível traduzir para o caminho do sandbox."
            ) from e
        sandbox_path = Path(self.SANDBOX_WORKSPACE_PATH) / relative_path
        return str(sandbox_path)

    async def get_sandbox_path(self, host_path: PathLike) -> str:
        """Método público para obter o caminho traduzido do sandbox."""
        translated_path = self._translate_to_sandbox_path(host_path)
        return translated_path

    async def _ensure_sandbox_initialized(self):
        """Garante que o sandbox esteja inicializado."""
        if not self.sandbox_client.sandbox:
            await self.sandbox_client.create(config=SandboxSettings())

    async def read_file(self, path: PathLike) -> str:
        """Lê o conteúdo de um arquivo no sandbox."""
        await self._ensure_sandbox_initialized()
        sandbox_path = self._translate_to_sandbox_path(path)
        try:
            content = await self.sandbox_client.read_file(sandbox_path)
            return content
        except Exception as e:
            raise ToolError(f"Falha ao ler {sandbox_path} no sandbox: {str(e)}") from None

    async def write_file(self, path: PathLike, content: str) -> None:
        """Escreve conteúdo em um arquivo no sandbox."""
        await self._ensure_sandbox_initialized()
        sandbox_path = self._translate_to_sandbox_path(path)
        try:
            await self.sandbox_client.write_file(sandbox_path, content)
        except Exception as e:
            raise ToolError(f"Falha ao escrever em {sandbox_path} no sandbox: {str(e)}") from None

    async def is_directory(self, path: PathLike) -> bool:
        """Verifica se o caminho aponta para um diretório no sandbox."""
        await self._ensure_sandbox_initialized()
        sandbox_path = self._translate_to_sandbox_path(path)
        cmd_str = f"test -d {sandbox_path} && echo 'true' || echo 'false'"
        result_str = await self.sandbox_client.run_command(cmd_str)
        result_bool = result_str.strip().lower() == "true" # Garante comparação em minúsculas
        return result_bool

    async def exists(self, path: PathLike) -> bool:
        """Verifica se o caminho existe no sandbox."""
        await self._ensure_sandbox_initialized()
        sandbox_path = self._translate_to_sandbox_path(path)
        cmd_str = f"test -e {sandbox_path} && echo 'true' || echo 'false'"
        result_str = await self.sandbox_client.run_command(cmd_str)
        result_bool = result_str.strip().lower() == "true" # Garante comparação em minúsculas
        return result_bool

    async def run_command(
        self, cmd: str, timeout: Optional[float] = 120.0
    ) -> Tuple[int, str, str]:
        """Executa um comando no ambiente sandbox."""
        await self._ensure_sandbox_initialized()
        try:
            stdout = await self.sandbox_client.run_command(
                cmd, timeout=int(timeout) if timeout else None
            )
            return (
                0,
                stdout,
                "", 
            )
        except TimeoutError as exc:
            raise TimeoutError(
                f"Comando '{cmd}' excedeu o tempo limite após {timeout} segundos no sandbox"
            ) from exc
        except Exception as exc:
            return 1, "", f"Erro ao executar comando no sandbox: {str(exc)}"
