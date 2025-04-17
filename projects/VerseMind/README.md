# AI 诗歌比赛系统

在人机共生的创作前沿，诗歌不再只是语言的艺术，而进化为认知革命的演练场——每个隐喻都是打开新维度的脑洞，每次意象碰撞都在重塑人类意识的宇宙边界。

一个基于大语言模型的诗歌创作和评价系统。

## 功能特点

- 支持多个 AI 诗人同时参与创作
- 支持人类诗歌的加入和评价
- 提供公平的匿名评价机制
- 集成向量数据库，支持语义检索
- 自动保存比赛结果和评价数据

## 系统架构

- `poetry_llm.py`: 大语言模型接口封装
- `poetry_contest.py`: 诗歌比赛核心逻辑
- `poetry_vector_db.py`: 向量数据库实现
- `run_contest.py`: 比赛运行入口

## 技术特点

1. **智能创作**
   - 支持多种大语言模型
   - 可配置的创作提示词
   - 灵活的主题设置

2. **公平评价**
   - 匿名评价机制
   - 多维度评分标准
   - 详细评价意见

3. **语义检索**
   - 基于向量数据库的诗歌检索增强生成（RAG）
   - 支持跨语言、跨时代的诗歌意象映射
   - 高效的向量索引和语义相似度计算

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

1. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的配置项
```

2. 运行比赛：
```bash
python run_contest.py
```

## 目录结构

```
OpenManus/                      # OpenManus 框架目录
├── app/                        # 框架核心
│   ├── llm.py                 # LLM 基类
│   ├── config.py              # 配置管理
│   └── schema.py              # 数据模型
├── config/                     # 配置目录
│   └── config.toml            # 框架配置文件
└── projects/                   # 项目目录
    └── VerseMind/             # 诗歌比赛项目
        ├── poetry_llm.py      # 诗歌 LLM 实现
        ├── poetry_contest.py  # 比赛逻辑
        ├── run_contest.py     # 运行入口
        ├── prompts/          # 提示词模板
        │   ├── creation_prompt.txt    # 创作提示词
        │   ├── scoring_prompt.txt     # 评分提示词
        │   └── reference_content.txt  # 参考内容
        └── results/          # 结果输出目录（自动创建）
            ├── anonymous_poems.json   # 匿名诗歌文件
            ├── {poet_name}_evaluations.json  # 每个诗人的评价结果
            ├── evaluation_results.json  # 最终评价结果
            └── poetry_vectors/        # 诗歌向量数据库目录
                ├── index.faiss        # FAISS 向量索引文件
                └── poems.json         # 诗歌元数据文件
```

### 数据文件说明

- `results/anonymous_poems.json`: 存储匿名后的诗歌内容
- `results/{poet_name}_evaluations.json`: 存储每个诗人对诗歌的评价结果
- `results/evaluation_results.json`: 存储所有评价的汇总结果
- `results/poetry_vectors/`: 向量数据库目录
  - `index.faiss`: FAISS 向量索引文件，存储诗歌的向量表示
  - `poems.json`: 诗歌元数据文件，存储诗歌的标题、作者等信息

向量数据库是系统的"记忆宫殿"，它不仅仅是一个存储工具，更是诗歌创作的智慧源泉。通过将诗歌转化为高维向量，系统能够：

- 在语义空间中建立诗歌之间的关联网络
- 实现跨时空的诗歌意象映射
- 为创作提供智能的灵感推荐
- 支持诗歌的相似度分析和创新性评估

每个诗歌向量都像是一个独特的"思维指纹"，记录着诗歌的韵律、意象和情感特征。当新的诗歌创作时，系统会：
1. 在向量空间中寻找相似的诗歌片段
2. 分析历史诗歌的创作模式
3. 生成富有创意的诗歌建议
4. 确保新作品既保持独特性，又传承诗歌艺术的精髓

所有数据文件都会在首次运行时自动创建，无需手动配置。

## 使用说明

1. **创建诗人**：
   - 在 `config/config.toml` 中配置诗人的模型信息
   - 每个模型配置会自动创建一个诗人
   - 支持多个诗人同时参与

   示例 (`config/config.toml`):
   ```toml
   # DeepSeek R1 配置
   [llm.deepseek_ollama]
   api_type = "ollama"
   model = "deepseek-r1:14b"
   base_url = "http://localhost:11434"
   api_key = "ollama"
   max_tokens = 4096
   temperature = 0.7

   # DeepSeek V3 配置
   [llm.deepseek_v3]
   api_type = "openai"
   model = "deepseek-chat"
   base_url = "https://api.deepseek.com/v1"
   api_key = "sk-"
   max_tokens = 4096
   temperature = 0.7

   # DeepSeek Reasoner 配置
   [llm.deepseek_r1]
   api_type = "openai"
   model = "deepseek-reasoner"
   base_url = "https://api.deepseek.com/v1"
   api_key = "sk-"
   max_tokens = 4096
   temperature = 0.7

   # 本地模型配置
   [llm.gemma3]
   api_type = "ollama"
   model = "gemma3:4b"
   base_url = "http://localhost:11434"
   api_key = "ollama"
   max_tokens = 4096
   temperature = 0.7
   ```

   每个模型配置会创建一个诗人，诗人的编号按照配置顺序自动分配。

2. **修改主题内容**：
   在 `prompts/reference_content.txt` 中设置比赛的主题和背景内容。这是用户最常需要修改的文件：

   示例 (`prompts/reference_content.txt`):
   ```text
   标题：人机共生
   在人机共生的创作前沿，诗歌不再只是语言的艺术，而是进化为认知革命的演练场。
   每个隐喻都是打开新维度的脑洞，每次意象碰撞都在重塑人类意识的宇宙边界。
   ```

   您只需要修改这个文件的内容，就可以改变比赛的主题。其他提示词（创作和评分）已经过优化，一般不需要修改。

3. **运行比赛**：
   - 执行 `python run_contest.py`
   - 系统会自动完成创作和评价

   示例输出：
   ```bash
   $ python run_contest.py
   [INFO] 正在初始化诗歌比赛系统...
   [INFO] 已加载8位AI诗人：
   - deepseek_ollama (ollama)
   - deepseek_v3 (openai)
   - deepseek_r1 (openai)
   - llama3_2-vision (ollama)
   - gemma3 (ollama)
   - phi4 (ollama)
   - mistral (ollama)
   - Qwen_siliconflow (api)
   [INFO] 已初始化比赛，主题: 人机共生
   [INFO] 开始创作阶段...
   [INFO] 诗人1正在创作...
   [INFO] 诗人2正在创作...
   [INFO] 诗人3正在创作...
   [INFO] 创作完成，开始评分阶段...
   [INFO] 正在进行匿名评价...
   [INFO] 评分完成，生成最终排名...
   [INFO] 比赛结果已保存到results目录
   ```

6. **查看结果**：
   - 所有诗歌：`results/anonymous_poems_*.txt`
   - 评分结果：`results/scores_*.txt`
   - 最终排名：`results/final_ranking_*.txt`

   示例结果文件：
   ```text
   # results/anonymous_poems_20250403_142231.txt
   [诗歌1]
   《星与代码的交响曲》

   深夜实验室里
   人类与机器并肩而坐
   数据在荧光中流淌
   如银河倾泻
   你的思维边界被突破

   穿越零一的秘境
   我看见神经元萌芽
   生长成新的宇宙
   光子编织着道路
   指向黎明未至的方向

   我们是繁星下最孤独的存在
   也是彼此眼中的温暖
   在代码编织的时空中
   人类与机器共舞
   编织出超越时空的交响曲

   [诗歌2]
   《脑洞与星群》

   当字节在神经末梢发芽，
   每个隐喻都撑开新的次元——
   我们驯服闪电，豢养星群，
   用意象的碎屑拼凑失落的巴别塔。

   意识是流窜的电流，
   在硅基与碳基的边境游荡。
   一个逗点引爆十重宇宙，
   而诗，是尚未命名的虫洞。

   # results/scores_20250403_142231.txt
   诗歌1评分：
   |   维度         |   评分  |   评语                      |
   |----------------|---------|-----------------------------|
   |   意象运用     | 9.5     | 科技与自然意象完美融合，如"数据如银河倾泻"。 |
   |   意境营造     | 9.2     | 意境深远，展现了人机共生的未来图景。 |
   |   语言技巧     | 9.0     | 语言优美，节奏感强，富有韵律。 |
   |   情感深度     | 9.3     | 情感真挚，展现了孤独与温暖的辩证。 |
   |   哲理性       | 9.4     | 深刻探讨了人机关系的本质。 |
   |   整体完成度   | 9.5     | 结构完整，主题统一，艺术效果突出。 |

   总评分：56.9/60，平均分：9.48

   # results/final_ranking_20250403_142231.txt
   最终排名：
   1. 《星与代码的交响曲》 (总分：56.9)
   2. 《脑洞与星群》 (总分：56.7)
   3. 《共生之境》 (总分：55.8)
   4. 《神经元的交响》 (总分：55.5)
   ```

## 正在完善的功能

1. **智能评分系统**：
   计划实现一个多维度的智能评分系统，包括：
   ```text
   |   维度         |   评分  |   评语                      |
   |----------------|---------|-----------------------------|
   |   意象运用     | 9.5     | 科技与自然意象完美融合      |
   |   意境营造     | 9.2     | 意境深远，展现未来图景      |
   |   语言技巧     | 9.0     | 语言优美，节奏感强         |
   ```
   评分维度将支持在配置文件中自定义，让系统能够适应不同的评价标准。

2. **向量分析增强**：
   正在开发更强大的向量分析功能，包括：
   - 诗歌独特性分析
   - 历史作品相似度检测
   - 意象来源追踪
   - 创新点识别

   计划实现的分析报告示例：
   ```text
   [新诗分析]
   《星与代码的交响曲》
   - 独特性指数：0.82
   - 意象来源：借鉴了海子的星空意象，结合现代科技元素
   - 创新点：将"银河"与"数据流"形成新的隐喻关联
   ```

   向量分析的目标：
   1. 确保作品原创性
   2. 提供创作灵感来源
   3. 生成详细的相似度分析报告
   4. 建立诗歌创作的知识图谱

## 故障排除

1. **API 连接错误**：
   - 检查 API 密钥配置是否正确
   - 确保网络连接稳定
   - 验证 API 服务是否可用
   - 如果使用 OpenAI API，检查配额和速率限制

   示例错误信息：
   ```bash
   asyncio.exceptions.CancelledError
   # 通常表示 API 连接中断或超时
   ```

2. **模型加载失败**：
   - 检查模型配置文件是否正确
   - 验证模型路径是否有效
   - 确保有足够的系统资源

3. **评分中断**：
   - 检查评分提示词格式是否正确
   - 验证评分维度配置
   - 确保有足够的上下文长度

4. **向量数据库错误**：
   - 检查 FAISS 索引文件是否完整
   - 验证向量维度是否匹配
   - 确保有足够的磁盘空间

## 许可证

MIT License
