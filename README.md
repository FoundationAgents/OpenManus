<p align="center">
  <img src="assets/logo.jpg" width="200"/>
</p>

<p align="center">
  <strong>OpenManus: Your Versatile AI Agent Framework</strong>
</p>

<p align="center">
  English | <a href="README_zh.md">中文</a> | <a href="README_ko.md">한국어</a> | <a href="README_ja.md">日本語</a>
</p>

<p align="center">
  <a href="https://github.com/mannaandpoem/OpenManus/stargazers"><img src="https://img.shields.io/github/stars/mannaandpoem/OpenManus?style=social" alt="GitHub stars"></a>
  &ensp;
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  &ensp;
  <a href="https://discord.gg/DYn29wFk9z"><img src="https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat" alt="Discord Follow"></a>
  &ensp;
  <a href="https://huggingface.co/spaces/lyh-917/OpenManusDemo"><img src="https://img.shields.io/badge/Demo-Hugging%20Face-yellow" alt="Demo"></a>
</p>

---

## 👋 Introduction

Manus is incredible, but OpenManus can achieve any idea without an *Invite Code* 🛫!

**This fork enhances the original OpenManus by adding a user-friendly Web UI, an OpenAI-compatible API, a dedicated CLI entry point, multi-turn conversation support, and persistent chat history.**

Our team members [@Xinbin Liang](https://github.com/mannaandpoem) and [@Jinyu Xiang](https://github.com/XiangJinyu) (core authors), along with [@Zhaoyang Yu](https://github.com/MoshiQAQ), [@Jiayi Zhang](https://github.com/didiforgithub), and [@Sirui Hong](https://github.com/stellaHSR), we are from [@MetaGPT](https://github.com/geekan/MetaGPT). The prototype is launched within 3 hours and we are keeping building!

It's a simple implementation, so we welcome any suggestions, contributions, and feedback!

Enjoy your own agent with OpenManus!

We're also excited to introduce [OpenManus-RL](https://github.com/OpenManus/OpenManus-RL), an open-source project dedicated to reinforcement learning (RL)- based (such as GRPO) tuning methods for LLM agents, developed collaboratively by researchers from UIUC and OpenManus.

## ✨ Features (Enhanced in this Fork)

*   **Multi-Turn Conversation**: Engage in extended dialogues with context retention.
*   **Web UI (Gradio)**: Interact with the agent through an intuitive web interface featuring:
    *   Streaming responses for real-time updates.
    *   Session management (create, rename, delete, switch conversations).
    *   Persistent chat history stored locally in the `chatsHistory/` directory.
*   **OpenAI-Compatible API (FastAPI)**: Integrate OpenManus into your applications using the familiar OpenAI SDK format (`/v1/chat/completions` endpoint). Supports both streaming and non-streaming modes.
*   **Command-Line Interface (CLI)**: A dedicated entry point (`cli_main.py`) for terminal-based interaction.
*   **Versatile Tools**: Equipped with tools for:
    *   Web Browsing (`BrowserUseTool`)
    *   Code Execution (Python in a sandbox environment)
    *   File Operations (String replacement editor)
    *   Web Search (Google, Bing, DuckDuckGo, Baidu)
    *   Bash Command Execution (via sandbox terminal)
*   **Extensible Framework**: Built with a clear, object-oriented structure (`BaseAgent` -> `ReActAgent` -> `ToolCallAgent` -> `BrowserAgent` -> `Manus`).

## 📸 Screenshots

**Web UI:**
![OpenManus Web UI Screenshot 1](https://github.com/Hank-Chromela/Hank-Chroela-images/blob/main/1743753144854.png?raw=true)

**Session Management:**
![OpenManus Web UI Screenshot 2](https://github.com/Hank-Chromela/Hank-Chroela-images/blob/main/1743753160804.png?raw=true)

## 🚀 Installation

We recommend using `uv` for faster installation and dependency management.

### Method 1: Using conda

1.  Create a new conda environment:
    ```bash
    conda create -n open_manus python=3.12 -y
    conda activate open_manus
    ```
2.  Clone this repository (Your Fork):
    ```bash
    git clone https://github.com/Hank-Chromela/OpenManus-GUI.git
    cd OpenManus-GUI
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Method 2: Using uv (Recommended)

1.  Install `uv` (if you haven't already):
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Or follow instructions at https://github.com/astral-sh/uv
    ```
2.  Clone this repository (Your Fork):
    ```bash
    git clone https://github.com/Hank-Chromela/OpenManus-GUI.git
    cd OpenManus-GUI
    ```
3.  Create and activate a virtual environment:
    ```bash
    uv venv --python 3.12 # Or your preferred Python 3.10+ version
    source .venv/bin/activate  # Unix/macOS
    # .venv\Scripts\activate    # Windows
    ```
4.  Install dependencies:
    ```bash
    uv pip install -r requirements.txt
    ```

### Install Playwright Browsers (Required for Browser Tool)
```bash
playwright install --with-deps
⚙️ Configuration
OpenManus requires configuration for the Large Language Model (LLM) you intend to use.

Ensure config/config.example.toml exists: This file serves as the configuration template.
Create config/config.toml:
cp config/config.example.toml config/config.toml
Edit config/config.toml to add your API keys and customize settings:
# Global LLM configuration (primarily uses default)
[llm.default]
model = "gpt-4o" # e.g., gpt-4o, gpt-3.5-turbo, claude-3-opus-20240229, etc.
api_type = "openai" # Supported: "openai", "azure", "aws" (Bedrock), etc. depending on your LLM config
base_url = "https://api.openai.com/v1" # Replace with your API endpoint
api_key = "sk-..."  # IMPORTANT: Replace with your actual API key!
max_tokens = 4096
temperature = 0.0
# api_version = "..." # Required for Azure OpenAI

# Optional configuration for specific LLM models (e.g., for vision)
# [llm.vision]
# model = "gpt-4o"
# base_url = "https://api.openai.com/v1"
# api_key = "sk-..."
Note: config/config.toml contains sensitive information and is included in .gitignore to prevent accidental commits.
▶️ Running the Application
You can now run different modes using separate entry points or the main launcher:

1. Run Web UI & API Server (Recommended)

Use the main.py launcher script:

python main.py
# Or explicitly (default behavior):
# python main.py --service all
This will:

Start the Gradio Web UI server (default: http://127.0.0.1:7860).
Start the FastAPI API server (default: http://0.0.0.0:8000).
Attempt to automatically open the Web UI in your browser.
2. Run Only Web UI

python main.py --service ui
Starts only the Gradio Web UI server (default: http://127.0.0.1:7860).
Attempts to open the browser.
3. Run Only API Server

python main.py --service api
Starts only the FastAPI API server (default: http://0.0.0.0:8000).
4. Run Command-Line Interface (CLI)

python cli_main.py
Starts the pure command-line interaction mode.
💻 Using the Web UI
Navigate to http://127.0.0.1:7860 in your browser if it didn't open automatically.
Chat: Enter your requests in the message box at the bottom and press Enter or click "Send". The agent's thoughts, tool usage, and final response will stream into the chat window.
Session Management:
Use the left sidebar to manage conversations.
Click "➕ New Chat" to start a fresh conversation.
Select a session from the list to load its history.
Use the "Manage Selected Session" section below the list to rename or delete the currently selected chat (you cannot delete the last remaining chat).
Persistence: Chat history and session names are automatically saved in the chatsHistory/ directory as JSON files and will be reloaded when you restart the application.
🔌 Using the API
The server exposes an OpenAI-compatible API endpoint at /v1/chat/completions (default runs on http://0.0.0.0:8000). You can use standard OpenAI client libraries (like the official Python openai library) to interact with it.

Configuration in Client:

Base URL: http://<your-server-ip-or-localhost>:8000/v1 (e.g., http://127.0.0.1:8000/v1)
API Key: Any non-empty string (e.g., "not-needed"). The server does not validate the key.
Model: Any non-empty string (e.g., "openmanus"). The server uses the configured Manus agent regardless of the model name sent.
Example using openai Python library:

# test_api.py
import openai

# Configure the client (assuming API server runs on localhost:8000)
client = openai.OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="not-needed", # Provide a dummy key
)

# Non-streaming request
try:
    completion = client.chat.completions.create(
        model="openmanus-local", # Model name is required but ignored by server
        messages=[
            {"role": "user", "content": "What is the capital of France?"}
        ]
    )
    print("Non-Streaming Response:")
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"API Error: {e}")

# Streaming request
try:
    stream = client.chat.completions.create(
        model="openmanus-local",
        messages=[
            {"role": "user", "content": "Explain quantum entanglement briefly."}
        ],
        stream=True
    )
    print("\nStreaming Response:")
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end="")
    print()
except Exception as e:
    print(f"API Streaming Error: {e}")
🙌 How to contribute
We welcome any friendly suggestions and helpful contributions! Just create issues or submit pull requests.

Or contact @mannaandpoem via 📧email: mannaandpoem@gmail.com

Note: Before submitting a pull request, please use the pre-commit tool to check your changes. Run pre-commit run --all-files to execute the checks.

💬 Community Group
Join our networking group on Feishu and share your experience with other developers!

⭐ Star History
Star History Chart

🙏 Acknowledgement
Thanks to anthropic-computer-use and browser-use for providing basic support for this project!

Additionally, we are grateful to AAAJ, MetaGPT, OpenHands and SWE-agent.

We also thank stepfun(阶跃星辰) for supporting our Hugging Face demo space.

OpenManus is built by contributors from MetaGPT. Huge thanks to this agent community!

📜 Cite
If you use OpenManus in your research or work, please cite it as follows:

@misc{openmanusGUI2025,
  author = {Xinbin Liang and Jinyu Xiang and Zhaoyang Yu and Jiayi Zhang and Sirui Hong and Hank-Chromela (UI/API Integration)},
  title = {OpenManus-GUI: An Enhanced Open-Source Framework for Versatile AI Agents with UI and API},
  year = {2025},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/Hank-Chromela/OpenManus-GUI}},
}
