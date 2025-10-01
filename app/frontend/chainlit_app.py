"""Chainlit frontend integration for OpenManus agent system."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import chainlit as cl
from chainlit.types import AskFileResponse

from app.agent.manus import Manus
from app.config import config
from app.logger import logger


class ChainlitOpenManus:
    """Chainlit frontend integration for OpenManus agent system."""

    def __init__(self):
        self.agent: Optional[Manus] = None
        self.conversation_history: List[Dict] = []
        self.session_id: Optional[str] = None

    async def initialize_agent(self) -> Manus:
        """Initialize OpenManus agent with proper async setup."""
        if not self.agent:
            self.agent = await Manus.create()
            logger.info("OpenManus agent initialized for Chainlit session")
        return self.agent

    async def cleanup_agent(self):
        """Clean up agent resources."""
        if self.agent:
            await self.agent.cleanup()
            self.agent = None
            logger.info("OpenManus agent cleaned up")

    def get_capabilities_message(self) -> str:
        """Get formatted capabilities message."""
        capabilities = [
            "🌐 **Navegação Web**: Automação completa de browser com Playwright",
            "📝 **Edição de Arquivos**: Operações CRUD em arquivos com sandbox",
            "🐍 **Execução Python**: Ambiente isolado para execução de código",
            "🔧 **Ferramentas MCP**: Integração com servidores externos via MCP",
            "🏗️ **Multi-Agent**: Orquestração de múltiplos agentes especializados",
            "🔍 **Web Search**: Busca em múltiplos motores (Google, Bing, DuckDuckGo)",
            "📊 **Análise de Dados**: Processamento e visualização de dados",
        ]

        return f"""# Bem-vindo ao OpenManus! 🤖

Sou um agente AI versátil com múltiplas capacidades:

{chr(10).join(capabilities)}

**Como usar:**
- Digite suas solicitações em linguagem natural
- Use o botão de upload (📎) para enviar arquivos
- Use os botões de ação para funções rápidas
- Digite `/help` para ver comandos disponíveis

**Exemplos de comandos:**
- "Analise este arquivo CSV e crie gráficos"
- "Pesquise sobre IA no Google e resuma os resultados"
- "Crie um script Python para processar logs"
- "Navegue até site X e extraia informações Y"

O que você gostaria de fazer hoje?"""


# Global instance for session management
chainlit_manus = ChainlitOpenManus()


@cl.on_chat_start
async def start_chat():
    """Initialize chat session with OpenManus agent."""
    try:
        # Set session ID
        chainlit_manus.session_id = cl.context.session.id

        # Initialize agent
        await chainlit_manus.initialize_agent()

        # Send welcome message
        welcome_msg = chainlit_manus.get_capabilities_message()

        await cl.Message(content=welcome_msg, author="OpenManus").send()

        # Add action buttons
        await add_action_buttons()

        logger.info(f"Chainlit session started: {chainlit_manus.session_id}")

    except Exception as e:
        logger.error(f"Erro ao inicializar sessão: {e}")
        await cl.Message(
            content="❌ Erro ao inicializar o agente. Tente recarregar a página.",
            author="Sistema",
        ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Handle user messages and route to OpenManus agent."""
    try:
        # Handle special commands
        if message.content.strip().startswith("/"):
            await handle_command(message.content.strip())
            return

        # Show processing indicator
        processing_msg = cl.Message(
            content="🤖 Processando sua solicitação...", author="Sistema"
        )
        await processing_msg.send()

        # Get or initialize agent
        agent = await chainlit_manus.initialize_agent()

        # Process message with agent
        logger.info(f"Processing message: {message.content[:100]}...")
        response = await agent.run(message.content)

        # Update processing message with result
        processing_msg.content = response
        processing_msg.author = "OpenManus"
        await processing_msg.update()

        # Store conversation for context
        chainlit_manus.conversation_history.extend(
            [
                {"role": "user", "content": message.content},
                {"role": "assistant", "content": response},
            ]
        )

        logger.info("Message processed successfully")

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        await cl.Message(
            content=f"❌ Erro ao processar sua solicitação: {str(e)}", author="Sistema"
        ).send()


async def handle_command(command: str):
    """Handle special slash commands."""
    command = command.lower().strip()

    if command == "/help":
        help_text = """**Comandos Disponíveis:**

`/help` - Mostra esta ajuda
`/clear` - Limpa o contexto da conversa
`/tools` - Lista ferramentas disponíveis
`/status` - Mostra status do agente
`/config` - Mostra configuração atual

**Dicas:**
- Use linguagem natural para suas solicitações
- Seja específico sobre o que deseja
- Para arquivos, use o botão de upload (📎)"""

        await cl.Message(content=help_text, author="Sistema").send()

    elif command == "/clear":
        await clear_context()

    elif command == "/tools":
        await show_tools()

    elif command == "/status":
        await show_status()

    elif command == "/config":
        await show_config()

    else:
        await cl.Message(
            content=f"Comando desconhecido: {command}. Digite `/help` para ver comandos disponíveis.",
            author="Sistema",
        ).send()


@cl.on_chat_end
async def end_chat():
    """Clean up resources when chat ends."""
    await chainlit_manus.cleanup_agent()
    logger.info(f"Sessão Chainlit finalizada: {chainlit_manus.session_id}")


@cl.action_callback("clear_context")
async def clear_context():
    """Clear conversation context."""
    try:
        chainlit_manus.conversation_history.clear()
        if chainlit_manus.agent and chainlit_manus.agent.memory:
            chainlit_manus.agent.memory.messages.clear()

        await cl.Message(
            content="🧹 Contexto da conversa limpo!", author="Sistema"
        ).send()

        logger.info("Context cleared")

    except Exception as e:
        logger.error(f"Erro ao limpar contexto: {e}")
        await cl.Message(content="❌ Erro ao limpar contexto", author="Sistema").send()


@cl.action_callback("show_tools")
async def show_tools():
    """Show available tools."""
    try:
        if chainlit_manus.agent and chainlit_manus.agent.available_tools:
            tools_info = []
            for tool in chainlit_manus.agent.available_tools.tools:
                tools_info.append(f"**{tool.name}**: {tool.description}")

            tools_text = "🔧 **Ferramentas Disponíveis:**\n\n" + "\n\n".join(tools_info)
        else:
            tools_text = "ℹ️ Nenhuma ferramenta disponível no momento."

        await cl.Message(content=tools_text, author="Sistema").send()

    except Exception as e:
        logger.error(f"Erro ao mostrar ferramentas: {e}")
        await cl.Message(
            content="❌ Erro ao listar ferramentas", author="Sistema"
        ).send()


@cl.action_callback("show_status")
async def show_status():
    """Show agent status."""
    try:
        if chainlit_manus.agent:
            status_info = f"""📊 **Status do Agente:**

- **Estado**: {chainlit_manus.agent.state.value}
- **Passo Atual**: {chainlit_manus.agent.current_step}/{chainlit_manus.agent.max_steps}
- **Mensagens na Memória**: {len(chainlit_manus.agent.memory.messages)}
- **Ferramentas Carregadas**: {len(chainlit_manus.agent.available_tools.tools)}
- **Sessão**: {chainlit_manus.session_id}"""
        else:
            status_info = "⚠️ Agente não inicializado"

        await cl.Message(content=status_info, author="Sistema").send()

    except Exception as e:
        logger.error(f"Erro ao mostrar status: {e}")
        await cl.Message(content="❌ Erro ao obter status", author="Sistema").send()


@cl.action_callback("show_config")
async def show_config():
    """Show current configuration."""
    try:
        config_info = f"""⚙️ **Configuração Atual:**

- **Modelo LLM**: {config.llm['default'].model}
- **Provider**: {config.llm['default'].api_type}
- **Max Tokens**: {config.llm['default'].max_tokens}
- **Temperature**: {config.llm['default'].temperature}
- **Workspace**: {config.workspace_root}
- **Sandbox**: {config.sandbox.use_sandbox}"""

        await cl.Message(content=config_info, author="Sistema").send()

    except Exception as e:
        logger.error(f"Erro ao mostrar configuração: {e}")
        await cl.Message(
            content="❌ Erro ao obter configuração", author="Sistema"
        ).send()


# Note: File upload functionality removed due to Chainlit version compatibility
# @cl.on_file_upload will be added in future versions
# async def handle_file_upload(files): ...


async def add_action_buttons():
    """Add action buttons to chat interface."""
    actions = [
        cl.Action(
            name="clear_context", value="clear", description="🧹 Limpar Contexto"
        ),
        cl.Action(name="show_tools", value="tools", description="🔧 Ver Ferramentas"),
        cl.Action(
            name="show_status", value="status", description="📊 Status do Agente"
        ),
        cl.Action(name="show_config", value="config", description="⚙️ Configuração"),
    ]

    await cl.Message(
        content="💡 **Ações Rápidas Disponíveis:**", actions=actions, author="Sistema"
    ).send()


# Chainlit settings - configured via .chainlit/config.toml instead
# cl.config.ui.name = "OpenManus Assistant"
# cl.config.ui.description = "Multi-Agent AI Automation Framework"
# cl.config.ui.github = "https://github.com/Copyxyzai/OpenManus"
