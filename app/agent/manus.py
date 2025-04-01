from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.tool.google_search import GoogleSearch
from app.tool.python_execute import PythonExecute
from app.tool.baidu_search import BaiduSearch
from  app.tool.bing_search import BingSearch
from pathlib import Path
import tomllib

from typing import ClassVar, Dict, Type, Any

def load_config():
    try:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.toml"
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        return {"engine": config["search"]["engine"].lower()}  # 使用 engine 而不是 default_engine
    except FileNotFoundError:
        raise RuntimeError(
            "Configuration file not found, please check if config/config.toml exists"
        )
    except KeyError as e:
        raise RuntimeError(
            f"The configuration file is missing necessary fields: {str(e)}"
        )
def search_engine() -> Any:
    """
    根据配置文件选择并返回相应的搜索引擎实例。
    如果配置无效，则回退到默认搜索引擎 GoogleSearch。
    """
    SEARCH_ENGINES: ClassVar[Dict[str, Type]] = {
        "baidu": BaiduSearch,
        "bing": BingSearch,
        "google": GoogleSearch,
    }
    config: Dict[str, str] = load_config()
    engine_class: Type = SEARCH_ENGINES.get(config["engine"], GoogleSearch)
    return engine_class()  # 返回具体搜索引擎的实例
class Manus(ToolCallAgent):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends PlanningAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    """

    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 2000
    max_steps: int = 20
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            search_engine(),
            BrowserUseTool(),
            FileSaver(),
            Terminate()
        )
    )
    description = "A versatile agent that can solve various tasks using multiple tools"
