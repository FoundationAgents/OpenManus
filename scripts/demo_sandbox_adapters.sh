#!/bin/bash
# Script para demonstrar uso dos sandbox adapters

set -e

echo "🎯 OpenManus Sandbox Adapters Demo"
echo "=================================="

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# Função para executar demo de um backend
demo_backend() {
    local backend=$1
    echo
    log_info "Demonstrando backend: $backend"
    echo "---"

    python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')

from app.sandbox.adapters.unified_client import UnifiedSandboxClient

async def demo():
    client = UnifiedSandboxClient('$backend')

    try:
        print('🚀 Criando sandbox...')
        async with client.sandbox_context() as sandbox_id:
            print(f'📦 Sandbox criado: {sandbox_id}')

            print('💻 Executando comandos...')
            result = await client.execute(sandbox_id, 'echo \"Olá do $backend!\"')
            print(f'   Output: {result.stdout.strip()}')

            print('📝 Testando operações de arquivo...')
            await client.write_file(sandbox_id, '/tmp/demo.txt', 'Demo do OpenManus com $backend!')
            content = await client.read_file(sandbox_id, '/tmp/demo.txt')
            print(f'   Arquivo: {content.strip()}')

            print('📁 Listando arquivos...')
            files = await client.list_files(sandbox_id, '/tmp')
            print(f'   Arquivos em /tmp: {len(files)} encontrados')

            print('🔬 Testando Python...')
            py_result = await client.execute(sandbox_id, 'python3 -c \"print(2+2)\"')
            print(f'   Python result: {py_result.stdout.strip()}')

        print('✅ Demo concluída com sucesso!')
        return True

    except Exception as e:
        print(f'❌ Erro na demo: {e}')
        return False

success = asyncio.run(demo())
exit(0 if success else 1)
"
}

# Menu principal
echo "Escolha o backend para demonstração:"
echo "1) Docker (local)"
echo "2) GitPod (auto-hospedado)"
echo "3) E2B (nuvem)"
echo "4) Todos os disponíveis"
echo "5) Teste de performance"

read -p "Digite sua escolha (1-5): " choice

case $choice in
    1)
        demo_backend "docker"
        ;;
    2)
        if [ -z "$GITPOD_TOKEN" ]; then
            log_warning "GITPOD_TOKEN não definido. Configure antes de testar GitPod."
            echo "export GITPOD_TOKEN=your_token_here"
            exit 1
        fi
        demo_backend "gitpod"
        ;;
    3)
        if [ -z "$E2B_API_KEY" ]; then
            log_warning "E2B_API_KEY não definido. Configure antes de testar E2B."
            echo "export E2B_API_KEY=your_key_here"
            exit 1
        fi
        demo_backend "e2b"
        ;;
    4)
        log_info "Testando todos os backends disponíveis..."

        # Docker sempre deve funcionar
        demo_backend "docker"

        # GitPod se configurado
        if [ -n "$GITPOD_TOKEN" ]; then
            demo_backend "gitpod"
        else
            log_warning "Pulando GitPod (GITPOD_TOKEN não definido)"
        fi

        # E2B se configurado
        if [ -n "$E2B_API_KEY" ]; then
            demo_backend "e2b"
        else
            log_warning "Pulando E2B (E2B_API_KEY não definido)"
        fi
        ;;
    5)
        log_info "Executando teste de performance..."
        python3 -c "
import asyncio
import time
import sys
sys.path.insert(0, '.')

from app.sandbox.adapters.unified_client import UnifiedSandboxClient

async def performance_test():
    backends = ['docker']

    if 'GITPOD_TOKEN' in os.environ:
        backends.append('gitpod')
    if 'E2B_API_KEY' in os.environ:
        backends.append('e2b')

    for backend in backends:
        print(f'\\n🏃 Testando performance do {backend}...')
        client = UnifiedSandboxClient(backend)

        # Teste de criação
        start = time.time()
        async with client.sandbox_context() as sandbox_id:
            creation_time = time.time() - start
            print(f'   Criação: {creation_time:.2f}s')

            # Teste de execução
            start = time.time()
            await client.execute(sandbox_id, 'echo test')
            exec_time = time.time() - start
            print(f'   Execução: {exec_time:.2f}s')

            # Teste de I/O
            start = time.time()
            await client.write_file(sandbox_id, '/tmp/test.txt', 'test data')
            await client.read_file(sandbox_id, '/tmp/test.txt')
            io_time = time.time() - start
            print(f'   I/O: {io_time:.2f}s')

import os
asyncio.run(performance_test())
"
        ;;
    *)
        log_warning "Escolha inválida"
        exit 1
        ;;
esac

echo
log_success "Demo concluída!"
log_info "Para mais informações, consulte: app/sandbox/adapters/README.md"
