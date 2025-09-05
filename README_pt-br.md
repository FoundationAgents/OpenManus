<p align="center">
  <img src="assets/logo.jpg" width="200"/>
</p>

[English](README.md) | [中文](README_zh.md) | [한국어](README_ko.md) | [日本語](README_ja.md) | **Português (Brasil)**

[![GitHub stars](https://img.shields.io/github/stars/FoundationAgents/OpenManus?style=social)](https://github.com/FoundationAgents/OpenManus/stargazers)
&ensp;
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) &ensp;
[![Discord Follow](https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat)](https://discord.gg/DYn29wFk9z)
[![Demo](https://img.shields.io/badge/Demo-Hugging%20Face-yellow)](https://huggingface.co/spaces/lyh-917/OpenManusDemo)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15186407.svg)](https://doi.org/10.5281/zenodo.15186407)

# 👋 OpenManus

Manus é incrível, mas o OpenManus pode realizar qualquer ideia sem precisar de *código de convite* 🛫!

Nossa equipe é formada por [@Xinbin Liang](https://github.com/mannaandpoem) e [@Jinyu Xiang](https://github.com/XiangJinyu) (autores principais), junto com [@Zhaoyang Yu](https://github.com/MoshiQAQ), [@Jiayi Zhang](https://github.com/didiforgithub) e [@Sirui Hong](https://github.com/stellaHSR), do [@MetaGPT](https://github.com/geekan/MetaGPT). Criamos o protótipo em apenas 3 horas e continuamos desenvolvendo!

É uma implementação simples, então aceitamos sugestões, contribuições e feedback!

Aproveite o seu próprio agente com o OpenManus!

Também estamos empolgados em apresentar o [OpenManus-RL](https://github.com/OpenManus/OpenManus-RL), um projeto de código aberto dedicado a métodos de ajuste baseados em aprendizado por reforço (RL) (como GRPO) para agentes LLM, desenvolvido em colaboração por pesquisadores da UIUC e do OpenManus.

## Demonstração do Projeto

<video src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" data-canonical-src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" controls="controls" muted="muted" class="d-block rounded-bottom-2 border-top width-fit" style="max-height:640px; min-height: 200px"></video>

## Instalação

Fornecemos dois métodos de instalação. O Método 2 (usando uv) é recomendado para uma instalação mais rápida e melhor gerenciamento de dependências.

### Método 1: Usando conda

1. Crie um novo ambiente conda:

```bash
conda create -n open_manus python=3.12
conda activate open_manus
```

2. Clone o repositório:

```bash
git clone https://github.com/FoundationAgents/OpenManus.git
cd OpenManus
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

### Método 2: Usando uv (Recomendado)

1. Instale uv (Um instalador e resolvedor rápido de pacotes Python):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone o repositório:

```bash
git clone https://github.com/FoundationAgents/OpenManus.git
cd OpenManus
```

3. Crie um novo ambiente virtual e ative-o:

```bash
uv venv --python 3.12
source .venv/bin/activate  # Em Unix/macOS
# Ou no Windows:
# .venv\Scriptsctivate
```

4. Instale as dependências:

```bash
uv pip install -r requirements.txt
```

### Ferramenta de Automação de Navegador (Opcional)
```bash
playwright install
```

## Configuração

O OpenManus requer configuração para as APIs LLM que utiliza. Siga estes passos para configurar:

1. Crie um arquivo `config.toml` no diretório `config` (você pode copiar do exemplo):

```bash
cp config/config.example.toml config/config.toml
```

2. Edite `config/config.toml` para adicionar suas chaves de API e personalizar as configurações:

```toml
# Configuração global do LLM
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Substitua pela sua chave de API real
max_tokens = 4096
temperature = 0.0

# Configuração opcional para modelos LLM específicos
[llm.vision]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Substitua pela sua chave de API real
```

## Início Rápido

Uma linha para executar o OpenManus:

```bash
python main.py
```

Então, insira sua ideia via terminal!

Para a versão com ferramenta MCP, você pode executar:
```bash
python run_mcp.py
```

Para a versão instável multi-agente, você também pode executar:

```bash
python run_flow.py
```

### Adicionando Múltiplos Agentes Personalizados

Atualmente, além do Agente OpenManus geral, também integramos o Agente DataAnalysis, que é adequado para tarefas de análise e visualização de dados. Você pode adicionar este agente ao `run_flow` em `config.toml`.

```toml
# Configuração opcional para run-flow
[runflow]
use_data_analysis_agent = true     # Desabilitado por padrão, mude para true para ativar
```
Além disso, você precisa instalar as dependências relevantes para garantir que o agente funcione corretamente: [Guia de Instalação Detalhado](app/tool/chart_visualization/README_pt-br.md#instalação) (Nota: O link deve apontar para o README traduzido da ferramenta de visualização quando estiver pronto)

## Como contribuir

Acolhemos quaisquer sugestões amigáveis e contribuições úteis! Apenas crie issues ou envie pull requests.

Ou contate @mannaandpoem via 📧email: mannaandpoem@gmail.com

**Nota**: Antes de enviar um pull request, por favor, use a ferramenta pre-commit para verificar suas alterações. Execute `pre-commit run --all-files` para executar as verificações.

## Grupo da Comunidade
Junte-se ao nosso grupo de networking no Feishu e compartilhe sua experiência com outros desenvolvedores!

<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/community_group.jpg" alt="OpenManus Grupo de Discussão" width="300" />
</div>

## Histórico de Estrelas

[![Star History Chart](https://api.star-history.com/svg?repos=FoundationAgents/OpenManus&type=Date)](https://star-history.com/#FoundationAgents/OpenManus&Date)

## Patrocinadores
Agradecimentos à [PPIO](https://ppinfra.com/user/register?invited_by=OCPKCN&utm_source=github_openmanus&utm_medium=github_readme&utm_campaign=link) pelo suporte de recursos computacionais.
> PPIO: A solução MaaS e nuvem GPU mais acessível e de fácil integração.

## Agradecimentos

Agradecimentos a [anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo)
e [browser-use](https://github.com/browser-use/browser-use) por fornecerem suporte básico para este projeto!

Além disso, somos gratos a [AAAJ](https://github.com/metauto-ai/agent-as-a-judge), [MetaGPT](https://github.com/geekan/MetaGPT), [OpenHands](https://github.com/All-Hands-AI/OpenHands) e [SWE-agent](https://github.com/SWE-agent/SWE-agent).

Também agradecemos a stepfun (阶跃星辰) por apoiar nosso espaço de demonstração na Hugging Face.

O OpenManus é construído por contribuidores do MetaGPT. Um enorme obrigado a esta comunidade de agentes!

## Citar
```bibtex
@misc{openmanus2025,
  author = {Xinbin Liang and Jinyu Xiang and Zhaoyang Yu and Jiayi Zhang and Sirui Hong and Sheng Fan and Xiao Tang},
  title = {OpenManus: An open-source framework for building general AI agents},
  year = {2025},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.15186407},
  url = {https://doi.org/10.5281/zenodo.15186407},
}
```
