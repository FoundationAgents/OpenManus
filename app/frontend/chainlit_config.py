"""Chainlit configuration for OpenManus integration."""

import os
from pathlib import Path
from typing import Any, Dict

# Chainlit configuration dictionary
CHAINLIT_CONFIG = {
    "project": {
        "name": "OpenManus",
        "description": "Multi-Agent AI Automation Framework",
        "website": "https://github.com/Copyxyzai/OpenManus",
        "github": "https://github.com/Copyxyzai/OpenManus",
    },
    "ui": {
        "name": "OpenManus Assistant",
        "theme": "dark",
        "default_expand_messages": True,
        "hide_cot": False,
        "show_readme_as_default": False,
        "collapse_assistant_messages": False,
    },
    "features": {
        "prompt_playground": True,
        "multi_modal": True,
        "latex": True,
        "unsafe_allow_html": False,
        "speech_to_text": False,
    },
    "session": {
        "max_size_mb": 100,
        "timeout": 3600,  # 1 hour
        "memory": True,
    },
    "files": {
        "max_size_mb": 10,
        "max_files": 10,
        "allowed_extensions": [
            ".txt",
            ".md",
            ".py",
            ".json",
            ".yaml",
            ".yml",
            ".csv",
            ".xml",
            ".html",
            ".js",
            ".ts",
            ".css",
        ],
    },
}


def setup_chainlit_config(config_dir: Path = None) -> None:
    """Setup Chainlit configuration file.

    Args:
        config_dir: Directory to create config in. Defaults to project root.
    """
    if config_dir is None:
        config_dir = Path.cwd()

    chainlit_dir = config_dir / ".chainlit"
    config_file = chainlit_dir / "config.toml"

    # Only create config if it doesn't exist or is invalid
    if not config_file.exists():
        # Create .chainlit directory if it doesn't exist
        if not chainlit_dir.exists():
            chainlit_dir.mkdir(parents=True, exist_ok=True)

        # Create config.toml for Chainlit
        config_content = generate_config_toml()

        with open(config_file, "w", encoding="utf-8") as f:
            f.write(config_content)

        print(f"Chainlit configuration created at: {config_file}")
    else:
        print(f"Chainlit configuration already exists at: {config_file}")


def generate_config_toml() -> str:
    """Generate TOML configuration content for Chainlit."""
    config = CHAINLIT_CONFIG

    return f"""[project]
# Whether to enable telemetry (default: true). No personal data is collected.
enable_telemetry = true

# List of environment variables to be provided by each user to use the app.
user_env = []

# Duration (in seconds) during which the session is saved when the connection is lost
session_timeout = {config['session']['timeout']}

# Enable third parties caching (e.g LangChain cache)
cache = false

# Authorized origins
allow_origins = ["*"]

# Follow symlink for asset mount (see https://github.com/Chainlit/chainlit/issues/317)
# follow_symlink = false

[features]
# Show the prompt playground
prompt_playground = {str(config['features']['prompt_playground']).lower()}

# Process and display HTML in messages. This can be a security risk (see https://stackoverflow.com/questions/19603097/why-is-it-dangerous-to-render-user-generated-html-or-javascript)
unsafe_allow_html = {str(config['features']['unsafe_allow_html']).lower()}

# Process and display mathematical expressions. This can clash with "$" characters in messages.
latex = {str(config['features']['latex']).lower()}

# Automatically tag threads when a user takes an action (useful for analytics)
auto_tag_thread = true

# Literal AI connection to easily debugging and improving your AI system
[features.literalai]
# The server URL used to connect to Literal AI.
api_url = "https://cloud.getliteral.ai"
# The public key of your LiteralAI project.
# public_key = ""

[UI]
# Name of the app and chatbot.
name = "{config['ui']['name']}"

# Show the readme while the thread is empty.
show_readme_as_default = {str(config['ui']['show_readme_as_default']).lower()}

# Description of the app and chatbot. This is used for HTML tags.
description = "{config['project']['description']}"

# Large size content are by default collapsed for a cleaner ui
default_collapse_content = true

# The default value for the expand messages settings.
default_expand_messages = {str(config['ui']['default_expand_messages']).lower()}

# Hide the chain of thought details from the user in the UI.
hide_cot = {str(config['ui']['hide_cot']).lower()}

# Link to your github repo. This will add a github button in the UI's header.
github = "{config['project']['github']}"

# Specify a CSS file that can be used to customize the user interface.
# The CSS file can be served from the public directory or via an external link.
# custom_css = "/public/test.css"

# Specify a Javascript file that can be used to customize the user interface.
# The Javascript file can be served from the public directory.
# custom_js = "/public/test.js"

# Specify a custom font url.
# custom_font = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap"

# Specify a custom build directory for the UI.
# This is useful when you want to customize the UI using React.
# default_build_dir = "./chainlit/frontend/dist"

# Override default MUI light theme. (Check theme.ts)
[UI.theme]
# primary_color = "#F80061"
# background_color = "#FAFAFA"
# text_color = "#212121"
# paper_color = "#FFFFFF"
# [UI.theme.header]
# unsafe_allow_html = false
# height = "60px"

# Override default MUI dark theme. (Check theme.ts)
[UI.theme.dark]
# primary_color = "#FFFF80"
# background_color = "#1E1E1E"
# text_color = "#EEEEEE"
# paper_color = "#262626"

# [UI.theme.dark.header]
# unsafe_allow_html = false
# height = "60px"

[meta]
generated_by = "2.8.1"
"""


def get_chainlit_env_vars() -> Dict[str, str]:
    """Get environment variables for Chainlit configuration."""
    return {
        "CHAINLIT_HOST": os.getenv("CHAINLIT_HOST", "localhost"),
        "CHAINLIT_PORT": os.getenv("CHAINLIT_PORT", "8000"),
        "CHAINLIT_DEBUG": os.getenv("CHAINLIT_DEBUG", "0"),
        "CHAINLIT_HEADLESS": os.getenv("CHAINLIT_HEADLESS", "0"),
        "CHAINLIT_WATCH": os.getenv("CHAINLIT_WATCH", "0"),
    }


def set_chainlit_env_vars(
    host: str = "localhost", port: int = 8000, debug: bool = False
) -> None:
    """Set environment variables for Chainlit."""
    os.environ["CHAINLIT_HOST"] = host
    os.environ["CHAINLIT_PORT"] = str(port)
    os.environ["CHAINLIT_DEBUG"] = "1" if debug else "0"


if __name__ == "__main__":
    # Setup configuration when run directly
    setup_chainlit_config()
