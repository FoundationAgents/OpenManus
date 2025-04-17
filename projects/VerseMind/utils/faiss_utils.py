"""FAISS工具模块，用于处理FAISS的初始化和配置"""

import io
import os
from contextlib import redirect_stderr


# 配置FAISS只使用CPU
os.environ["FAISS_NO_GPU"] = "1"

# 临时重定向stderr以抑制FAISS的GPU警告
with redirect_stderr(io.StringIO()):
    import faiss


def get_faiss_index(dimension: int):
    """获取FAISS索引实例

    Args:
        dimension (int): 向量维度

    Returns:
        faiss.IndexFlatL2: FAISS索引实例
    """
    return faiss.IndexFlatL2(dimension)


def save_faiss_index(index, path: str):
    """保存FAISS索引

    Args:
        index: FAISS索引实例
        path (str): 保存路径
    """
    faiss.write_index(index, path)


def load_faiss_index(path: str):
    """加载FAISS索引

    Args:
        path (str): 索引文件路径

    Returns:
        faiss.IndexFlatL2: 加载的FAISS索引实例
    """
    return faiss.read_index(path)
