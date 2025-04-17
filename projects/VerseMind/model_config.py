"""模型配置类"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class ModelConfig:
    """模型配置类"""

    name: str
    type: str
    model: str
    base_url: str
    api_key: str
    api_version: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "type": self.type,
            "model": self.model,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "api_version": self.api_version,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ModelConfig":
        """从字典创建配置对象"""
        return cls(
            name=data["name"],
            type=data["type"],
            model=data["model"],
            base_url=data["base_url"],
            api_key=data["api_key"],
            api_version=data.get("api_version", ""),
            max_tokens=data.get("max_tokens", 4096),
            temperature=data.get("temperature", 0.7),
        )

    def validate(self) -> bool:
        """验证配置是否有效"""
        required_fields = ["name", "type", "model", "base_url", "api_key"]
        return all(hasattr(self, field) for field in required_fields)
