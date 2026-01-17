#!/usr/bin/env python3
"""
Launcher simplificado do OpenManus sem dependências do Daytona.
Este launcher usa apenas os adapters de sandbox open source implementados.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Config
from app.logger import logger
from app.sandbox.adapters.factory import SandboxFactory
from app.sandbox.adapters.unified_client import UnifiedSandboxClient


async def demo_sandbox_system():
    """Demonstração do sistema de sandbox open source."""
    print("🚀 OpenManus - Sistema de Sandbox Open Source")
    print("=" * 50)

    try:
        # Caregar configuração
        config = Config()
        sandbox_config = config.sandbox

        print(f"📋 Configuração carregada:")
        print(f"   Backend: {sandbox_config.backend}")
        print(f"   Use sandbox: {sandbox_config.use_sandbox}")
        print(f"   Image: {sandbox_config.image}")
        print()

        # Verificar backends disponíveis
        available = SandboxFactory.get_available_adapters()
        print(f"🔧 Backends disponíveis: {', '.join(available)}")

        # Auto-detectar melhor backend
        best = SandboxFactory.auto_detect_backend()
        print(f"🎯 Melhor backend detectado: {best}")
        print()

        # Testar o backend configurado
        backend = sandbox_config.backend or best
        print(f"🧪 Testando backend: {backend}")

        client = UnifiedSandboxClient(backend)

        async with client.sandbox_context() as sandbox_id:
            print(f"✅ Sandbox criado: {sandbox_id}")

            # Teste básico
            result = await client.execute(sandbox_id, "echo 'OpenManus funcionando!'")
            print(f"💻 Saída: {result.stdout.strip()}")

            # Teste Python
            py_result = await client.execute(
                sandbox_id, "python3 -c \"print('Python:', __import__('sys').version)\""
            )
            print(f"🐍 {py_result.stdout.strip()}")

            # Teste de arquivo
            await client.write_file(
                sandbox_id,
                "/tmp/openmanus_test.txt",
                "OpenManus com sandbox open source funcionando!",
            )

            content = await client.read_file(sandbox_id, "/tmp/openmanus_test.txt")
            print(f"📄 Arquivo: {content.strip()}")

            # Listar arquivos
            files = await client.list_files(sandbox_id, "/tmp")
            print(f"📁 Arquivos em /tmp: {len(files)} encontrados")

        print(f"🎉 Teste do backend {backend} concluído com sucesso!")

    except Exception as e:
        logger.error(f"Erro na demonstração: {e}")
        print(f"❌ Erro: {e}")
        return False

    return True


async def interactive_mode():
    """Modo interativo simples para testar comandos."""
    print("🔧 Modo Interativo OpenManus")
    print("Digite comandos para executar no sandbox (ou 'quit' para sair)")
    print("-" * 50)

    try:
        config = Config()
        backend = config.sandbox.backend or "docker"

        client = UnifiedSandboxClient(backend)

        async with client.sandbox_context() as sandbox_id:
            print(f"📦 Sandbox {backend} criado: {sandbox_id}")
            print("Digite seus comandos:")

            while True:
                try:
                    command = input("🔴 > ").strip()

                    if command.lower() in ["quit", "exit", "q"]:
                        break

                    if not command:
                        continue

                    if command.startswith("write "):
                        # Comando especial para escrever arquivo
                        # Formato: write /path/to/file content here
                        parts = command[6:].split(" ", 1)
                        if len(parts) == 2:
                            path, content = parts
                            await client.write_file(sandbox_id, path, content)
                            print(f"✅ Arquivo {path} criado")
                        else:
                            print("❌ Uso: write /path/to/file content")
                        continue

                    if command.startswith("read "):
                        # Comando especial para ler arquivo
                        path = command[5:].strip()
                        try:
                            content = await client.read_file(sandbox_id, path)
                            print(f"📄 {path}:")
                            print(content)
                        except Exception as e:
                            print(f"❌ Erro lendo {path}: {e}")
                        continue

                    if command.startswith("ls "):
                        # Comando especial para listar arquivos
                        path = command[3:].strip() or "/"
                        try:
                            files = await client.list_files(sandbox_id, path)
                            print(f"📁 {path}:")
                            for f in files:
                                print(f"  {f}")
                        except Exception as e:
                            print(f"❌ Erro listando {path}: {e}")
                        continue

                    # Comando normal
                    result = await client.execute(sandbox_id, command)

                    if result.stdout:
                        print(result.stdout.rstrip())
                    if result.stderr:
                        print(f"❌ Erro: {result.stderr.rstrip()}")
                    if result.exit_code != 0:
                        print(f"⚠️  Exit code: {result.exit_code}")

                except KeyboardInterrupt:
                    print("\\nInterrompido pelo usuário")
                    break
                except EOFError:
                    print("\\nSaindo...")
                    break
                except Exception as e:
                    print(f"❌ Erro: {e}")

    except Exception as e:
        print(f"❌ Erro no modo interativo: {e}")


def print_help():
    """Mostra ajuda de uso."""
    print(
        """
🚀 OpenManus - Launcher Sandbox Open Source

Uso: python simple_launcher.py [opção]

Opções:
  demo          Demonstração do sistema de sandbox
  interactive   Modo interativo para executar comandos
  test          Executar testes dos backends
  help          Mostrar esta ajuda

Exemplos:
  python simple_launcher.py demo
  python simple_launcher.py interactive
  python simple_launcher.py test

Backends disponíveis:
  - docker  : Local, gratuito
  - gitpod  : Self-hosted (requer GITPOD_TOKEN)
  - e2b     : Cloud (requer E2B_API_KEY)

Configure em config/config.toml:
  [sandbox]
  backend = "docker"
  use_sandbox = true
"""
    )


async def run_tests():
    """Executar testes dos backends."""
    print("🧪 Executando testes dos backends...")

    import subprocess

    result = subprocess.run(
        [sys.executable, "scripts/test_sandbox_backends.py"], cwd=PROJECT_ROOT
    )

    return result.returncode == 0


async def main():
    """Função principal."""
    if len(sys.argv) < 2:
        await demo_sandbox_system()
        return

    command = sys.argv[1].lower()

    if command == "demo":
        success = await demo_sandbox_system()
        sys.exit(0 if success else 1)

    elif command == "interactive":
        await interactive_mode()

    elif command == "test":
        success = await run_tests()
        sys.exit(0 if success else 1)

    elif command in ["help", "-h", "--help"]:
        print_help()

    else:
        print(f"❌ Comando desconhecido: {command}")
        print("Use 'help' para ver comandos disponíveis")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n🛑 Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        print(f"💥 Erro fatal: {e}")
        sys.exit(1)
