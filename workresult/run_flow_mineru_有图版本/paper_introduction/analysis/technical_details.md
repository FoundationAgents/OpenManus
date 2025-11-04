# INFNet 技术细节分析

## 🔧 架构设计详解

### 特征表示与令牌化

#### 1. 分类特征令牌
- **输入**: 用户ID、物品ID、静态属性、分桶连续变量
- **嵌入表**: $\mathbf{E}_j^{\mathrm{cat}} \in \mathbb{R}^{V_j \times d}$
- **令牌生成**: $\mathbf{c}_j = \mathbf{E}_j^{\mathrm{cat}}[v_j] \in \mathbb{R}^d$
- **令牌矩阵**: $\mathbf{C} = [\mathbf{c}_1 \| \ldots \| \mathbf{c}_M]^\top \in \mathbb{R}^{M \times d}$

#### 2. 序列特征令牌
- **行为分组**: F个动作特定序列（点击、点赞、播放等）
- **统一序列**: $\mathbf{S} = [\mathsf{s}_{1,1}, \ldots, \mathsf{s}_{F,n_F}] \in \mathbb{R}^{L \times d}$
- **序列长度**: $L = \sum_{a=1}^F n_a$

#### 3. 任务特征令牌
- **真实任务令牌**: $\mathbf{T} \in \mathbb{R}^{N_{\mathrm{task}} \times d}$（可学习向量）
- **共享任务令牌**: $\tilde{\mathbf{T}} \in \mathbb{R}^{N_s \times d}$（跨任务知识）

### 代理令牌生成

#### 分类代理令牌
- **全局上下文压缩**: $\tilde{\mathbf{C}} = \mathrm{Reshape}(\phi_{\mathrm{cat}}(\mathrm{Flatten}(\mathbf{C}))) \in \mathbb{R}^{m \times d}$
- **优势**: 在相同令牌预算下保留更多信息

#### 序列代理令牌
- **类型内池化**: $\tilde{\mathbf{S}} = \left[\sum_{t=1}^{n_1} \boldsymbol{\phi}_{\mathrm{seq}}(\mathsf{s}_{1,t}); \ldots; \sum_{t=1}^{n_F} \boldsymbol{\phi}_{\mathrm{seq}}(\mathsf{s}_{F,t})\right] \in \mathbb{R}^{F \times d}$
- **优势**: 保持每类型时间语义

## 🔄 信息流机制

### 异质特征交互

#### 交叉注意力定义
$$\mathrm{CA}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \mathrm{softmax}\left(\frac{\mathbf{Q}\mathbf{W}_Q(\mathbf{K}\mathbf{W}_K)^\top}{\sqrt{d_k}}\right)(\mathbf{V}\mathbf{W}_V)$$

#### 信息流向分类
- **查询**: 分类代理令牌 $\tilde{\mathbf{C}}^{(l)}$
- **键值**: 序列令牌 $\mathbf{S}^{(l)}$ + 任务令牌 $\mathbf{T}^{(l)}$
- **输出**: $\tilde{\mathbf{C}}^{(l+1)} = \mathbf{CA}(\tilde{\mathbf{C}}^{(l)}, \mathbf{S}^{(l)}, \mathbf{S}^{(l)}) + \mathbf{CA}(\tilde{\mathbf{C}}^{(l)}, \mathbf{T}^{(l)}, \mathbf{T}^{(l)})$

#### 信息流向序列
- **查询**: 序列代理令牌 $\tilde{\mathbf{S}}^{(l)}$
- **键值**: 分类令牌 $\mathbf{C}^{(l)}$ + 任务令牌 $\mathbf{T}^{(l)}$
- **输出**: $\tilde{\mathbf{S}}^{(l+1)} = \mathrm{CA}(\tilde{\mathbf{S}}^{(l)}, \mathbf{C}^{(l)}, \mathbf{C}^{(l)}) + \mathrm{CA}(\tilde{\mathbf{S}}^{(l)}, \mathbf{T}^{(l)}, \mathbf{T}^{(l)})$

#### 信息流向任务
- **任务代理**: $\tilde{\mathbf{T}}^{(l+1)} = \mathbf{CA}(\tilde{\mathbf{T}}^{(l)}, \mathbf{C}^{(l)}, \mathbf{C}^{(l)}) + \mathbf{CA}(\tilde{\mathbf{T}}^{(l)}, \mathbf{S}^{(l)}, \mathbf{S}^{(l)})$
- **真实任务**: $\hat{\mathbf{T}}^{(l+1)} = \mathbf{CA}(\mathbf{T}^{(l)}, \mathbf{C}^{(l)}, \mathbf{C}^{(l)}) + \mathbf{CA}(\mathbf{T}^{(l)}, \mathbf{S}^{(l)}, \mathbf{S}^{(l)})$

### 同质特征交互

#### 代理门控单元(PGU)
$$\operatorname{PGU}(\mathbf{X}, \tilde{\mathbf{X}}) = \mathbf{X} \odot \sigma{\big(} \operatorname{MLP}(\tilde{\mathbf{X}}_f) {\big)}$$

#### 类型内精炼
- **分类令牌**: $\mathbf{C}^{(l+1)} = \mathrm{PGU}(\mathbf{C}^{(l)}, \tilde{\mathbf{C}}^{(l)})$
- **序列令牌**: $\mathbf{S}^{(l+1)} = \mathrm{PGU}(\mathbf{S}^{(l)}, \tilde{\mathbf{S}}^{(l)})$
- **任务令牌**: $\mathbf{T}^{(l+1)} = \mathrm{PGU}(\hat{\mathbf{T}}^{(l+1)}, \tilde{\mathbf{T}}^{(l)})$

## ⚙️ 优化与训练

### 多任务预测头
- **任务特定MLP**: $\hat{y}_i = \sigma(\mathrm{MLP}_i(\mathbf{T}_i^{(N)}))$
- **架构共享**: 跨任务共享架构，参数独立

### 损失函数
- **加权多任务损失**: $\mathcal{L} = \sum_{i=1}^{N_{\mathrm{task}}} \lambda_i \mathcal{L}_i(\hat{y}_i, y_i)$
- **二元交叉熵**: $\mathcal{L}_i(\hat{y}_i, y_i) = -[y_i \log \hat{y}_i + (1 - y_i) \log(1 - \hat{y}_i)]$

### 训练配置
- **批量大小**: 4096
- **嵌入维度**: {8, 16, 32, 64, 96, 128}
- **优化器**: Adam/Adagrad
- **学习率**: {1e-4, 3e-4, 1e-3}
- **正则化**: L2 {0, 1e-7, 1e-6, 1e-5}
- **Dropout**: {0.0, 0.1, 0.2}

## 📈 实验细节

### 评估指标
- **AUC**: 接收者操作特征曲线下面积
- **gAUC**: 用户级平均AUC，反映个性化质量

### 数据集统计

| 数据集 | 用户数 | 物品数 | 交互数 | 分类特征 | 序列特征 | 任务数 |
|--------|--------|--------|--------|-----------|-----------|--------|
| KuaiRand-Pure | 27,285 | 7,551 | 1,436,609 | 89 | 28 | 3 |
| KuaiRand-27K | 27,285 | 32,038,725 | 322,278,385 | 89 | 28 | 3 |
| QB-Video | 34,240 | 130,637 | 1,726,886 | 6 | 12 | 4 |

### 性能对比

#### 特征交互模型对比
- **FM**: 二阶交互，轻量级基线
- **DIN**: 目标感知注意力
- **DIEN**: 兴趣演化网络
- **DCNv2**: 改进的深度交叉网络
- **GDCN**: 门控交叉层
- **WuKong**: 任意阶交互扩展
- **HSTU**: 层次序列转换

#### 多任务模型对比
- **Shared-Bottom**: 共享编码器
- **MMoE**: 多门混合专家
- **OMoE**: 单门混合专家
- **PLE**: 渐进层提取
- **STEM**: 共享和任务特定嵌入

## 🔍 消融研究结果

### 消融变体影响
- **w/o1 (移除任务令牌)**: 普遍性能下降，特别是分享任务(+0.0344 AUC)
- **w/o2 (移除同质交互)**: 序列相关任务显著受损
- **w/o3 (移除异质交互)**: 大多数任务最大损失

### 代理令牌数量影响
- **分类/序列代理**: 2→4个提升性能，8个导致过参数化
- **共享任务令牌**: 1→2个提升性能，3个带来递减回报
- **最优配置**: 分类/序列代理=4，共享任务令牌=2

## 🎯 技术优势总结

### 计算效率
- **代理令牌**: 限制注意力扇出，避免二次复杂度
- **PGU设计**: 复杂度与令牌长度解耦
- **层次交互**: 全局+局部信息处理

### 任务感知
- **早期条件化**: 任务信息在特征交互阶段注入
- **混合表示**: 任务特定+共享令牌
- **负迁移缓解**: 任务边界清晰化

### 工业适用性
- **延迟友好**: 紧凑架构，低推理延迟
- **内存高效**: 代理令牌减少内存占用
- **部署稳定**: 流式训练，版本对齐