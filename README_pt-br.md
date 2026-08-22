<p align="center">
  <img src="assets/logo.jpg" width="200"/>
</p>

[English](README.md) | [中文](README_zh.md) | [한국어](README_ko.md) | [日本語](README_ja.md) | Português (Brasil)

[![GitHub stars](https://img.shields.io/github/stars/mannaandpoem/OpenManus?style=social)](https://github.com/mannaandpoem/OpenManus/stargazers)
&ensp;
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) &ensp;
[![Discord Follow](https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat)](https://discord.gg/DYn29wFk9z)
[![Demo](https://img.shields.io/badge/Demo-Hugging%20Face-yellow)](https://huggingface.co/spaces/lyh-917/OpenManusDemo)

# 👋 OpenManus

Manus é incrível, mas OpenManus pode realizar qualquer ideia sem um *Código de Convite* 🛫!

Nossa equipe, composta por [@Xinbin Liang](https://github.com/mannaandpoem) e [@Jinyu Xiang](https://github.com/XiangJinyu) (autores principais), junto com [@Zhaoyang Yu](https://github.com/MoshiQAQ), [@Jiayi Zhang](https://github.com/didiforgithub) e [@Sirui Hong](https://github.com/stellaHSR), somos da [@MetaGPT](https://github.com/geekan/MetaGPT). O protótipo foi lançado em apenas 3 horas e continuamos desenvolvendo!

Esta é uma implementação simples, por isso aceitamos quaisquer sugestões, contribuições e feedback!

Aproveite seu próprio agente com OpenManus!

Também estamos entusiasmados em apresentar [OpenManus-RL](https://github.com/OpenManus/OpenManus-RL), um projeto de código aberto dedicado a métodos de ajuste baseados em aprendizado por reforço (RL) (como GRPO) para agentes LLM, desenvolvido colaborativamente por pesquisadores da UIUC e OpenManus.

## Demonstração do Projeto

<video src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" data-canonical-src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" controls="controls" muted="muted" class="d-block rounded-bottom-2 border-top width-fit" style="max-height:640px; min-height: 200px"></video>

## Instalação

Oferecemos dois métodos de instalação. O Método 2 (usando uv) é recomendado para uma instalação mais rápida e melhor gerenciamento de dependências.

### Método 1: Usando conda

1. Crie um novo ambiente conda:

```bash
conda create -n open_manus python=3.12
conda activate open_manus
```

2. Clone o repositório:

```bash
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

### Método 2: Usando uv (Recomendado)

1. Instale o uv (Um instalador e resolvedor de pacotes Python rápido):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone o repositório:

```bash
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus
```

3. Crie um novo ambiente virtual e ative-o:

```bash
uv venv --python 3.12
source .venv/bin/activate  # No Unix/macOS
# Ou no Windows:
# .venv\Scripts\activate
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

OpenManus requer configuração para as APIs LLM que utiliza. Siga estes passos para configurar:

1. Crie um arquivo `config.toml` no diretório `config` (você pode copiar do exemplo):

```bash
cp config/config.example.toml config/config.toml
```

2. Edite o `config/config.toml` para adicionar suas chaves de API e personalizar configurações:

```toml
# Configuração global LLM
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

Em seguida, insira sua ideia via terminal!

Para a versão com ferramentas MCP, você pode executar:
```bash
python run_mcp.py
```

Para a versão instável multi-agente, você também pode executar:

```bash
python run_flow.py
```

## Como contribuir

Recebemos com prazer quaisquer sugestões amigáveis e contribuições úteis! Basta criar issues ou enviar pull requests.

Ou entre em contato com @mannaandpoem via 📧email: mannaandpoem@gmail.com

**Observação**: Antes de enviar um pull request, use a ferramenta pre-commit para verificar suas alterações. Execute `pre-commit run --all-files` para realizar as verificações.

## Grupo Comunitário
Junte-se ao nosso grupo na Feishu e compartilhe sua experiência com outros desenvolvedores!

<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/community_group.jpg" alt="OpenManus 交流群" width="300" />
</div>

## Histórico de Estrelas

[![Star History Chart](https://api.star-history.com/svg?repos=mannaandpoem/OpenManus&type=Date)](https://star-history.com/#mannaandpoem/OpenManus&Date)

## Patrocinadores
Agradecemos a [PPIO](https://ppinfra.com/user/register?invited_by=OCPKCN&utm_source=github_openmanus&utm_medium=github_readme&utm_campaign=link) pelo suporte em recursos computacionais.
> PPIO: A solução de nuvem GPU e MaaS mais acessível e facilmente integrável.

## Agradecimentos

Agradecemos ao [anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo)
e [browser-use](https://github.com/browser-use/browser-use) por fornecerem suporte básico para este projeto!

Além disso, somos gratos a [AAAJ](https://github.com/metauto-ai/agent-as-a-judge), [MetaGPT](https://github.com/geekan/MetaGPT), [OpenHands](https://github.com/All-Hands-AI/OpenHands) e [SWE-agent](https://github.com/SWE-agent/SWE-agent).

Também agradecemos à stepfun (阶跃星辰) por apoiar nosso espaço de demonstração no Hugging Face.

OpenManus é construído por colaboradores do MetaGPT. Imensos agradecimentos a esta comunidade de agentes!

## Citação
```bibtex
@misc{openmanus2025,
  author = {Xinbin Liang and Jinyu Xiang and Zhaoyang Yu and Jiayi Zhang and Sirui Hong},
  title = {OpenManus: An open-source framework for building general AI agents},
  year = {2025},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/mannaandpoem/OpenManus}},
}
```
