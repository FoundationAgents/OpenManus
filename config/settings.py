import os
from dotenv import load_dotenv
from pathlib import Path

class Settings:
    """应用配置类"""
    
    _initialized = False
    
    # Azure OpenAI 配置
    AZURE_OPENAI_API_KEY = None
    AZURE_OPENAI_ENDPOINT = None
    AZURE_OPENAI_DEPLOYMENT_NAME = None
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = None
    AZURE_OPENAI_API_VERSION = "2023-05-15"
    
    OPENMODELICA_PATHS = [
        '/Applications/OpenModelica.app/Contents/Resources',
        '/opt/openmodelica',
    ]
    
    SIMULATION_SETTINGS = {
        'startTime': 0.0,
        'stopTime': 10.0,
        'numberOfIntervals': 500,
        'tolerance': 1e-6,
        'method': 'dassl'
    }
    
    @classmethod
    def load_env(cls):
        """加载环境变量"""
        if cls._initialized:
            return
            
        # 尝试多个可能的.env文件位置
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / '.env',  # 原始路径
            Path(__file__).parent.parent / '.env',                # 项目根目录
            Path.cwd() / '.env',                                  # 当前工作目录
        ]
        
        env_loaded = False
        for env_path in possible_paths:
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
                print(f"已加载环境变量文件: {env_path}")
                env_loaded = True
                break
                
        if not env_loaded:
            print("警告: 未找到.env文件，尝试从系统环境变量加载")
            
        # 加载环境变量到类属性
        cls.AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
        cls.AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
        cls.AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        cls.AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        cls.AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
        
        cls._initialized = True
        
        # 打印加载的值（调试用）
        print(f"API_KEY: {cls.AZURE_OPENAI_API_KEY and '已设置' or '未设置'}")
        print(f"ENDPOINT: {cls.AZURE_OPENAI_ENDPOINT and '已设置' or '未设置'}")
        print(f"DEPLOYMENT_NAME: {cls.AZURE_OPENAI_DEPLOYMENT_NAME and '已设置' or '未设置'}")

    @classmethod
    def validate_settings(cls):
        """验证配置是否完整"""
        # 确保环境变量已加载
        cls.load_env()
        
        required = [
            'AZURE_OPENAI_API_KEY',
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_OPENAI_DEPLOYMENT_NAME',
            'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
        ]
        
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"缺少必要的配置项: {', '.join(missing)}") 