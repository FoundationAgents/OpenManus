#!/usr/bin/env python
"""Script para testar se o Chainlit está funcionando corretamente."""

import subprocess
import sys
import time
from pathlib import Path


def test_chainlit_startup():
    """Testa se o Chainlit consegue inicializar sem erros."""

    print("🧪 Testando inicialização do Chainlit...")

    # Comando para testar o Chainlit
    cmd = [sys.executable, "run_chainlit.py", "--headless", "--debug"]

    try:
        # Inicia o processo em background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # Aguarda alguns segundos para ver se inicializa
        time.sleep(5)

        # Verifica se o processo ainda está rodando
        if process.poll() is None:
            print("✅ Chainlit iniciou com sucesso!")
            print("🌐 O servidor estaria disponível em http://localhost:8000")

            # Termina o processo
            process.terminate()
            process.wait(timeout=5)

            return True
        else:
            # Processo terminou, vamos ver os erros
            stdout, stderr = process.communicate()
            print("❌ Chainlit falhou ao inicializar")
            print("STDOUT:", stdout[-1000:])  # Últimas 1000 chars
            print("STDERR:", stderr[-1000:])
            return False

    except subprocess.TimeoutExpired:
        print("❌ Timeout na inicialização")
        process.kill()
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False


def main():
    """Função principal do teste."""

    print("\n" + "=" * 50)
    print("🚀 Teste de Integração Chainlit + OpenManus")
    print("=" * 50)

    success = test_chainlit_startup()

    if success:
        print("\n🎉 TESTE PASSOU!")
        print("✅ A integração Chainlit + OpenManus está funcionando!")
        print("\n📋 Para usar:")
        print("  1. Execute: python run_chainlit.py")
        print("  2. Acesse: http://localhost:8000")
        print("  3. Comece a conversar com o OpenManus!")
    else:
        print("\n❌ TESTE FALHOU!")
        print("⚠️  Verifique as dependências e configurações.")

    print("\n" + "=" * 50)
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
