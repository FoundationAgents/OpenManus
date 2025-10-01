# OpenManus Sandbox Adapters

Este módulo fornece múltiplos backends de sandbox para o OpenManus, permitindo escolher entre soluções locais, auto-hospedadas e em nuvem como alternativas ao Daytona proprietário.

## 🏗️ Arquitetura

```
app/sandbox/adapters/
├── __init__.py              # Exports principais
├── base.py                  # Interface base e tipos
├── docker_adapter.py        # Adapter Docker local
├── gitpod_adapter.py        # Adapter GitPod auto-hospedado
├── e2b_adapter.py           # Adapter E2B em nuvem
├── factory.py               # Factory para criação de adapters
├── unified_client.py        # Cliente unificado
└── README.md               # Esta documentação
```

### Padrões de Design

- **Adapter Pattern**: Interface unificada para diferentes backends
- **Factory Pattern**: Criação inteligente de adapters baseada em configuração
- **Context Manager**: Gerenciamento automático de ciclo de vida dos sandboxes
- **Async/Await**: Operações assíncronas para melhor performance

## 📋 Backends Disponíveis

### 1. Docker (Local)

- **Tipo**: Solução local gratuita
- **Prós**: Sem custo, setup simples, controle total
- **Contras**: Apenas local, requer Docker instalado

### 2. GitPod (Auto-hospedado)

- **Tipo**: Solução auto-hospedada gratuita
- **Prós**: Interface web, colaboração, gratuito
- **Contras**: Requer setup inicial, manutenção própria

### 3. E2B (Nuvem)

- **Tipo**: Solução em nuvem comercial
- **Prós**: Sem setup, escalável, especializado em código
- **Contras**: Requer API key, cobrança por uso

## 🚀 Início Rápido

### 1. Configuração

Adicione ao seu `config/config.toml`:

```toml
[sandbox]
# Escolha o backend: docker, gitpod, e2b
backend = "docker"
use_sandbox = true
auto_cleanup = true
timeout = 300

# Configurações Docker (padrão)
image = "python:3.12-slim"
memory_limit = "1g"
cpu_limit = 2.0

# Configurações GitPod (quando backend = "gitpod")
gitpod_url = "http://localhost"
gitpod_token = "your_token_here"

# Configurações E2B (quando backend = "e2b")
e2b_api_key = "your_api_key_here"  # Ou via E2B_API_KEY env var
e2b_template = "base"
```

### 2. Uso Básico

```python
from app.sandbox.adapters.unified_client import UnifiedSandboxClient

# Criar cliente (usa configuração automática)
client = UnifiedSandboxClient("docker")

# Usar sandbox com context manager
async with client.sandbox_context() as sandbox_id:
    # Executar comando
    result = await client.execute(sandbox_id, "echo 'Hello World!'")
    print(result.stdout)

    # Operações de arquivo
    await client.write_file(sandbox_id, "/tmp/test.txt", "Hello!")
    content = await client.read_file(sandbox_id, "/tmp/test.txt")

    # Listar arquivos
    files = await client.list_files(sandbox_id, "/tmp")
```

### 3. Factory Pattern

```python
from app.sandbox.adapters.factory import SandboxFactory

# Auto-detectar melhor backend disponível
adapter = SandboxFactory.create_best_available()

# Ou criar específico
adapter = SandboxFactory.create("docker")
```

## 🛠️ Setup dos Backends

### Docker (Recomendado para desenvolvimento)

```bash
# Instalar Docker (se necessário)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Testar
docker run hello-world
```

### GitPod Auto-hospedado

```bash
# Setup completo com script automatizado
./scripts/deploy_gitpod.sh

# Ou manual
cd gitpod-deployment
./start-gitpod.sh

# Obter token na interface web: http://localhost
```

### E2B

```bash
# Instalar dependências
pip install e2b-code-interpreter

# Configurar chave (obter em https://e2b.dev)
export E2B_API_KEY="your_key_here"
```

## 🧪 Testes

### Teste Todos os Backends

```bash
python scripts/test_sandbox_backends.py
```

### Teste Backend Específico

```bash
python scripts/test_sandbox_backends.py docker
python scripts/test_sandbox_backends.py gitpod
python scripts/test_sandbox_backends.py e2b
```

### Teste com Configuração

```bash
export GITPOD_TOKEN="your_token"
export E2B_API_KEY="your_key"
python scripts/test_sandbox_backends.py
```

## 📖 Exemplos Avançados

### Configuração Personalizada

```python
from app.sandbox.adapters.unified_client import UnifiedSandboxClient

# GitPod personalizado
config = {
    'gitpod_url': 'https://gitpod.company.com',
    'gitpod_token': 'token_here',
    'image': 'custom/python-env:latest',
    'timeout': 600
}

client = UnifiedSandboxClient("gitpod", config)
```

### Tratamento de Erros

```python
from app.sandbox.adapters.base import SandboxError, SandboxTimeout
from app.sandbox.adapters.unified_client import UnifiedSandboxClient

client = UnifiedSandboxClient("docker")

try:
    async with client.sandbox_context() as sandbox_id:
        result = await client.execute(sandbox_id, "long_running_command", timeout=10)
except SandboxTimeout:
    print("Comando demorou muito para executar")
except SandboxError as e:
    print(f"Erro no sandbox: {e}")
```

### Múltiplos Sandboxes

```python
from app.sandbox.adapters.unified_client import UnifiedSandboxClient

client = UnifiedSandboxClient("docker")

# Criar múltiplos sandboxes
sandboxes = []
for i in range(3):
    sandbox_id = await client.create_sandbox()
    sandboxes.append(sandbox_id)

# Usar em paralelo
import asyncio

async def process_in_sandbox(sandbox_id, data):
    await client.write_file(sandbox_id, f"/tmp/data_{sandbox_id}.txt", data)
    result = await client.execute(sandbox_id, f"wc -l /tmp/data_{sandbox_id}.txt")
    return result.stdout.strip()

# Processar em paralelo
tasks = [process_in_sandbox(sid, f"data for {sid}") for sid in sandboxes]
results = await asyncio.gather(*tasks)

# Cleanup
for sandbox_id in sandboxes:
    await client.destroy_sandbox(sandbox_id)
```

## 🔧 Troubleshooting

### Problemas Comuns

1. **Docker não encontrado**

   ```bash
   sudo systemctl start docker
   sudo usermod -aG docker $USER
   ```

2. **GitPod não responde**

   ```bash
   cd gitpod-deployment
   ./manage-gitpod.sh logs
   ```

3. **E2B autenticação falha**

   ```bash
   export E2B_API_KEY="your_correct_key"
   # Ou atualizar em config/config.toml
   ```

4. **Timeout nos comandos**

   ```toml
   [sandbox]
   timeout = 600  # Aumentar timeout
   ```

### Debug

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Logs detalhados dos adapters
client = UnifiedSandboxClient("docker")
```

### Verificar Configuração

```python
from app.sandbox.adapters.factory import SandboxFactory

# Ver backends disponíveis
print(f"Disponíveis: {SandboxFactory.get_available_adapters()}")

# Auto-detectar melhor opção
backend = SandboxFactory.auto_detect_backend()
print(f"Recomendado: {backend}")

# Testar criação
try:
    adapter = SandboxFactory.create(backend)
    print(f"✅ {backend} funcionando")
except Exception as e:
    print(f"❌ {backend} com problema: {e}")
```

## 🤝 Migração do Daytona

Se você estava usando Daytona, aqui está como migrar:

### Antes (Daytona)

```toml
[daytona]
daytona_api_key = "key"  # Agora opcional
```

### Depois (Open Source)

```toml
[sandbox]
backend = "docker"       # ou "gitpod", "e2b"
use_sandbox = true
auto_cleanup = true
```

### Mudanças no Código

O `UnifiedSandboxClient` mantém compatibilidade com a interface existente, então o código que usa sandboxes deve funcionar sem alterações.

## 📚 Referência da API

### UnifiedSandboxClient

```python
class UnifiedSandboxClient:
    def __init__(self, backend: str, config: dict = None)

    async def create_sandbox(self) -> str
    async def destroy_sandbox(self, sandbox_id: str) -> None
    async def get_sandbox_info(self, sandbox_id: str) -> SandboxInfo

    async def execute(self, sandbox_id: str, command: str, **kwargs) -> CommandResult
    async def write_file(self, sandbox_id: str, path: str, content: str) -> None
    async def read_file(self, sandbox_id: str, path: str) -> str
    async def list_files(self, sandbox_id: str, path: str) -> List[str]

    @asynccontextmanager
    async def sandbox_context(self) -> str  # Auto cleanup
```

### SandboxFactory

```python
class SandboxFactory:
    @staticmethod
    def create(backend: str, config: dict = None) -> BaseSandboxAdapter

    @staticmethod
    def create_best_available(config: dict = None) -> BaseSandboxAdapter

    @staticmethod
    def get_available_adapters() -> List[str]

    @staticmethod
    def auto_detect_backend() -> str
```

## 🌟 Próximos Passos

1. **Teste os backends**: `python scripts/test_sandbox_backends.py`
2. **Configure seu backend favorito** no `config/config.toml`
3. **Execute o OpenManus** normalmente - os adapters são transparentes
4. **Para produção**: Configure GitPod self-hosted ou E2B com API key

## 📄 Licença

Este módulo segue a mesma licença do projeto OpenManus principal.
