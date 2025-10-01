#!/usr/bin/env python3
"""
Chainlit Standalone - Interface web para demonstrar os sandbox adapters
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import chainlit as cl
from chainlit.config import config

from app.config import Config
from app.sandbox.adapters.factory import SandboxFactory
from app.sandbox.adapters.unified_client import UnifiedSandboxClient

# Global client para reutilizar conexões
global_client = None
global_sandbox_id = None


@cl.on_chat_start
async def start():
    """Inicializar sessão do chat."""
    global global_client, global_sandbox_id

    await cl.Message(
        content="🚀 **OpenManus Sandbox Demo**\\n\\nBem-vindo ao sistema de sandbox open source!"
    ).send()

    try:
        # Carregar configuração
        config_obj = Config()
        sandbox_config = config_obj.sandbox

        # Verificar backends disponíveis
        available = SandboxFactory.get_available_adapters()
        best = SandboxFactory.auto_detect_backend()

        backend = sandbox_config.backend or best

        await cl.Message(
            content=f"""
📋 **Configuração:**
- Backend: `{backend}`
- Backends disponíveis: `{', '.join(available)}`
- Imagem: `{sandbox_config.image}`

🔧 Criando sandbox...
            """,
        ).send()

        # Criar cliente e sandbox
        global_client = UnifiedSandboxClient(backend)
        global_sandbox_id = await global_client.create_sandbox()

        await cl.Message(
            content=f"""
✅ **Sandbox criado com sucesso!**
- ID: `{global_sandbox_id}`
- Backend: `{backend}`

💡 **Comandos disponíveis:**
- Execute qualquer comando Linux/Python
- `ls /path` - listar arquivos
- `write /path/file.txt conteúdo` - criar arquivo
- `read /path/file.txt` - ler arquivo
- `python3 -c "print('Hello')"` - executar Python

Digite seu comando abaixo!
            """,
        ).send()

    except Exception as e:
        await cl.Message(
            content=f"❌ **Erro ao inicializar sandbox:** {e}",
        ).send()


@cl.on_message
async def main(message: cl.Message):
    """Processar mensagens do usuário."""
    global global_client, global_sandbox_id

    if not global_client or not global_sandbox_id:
        await cl.Message(
            content="❌ Sandbox não inicializado. Recarregue a página."
        ).send()
        return

    user_input = message.content.strip()

    if not user_input:
        return

    # Mostrar que está processando
    processing_msg = cl.Message(content="⏳ Executando comando...")
    await processing_msg.send()

    try:
        # Comandos especiais
        if user_input.startswith("write "):
            # write /path/file.txt content here
            parts = user_input[6:].split(" ", 1)
            if len(parts) == 2:
                path, content = parts
                await global_client.write_file(global_sandbox_id, path, content)

                await processing_msg.update(
                    content=f"""
✅ **Arquivo criado**
- Caminho: `{path}`
- Tamanho: {len(content)} caracteres
                    """
                )
                return
            else:
                await processing_msg.update(
                    content="❌ **Uso:** `write /path/to/file.txt conteúdo do arquivo`"
                )
                return

        elif user_input.startswith("read "):
            # read /path/file.txt
            path = user_input[5:].strip()
            try:
                content = await global_client.read_file(global_sandbox_id, path)
                await processing_msg.update(
                    content=f"""
📄 **Conteúdo de {path}:**
```
{content}
```
                    """
                )
                return
            except Exception as e:
                await processing_msg.update(content=f"❌ **Erro lendo arquivo:** {e}")
                return

        elif user_input.startswith("ls "):
            # ls /path
            path = user_input[3:].strip() or "/"
            try:
                files = await global_client.list_files(global_sandbox_id, path)
                files_list = "\\n".join([f"- {f}" for f in files])

                await processing_msg.update(
                    content=f"""
📁 **Arquivos em {path}:**
{files_list if files else "*(vazio)*"}

Total: {len(files)} arquivos
                    """
                )
                return
            except Exception as e:
                await processing_msg.update(
                    content=f"❌ **Erro listando diretório:** {e}"
                )
                return

        # Comando normal do sistema
        result = await global_client.execute(global_sandbox_id, user_input)

        # Preparar resposta
        response_parts = []
        response_parts.append(f"**Comando:** `{user_input}`")
        response_parts.append(f"**Tempo de execução:** {result.execution_time:.2f}s")

        if result.stdout:
            response_parts.append(f"**Saída:**\\n```\\n{result.stdout.rstrip()}\\n```")

        if result.stderr:
            response_parts.append(f"**Erro:**\\n```\\n{result.stderr.rstrip()}\\n```")

        if result.exit_code != 0:
            response_parts.append(f"**Exit Code:** {result.exit_code}")
            response_parts.insert(0, "⚠️")
        else:
            response_parts.insert(0, "✅")

        await processing_msg.update(content="\\n\\n".join(response_parts))

    except Exception as e:
        await processing_msg.update(content=f"❌ **Erro executando comando:** {e}")


@cl.on_chat_end
async def end():
    """Limpar recursos ao fim da sessão."""
    global global_client, global_sandbox_id

    if global_client and global_sandbox_id:
        try:
            await global_client.destroy_sandbox(global_sandbox_id)
            await cl.Message(content="🧹 Sandbox limpo com sucesso!").send()
        except Exception as e:
            print(f"Erro limpando sandbox: {e}")
        finally:
            global_client = None
            global_sandbox_id = None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenManus Chainlit Sandbox Demo")
    parser.add_argument("--host", default="localhost", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # Configurar Chainlit
    config.ui.name = "OpenManus Sandbox Demo"

    print(f"🌐 Iniciando Chainlit em http://{args.host}:{args.port}")
    print("🔧 Sistema de sandbox open source carregado")
    print("📱 Acesse pelo navegador para usar a interface web")

    # Iniciar o servidor
    cl.run(host=args.host, port=args.port, debug=args.debug, watch=False)
