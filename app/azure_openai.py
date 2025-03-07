from typing import List, Optional, Dict, Any
from openai import AzureOpenAI
from ..config.settings import Settings

class AzureOpenAIProvider:
    """Azure OpenAI服务提供者"""
    
    def __init__(self):
        """初始化Azure OpenAI客户端"""
        Settings.validate_settings()  # 验证配置
        
        # self.client = AzureOpenAI(
        #     api_key=Settings.AZURE_OPENAI_API_KEY,
        #     api_version=Settings.AZURE_OPENAI_API_VERSION,
        #     azure_endpoint=Settings.AZURE_OPENAI_ENDPOINT,
        #     timeout=30.0,
        #     max_retries=3
        # )

    
        self.client = AzureOpenAI(
            api_key=Settings.AZURE_OPENAI_API_KEY,
            api_version="2023-05-15",
            azure_endpoint=Settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment_name = Settings.AZURE_OPENAI_DEPLOYMENT_NAME


    def _call_azure_openai(self, prompt: str) -> Any:
        """调用Azure OpenAI API"""
        return self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的embedding向量"""
        try:
            if not text or not text.strip():
                return None
                
            response = self.client.embeddings.create(
                input=text,
                model=Settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
            )
            return response.data[0].embedding if response.data else None
        except Exception as e:
            print(f"获取embedding失败: {str(e)}")
            return None

    def generate_completion(self, 
                          messages: List[Dict[str, str]], 
                          temperature: float = 0.7,
                          max_tokens: int = 800) -> Optional[str]:
        """生成文本补全"""
        try:
            response = self._call_azure_openai(messages)
            return response.choices[0].message.content if response.choices else None
        except Exception as e:
            print(f"生成补全失败: {str(e)}")
            return None

# 创建全局实例
azure_openai = AzureOpenAIProvider() 