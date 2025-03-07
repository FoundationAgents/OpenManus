import threading
import tomllib
from pathlib import Path
from typing import Dict
from config.settings import Settings

from pydantic import BaseModel, Field


def get_project_root() -> Path:
    """获取项目根目录
    
    Returns:
        项目根目录的Path对象
    """
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()  # 项目根目录
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"  # 工作空间目录


class LLMSettings(BaseModel):
    """LLM配置模型
    
    存储与语言模型相关的配置参数。
    """
    model: str = Field("default_model", description="模型名称")
    base_url: str = Field("http://localhost:8000", description="API基础URL")
    api_key: str = Field("default_key", description="API密钥")
    max_tokens: int = Field(4096, description="每个请求的最大令牌数")
    temperature: float = Field(1.0, description="采样温度")


class AppConfig(BaseModel):
    """应用程序配置模型
    
    存储整个应用程序的配置。
    """
    llm: Dict[str, LLMSettings]  # LLM配置字典


class Config:
    """配置管理类
    
    实现单例模式，管理应用程序配置的加载和访问。
    """
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """创建单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置管理器"""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config = None
                    self._load_initial_config()
                    self._initialized = True

    @staticmethod
    def _get_config_path() -> Path:
        """获取配置文件路径
        
        Returns:
            配置文件的Path对象
            
        Raises:
            FileNotFoundError: 在配置目录中找不到配置文件
        """
        root = PROJECT_ROOT
        config_path = root / "config" / "config.toml"
        if config_path.exists():
            return config_path
        example_path = root / "config" / "config.example.toml"
        if example_path.exists():
            return example_path
        raise FileNotFoundError("在配置目录中找不到配置文件")

    def _load_config(self) -> dict:
        """加载配置文件
        
        Returns:
            配置数据字典
        """
        config_path = self._get_config_path()
        with config_path.open("rb") as f:
            return tomllib.load(f)

    def _load_initial_config(self):
        """加载初始配置
        
        处理原始配置数据并转换为结构化配置对象。
        """
        
        try:
            # 尝试从配置文件加载
            raw_config = self._load_config()
            # 从配置文件中获取 llm 配置
            base_llm = raw_config.get("llm", {})
        except Exception:
            # 如果加载失败，使用 Settings 类
            raw_config = Settings()
            # 假设 Settings 类有 llm 属性，如果没有则使用空字典
            base_llm = getattr(raw_config, "llm", {})
        
        # 检查 base_llm 是否为字典类型
        if not isinstance(base_llm, dict):
            base_llm = {}
        
        # 获取 llm 覆盖配置
        llm_overrides = {
            k: v for k, v in base_llm.items() if isinstance(v, dict)
        }

        # 设置默认值，确保必填字段有值
        default_settings = {
            "model": base_llm.get("model", "default_model"),
            "base_url": base_llm.get("base_url", "http://localhost:8000"),
            "api_key": base_llm.get("api_key", "default_key"),
            "max_tokens": base_llm.get("max_tokens", 4096),
            "temperature": base_llm.get("temperature", 1.0),
        }

        config_dict = {
            "llm": {
                "default": default_settings,
                **{
                    name: {**default_settings, **override_config}
                    for name, override_config in llm_overrides.items()
                },
            }
        }

        self._config = AppConfig(**config_dict)

    @property
    def llm(self) -> Dict[str, LLMSettings]:
        """获取LLM配置
        
        Returns:
            LLM配置字典
        """
        return self._config.llm


config = Config()  # 全局配置单例实例
