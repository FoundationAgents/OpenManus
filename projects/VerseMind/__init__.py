"""AI诗歌比赛包"""

from .poetry_contest import Poet, AIPoetryContest
from .poetry_llm import PoetryLLM
from .model_types import ModelType

__all__ = ['Poet', 'AIPoetryContest', 'PoetryLLM', 'ModelType']

# AI Poetry Contest Package 

"""
AI Poetry Contest package
""" 

"""VerseMind package initialization"""

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='faiss')
warnings.filterwarnings('ignore', message='Failed to load GPU Faiss*')

# 配置FAISS只使用CPU
import os
os.environ['FAISS_NO_GPU'] = '1' 