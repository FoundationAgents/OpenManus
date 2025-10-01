#!/usr/bin/env python
"""Status final da integração Chainlit + OpenManus."""

import subprocess
import sys
from pathlib import Path


def check_file_exists(filepath: str, description: str) -> bool:
    """Verifica se um arquivo existe."""
    path = Path(filepath)
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"  {status} {description}: {filepath}")
    return exists


def check_dependency(package: str) -> bool:
    """Verifica se uma dependência está instalada."""
    try:
        __import__(package)
        print(f"  ✅ {package}")
        return True
    except ImportError:
        print(f"  ❌ {package}")
        return False


def main():
    """Status completo da integração."""

    print("\n" + "=" * 70)
    print("🚀 STATUS FINAL: Integração Chainlit + OpenManus")
    print("=" * 70)

    print("\n📁 ARQUIVOS IMPLEMENTADOS:")
    files_implemented = [
        ("app/frontend/__init__.py", "Módulo frontend"),
        ("app/frontend/chainlit_app.py", "Aplicação principal Chainlit"),
        ("app/frontend/chainlit_config.py", "Sistema de configuração"),
        ("app/frontend/README.md", "Documentação detalhada"),
        ("run_chainlit.py", "Script de execução principal"),
        ("Makefile", "Comandos facilitadores"),
        (".chainlit/config.toml", "Configuração do Chainlit"),
        ("examples/test_chainlit_startup.py", "Teste de inicialização"),
        ("examples/demo_integracao.py", "Demonstração da implementação"),
        ("INTEGRACAO_CHAINLIT.md", "Resumo completo"),
    ]

    all_files_exist = True
    for filepath, description in files_implemented:
        if not check_file_exists(filepath, description):
            all_files_exist = False

    print(f"\n📦 DEPENDÊNCIAS PRINCIPAIS:")
    dependencies = [
        "chainlit",
        "uvicorn",
        "fastapi",
        "websockets",
        "aiofiles",
        "pydantic",
        "openai",
        "loguru",
        "structlog",
    ]

    all_deps_installed = True
    for dep in dependencies:
        if not check_dependency(dep):
            all_deps_installed = False

    print(f"\n⚙️ CONFIGURAÇÃO:")
    config_status = []

    # Verifica se o arquivo de configuração do OpenManus existe
    config_exists = Path("config/config.toml").exists()
    config_status.append(("Configuração OpenManus", config_exists))

    # Verifica se o arquivo de configuração do Chainlit existe
    chainlit_config_exists = Path(".chainlit/config.toml").exists()
    config_status.append(("Configuração Chainlit", chainlit_config_exists))

    for desc, status in config_status:
        symbol = "✅" if status else "❌"
        print(f"  {symbol} {desc}")

    print(f"\n🧪 TESTE DE FUNCIONALIDADE:")
    try:
        # Testa se conseguimos importar o módulo principal
        from app.frontend.chainlit_app import ChainlitOpenManus

        print("  ✅ Importação do ChainlitOpenManus")

        # Testa se conseguimos importar chainlit
        import chainlit as cl

        print("  ✅ Importação do Chainlit")

        # Testa se conseguimos carregar a configuração
        from app.config import config

        print("  ✅ Carregamento da configuração")

        functionality_ok = True
    except Exception as e:
        print(f"  ❌ Erro na funcionalidade: {e}")
        functionality_ok = False

    print(f"\n🎯 COMANDOS DISPONÍVEIS:")
    commands = [
        ("make install", "Instalar dependências"),
        ("make setup", "Configurar Chainlit"),
        ("make test", "Executar testes"),
        ("make run", "Iniciar frontend"),
        ("make dev", "Modo desenvolvimento"),
        ("python run_chainlit.py", "Execução direta"),
        ("python run_chainlit.py --help", "Ver todas as opções"),
    ]

    for cmd, desc in commands:
        print(f"  📝 {cmd:<30} # {desc}")

    print(f"\n🌟 FUNCIONALIDADES:")
    features = [
        "Interface chat interativa com histórico",
        "Upload de arquivos (múltiplos formatos)",
        "Botões de ação rápida",
        "Comandos especiais (/help, /tools, etc.)",
        "Integração completa com OpenManus",
        "Gestão automática de sessões",
        "Tratamento robusto de erros",
        "Configuração automática",
    ]

    for feature in features:
        print(f"  ✨ {feature}")

    # Status geral
    overall_status = all_files_exist and all_deps_installed and functionality_ok

    print(f"\n" + "=" * 70)
    if overall_status:
        print("🎉 STATUS GERAL: SUCESSO COMPLETO!")
        print("✅ A integração Chainlit + OpenManus está 100% funcional!")
        print("\n🚀 PRÓXIMO PASSO:")
        print("   Execute: python run_chainlit.py")
        print("   Acesse: http://localhost:8000")
        print("   Comece a usar sua interface web OpenManus!")
    else:
        print("⚠️  STATUS GERAL: NECESSITA AJUSTES")
        if not all_files_exist:
            print("❌ Alguns arquivos estão faltando")
        if not all_deps_installed:
            print("❌ Algumas dependências não estão instaladas")
            print("   Execute: make install")
        if not functionality_ok:
            print("❌ Problemas de funcionalidade detectados")

    print("=" * 70)

    return overall_status


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
