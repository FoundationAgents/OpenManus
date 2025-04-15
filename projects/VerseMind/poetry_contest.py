"""AI诗歌比赛核心逻辑"""

import json
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from logger_config import get_logger
from poetry_llm import PoetryLLM
from poetry_vector_db import PoetryVectorDB


# 忽略 PyTorch flash attention 警告
warnings.filterwarnings(
    "ignore", message=".*Torch was not compiled with flash attention.*"
)

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class Poet:
    """诗人信息"""

    name: str
    model_name: str
    model: PoetryLLM
    poems: List[Dict] = field(default_factory=list)
    evaluations: List[Dict] = field(default_factory=list)


@dataclass
class AIPoetryContest:
    """AI诗歌比赛类"""

    theme: str
    poets: List[Poet]
    results_dir: Path
    reference_content: str = ""
    creation_prompt: str = ""
    scoring_prompt: str = ""
    anonymous_poems: List[Dict] = field(default_factory=list)
    human_poem: Optional[Dict] = None
    vector_db: Optional[PoetryVectorDB] = None

    def __post_init__(self):
        """初始化后的处理"""
        # 创建结果目录
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # 从主题中移除"标题："前缀
        theme_content = self.theme.replace("标题：", "").strip()
        logger.info(f"\n已初始化比赛，主题: {theme_content}\n")

        # 检查每个诗人的模型配置
        for i, poet in enumerate(self.poets, 1):
            # 添加详细的模型配置日志
            logger.info(f"{i}. {poet.name}:")
            logger.info(f"   - 模型名称: {poet.model_name}")
            logger.info(f"   - 模型配置: {poet.model.llm_config}")
            if poet.model_name == "default":
                logger.warning(f"   ⚠️ 警告: 发现默认模型名称 'default'，这可能导致问题")
                logger.warning(f"   建议: 请在配置文件中使用实际的模型名称（如 'gemma3:4b'）替换 'default'")

        logger.info(f"\n共有 {len(self.poets)} 位诗人参赛\n")

        # 初始化参考内容和提示词
        self.reference_content = ""
        self.creation_prompt = ""
        self.scoring_prompt = ""

        # 初始化向量数据库
        vector_db_path = self.results_dir / "poetry_vectors"
        self.vector_db = PoetryVectorDB(db_path=str(vector_db_path))
        logger.info(f"已初始化诗歌向量数据库，存储路径: {vector_db_path.absolute()}")

    async def run(self) -> bool:
        """运行比赛

        Returns:
            bool: 比赛是否成功完成
        """
        if not self.poets:
            logger.error("没有可用的诗人，比赛无法进行")
            return False

        try:
            # 检查模型配置
            logger.info("\n========== 模型配置检查 ==========")
            for poet in self.poets:
                logger.info(f"\n检查 {poet.name} 的模型配置:")
                logger.info(f"- 模型名称: {poet.model_name}")

                # 检查是否使用了default
                if poet.model_name == "default":
                    logger.error(f"⚠️ 错误: {poet.name} 使用了默认模型名称 'default'")
                    logger.error("这会导致模型调用失败，请修改配置文件使用实际的模型名称")
                    return False
            logger.info("\n================================\n")

            # 读取参考内容
            reference_file = Path(__file__).parent / "prompts" / "reference_content.txt"
            try:
                with open(reference_file, "r", encoding="utf-8") as f:
                    self.reference_content = f.read()

                # 断言参考内容不为空
                assert self.reference_content, "参考内容不能为空"
            except Exception as e:
                logger.error(f"读取参考内容文件失败: {str(e)}")
                return False

            # 读取创作提示词
            creation_prompt_file = (
                Path(__file__).parent / "prompts" / "creation_prompt.txt"
            )
            try:
                with open(creation_prompt_file, "r", encoding="utf-8") as f:
                    self.creation_prompt = f.read()

                # 断言创作提示词不为空
                assert self.creation_prompt, "创作提示词不能为空"
            except Exception as e:
                logger.error(f"读取创作提示词文件失败: {str(e)}")
                return False

            # 读取评分提示词
            scoring_prompt_file = (
                Path(__file__).parent / "prompts" / "scoring_prompt.txt"
            )
            try:
                with open(scoring_prompt_file, "r", encoding="utf-8") as f:
                    self.scoring_prompt = f.read()

                # 断言评分提示词不为空
                assert self.scoring_prompt, "评分提示词不能为空"
            except Exception as e:
                logger.error(f"读取评分提示词文件失败: {str(e)}")
                return False

            # 创作阶段
            logger.info("开始创作阶段...")
            for poet in self.poets:
                try:
                    # 格式化提示词
                    prompt = self.creation_prompt.replace(
                        "{theme}", self.reference_content
                    )

                    # 断言格式化后的提示词不为空
                    assert prompt, "格式化后的创作提示词不能为空"

                    # 确保提示词包含参考内容
                    if "参考内容：" not in prompt:
                        prompt = f"{prompt}\n\n参考内容：\n{self.reference_content}"

                    # 创建诗歌
                    logger.info(f"{poet.name}（{poet.model_name}）正在创作...")
                    logger.info(f"使用创作提示词文件: {creation_prompt_file}")
                    poem = await poet.model.create_poem(self.theme, prompt)

                    if poem:
                        # 保存诗歌
                        poem_info = {
                            "id": len(self.anonymous_poems) + 1,
                            "poet": poet.name,
                            "model": poet.model_name,
                            "content": poem,
                        }
                        self.anonymous_poems.append(poem_info)
                        poet.poems.append(poem_info)
                        logger.info(f"{poet.name}（{poet.model_name}）创作成功")

                        # 添加到向量数据库
                        metadata = {
                            "poet": poet.name,
                            "model": poet.model_name,
                            "theme": self.theme,
                            "timestamp": datetime.now().isoformat(),
                        }
                        self.vector_db.add_poem(poem, metadata)
                        logger.info(f"已将诗歌添加到向量数据库: {self.vector_db.db_path}")
                    else:
                        logger.error(f"{poet.name}（{poet.model_name}）创作失败")
                except Exception as e:
                    logger.error(f"{poet.name}（{poet.model_name}）创作出错: {e}")
                    continue

            if not self.anonymous_poems:
                logger.error("所有诗人都创作失败，比赛终止")
                return False

            # 评价阶段
            logger.info("开始评价阶段...")

            # 检查是否存在人类诗歌文件，如果存在则添加到评价中
            human_poem_path = self.results_dir / "human_poem_example.txt"
            human_poem_added = False
            if human_poem_path.exists():
                try:
                    # 读取人类诗歌文件
                    logger.info(f"读取人类诗歌文件: {human_poem_path}")
                    with open(human_poem_path, "r", encoding="utf-8") as f:
                        human_poem = f.read()

                    # 断言人类诗歌不为空
                    assert human_poem, "人类诗歌不能为空"

                    # 添加人类诗歌到匿名诗歌文件
                    if self.add_human_poem(human_poem):
                        logger.info(f"人类诗歌已添加到评价中: {human_poem_path}")
                        human_poem_added = True
                    else:
                        logger.error("添加人类诗歌失败")
                except Exception as e:
                    logger.error(f"添加人类诗歌时出错: {e}")

            # 断言人类诗歌是否成功添加
            if human_poem_path.exists():
                assert human_poem_added, "人类诗歌文件存在但未能成功添加到评价中"

            for poet in self.poets:
                for poem_info in self.anonymous_poems:
                    try:
                        # 断言诗歌内容不为空
                        assert poem_info["content"], "诗歌内容不能为空"

                        # 格式化评分提示词
                        formatted_scoring_prompt = self.scoring_prompt.replace(
                            "{theme}", self.reference_content
                        ).replace("{poem}", poem_info["content"])

                        # 断言格式化后的评分提示词不为空
                        assert formatted_scoring_prompt, "格式化后的评分提示词不能为空"

                        # 评价诗歌
                        logger.info(f"{poet.name}（{poet.model_name}）正在评价...")
                        logger.info(f"使用评分提示词文件: {scoring_prompt_file}")

                        # 检查是否是人类诗歌
                        is_human_poem = poem_info.get("model") == "human"
                        if is_human_poem:
                            logger.info(
                                f"{poet.name}（{poet.model_name}）正在评价人类诗歌，ID: {poem_info['id']}"
                            )

                        # 使用格式化后的评分提示词，并设置 is_human_poem 参数
                        evaluation = await poet.model.evaluate_poem(
                            poem_info["content"],
                            self.theme,
                            is_human_poem=is_human_poem,
                            prompt=formatted_scoring_prompt,
                        )

                        if evaluation:
                            # 保存评价结果
                            evaluation_info = {
                                "poem_id": poem_info["id"],
                                "poet": poet.name,
                                "model": poet.model_name,
                                "score": evaluation.get("total_score", 0),
                                "dimensions": evaluation.get("dimensions", {}),
                                "comment": evaluation.get("comment", "未提供评论"),
                            }
                            poet.evaluations.append(evaluation_info)
                            logger.info(
                                f"{poet.name}（{poet.model_name}）完成了对诗歌 {poem_info['id']} 的评价"
                            )

                            # 只显示模型返回的维度
                            if evaluation.get("dimensions"):
                                for dimension, score in evaluation[
                                    "dimensions"
                                ].items():
                                    logger.info(f"{dimension}: {score}")
                        else:
                            logger.error(
                                f"{poet.name}（{poet.model_name}）评价诗歌 {poem_info['id']} 失败"
                            )
                    except Exception as e:
                        logger.error(f"{poet.name}（{poet.model_name}）评价诗歌出错: {e}")
                        continue

            # 显示向量数据库统计信息
            if self.vector_db:
                poems_count = len(self.vector_db.get_all_poems())
                db_path = self.vector_db.db_path.absolute()
                logger.info(f"向量数据库统计: 共存储 {poems_count} 首诗歌，存储路径: {db_path}")

                # 显示一些示例查询
                if poems_count > 0:
                    # 使用主题作为查询
                    similar_poems = self.vector_db.search_similar_poems(self.theme, k=3)
                    if similar_poems:
                        logger.info("向量数据库示例查询 - 与主题相似的诗歌:")
                        for i, (poem, similarity) in enumerate(similar_poems):
                            logger.info(
                                f"  相似度 {similarity:.2f}: {poem['content'][:50]}..."
                            )
            else:
                logger.warning("向量数据库未初始化，无法显示统计信息")

            # 显示最终排名
            await self._show_final_ranking()

            # 添加RAG分析报告
            logger.info("\n========== RAG分析报告 ==========")
            for i, poem in enumerate(self.anonymous_poems):
                logger.info(f"\n[诗歌{i+1}分析]")
                logger.info(f"标题：{poem['content'][:50]}...")

                # 1. 检索相似诗歌
                similar_poems = self.vector_db.search_similar_poems(
                    poem["content"], k=2
                )
                if similar_poems:
                    # 计算独特性
                    avg_similarity = sum(score for _, score in similar_poems) / len(
                        similar_poems
                    )
                    uniqueness = 1 - avg_similarity
                    logger.info(f"独特性指数：{uniqueness:.2f}")

                    # 展示意象来源
                    for similar_poem, similarity in similar_poems:
                        if similarity > 0.5:  # 只显示相似度较高的
                            shared_words = set(poem["content"]) & set(
                                similar_poem["content"]
                            )
                            if shared_words:
                                logger.info(f"共享意象：{''.join(shared_words)}")

                # 2. 分析创新点
                if uniqueness > 0.7:
                    logger.info("创新亮点：意象独特，形式创新")
                elif uniqueness > 0.5:
                    logger.info("创新亮点：在传统意象基础上有所发展")
                else:
                    logger.info("建议：可以尝试更独特的表达方式")

            logger.info("\n================================")

            # 保存比赛结果
            try:
                # 保存匿名诗歌
                anonymous_file = self.results_dir / "anonymous_poems.json"
                with open(anonymous_file, "w", encoding="utf-8") as f:
                    json.dump(self.anonymous_poems, f, ensure_ascii=False, indent=2)
                logger.info(f"已创建匿名诗歌文件: {anonymous_file}")

                # 断言匿名诗歌文件包含所有诗歌，包括人类诗歌（如果存在）
                with open(anonymous_file, "r", encoding="utf-8") as f:
                    saved_poems = json.load(f)
                assert len(saved_poems) == len(
                    self.anonymous_poems
                ), "保存的匿名诗歌数量与内存中的不一致"
                if human_poem_added:
                    assert any(
                        poem["model"] == "human" for poem in saved_poems
                    ), "保存的匿名诗歌中不包含人类诗歌"
            except Exception as e:
                logger.error(f"创建匿名诗歌文件失败: {e}")
                return False

            # 保存评价结果
            try:
                # 保存每个诗人的评价结果
                for poet in self.poets:
                    if poet.evaluations:
                        evaluation_file = (
                            self.results_dir / f"{poet.name}_evaluations.json"
                        )
                        with open(evaluation_file, "w", encoding="utf-8") as f:
                            json.dump(poet.evaluations, f, ensure_ascii=False, indent=2)
                        logger.info(f"已保存评价结果: {evaluation_file}")
            except Exception as e:
                logger.error(f"保存评价结果失败: {e}")
                return False

            logger.info(f"比赛结果已保存到目录: {self.results_dir}")
            return True

        except Exception as e:
            logger.error(f"比赛运行出错: {str(e)}")
            return False

    async def _evaluate_poem(self, poem: str, poet: Poet) -> bool:
        """评估单首诗歌

        Args:
            poem: 要评估的诗歌
            poet: 评估的诗人

        Returns:
            bool: 是否评估成功
        """
        try:
            # 读取匿名诗歌文件
            anonymous_file = self.results_dir / "anonymous_poems.json"
            with open(anonymous_file, "r", encoding="utf-8") as f:
                anonymous_poems = json.load(f)

            # 检查是否已经评估过
            poem_id = None
            for p in anonymous_poems:
                if p["content"] == poem:
                    poem_id = p["id"]
                    break

            if not poem_id:
                logger.error(f"未找到诗歌: {poem[:50]}...")
                return False

            # 检查是否已经评估过
            if poem_id in poet.evaluations:
                logger.info(f"诗人 {poet.name} 已经评估过诗歌 {poem_id}")
                return True

            # 获取评分结果
            result = await poet.model.evaluate_poem(poem, self.theme)

            if not result:
                logger.error(f"诗人 {poet.name} 评估诗歌 {poem_id} 失败")
                return False

            # 保存评分结果
            poet.evaluations[poem_id] = result
            logger.info(f"诗人 {poet.name} 评估诗歌 {poem_id} 成功")
            return True

        except Exception as e:
            logger.error(f"评估诗歌时出错: {str(e)}")
            return False

    def announce_results(self) -> bool:
        """宣布比赛结果

        Returns:
            bool: 是否成功宣布结果
        """
        try:
            # 读取匿名诗歌文件
            anonymous_file = self.results_dir / "anonymous_poems.json"
            if not anonymous_file.exists():
                logger.error("匿名诗歌文件不存在")
                return False

            with open(anonymous_file, "r", encoding="utf-8") as f:
                json.load(f)

            # 计算每个诗人的平均得分
            poet_scores = {}
            for poet in self.poets:
                if poet.evaluations:
                    total_score = sum(e["score"] for e in poet.evaluations)
                    average_score = total_score / len(poet.evaluations)
                    poet_scores[poet.name] = average_score

            # 按得分排序
            sorted_poets = sorted(poet_scores.items(), key=lambda x: x[1], reverse=True)

            # 保存排名结果
            ranking_file = self.results_dir / "ranking.json"
            with open(ranking_file, "w", encoding="utf-8") as f:
                json.dump(sorted_poets, f, ensure_ascii=False, indent=2)

            # 显示向量数据库统计信息
            if self.vector_db:
                poems_count = len(self.vector_db.get_all_poems())
                db_path = self.vector_db.db_path.absolute()
                logger.info(f"向量数据库最终统计: 共存储 {poems_count} 首诗歌，存储路径: {db_path}")

                # 显示一些示例查询
                if poems_count > 0:
                    # 使用主题作为查询
                    similar_poems = self.vector_db.search_similar_poems(self.theme, k=3)
                    if similar_poems:
                        logger.info("向量数据库示例查询 - 与主题相似的诗歌:")
                        for i, (poem, similarity) in enumerate(similar_poems):
                            logger.info(
                                f"  相似度 {similarity:.2f}: {poem['content'][:50]}..."
                            )
            else:
                logger.warning("向量数据库未初始化，无法显示统计信息")

            return True

        except Exception as e:
            logger.error(f"宣布比赛结果失败: {str(e)}")
            return False

    def add_human_poem(self, poem_content: str) -> bool:
        """添加人类诗歌到匿名诗歌列表

        Args:
            poem_content: 诗歌内容

        Returns:
            bool: 是否成功添加
        """
        try:
            # 创建人类诗歌信息
            human_poem = {
                "id": len(self.anonymous_poems) + 1,
                "poet": "人类诗人",
                "model": "human",
                "content": poem_content,
            }

            # 添加到匿名诗歌列表
            self.anonymous_poems.append(human_poem)

            # 添加到向量数据库
            if self.vector_db:
                metadata = {
                    "poet": "人类诗人",
                    "model": "human",
                    "theme": self.theme,
                    "timestamp": datetime.now().isoformat(),
                }
                self.vector_db.add_poem(poem_content, metadata)
                logger.info("已将人类诗歌添加到向量数据库")

            # 断言人类诗歌已成功添加到匿名诗歌列表
            assert any(
                poem["model"] == "human" for poem in self.anonymous_poems
            ), "人类诗歌未能成功添加到匿名诗歌列表"

            logger.info(f"人类诗歌已添加到匿名诗歌列表，ID: {human_poem['id']}")
            return True
        except Exception as e:
            logger.error(f"添加人类诗歌失败: {e}")
            return False

    def _save_results(self) -> bool:
        """保存比赛结果

        Returns:
            bool: 是否保存成功
        """
        try:
            # 保存匿名诗歌
            with open(
                self.results_dir / "anonymous_poems.json", "w", encoding="utf-8"
            ) as f:
                json.dump(self.anonymous_poems, f, ensure_ascii=False, indent=2)

            # 保存评分结果
            evaluation_results = []
            for poet in self.poets:
                for evaluation in poet.evaluations:
                    evaluation_results.append(
                        {
                            "poem_id": evaluation["poem_id"],
                            "poet": poet.name,
                            "model": poet.model_name,
                            "score": evaluation["score"],
                            "dimensions": evaluation["dimensions"],
                            "comment": evaluation["comment"],
                        }
                    )

            with open(
                self.results_dir / "evaluation_results.json", "w", encoding="utf-8"
            ) as f:
                json.dump(evaluation_results, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error(f"保存结果时出错: {str(e)}")
            return False

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
        if not self.vector_db:
            logger.error("向量数据库未初始化")
            return []

        try:
            results = self.vector_db.search_similar_poems(query, k)
            logger.info(f"找到 {len(results)} 首相似诗歌")
            return results
        except Exception as e:
            logger.error(f"搜索相似诗歌时出错: {e}")
            return []

    async def _show_final_ranking(self) -> bool:
        """显示最终排名"""
        try:
            # 读取匿名诗歌文件
            anonymous_file = self.results_dir / "anonymous_poems.json"
            if not anonymous_file.exists():
                logger.error("匿名诗歌文件不存在")
                return False

            with open(anonymous_file, "r", encoding="utf-8") as f:
                json.load(f)

            # 计算每个诗人的平均得分
            poet_scores = {}
            for poet in self.poets:
                if poet.evaluations:
                    total_score = sum(e["score"] for e in poet.evaluations)
                    average_score = total_score / len(poet.evaluations)
                    poet_scores[poet.name] = average_score

            # 按得分排序
            sorted_poets = sorted(poet_scores.items(), key=lambda x: x[1], reverse=True)

            # 显示最终排名
            logger.info("\n========== 最终排名 ==========")
            for i, (name, score) in enumerate(sorted_poets, 1):
                logger.info(f"{i}. {name} - 得分: {score:.2f}")
            logger.info("\n================================")

            return True

        except Exception as e:
            logger.error(f"显示最终排名失败: {str(e)}")
            return False
