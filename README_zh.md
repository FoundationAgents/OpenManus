<p align="left">
    中文&nbsp ｜ &nbsp<a href="README.md">English</a>&nbsp
</p>

# OpenManus 🙋  

Manus 非常棒，但 OpenManus 无需邀请码即可实现任何创意 🛫！

我们来自 [@MetaGPT](https://github.com/geekan/MetaGPT) 的团队成员 [@mannaandpoem](https://github.com/mannaandpoem) [@XiangJinyu](https://github.com/XiangJinyu) [@MoshiQAQ](https://github.com/MoshiQAQ) [@didiforgithub](https://github.com/didiforgithub) 在 3 小时内完成了开发！

这是一个简洁的实现方案，欢迎任何建议、贡献和反馈！

用 OpenManus 开启你的智能体之旅吧！

## 项目演示  

## 安装指南

1. 创建新的 conda 环境：

```bash
conda create -n open_manus python=3.12
conda activate open_manus
```

2. 克隆仓库：

```bash
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

## 配置说明

OpenManus 需要配置使用的 LLM API，请按以下步骤设置：

1. 在根目录创建 `.env` 文件（可从示例复制）：

```bash
cp env_example .env
```

2. 编辑 `.env` 添加 API 密钥和自定义设置：

```.env
AZURE_OPENAI_API_KEY=xxxxx
AZURE_OPENAI_ENDPOINT=https://xxxx.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2023-05-15
```

## 快速启动
一行命令运行 OpenManus：

```bash
python main.py
```

然后通过终端输入你的创意！

如需体验开发中版本，可运行：

```bash
python run_flow.py
```

## 贡献指南
我们欢迎任何友好的建议和有价值的贡献！可以直接创建 issue 或提交 pull request。

或通过📧邮件联系 @mannaandpoem：mannaandpoem@gmail.com

## 发展路线
- [ ] 更优的规划系统
- [ ] 实时演示功能
- [ ] 运行回放
- [ ] 强化学习微调模型
- [ ] 全面的性能基准测试

## 交流群
加入我们的交流群，与其他开发者分享经验！

<div align="center">
    <img src="assets/community_group.jpeg" alt="OpenManus 交流群" width="300"/>
</div>

## 致谢

特别感谢 [anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo) 和 [broswer-use](https://github.com/browser-use/browser-use) 为本项目提供的基础支持！

OpenManus 由 MetaGPT 社区的贡献者共同构建，感谢这个充满活力的智能体开发者社区！
