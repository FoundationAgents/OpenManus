# OpenManus Chainlit Frontend

Uma interface web moderna e intuitiva para interagir com o framework OpenManus através do Chainlit.

## 🚀 Funcionalidades

### Interface de Chat Avançada

- **Chat em tempo real** com o agente OpenManus
- **Upload de arquivos** com suporte a múltiplos formatos
- **Botões de ação rápida** para operações comuns
- **Comandos especiais** com prefixo `/`
- **Histórico de conversas** mantido durante a sessão

### Integrações Completas

- **Navegação Web**: Automação completa de browser com Playwright
- **Edição de Arquivos**: Operações CRUD em arquivos com sandbox
- **Execução Python**: Ambiente isolado para execução de código
- **Ferramentas MCP**: Integração com servidores externos
- **Multi-Agent**: Orquestração de múltiplos agentes especializados
- **Web Search**: Busca em múltiplos motores de pesquisa
- **Análise de Dados**: Processamento e visualização de dados

## 📋 Pré-requisitos

Certifique-se de ter o OpenManus configurado:

```bash
# Instalar dependências básicas do OpenManus
pip install -r requirements.txt

# Dependências do Chainlit já estão incluídas no requirements.txt
```

## 🛠️ Instalação e Configuração

### 1. Configuração Automática

```bash
# Executar apenas configuração (sem iniciar o servidor)
python run_chainlit.py --config-only
```

### 2. Configuração Manual (Opcional)

Se precisar configurar manualmente:

```bash
# Criar configuração do Chainlit
python -c "from app.frontend.chainlit_config import setup_chainlit_config; setup_chainlit_config()"
```

## 🚀 Execução

### Execução Básica

```bash
# Iniciar frontend Chainlit (host padrão: localhost:8000)
python run_chainlit.py
```

### Opções Avançadas

```bash
# Customizar host e porta
python run_chainlit.py --host 0.0.0.0 --port 8080

# Modo desenvolvimento com auto-reload
python run_chainlit.py --debug --auto-reload

# Modo headless (sem abrir browser automaticamente)
python run_chainlit.py --headless

# Ver todas as opções
python run_chainlit.py --help
```

## 💬 Como Usar

### Interface Principal

1. **Acesse** `http://localhost:8000` no seu browser
2. **Digite** suas solicitações em linguagem natural
3. **Use** botões de ação para operações rápidas
4. **Faça upload** de arquivos usando o botão 📎

### Comandos Especiais

| Comando | Descrição |
|---------|-----------|
| `/help` | Mostra lista de comandos disponíveis |
| `/clear` | Limpa o contexto da conversa |
| `/tools` | Lista ferramentas disponíveis |
| `/status` | Mostra status do agente |
| `/config` | Mostra configuração atual |

### Exemplos de Uso

```
# Análise de dados
"Analise este arquivo CSV e crie gráficos das tendências"

# Automação web
"Pesquise sobre inteligência artificial no Google e resuma os principais pontos"

# Programação
"Crie um script Python para processar logs de sistema"

# Operações de arquivo
"Organize os arquivos na pasta workspace por tipo"

# Multi-modal
"Analise esta imagem e descreva o que você vê"
```

### Upload de Arquivos

Formatos suportados:

- **Texto**: `.txt`, `.md`, `.py`, `.json`
- **Configuração**: `.yaml`, `.yml`, `.xml`
- **Web**: `.html`, `.js`, `.ts`, `.css`
- **Dados**: `.csv`

Limites:

- **Tamanho máximo por arquivo**: 10MB
- **Número máximo de arquivos**: 10
- **Tamanho total**: 100MB por sessão

## ⚙️ Configuração Avançada

### Arquivo de Configuração

O Chainlit cria automaticamente `.chainlit/config.toml`:

```toml
[project]
name = "OpenManus"
description = "Multi-Agent AI Automation Framework"

[UI]
name = "OpenManus Assistant"
theme = "dark"
default_expand_messages = true

[features]
prompt_playground = true
multi_modal = true
latex = true

[session]
max_size_mb = 100
timeout = 3600
```

### Variáveis de Ambiente

```bash
# Configurações do servidor
export CHAINLIT_HOST="localhost"
export CHAINLIT_PORT="8000"
export CHAINLIT_DEBUG="0"
export CHAINLIT_HEADLESS="0"
```

## 🔧 Desenvolvimento

### Estrutura do Código

```
app/frontend/
├── __init__.py              # Módulo frontend
├── chainlit_app.py          # App principal com handlers
├── chainlit_config.py       # Configurações do Chainlit
└── README.md               # Esta documentação
```

### Handlers Principais

- `@cl.on_chat_start`: Inicialização da sessão
- `@cl.on_message`: Processamento de mensagens
- `@cl.on_file_upload`: Upload de arquivos
- `@cl.action_callback`: Botões de ação
- `@cl.on_chat_end`: Limpeza de recursos

### Adicionando Funcionalidades

1. **Novos comandos**: Adicione em `handle_command()`
2. **Novas ações**: Crie `@cl.action_callback`
3. **Processamento customizado**: Modifique `handle_message()`

## 🐛 Troubleshooting

### Problemas Comuns

**Erro de importação do Chainlit:**

```bash
pip install chainlit>=1.0.0
```

**Porta já em uso:**

```bash
python run_chainlit.py --port 8080
```

**Problemas de configuração do OpenManus:**

```bash
# Verifique se config/config.toml existe
cp config/config.example.toml config/config.toml
# Edite com suas chaves de API
```

**Agente não responde:**

- Verifique logs no terminal
- Confirme configuração LLM em `config/config.toml`
- Teste com `python main.py` primeiro

### Logs e Debug

```bash
# Executar com debug detalhado
python run_chainlit.py --debug

# Verificar logs do OpenManus
tail -f logs/openmanus.log  # se existir
```

## 🤝 Contribuição

Para contribuir com melhorias no frontend:

1. **Fork** o repositório
2. **Crie** uma branch para sua feature
3. **Implemente** suas mudanças em `app/frontend/`
4. **Teste** com `python run_chainlit.py --debug`
5. **Submeta** um pull request

## 📄 Licença

Este frontend segue a mesma licença do projeto OpenManus principal.

## 🔗 Links Úteis

- [OpenManus GitHub](https://github.com/Copyxyzai/OpenManus)
- [Chainlit Documentation](https://docs.chainlit.io/)
- [Chainlit Cookbook](https://github.com/Chainlit/cookbook)

---

**Desenvolvido com ❤️ para o OpenManus Framework**
