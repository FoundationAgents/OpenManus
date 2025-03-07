class ToolError(Exception):
    """当工具遇到错误时引发
    
    用于工具执行过程中的错误处理和传递错误信息。
    
    Attributes:
        message: 错误消息
    """

    def __init__(self, message):
        """初始化ToolError实例
        
        Args:
            message: 描述错误的消息
        """
        self.message = message
