<p align="center">
  <img src="assets/logo.jpg" width="200"/>
</p>

English | [中文](README_zh.md) | [한국어](README_ko.md) | [日本語](README_ja.md)

[![GitHub stars](https://img.shields.io/github/stars/FoundationAgents/OpenManus?style=social)](https://github.com/FoundationAgents/OpenManus/stargazers)
&ensp;
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) &ensp;
[![Discord Follow](https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat)](https://discord.gg/DYn29wFk9z)
[![Demo](https://img.shields.io/badge/Demo-Hugging%20Face-yellow)](https://huggingface.co/spaces/lyh-917/OpenManusDemo)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15186407.svg)](https://doi.org/10.5281/zenodo.15186407)

# 👋 OpenManus

Manus is incredible, but OpenManus can achieve any idea without an *Invite Code* 🛫!

OpenManus is an open-source framework for building general AI agents. This version provides an easy-to-use graphical interface to interact with the agent.

## Getting Started (Recommended)

This is the easiest way to get OpenManus up and running with a graphical user interface (GUI).

**Prerequisites:**
*   Git ([how to install](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git))
*   Python 3.12 or higher ([how to install](https://www.python.org/downloads/))

**Steps:**

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/FoundationAgents/OpenManus.git
    cd OpenManus
    ```

2.  **Run the Launcher:**
    The launcher script will automatically:
    *   Verify your Python version.
    *   Create a Python virtual environment (`.venv`).
    *   Install all necessary dependencies (including Gradio for the GUI).
    *   Install Playwright browser components.
    *   Ensure `config/config.toml` exists (copying from `config.example.toml` if needed).
    *   **Prompt for an API key if not found in `config.toml` (one-time setup).**
    *   Create a `workspace/` directory.
    *   Start the Gradio web interface.

    *   **For Windows:**
        Double-click on `OpenManus.bat`.
        (If you encounter issues, you might need to run it from a command prompt: `.\OpenManus.bat`)

    *   **For macOS/Linux:**
        Open your terminal, navigate to the `OpenManus` directory, and run:
        ```bash
        chmod +x openmanus.sh  # Make the script executable (only needed once)
        ./openmanus.sh
        ```

3.  **Open in Browser:**
    Once the launcher starts the GUI, it will typically print a local URL (like `http://127.0.0.1:7860` or `http://localhost:7860`). Open this URL in your web browser to use the OpenManus application.

## Configuration

*   **API Key:** The application requires an API key for Large Language Model access. The launcher script will prompt you for this key if it's not already set in `config/config.toml`. The key is stored locally in this file.
*   **Other Settings:** You can customize other settings (like the LLM model, agents used, etc.) by editing the `config/config.toml` file. Refer to `config/config.example.toml` for available options. For example, to use the Data Analysis agent:
    ```toml
    # In config/config.toml
    [runflow]
    use_data_analysis_agent = true     # Disabled by default, change to true to activate
    ```
    If you enable agents like `DataAnalysis`, ensure any extra dependencies they require are installed. (The launcher handles base dependencies; specific agent dependencies might need manual checks as per their documentation, e.g., [Data Analysis Agent Dependencies](app/tool/chart_visualization/README.md##Installation)).

## Legacy Installation & Usage (Manual Setup)

If you prefer a manual setup or are developing OpenManus, the following information might be useful. However, for most users, the **Getting Started** section above is recommended.

1.  **Environment:**
    Ensure you have Python 3.12+. You can use `conda` or `uv` to manage environments:
    *   Using `uv`:
        ```bash
        curl -LsSf https://astral.sh/uv/install.sh | sh # Install uv
        uv venv --python 3.12 # Create venv
        source .venv/bin/activate # Or .venv\Scriptsctivate on Windows
        ```
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt # Or uv pip install -r requirements.txt
    playwright install # For browser automation tools
    ```
3.  **Configuration:**
    Manually copy `config/config.example.toml` to `config/config.toml` and edit it with your API key and other settings.

4.  **Running Scripts Directly:**
    You can still run individual scripts like `main.py` (basic CLI), `run_flow.py` (CLI for flows), or `app_gui.py` (starts the Gradio GUI) directly using the Python interpreter from your activated virtual environment (e.g., `python app_gui.py`).

## How to Contribute

We welcome any friendly suggestions and helpful contributions! Just create issues or submit pull requests.
Or contact @mannaandpoem via 📧email: mannaandpoem@gmail.com

**Note**: Before submitting a pull request, please use the pre-commit tool to check your changes. Run `pre-commit run --all-files` to execute the checks.

## Community Group
Join our networking group on Feishu and share your experience with other developers!
<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/community_group.jpg" alt="OpenManus 交流群" width="300" />
</div>

## Star History
[![Star History Chart](https://api.star-history.com/svg?repos=FoundationAgents/OpenManus&type=Date)](https://star-history.com/#FoundationAgents/OpenManus&Date)

## Sponsors
Thanks to [PPIO](https://ppinfra.com/user/register?invited_by=OCPKCN&utm_source=github_openmanus&utm_medium=github_readme&utm_campaign=link) for computing source support.
> PPIO: The most affordable and easily-integrated MaaS and GPU cloud solution.

## Acknowledgement
Thanks to [anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo)
and [browser-use](https://github.com/browser-use/browser-use) for providing basic support for this project!
Additionally, we are grateful to [AAAJ](https://github.com/metauto-ai/agent-as-a-judge), [MetaGPT](https://github.com/geekan/MetaGPT), [OpenHands](https://github.com/All-Hands-AI/OpenHands) and [SWE-agent](https://github.com/SWE-agent/SWE-agent).
We also thank stepfun(阶跃星辰) for supporting our Hugging Face demo space.
OpenManus is built by contributors from MetaGPT. Huge thanks to this agent community!

## Cite
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
