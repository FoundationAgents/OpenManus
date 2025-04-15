"""诗歌向量数据库模块，用于存储和检索诗歌的向量表示"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
from utils.faiss_utils import get_faiss_index, load_faiss_index, save_faiss_index


# 配置FAISS只使用CPU
os.environ["FAISS_NO_GPU"] = "1"

# 设置日志级别来抑制进度条输出
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)


class PoetryVectorDB:
    """诗歌向量数据库类，用于存储和检索诗歌的向量表示"""

    def __init__(
        self,
        db_path: str = "poetry_vectors",
        model_name: str = "shibing624/text2vec-base-chinese",
    ):
        """初始化向量数据库

        Args:
            db_path (str): 数据库文件路径
            model_name (str): 文本向量化模型名称
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        # 初始化文本向量化模型
        self.model = SentenceTransformer(model_name)

        # 初始化向量索引
        self.dimension = 768  # 默认维度，根据模型输出调整
        self.index = get_faiss_index(self.dimension)

        # 存储诗歌元数据
        self.poems = []

        # 加载现有数据
        self._load_existing_data()

    def _load_existing_data(self):
        """加载现有数据"""
        index_path = self.db_path / "index.faiss"
        poems_path = self.db_path / "poems.json"

        if index_path.exists() and poems_path.exists():
            try:
                # 加载向量索引
                self.index = load_faiss_index(str(index_path))

                # 加载诗歌元数据
                with open(poems_path, "r", encoding="utf-8") as f:
                    self.poems = json.load(f)

                print(f"已加载 {len(self.poems)} 首诗歌的向量数据")
                print(f"向量索引文件: {index_path.absolute()}")
                print(f"诗歌元数据文件: {poems_path.absolute()}")
            except Exception as e:
                print(f"加载向量数据失败: {e}")

    def _save_data(self):
        """保存数据"""
        try:
            index_path = self.db_path / "index.faiss"
            poems_path = self.db_path / "poems.json"

            # 保存向量索引
            save_faiss_index(self.index, str(index_path))

            # 保存诗歌元数据
            with open(poems_path, "w", encoding="utf-8") as f:
                json.dump(self.poems, f, ensure_ascii=False, indent=2)

            print(f"已保存向量数据:")
            print(f"向量索引文件: {index_path.absolute()}")
            print(f"诗歌元数据文件: {poems_path.absolute()}")
        except Exception as e:
            print(f"保存向量数据失败: {e}")

    def add_poem(self, poem: str, metadata: Dict[str, Any] = None):
        """添加诗歌到向量数据库

        Args:
            poem (str): 诗歌内容
            metadata (Dict[str, Any], optional): 诗歌元数据
        """
        if metadata is None:
            metadata = {}

        # 生成诗歌向量
        vector = self.model.encode([poem])[0]

        # 添加到向量索引
        self.index.add(np.array([vector], dtype=np.float32))

        # 保存诗歌元数据
        poem_data = {"id": len(self.poems), "content": poem, "metadata": metadata}
        self.poems.append(poem_data)

        # 保存数据
        self._save_data()

        return poem_data["id"]

    def search_similar_poems(
        self, query: str, k: int = 5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """搜索相似诗歌

        Args:
            query (str): 查询文本
            k (int): 返回结果数量

        Returns:
            List[Tuple[Dict[str, Any], float]]: 相似诗歌列表，每个元素为(诗歌数据, 相似度)
        """
        # 生成查询向量
        query_vector = self.model.encode([query])[0]

        # 搜索相似向量
        distances, indices = self.index.search(
            np.array([query_vector], dtype=np.float32), k
        )

        # 返回结果
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.poems):
                # 计算相似度（将距离转换为相似度）
                similarity = 1 / (1 + distances[0][i])
                results.append((self.poems[idx], similarity))

        return results

    def get_poem_by_id(self, poem_id: int) -> Dict[str, Any]:
        """根据ID获取诗歌

        Args:
            poem_id (int): 诗歌ID

        Returns:
            Dict[str, Any]: 诗歌数据
        """
        if 0 <= poem_id < len(self.poems):
            return self.poems[poem_id]
        return None

    def get_all_poems(self) -> List[Dict[str, Any]]:
        """获取所有诗歌

        Returns:
            List[Dict[str, Any]]: 诗歌列表
        """
        return self.poems
