import json
import os
from typing import Any, Dict, Optional
import dotenv
from pathlib import Path
from agentbay.logger import get_logger

# Initialize logger for this module
logger = get_logger("config")


def default_config() -> Dict[str, Any]:
    """Return the default configuration"""
    return {
        "endpoint": "wuyingai.cn-shanghai.aliyuncs.com",
        "timeout_ms": 60000,
    }


# Browser data path constant
BROWSER_DATA_PATH = "/tmp/agentbay_browser"


def find_dotenv_file(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find .env file by searching upward from start_path.
    
    Search order:
    1. Current working directory
    2. Parent directories (up to root)
    3. Git repository root (if found)
    
    Args:
        start_path: Starting directory for search (defaults to current working directory)
        
    Returns:
        Path to .env file if found, None otherwise
    """
    if start_path is None:
        start_path = Path.cwd()
    
    current_path = Path(start_path).resolve()
    
    # Search upward until we reach root directory
    while current_path != current_path.parent:
        env_file = current_path / ".env"
        if env_file.exists():
            logger.debug(f"Found .env file at: {env_file}")
            return env_file
        
        # Check if this is a git repository root
        git_dir = current_path / ".git"
        if git_dir.exists():
            logger.debug(f"Found git repository root at: {current_path}")
        
        current_path = current_path.parent
    
    # Check root directory as well
    root_env = current_path / ".env"
    if root_env.exists():
        logger.debug(f"Found .env file at root: {root_env}")
        return root_env
    
    return None


def load_dotenv_with_fallback(custom_env_path: Optional[str] = None) -> None:
    """
    Load .env file with improved search strategy.
    
    Args:
        custom_env_path: Custom path to .env file (optional)
    """
    if custom_env_path:
        # Use custom path if provided
        env_path = Path(custom_env_path)
        if env_path.exists():
            dotenv.load_dotenv(env_path)
            logger.info(f"Loaded custom .env file from: {env_path}")
            return
        else:
            logger.warning(f"Custom .env file not found: {env_path}")
    
    # Find .env file using upward search
    env_file = find_dotenv_file()
    if env_file:
        try:
            dotenv.load_dotenv(env_file)
            logger.info(f"Loaded .env file from: {env_file}")
        except Exception as e:
            logger.warning(f"Failed to load .env file {env_file}: {e}")
    else:
        logger.debug("No .env file found in current directory or parent directories")


"""
The SDK uses the following precedence order for configuration (highest to lowest):
1. Explicitly passed configuration in code.
2. Environment variables.
3. .env file (searched upward from current directory).
4. Default configuration.
"""


def load_config(cfg, custom_env_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration with improved .env file search.
    
    Args:
        cfg: Configuration object (if provided, skips env loading)
        custom_env_path: Custom path to .env file (optional)
        
    Returns:
        Configuration dictionary
    """
    if cfg is not None:
        config = {
            "endpoint": cfg.endpoint,
            "timeout_ms": cfg.timeout_ms,
        }
    else:
        config = default_config()
        
        # Load .env file with improved search
        try:
            load_dotenv_with_fallback(custom_env_path)
        except Exception as e:
            logger.warning(f"Failed to load .env file: {e}")
        
        # Apply environment variables (highest priority)
        if endpoint := os.getenv("AGENTBAY_ENDPOINT"):
            config["endpoint"] = endpoint
        if timeout_ms := os.getenv("AGENTBAY_TIMEOUT_MS"):
            try:
                config["timeout_ms"] = int(timeout_ms)
            except ValueError:
                logger.warning(f"Invalid AGENTBAY_TIMEOUT_MS value: {timeout_ms}, using default")
    
    return config
