<p align="left">
    <a href="README_zh.md">中文</a>&nbsp ｜ &nbspEnglish&nbsp
</p>

This project fork from：
https://github.com/mannaandpoem/OpenManus


# OpenManus 🙋
Manus is incredible, but OpenManus can achieve any ideas without an Invite Code 🛫!

Our team members [@mannaandpoem](https://github.com/mannaandpoem) [@XiangJinyu](https://github.com/XiangJinyu) [@MoshiQAQ](https://github.com/MoshiQAQ) [@didiforgithub](https://github.com/didiforgithub) from [@MetaGPT](https://github.com/geekan/MetaGPT) built it within 3 hours!

It's a simple implementation, so we welcome any suggestions, contributions, and feedback!

Enjoy your own agent with OpenManus!

## Project Demo
![截屏2025-03-07 16 49 18](https://github.com/user-attachments/assets/3b7f425a-3849-4e27-aaa4-2ff1c3d307d6)
![截屏2025-03-07 16 49 32](https://github.com/user-attachments/assets/fef9e0b7-6b85-498a-bf8c-6985771e9428)


## Installation

1. Create a new conda environment:

```bash
conda create -n open_manus python=3.12
conda activate open_manus
```

2. Clone the repository:

```bash
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

OpenManus requires configuration for the LLM APIs it uses. Follow these steps to set up your configuration:

1. Create a `.env` file in the root directory (you can copy from the example):

```bash
cp env_example .env
```

2. Edit `.env` to add your API keys and customize settings:

```.env
AZURE_OPENAI_API_KEY=xxxxx
AZURE_OPENAI_ENDPOINT=https://xxxx.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2023-05-15
```

## Quick Start
One line for run OpenManus:

```bash
python main.py
```

Then input your idea via terminal!

For unstable version, you also can run:

```bash
python run_flow.py
```


## Roadmap
- [ ] Better Planning
- [ ] Live Demos
- [ ] Replay
- [ ] RL Fine-tuned Models
- [ ] Comprehensive Benchmarks

## Community Group
Join our networking group and share your experience with other developers!
<div align="center">
    <img src="assets/community_group.jpeg" alt="OpenManus Community Group" width="300"/>
</div>

## Acknowledgement

Thanks to [anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo) and [broswer-use](https://github.com/browser-use/browser-use) for providing basic support for this project!

OpenManus is built by contributors from MetaGPT. Huge thanks to this agent community!
