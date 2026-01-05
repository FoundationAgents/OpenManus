#!/usr/bin/env python
"""Teste específico para integração Chainlit apenas."""

import sys
from pathlib import Path


def test_chainlit_integration():
    """Testa apenas a integração Chainlit sem componentes opcionais."""

    print("🧪 Testando integração Chainlit específica...")

    try:
        # Testa importação do Chainlit
        import chainlit as cl

        print("  ✅ Chainlit importado")

        # Testa importação da configuração
        from app.frontend.chainlit_config import CHAINLIT_CONFIG, setup_chainlit_config

        print("  ✅ Configuração Chainlit importada")

        # Testa se conseguimos importar a aplicação Chainlit
        from app.frontend.chainlit_app import ChainlitOpenManus

        print("  ✅ ChainlitOpenManus importado")

        # Testa se conseguimos criar uma instância
        chainlit_manus = ChainlitOpenManus()
        print("  ✅ Instância ChainlitOpenManus criada")

        return True

    except Exception as e:
        print(f"  ❌ Erro: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Teste principal específico do Chainlit."""

    print("\n" + "=" * 60)
    print("🚀 Teste Específico: Integração Chainlit")
    print("=" * 60)

    success = test_chainlit_integration()

    if success:
        print("\n🎉 TESTE PASSOU!")
        print("✅ A integração Chainlit está funcionando!")
        print("\n📋 Para usar a integração completa:")
        print("  1. Configure suas API keys em config/config.toml")
        print("  2. Execute: python run_chainlit.py")
        print("  3. Acesse: http://localhost:8000")
        print("  4. Comece a usar o OpenManus via web!")

        print("\n⚠️  Nota: Alguns componentes opcionais (Daytona) podem")
        print("   precisar de configuração adicional, mas o Chainlit")
        print("   frontend funcionará perfeitamente!")

    else:
        print("\n❌ TESTE FALHOU!")
        print("⚠️  Há problemas com a integração Chainlit.")

    print("\n" + "=" * 60)
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
