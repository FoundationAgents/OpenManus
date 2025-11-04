# INFNet: A Task-aware Information Flow Network for Large-Scale Recommendation Systems

Kaiyuan Li   
likaiyuan03@kuaishou.com   
Kuaishou Technology   
Beijing, China   
Dongdong Mao   
maodongdong@kuaishou.com   
Kuaishou Technology   
Beijing, China   
Yongxiang Tang   
tangyongxiang@kuaishou.com   
Kuaishou Technology   
Beijing, China   
Yanhua Cheng   
chengyanhua@kuaishou.com   
Kuaishou Technology   
Beijing, China   
Yanxiang Zeng   
zengyanxiang@kuaishou.com   
Kuaishou Technology   
Beijing, China   
Chao Wang   
wangchao32@kuaishou.com   
Kuaishou Technology   
Beijing, China   
Xialong Liu   
zhaolei16@kuaishou.com   
Kuaishou Technology   
Beijing, China   
Peng Jiang   
jiangpeng@kuaishou.com   
Kuaishou Technology   
Beijing, China

# Abstract

Feature interaction has long been a cornerstone of ranking models in large-scale recommender systems due to its proven effectiveness in capturing complex dependencies among features. However, existing feature interaction strategies face two critical challenges in industrial applications: (1) The vast number of categorical and sequential features makes exhaustive interaction computationally prohibitive, often resulting in optimization difficulties. (2) Realworld recommender systems typically involve multiple prediction objectives, yet most current approaches apply feature interaction modules prior to the multi-task learning layers. This late-fusion design overlooks task-specific feature dependencies and inherently limits the capacity of multi-task modeling.

To address these limitations, we propose the Information Flow Network (INFNeT), a task-aware architecture designed for largescale recommendation scenarios. INFNeT distinguishes features into three token types, categorical tokens, sequence tokens, and task tokens, and introduces a novel dual-flow design comprising heterogeneous and homogeneous alternating information blocks. For heterogeneous information flow, we employ a cross attention mechanism with proxy that facilitates efficient cross-modal token interaction with balanced computational cost. For homogeneous flow, we design type-specific Proxy Gated Units (PGUs) to enable fine-grained intra-type feature processing.

Extensive experiments on multiple offline benchmarks confirm that INFNET achieves state-of-the-art performance. Moreover, INFNET has been successfully deployed in a commercial online advertising system, yielding significant gains of $+ 1 . 5 8 7 \%$ in Revenue (REV) and $+ 1 . 1 5 5 \%$ in Click-Through Rate (CTR).

# CCS Concepts

Information systems Recommender systems.

# Keywords

CTR-prediction; feature interaction; multi-task

# ACM Reference Format:

Kaiyuan Li, Dongdong Mao, Yongxiang Tang, Yanhua Cheng, Yanxiang Zeng, Chao Wang, Xialong Liu, and Peng Jiang. 2018. INFNet: A Task-aware Information Flow Network for Large-Scale Recommendation Systems. In Proceedings of Make sure to enter the correct conference title from your rights confirmation emai (Conference acronym 'XX). ACM, New York, NY, USA, 10 pages. https://doi.org/XXXXXXX.XXXXXXX

# 1 Introduction

Short video platforms such as TikTok and Kwai have surged in popularity in recent years, offering users a broad spectrum of interactive behaviors, such as clicks, scrolls, comments, and likes, as illustrated in Fig. 1. In large-scale industrial recommenders, two trends are converging: an explosion in the scale and heterogeneity of high-dimensional features, and the growing adoption of multi-task learning (MTL) to optimize numerous business objectives [1, 3, 8, 13, 24, 33].

In practice, a single model may process thousands of sequential features, hundreds of sparse categorical fields, and simultaneously serve dozens of downstream tasks. User behavior is typically represented by a mix of categorical identifiers (e.g., user ID, item ID) and rich sequence signals (e.g., clicked or liked item histories, augmented with contextual attributes such as creators or topics) [6, 10, 17, 20, 31, 32]. At the same time, modern MTL recommenders aim to jointly optimize diverse objectives ranging from CTR and watch time to revenue within a single unified framework. This scale and diversity introduce a central challenge: the feature interaction stage must be (i) expressive enough to capture complex dependencies among heterogeneous inputs, (ii) efficient enough to satisfy strict latency and memory constraints, and (ii) sufficiently task-aware to mitigate negative transfer across objectives.

![](images/7b308ec2ed196de7db30c9c979964c076007ce8bd4844fa390a890c2851a757d.jpg)  
Figure 1: Massive features and multi-task at Kwai.

From the feature interaction perspective, early architectures such as FM [16] and DCN [22, 23] handle high-cardinality sparse features well through linear or cross-layer embeddings, but largely ignore sequential signals or compress them with coarse pooling. In production, sequence data are often truncated and flattened with side information, producing extremely large token sets directly feeding these into deep interaction layers incurs prohibitive costs, while aggressive pooling discards fine-grained temporal and contextual cues. Attention-based models such as DIN [35] and DIEN [34] alleviate this by applying target-aware attention to select relevant history for a single target item. However, their unidirectional, single-target design limits the modeling of broader cross-feature and cross-field dependencies, especially when multiple attributes jointly influence relevance.

From the MTL perspective, representative approaches such as MMoE [14], PLE [19], STEM [18], and HoME [24] introduce expertbased routing to separate shared and task-specific representations. Yet these methods typically perform feature interaction before task routing [29], meaning that the way two features interact is fixed regardless of which task is being optimized. This neglects task-aware dependencies during the interaction stage, leading to suboptimal representations and negative transfer. In large-scale deployments where objectives are optimized jointly under strict efficiency constraints, this misalignment can degrade both head and tail performance and slow convergence.

To address these challenges, we propose a Task-Aware Information Flow Network (INFNeT) that introduces task proxy tokens to inject task-awareness directly into the feature interaction stage. As shown in Fig. 2, all inputs are represented as categorical tokens, sequence tokens, and task tokens. We explicitly decouple the interaction process into (i) homogeneous flows, which perform within-type refinement using lightweight gated units, and (ii) heterogeneous flows, which enable cross-type exchange via cross attention with token proxies. In the latter, proxies condense large token sets into compact anchors, ensuring that cross-type complexity scales with the number of proxies rather than the raw token cardinality. Crucially, we introduce both task tokens and taskshared proxy tokens, allowing early-stage task-aware modulation of feature interactions while preserving cross-task generalization. This unified, structured information flow ensures that the target objective influences heterogeneous feature interactions from the very beginning of the pipeline.

![](images/47b00e4463fed28972c173dfaf1b75f01a940efe1224e9056897aa6a8d14f69f.jpg)  
Figure 2: (a) Prior multi-task pipelines typically perform feature interaction before routing; (b) INFNeT integrates taskaware interaction via task tokens and structured information flows.

This design yields a compact yet expressive backbone that (i) meets industrial efficiency budgets through low-overhead withintype refinement and proxy-based cross-type exchange, (ii) mitigates negative transfer via early-stage task conditioning, and (iii) unifies heterogeneous features into a single, structured interaction flow. Extensive experiments on both public and large-scale industrial datasets validate the effectiveness of INFNeT; in a production advertising system, INFNET achieves $+ 1 . 5 8 7 \%$ Revenue (REV) and $+ 1 . 1 5 5 \%$ Click-Through Rate (CTR) gains, while maintaining stable performance across traffic segments and favorable training and serving characteristics.

Contributions. Our key contributions are as follows:

We introduce INFNeT, a task-aware information flow architecture that unifies categorical, sequence, and task tokens in a single interaction space, enabling downstream objectives to guide feature interactions from the earliest stage rather than only after feature fusion.   
•We design a structured interaction mechanism with two complementary flows: (i) homogeneous flows using lightweight gated units for within-type refinement, and (ii) heterogeneous flows using cross attention with token proxies to enable fine-grained cross-type exchange without quadratic cost growth.   
We propose task-specific and task-shared proxy tokens that explicitly inject task-awareness into the interaction process, mitigating negative transfer across objectives while preserving beneficial cross-task generalization.   
•We demonstrate both algorithmic and system-level gains: consistent improvements on public and large-scale industrial datasets, with $+ 1 . 5 8 7 \%$ Revenue (REV) and $+ 1 . 1 5 5 \%$ CTR in a

production advertising system, all under strict latency and memory budgets.

# 2 Related Work

We review two closely related lines of research feature interaction and multi-task recommendation highlighting their evolution, design trade-offs, and limitations in industrial settings.

Feature Interaction. Feature interaction modeling has progressed from explicit factorization to structured and sequenceaware designs. Early factorization methods such as FM [16] and its field-aware extensions [9, 15] are efficient and interpretable but restricted to second-order relations. Deep hybrids like DeepFM [7], xDeepFM [12], and DCN/DCN-V2 [23] enhance expressiveness via high-order semantics or polynomial expansions, but still rely on flat, global interactions that can be inefficient under strict latency and memory budgets. Recent structured designs such as xDeepInt [25] and FuXi- $_ \alpha$ [26] allow controllable capacity allocation across fields, improving scalability but focusing mainly on static or aggregated features and often neglecting fine-grained sequential patterns.

Sequence-aware models, including DIN, DIEN, and DSIN [4], employ target-aware attention for behavior modeling, while temporal methods like TiSASRec [11] and TIN [36] encode timing signals for better interest extraction. Cross-modal designs such as InterFormer [28] and HSTU [29] bridge sequence and non-sequence features. Despite these advances, sequences are often pooled too early, weakening conditioning, and task signals are typically injected late, limiting task-aware crossing in multi-objective scenarios.

Multi-Task Recommendation. Multi-task recommendation addresses the need to optimize multiple objectives jointly. Expertbased architectures such as MMoE [14], PLE [19], STEM [18], and HoME [24] separate shared and task-specific components to improve representation sharing. However, most follow a two-stage pipeline first performing feature interaction, then applying taskspecific routing overlooking that interaction patterns can be taskdependent. This late integration of task information risks negative transfer and suboptimal representations, especially when serving constraints demand both high efficiency and strong task alignment.

These limitations motivate our approach, which unifies categorical, sequential, and task proxy tokens into a structured information flow, enabling early-stage task-aware interactions while controlling computational cost for industrial-scale deployment.

# 3 Methodology

In this section, we present the task-aware Information Flow Network (INFNeT) and its overall architecture in Fig. 3. We first introduce feature pre-processing and tokenization, then describe cross/within-type interaction via a stackable INFNet block, and finally detail the multi-task head and the optimization objective.

# 3.1 Feature Pre-processing

We unify all inputs into three token types: categorical, sequence, and task and each contains original tokens (full representation) and proxy tokens (compact queries). All embeddings share the same dimension $d$ , ensuring compatibility in subsequent interaction layers and aligning with the information flow design.

Categorical Feature Tokens and Proxy Tokens Categorical inputs include user/item IDs, static attributes, and bucketized continuous variables. For the $j$ -th field with value $v _ { j } \in \{ 1 , . . . , V _ { j } \}$ and embedding table $\mathbf { E } _ { j } ^ { \mathrm { c a t } } \in \mathbb { R } ^ { V _ { j } \times d }$ :

$$
\mathbf { c } _ { j } = \mathbf { E } _ { j } ^ { \mathrm { { c a t } } } [ v _ { j } ] \in \mathbb { R } ^ { d } .
$$

Stacking all $M$ fields yields:

$$
\mathbf { C } = \left[ \mathbf { c } _ { 1 } \parallel . . . \parallel \mathbf { c } _ { M } \right] ^ { \top } \in \mathbb { R } ^ { M \times d } .
$$

To form categorical proxies, we first flatten all field embeddings into a single vector, then project it through a shared MLP $\phi _ { \mathrm { c a t } }$ and reshape it into $m$ proxy tokens:

$$
\tilde { \mathbf { C } } = \mathrm { R e s h a p e } \bigl ( \phi _ { \mathrm { c a t } } ( \mathrm { F l a t t e n } ( \mathbf { C } ) ) \bigr ) \in \mathbb { R } ^ { m \times d } .
$$

This preserves global cross-field context before compression, yielding more informative proxies under the same token budget.

Sequence Feature Tokens and Proxy Tokens User behaviors are grouped into $F$ action-specific sequences (e.g., clicks, likes, plays). We concatenate all behavior-specific sequences to form a unified sequence token matrix:

$$
\mathbf { S } = [ \mathsf { s } _ { 1 , 1 } , . . . , \mathsf { s } _ { 1 , n _ { 1 } } , . . . , \mathsf { s } _ { F , 1 } , . . . , \mathsf { s } _ { F , n _ { F } } ] \in \mathbb { R } ^ { L \times d } ,
$$

where $\begin{array} { r } { L = \sum _ { a = 1 } ^ { F } n _ { a } } \end{array}$   
padding/truncation, and each ${ \bf s } _ { a , t }$ is obtained from its embedding   
table ${ \bf E } _ { a } ^ { \mathrm { s e q } }$   
shared projection $\phi _ { \mathrm { s e q } }$ and is pooled within its behavior type (sum   
pooling):

$$
\tilde { \mathbf { S } } = \left[ \begin{array} { c } { \sum _ { t = 1 } ^ { n _ { 1 } } \boldsymbol { \phi } _ { s \mathrm { e q } } ( \mathsf { s } _ { 1 , t } ) } \\ { \vdots } \\ { \sum _ { t = 1 } ^ { n _ { F } } \boldsymbol { \phi } _ { \mathrm { s e q } } ( \mathsf { s } _ { F , t } ) } \end{array} \right] \in \mathbb { R } ^ { F \times d } .
$$

This preserves per-type temporal semantics while keeping a bounded number of query tokens in heterogeneous flows.

Task Feature Tokens and Proxy Tokens Each real task i is represented by an original task tokens, initialized as learnable vectors:

$$
\mathbf { T } \in \mathbb { R } ^ { N _ { \mathrm { t a s k } } \times d } ,
$$

serving as task-specific keys/values and forming the basis for the corresponding prediction heads.

In addition, inspired by expert networks [18, 19], we introduce $N _ { s }$ shared task tokens to capture common knowledge across tasks. These shared tokens can be viewed as a special form of task proxy tokens, analogous to shared experts in mixture-of-experts architectures, providing a compact query set:

$$
\tilde { \mathbf { T } } \in \mathbb { R } ^ { N _ { s } \times d } .
$$

They participate as queries in heterogeneous attention, enabling early task-aware conditioning without increasing the overall query count. Meanwhile, the original $\mathbf { T }$ tokens remain in the within-type refinement stage, ensuring sufficient task-specific expressive capacity.

![](images/6f1af78519682782099e1b52012440d2c65d0198716a9045f13095be0939ba8d.jpg)  
C with its proxy set $\tilde { \mathbf { C } }$ sequence S with its proxy set , and task T with its proxies T. Each block alternates proxy-guided h  ttn: pox rk ar)nn t (,T). tacking $N$ blocks yields fused proxies $\bar { \tilde { \mathbf { C } } } ^ { ( N + 1 ) } , \tilde { \mathbf { S } } ^ { ( N + 1 ) }$ , and $\tilde { \mathbf { T } } ^ { ( N + 1 ) }$ ;the ulaskheadfee thenal-aye asktokes in task-specific MLPs.

Initialization for the Interaction Stack The first INFNeT block receives:

$$
\begin{array} { l l } { { { \bf C } ^ { ( 0 ) } = { \bf C } , \quad } } & { { \tilde { \bf C } ^ { ( 0 ) } = \tilde { \bf C } , } } \\ { { \mathrm { } } } & { { } { } } \\ { { { \bf S } ^ { ( 0 ) } = { \bf S } , \quad } } & { { \tilde { \bf S } ^ { ( 0 ) } = \tilde { \bf S } , } } \\ { { \mathrm { } } } & { { } { } } \\ { { { \bf T } ^ { ( 0 ) } = { \bf T } , \quad } } & { { \tilde { \bf T } ^ { ( 0 ) } = \tilde { \bf T } . } } \end{array}
$$

Proxies act as queries in cross-type cross attention, while originals serve as keys/values and undergo within-type refinement, consistent with the subsequent information flow design.

# 3.2 Information Flow

As shown in Fig. 3, we split the information flow into two stages: heterogeneous and homogeneous feature interactions, encapsulated in a stackable INFNeT Block. We treat the input tensors as layer (0); the superscript (l) indexes blocks, and after stacking $N$ blocks we denote outputs with superscript $\left( N { + } 1 \right)$ .Given inputs to the $l$ -th block categorical tokens $\bar { \mathbf { C } } ^ { ( l ) }$ , categorical proxies $\bar { \tilde { \mathbf { C } } } ^ { ( l ) }$ , sequence tokens $\mathsf { s } ^ { ( l ) }$ , sequence proxies $\tilde { \mathsf { S } } ^ { ( l ) }$ , and task tokens $\boldsymbol { \mathrm { T } } ^ { ( l ) }$ , task proxies $\tilde { \mathbf { T } } ^ { ( l ) }$   
interactions among them. Next, Proxy Gated Unit (PGU) handles homogeneous interactions within each feature type using its proxy, and residual connections are used for efficiency. The outputs $\hat { \tilde { \mathbf { C } } } ^ { ( l + 1 ) }$ $\tilde { \mathsf { S } } ^ { ( l + 1 ) }$ , and $\tilde { \mathbf { T } } ^ { ( l + 1 ) }$ are fed to the next block or the prediction head. CA(·) and PGU(·) denote cross attention and proxy gated unit, respectively. Proxies act as attention bottlenecks: they are used as queries to limit fan-out, while richer (non-proxy) tokens can serve as keys/values to preserve information.

3.2.1 Heterogeneous Feature Interactions. To enable information exchange between different feature types, we adopt a cross-attention mechanism that allows one set of tokens to query another. Intuitively, CA can be viewed as an information flow from a key-value set $( \mathbf { K } , \mathbf { V } )$ to a query set Q, where the query decides what information to retrieve based on content similarity. Specifically, given Q, K, and $\mathbf { V }$ ,cross attention mechanism is defined as:

$$
\begin{array} { r } { \mathrm { C A } ( { \bf Q } , { \bf K } , { \bf V } ) = \mathrm { s o f t m a x } \bigg ( \frac { { \bf Q } { \bf W } _ { Q } ( { \bf K } { \bf W } _ { K } ) ^ { \top } } { \sqrt { d _ { k } } } \bigg ) ( { \bf V } { \bf W } _ { V } ) , } \end{array}
$$

where $d _ { k }$ denotes the dimensionality of the key and query vectors. This formulation preserves the flexibility of content-based addressing while avoiding the quadratic complexity of self-attention across all tokens.

Having defined the cross attention operator, we now detail the specific information flow patterns in our architecture, namely: flow to categorical, flow to sequence, and flow to task. Each pattern specifies a distinct query-key-value configuration, determining how cross-type information is injected.

Information flow to categorical. In the information flow to categorical, categorical proxy tokens serve as the query in cross attention, while sequence and task tokens act as the key and value in their respective cross attention. The outputs of these cross attention are summed to produce the new result $\tilde { \mathbf { C } } ^ { ( l ) }$ of this information flow.

$$
\begin{array} { r } { \tilde { \mathbf { C } } ^ { ( l + 1 ) } = \mathbf { C A } \Big ( \tilde { \mathbf { C } } ^ { ( l ) } , \mathbf { S } ^ { ( l ) } , \mathbf { S } ^ { ( l ) } \Big ) + \mathbf { C A } \Big ( \tilde { \mathbf { C } } ^ { ( l ) } , \mathbf { T } ^ { ( l ) } , \mathbf { T } ^ { ( l ) } \Big ) . } \end{array}
$$

Information flow to sequence. Similarly, in the information flow to sequence, sequence proxies serve as the query in cross attention, while categorical and task tokens act as the key and value in their respective cross attention. The outputs are summed to produce $\tilde { \mathsf { S } } ^ { ( l ) }$ .

$$
\tilde { \mathbf { S } } ^ { ( l + 1 ) } = \mathrm { C A } \left( \tilde { \mathbf { S } } ^ { ( l ) } , \mathbf { C } ^ { ( l ) } , \mathbf { C } ^ { ( l ) } \right) + \mathrm { C A } \left( \tilde { \mathbf { S } } ^ { ( l ) } , \mathbf { T } ^ { ( l ) } , \mathbf { T } ^ { ( l ) } \right) .
$$

Information flow to task. Different from the flows to categorical and sequence tokens, both task proxies and real-task tokens are few in number, and each serves a distinct role: task proxies capture shared cross-task patterns, while real-task tokens focus on task-specific nuances. To fully exploit their capacity and allow these roles to complement each other, we perform cross attention for both, using categorical and sequence tokens as keys/values:

$$
\begin{array} { r l } & { \tilde { \mathbf { T } } ^ { ( l + 1 ) } = \mathbf { C A } \Bigl ( \tilde { \mathbf { T } } ^ { ( l ) } , \mathbf { C } ^ { ( l ) } , \mathbf { C } ^ { ( l ) } \Bigr ) + \mathbf { C A } \Bigl ( \tilde { \mathbf { T } } ^ { ( l ) } , \mathbf { S } ^ { ( l ) } , \mathbf { S } ^ { ( l ) } \Bigr ) , } \\ & { \hat { \mathbf { T } } ^ { ( l + 1 ) } = \mathbf { C A } \Bigl ( \mathbf { T } ^ { ( l ) } , \mathbf { C } ^ { ( l ) } , \mathbf { C } ^ { ( l ) } \Bigr ) + \mathbf { C A } \Bigl ( \mathbf { T } ^ { ( l ) } , \mathbf { S } ^ { ( l ) } , \mathbf { S } ^ { ( l ) } \Bigr ) . } \end{array}
$$

Here, ${ \hat { \mathbf { T } } } ^ { ( l + 1 ) }$ serves as an intermediate output enriched with task-specific information, thereby endowing the task tokens with explicit and concrete semantics.

3.2.2 Homogeneous Feature Interactions. After heterogeneous integration, we further refine features of the same type. We adopt PGU for homogeneous flows to mirror the channel-wise specialization role of MLPs in Transformers: Cross-Attention handles global, cross-type information exchange, while PGU refines intratype representations with proxy-conditioned, channel-wise modulation—avoiding redundant token-to-token attention and ensuring deployment-friendly complexity in large-scale systems.

Let $\mathbf { X } \in \mathbb { R } ^ { n \times d }$ denote the tokens of a given type and $\tilde { \mathbf { X } } \in \mathbb { R } ^ { \tilde { n } \times d }$ EY its $\tilde { n }$ proxy tokens from the heterogeneous stage. We first flatten $\tilde { \mathbf { X } }$ along the token dimension to form $\tilde { \mathbf { X } } _ { f } \in \mathbb { R } ^ { \tilde { n } \bar { d } }$ , map it through a lightweight MLP to produce a channel-wise gating vector $\mathbf { g } \in \mathbb { R } ^ { d }$ and then apply a Sigmoid activation to bound the gate values before broadcasting to all tokens for element-wise modulation:

$$
\operatorname { P G U } ( \mathbf { X } , { \tilde { \mathbf { X } } } ) = \mathbf { X } \odot \sigma { \big ( } \operatorname { M L P } ( { \tilde { \mathbf { X } } } _ { f } ) { \big ) } , \quad \in \mathbb { R } ^ { n \times d } .
$$

In our architecture, categorical, sequence, and task tokens are all refined using their own proxies:

$$
\begin{array} { r l } & { \mathbf { C } ^ { ( l + 1 ) } = \mathrm { P G U } \big ( \mathbf { C } ^ { ( l ) } , \tilde { \mathbf { C } } ^ { ( l ) } \big ) , } \\ & { ~ \mathbf { S } ^ { ( l + 1 ) } = \mathrm { P G U } \big ( \mathbf { S } ^ { ( l ) } , \tilde { \mathbf { S } } ^ { ( l ) } \big ) , } \\ & { ~ \mathbf { T } ^ { ( l + 1 ) } = \mathrm { P G U } \big ( \hat { \mathbf { T } } ^ { ( l + 1 ) } , \tilde { \mathbf { T } } ^ { ( l ) } \big ) . } \end{array}
$$

This channel-wise design decouples PGU's complexity from the token length $n$ , making it efficient even for very long sequences while preserving proxy-conditioned modulation.

# 3.3 Optimization Objective

Given the enhanced per-task representation $\mathbf { T } _ { i } ^ { ( N ) }$ obtained in the multi-task modeling stage, each task prediction is produced by a task-specific MLP followed by a Sigmoid activation:

$$
\begin{array} { r } { \hat { y } _ { i } ~ = ~ \sigma \big ( \mathrm { M L P } _ { i } ( \mathbf { T } _ { i } ^ { ( N ) } ) \big ) . } \end{array}
$$

This head shares architecture across tasks but maintains separate parameters, mapping the task proxy representation to a calibrated probability.

To optimize multiple tasks within a single network, we adopt a weighted multi-task loss:

$$
\mathcal { L } \ = \ \sum _ { i = 1 } ^ { N _ { \mathrm { t a s k } } } \lambda _ { i } \mathcal { L } _ { i } \big ( \hat { y } _ { i } , y _ { i } \big ) .
$$

where $\hat { y } _ { i }$ and $y _ { i }$ denote the predicted and ground-truth labels for task $i$ respectively. $\mathcal { L } _ { i }$ is the task-specific loss function. In this paper, we choose the binary cross-entropy:

$$
\mathcal { L } _ { i } \big ( \hat { y } _ { i } , y _ { i } \big ) \ = \ - \bigg [ y _ { i } \log \hat { y } _ { i } \ + \ ( 1 - y _ { i } ) \log \left( 1 - \hat { y } _ { i } \right) \bigg ] .
$$

The weight $\lambda _ { i }$ (default $= 1$ )balances gradient magnitudes across tasks and can be tuned via grid search or uncertainty-based methods when tasks vary in size or difficulty. The network parameters $\Theta$ are optimized end-to-end by minimizing $\mathcal { L } ( \Theta )$ over the training set, enabling both shared and task-specific learning.

# 4 Experiment

In this section, we evaluate INFNeT by comparing it with feature interaction models and multi-task recommendation models. We begin by introducing the experimental setup and analyze the experimental results.

# 4.1 Experimental Setup

Dataset. We evaluate INFNeT on three public short-video benchmarks KuaiRand-Pure, KuaiRand-27K [5], and QB-Video [27]—plus a large-scale internal dataset. As summarized in Table 2, KuaiRandPure is relatively compact, KuaiRand-27K expands to a much larger item and log scale with the same users, while QB-Video adopts a different schema and task setup. This mix covers diverse sparsity levels, feature richness, and task counts, offering a varied testbed for evaluation.

Baselines. We compare INFNeT against two baseline families: feature interaction models and multi-task recommendation models, using common instantiations from their original papers and adapting sequence handling only when required.

# Feature interaction models.

•FM [16]: models second-order interactions via factorized embeddings and linear terms, offering a strong lightweight baseline for sparse high-cardinality inputs.   
•DIN [35]: applies target-aware attention over a user's history, improving relevance modeling without heavy sequence encoders.   
DIEN [34]: builds on DIN by modeling interest extraction and temporal evolution with attention-updated GRUs and an auxiliary loss.   
DCN v2 [23]: enhances cross networks with low-rank residual mixing (CrossNet-Mix) for efficient high-order feature crossing.   
•GDCN [21]: uses gated cross layers and field-level dimension optimization to filter redundant capacity while improving expressiveness.   
• WuKong [30]: deepens and widens FM blocks under a scaling rule to capture any-order interactions at scale.   
•HSTU [29]: treats recommendation as generative sequential transduction with hierarchical units, excelling on very long contexts.

# Multi-task recommendation models.

Shared-Bottom [2]: shares a common encoder across tasks with separate towers; simple but prone to negative transfer.

best is underlined. All improvements are statistically significant $\dot { \boldsymbol { p } }$ -value $< 0 . 0 5 \dot { }$   

<table><tr><td rowspan="2"></td><td rowspan="2"></td><td colspan="7">Feature-interaction baselines</td><td colspan="7">Multi-task baselines</td></tr><tr><td>Metric</td><td>FM</td><td>DIN</td><td>DIEN</td><td>DCNv2</td><td>GDCN</td><td>WuKong</td><td>HSTU</td><td>Shared-Bottom</td><td>MMoE</td><td>OMoE</td><td>PLE</td><td>STEM</td><td>INFNET</td></tr><tr><td rowspan="4">KuaiRand-pure</td><td rowspan="2">click</td><td>AUC</td><td>0.7206 0.6367</td><td>0.7526</td><td>0.7252</td><td>0.7649</td><td>0.7652</td><td>0.7706</td><td>0.7709</td><td>0.7644</td><td>0.7639</td><td>0.7632</td><td>0.7648</td><td>0.7714</td><td>0.7736</td></tr><tr><td>gAUC</td><td></td><td>0.6570</td><td>0.6441</td><td>0.6669</td><td>0.6655</td><td>0.6704</td><td>0.6674</td><td>0.6634</td><td>0.6624</td><td>0.6609</td><td>0.6633</td><td>0.6728</td><td>0.6757</td></tr><tr><td rowspan="2">like</td><td>AUC</td><td>0.7020</td><td>0.8157</td><td>0.8218</td><td>0.7872</td><td>0.7909</td><td>0.8801</td><td>0.8837</td><td>0.7924</td><td>0.8047</td><td>0.7858</td><td>0.8621</td><td>0.8898</td><td>0.8960</td></tr><tr><td>gAUC</td><td>0.5021</td><td>0.5352</td><td>0.4942</td><td>0.5925</td><td>0.6160</td><td>0.6320</td><td>0.6015</td><td>0.5568</td><td>0.5484</td><td>0.5440</td><td>0.6060</td><td>0.6437</td><td>0.6464</td></tr><tr><td rowspan="6"></td><td rowspan="2">long-view</td><td>AUC</td><td>0.6973 0.6206</td><td>0.7532 0.6630</td><td>0.7184 0.6428</td><td>0.7556 0.6669</td><td>0.7602 0.6694</td><td>0.7697</td><td>0.7698 0.6713</td><td>0.7628</td><td>0.7623</td><td>0.7620</td><td>0.7648</td><td>0.7700</td><td>0.7727</td></tr><tr><td>gAUC</td><td></td><td></td><td></td><td></td><td></td><td>0.6743</td><td></td><td>0.6692</td><td>0.6688</td><td>0.6678</td><td>0.6716</td><td>0.6763</td><td>0.6784</td></tr><tr><td rowspan="3">click</td><td>AUC</td><td>0.9646</td><td>0.9702</td><td>0.9634</td><td>0.9699</td><td>0.9693</td><td>0.9737</td><td>0.9740</td><td>0.9684</td><td>0.9689</td><td>0.9692</td><td>0.9690</td><td>0.9699</td><td>0.9749</td></tr><tr><td>gAUC</td><td>0.9196</td><td>0.9273</td><td>0.9125</td><td>0.9280</td><td>0.9277</td><td>0.9300</td><td>0.9308</td><td>0.9263</td><td>0.9268</td><td>0.9269</td><td>0.9268</td><td>0.9270</td><td>0.9320</td></tr><tr><td>AUC</td><td>0.6832</td><td>0.9077</td><td>0.9021</td><td>0.9095</td><td>0.9093</td><td>0.9070</td><td>0.9078</td><td>0.8937</td><td>0.8836</td><td>0.8896</td><td>0.8996</td><td>0.9171</td><td>0.9225</td></tr><tr><td rowspan="4">like QB-video follow</td><td rowspan="2"></td><td>gAUC</td><td>0.5404</td><td>0.5647</td><td>0.5410</td><td>0.5964 0.5920</td><td>0.6428</td><td>0.5860</td><td></td><td>0.5793</td><td>0.5784</td><td>0.5762</td><td>0.5842</td><td>0.6020</td><td>0.6143</td></tr><tr><td>AUC</td><td>0.5940</td><td>0.8628</td><td>0.8431</td><td>0.8657</td><td>0.8745</td><td>0.8543</td><td>0.8409</td><td>0.8361</td><td>0.8447</td><td>0.8394</td><td>0.8747</td><td>0.8870</td><td>0.8881</td></tr><tr><td>gAUC</td><td>0.6042</td><td></td><td>0.5944 0.5714</td><td>0.5439</td><td>0.5996</td><td>0.6338</td><td>0.6578</td><td></td><td>0.6179</td><td>0.6065</td><td>0.6087</td><td>0.5544</td><td>0.5602</td><td>0.6401</td></tr><tr><td rowspan="2">share</td><td>AUC</td><td>0.6148</td><td>0.7388</td><td>0.6842</td><td>0.6786</td><td>0.6272</td><td>0.7628</td><td>0.7115</td><td>0.7022</td><td>0.6828</td><td>0.6824</td><td>0.7538</td><td>0.7057</td><td>0.8091</td></tr><tr><td>gAUC</td><td>0.6693</td><td>0.7012</td><td>0.7245</td><td>0.5898</td><td>0.6257</td><td>0.6888</td><td>0.7378</td><td>0.6500</td><td>0.6480</td><td>0.6498</td><td>0.5567</td><td>0.6618</td><td>0.7194</td></tr><tr><td rowspan="6">KuaiRand-27k</td><td rowspan="2">click</td><td>AUC</td><td>0.7311</td><td>0.7438</td><td>0.7345</td><td>0.7365</td><td>0.7115</td><td>0.7436</td><td>0.7293</td><td>0.7632</td><td>0.7686</td><td>0.7678</td><td>0.7667</td><td>0.7616</td><td>0.7820</td></tr><tr><td>gAUC</td><td>0.6383</td><td>0.6475</td><td>0.6411</td><td>0.6452</td><td>0.6256</td><td>0.6409</td><td>0.6390</td><td>0.6563</td><td>0.6641</td><td>0.6620</td><td>0.6603</td><td>0.6551</td><td>0.6826</td></tr><tr><td rowspan="2">like</td><td>AUC</td><td>0.8760</td><td>0.9129</td><td>0.8696</td><td>0.8676</td><td>0.7914</td><td>0.8885</td><td>0.8768</td><td>0.8812</td><td>0.9113</td><td>0.9116</td><td>0.9206</td><td>0.9181</td><td>0.9254</td></tr><tr><td>gAUC</td><td>0.5990</td><td>0.6544</td><td>0.5699</td><td>0.5816</td><td>0.5418</td><td>0.6075</td><td>0.5523</td><td>0.6041</td><td>0.6471</td><td>0.6543</td><td>0.6767</td><td>0.6608</td><td>0.7039</td></tr><tr><td rowspan="2">long-view</td><td>AUC</td><td>0.7647</td><td>0.7808</td><td>0.7731</td><td>0.7787</td><td>0.7435</td><td>0.7732</td><td>0.7608</td><td>0.7867</td><td>0.7945</td><td>0.7896</td><td>0.7926</td><td>0.7875</td><td>0.8038</td></tr><tr><td>gAUC</td><td>0.6824</td><td>0.6968</td><td>0.6897</td><td>0.6969</td><td>0.6668</td><td>0.6788</td><td>0.6801</td><td>0.6927</td><td>0.7034</td><td>0.6987</td><td>0.7003</td><td>0.6945</td><td>0.7203</td></tr></table>

Table 2: Statistics of datasets used for experiments.   

<table><tr><td>Dataset</td><td>kuairand-pure</td><td>kuairand-27k</td><td>QB-video</td></tr><tr><td># Users</td><td>27,285</td><td>27,285</td><td>34,240</td></tr><tr><td># Items</td><td>7,551</td><td>32,038,725</td><td>130,637</td></tr><tr><td># Interactions</td><td>1,436,609</td><td>322,278,385</td><td>1,726,886</td></tr><tr><td># Categorical Features</td><td>89</td><td>89</td><td>6</td></tr><tr><td># Sequence Features</td><td>28</td><td>28</td><td>12</td></tr><tr><td># Tasks</td><td>3</td><td>3</td><td>4</td></tr></table>

• MMoE [14]: combines multiple experts via task-specific gates to reduce interference and adapt to task difficulty.   
•OMoE [14]: a lighter single-gate variant of MMoE with less specialization capability.   
•PLE [19]: separates shared and task-specific experts progressively, mitigating the seesaw effect.   
•STEM [18]: uses shared and task-specific embeddings with gating to balance personalization and cross-task sharing.

Evaluation Metric. We report three standard metrics.

AUC: area under the receiver operating characteristic curve; measures overall ranking quality. Higher is better. gAUC: user-level averaged AUC that weights users more uniformly to reflect personalization quality. Higher is better.

Unless specified, we compute metrics on the test split and select checkpoints based on validation performance.

Experiment Settings. For a fair comparison, all methods are evaluated under the same data processing pipeline and a consistent hyperparameter tuning protocol. The batch size is fixed at 4096. Embedding dimensions are tuned over {8, 16, 32, 64, 96, 128}. All models are implemented using the fuxiCTR1 [37] framework, with necessary extensions for specific architectures. The optimizer is selected from {Adam, Adagrad}, and the initial learning rate is searched over $\{ 1 \mathrm { e } { - } 4 , 3 \mathrm { e } { - } 4 , 1 \mathrm { e } { - } 3 \}$ , combined with optional linear warmup or cosine decay schedules. L2 regularization is tuned from $\left\{ 0 , 1 \mathrm { e } { - } 7 , 1 \mathrm { e } { - } 6 , 1 \mathrm { e } { - } 5 \right\}$ , and dropout rates are searched in $\{ 0 . 0 , 0 . 1 , 0 . 2 \}$ Sequence lengths are tuned per dataset according to validation performance. Early stopping is applied when the validation AUC shows no improvement for five consecutive evaluations. All reported results are averaged over three runs with different random seeds to mitigate randomness and improve robustness.

# 4.2 Performance Comparison

Table 1 summarizes the overall comparison of INFNeT against both feature interaction and multi-task recommendation baselines on the public datasets. The main observations are as follows.

•Against feature interaction models. INFNeT consistently achieves higher AUC and gAUC on multiple targets such as click, like, long-view, and share. This indicates that the bidirectional heterogeneous information flow in INFNET integrates categorical fields with multi-behavior sequences more effectively, leading to stronger high-order interactions while keeping computational cost manageable.

•Against multi-task models. INFNeT shows clear gains over Shared-Bottom, MMoE, OMoE, PLE, and STEM, especially on challenging objectives and on KuaiRand-27K where behavior sparsity and noise are more pronounced. The cross attention with token proxies, together with hybrid task representations that include both shared and real task tokens, strengthens commonality learning across tasks while capturing task-specific nuances, which reduces negative transfer and improves overall multi-task performance.

![](images/0c8f7030b65080d6b9f87dfa7dda772960142cbf213a7b6d308aa40da48de6f1.jpg)  
Figure 4: Performance of INFNeT on the KuaiRand-pure dataset with different hyper-parameters.

Robustness across settings. We observe consistent improvements across a range of embedding sizes and sequence truncation lengths, suggesting that INFNeT maintains stable advantages under different capacity and context budgets.

In summary, INFNeT delivers consistent improvements over strong baselines in both the feature interaction and multi-task regimes, supporting its effectiveness and generalizability for largescale short-video recommendation.

# 4.3 Ablation Study

We evaluate INFNeT by removing each major component in turn while keeping data processing, optimization, and checkpoint selection identical to the main setup. Experiments are conducted on KuaiRand-pure and QB-video to cover short-video recommendation and multi-behavior advertising.

Ablated variants: w/o1 — Removes task tokens (learnable task vectors), preventing early integration of multi-task information. w/o2 — Removes homogeneous interaction (PGU updates for categorical, sequence, and task tokens), weakening within-type modeling. w/o3 — Removes heterogeneous interaction (cross attention across feature types), limiting cross-type fusion.

As shown in Table 3, the full INFNeT consistently outperforms all variants. (1) w/o1 shows universal drops, especially on share EMPY $\left( + 0 . 0 3 4 4 \right.$ AUC), confirming that task vectors improve alignment with task-specific objectives. (2) w/o2 notably hurts sequencedependent tasks (e.g., long-view, follow, like), indicating that pertype refinement improves feature quality before cross-type mixing. (3) w/o3 causes the largest losses on most tasks, highlighting the importance of aligning categorical and sequential evidence under task context.

Table 3: Performance comparison of INFNeT and its variants. Best results in bold.   

<table><tr><td>Dataset</td><td>Task</td><td>Metric</td><td>w/o1</td><td>w/o2</td><td>w/o3</td><td>INFNET</td></tr><tr><td rowspan="3">kuairand-pure</td><td>click</td><td>AUC</td><td>0.7720</td><td>0.7716</td><td>0.7705</td><td>0.7736</td></tr><tr><td>like</td><td>AUC</td><td>0.8925</td><td>0.8926</td><td>0.8899</td><td>0.8960</td></tr><tr><td>long-view</td><td>AUC</td><td>0.7707</td><td>0.7713</td><td>0.7701</td><td>0.7727</td></tr><tr><td rowspan="4">QB-video</td><td>click</td><td>AUC</td><td>0.9747</td><td>0.9741</td><td>0.9741</td><td>0.9749</td></tr><tr><td>like</td><td>AUC</td><td>0.9185</td><td>0.9183</td><td>0.9168</td><td>0.9225</td></tr><tr><td>follow</td><td>AUC</td><td>0.8842</td><td>0.8852</td><td>0.8829</td><td>0.8881</td></tr><tr><td>share</td><td>AUC</td><td>0.7747</td><td>0.7868</td><td>0.7854</td><td>0.8091</td></tr></table>

Overall, task vectors inject early task awareness, homogeneous flows strengthen per-type representations, and heterogeneous flows enable effective cross-type fusion. The full model benefits from all three for the best performance.

# 4.4 Effect of Proxy Token Counts

We study how the number of proxy tokens influences INFNeT 's multi-task performance on KuaiRand-pure, fixing task proxies $=$ 4 and shared task tokens $= 2$ unless otherwise noted. To isolate the effect of each factor, we vary one at a time under the same data pipeline, optimization schedule, and checkpoint selection.

As shown in Fig. 4a-4b, increasing categorical/sequential proxies from 2 to 4 improves AUC by enabling finer-grained representation of their respective feature spaces. More proxies allow the model to preserve diverse subspaces of categorical and sequential information, reducing the compression of multiple signals into a single vector and enhancing alignment between task intent and relevant regions. However, pushing the number to 8 leads to a drop in performance, consistent with over-parameterization: excessive proxies introduce redundancy, dilute attention focus, and increase optimization difficulty.

A similar pattern emerges for shared task tokens. Increasing from 1 to 2 yields gains on both click and long-view metrics by better summarizing cross-task patterns, while still allowing sufficient capacity for task-specific tokens to specialize. Setting this value to 3 brings diminishing or negative returns, consistent with oversharing: too many shared carriers blur task boundaries and compete with real task tokens, weakening per-task discrimination. Overall, categorical/sequential proxies $= 4$ and shared task tokens $= ~ 2$ offer a good trade-off between representation richness and stability, and serve as robust defaults in our training setup.

# 4.5 Visualization Analysis

As shown in Fig. 5, we visualize the final layer's cross attention where task query all categorical and sequential tokens ( $\mathbf { \dot { x } } \mathbf { \cdot }$ axis: token positions; y-axis: query channels). Shared-task channels exhibit smoother, low-frequency patterns covering broad regions, serving as carriers of cross-task context, while real-task channels show sharper peaks aligned with a few salient positions (e.g., ${ \sim } 6 0 { - } 7 0 $ ${ \sim } 9 0 _ { , }$ , emphasizing influential tokens from behavior sequences or key categorical fields. Dark "corridors" indicate tokens with limited utility.

![](images/6db3a0b7173552104842efc1ccdaa8eb7483368cddf494de14bbfc1210b10587.jpg)  
Figure 5: Visualization of the final-layer cross attention between task tokens and their proxies. The $\mathbf { x }$ axis indicates feature or attention weights (brighter indicates stronger attention).

These patterns match our design goals: real tasks specialize in task-specific cues, and shared tasks provide a broad prior that regularizes and complements them. The attention remains differentiated yet coordinated broad shared coverage does not overwhelm taskspecific spikes mirroring our quantitative trends that moderate sharing yields more effective attention than overly concentrated or diffuse maps.

![](images/9fe1167d2864561113a588876b00db2bfb8cf7e9a722fb369789ca6bbc594c2e.jpg)  
Figure 6: Inference Time and Parameters of INFNeT and baseline on the kuairand-pure Dataset.

# 4.6 Efficiency Analysis

Fig. 6 compares inference time and parameter count of representative models on KuaiRand-pure, illustrating the trade-off between complexity and online efficiency. The $\mathbf { X }$ -axis shows per-batch inference time (lower is better), and the y-axis indicates model size (smaller is easier to deploy), with circle size/color reflecting parameter magnitude.

Feature interaction models such as DIN, DIEN, and INFNET achieve low latency and compact sizes, whereas high-order or multiexpert methods (e.g., MMoE, OMoE, PLE, DCNv2, GDCN) incur higher cost due to additional branches, routing, or explicit crossing. Methods like AITM, WuKong, Shared-Bottom, and STEM sit in between.

Overall, deeper explicit-interaction models and multi-expert designs increase both parameters and inference time, while INFNET maintains compactness and low latency through hierarchical feature interaction and task-aware fusion with learnable task vectors, making it practical under strict latency and resource constraints.

# 4.7 Online Analysis

This section details the deployment of our model as a real-time ranking system for short-video ads in a large-scale online advertising system, targeting shallow signals such as click, play, and completion. Emphasizing task-specific efficiency and revenue impact, we evaluate the model under a streaming training setup from both training and serving perspectives. To ensure a fair assessment, the online experiment uses the same candidate generation and request routing as the production baseline, and we report results after the system reaches a steady state.

![](images/379bcc3e48508030a5b01dd6a20036417f146be167cfe5b9a0708f29cb6a7f24.jpg)  
Figure 7: Feature generation logic in the deployment stage of INFNET.

4.7.1 Online Deployment. As the model is trained in a streaming fashion, Fig. 7 illustrates feature generation and label acquisition during deployment. Upon receiving a ranking-stage request, the system splits it into two pipelines: inference and training. In inference, context features are sent to the feature server to retrieve user and video features, which are then scored by the infer server. In training, the sample producer fetches features, and the label matcher aligns callback timestamps to generate labels. The updated model is deployed to the infer server.

Model complexity thus affects both training efficiency and inference performance. To keep the end-to-end cost stable, we reuse cached embeddings for infrequently changing fields, maintain a bounded sequence length for behaviors, and apply consistent snapshotting so that features and model versions remain time-aligned. These practices help maintain predictable throughput under fluctuating traffic.

4.7.2 Online A/B Testing. We deployed our model in the main feed scenario, which serves billions of requests per day. The baseline, approximately a combination of DIN, DCNv2, and PLE, was compared against our INFNeT model in an A/B test conducted from 2025-03-10 to 2025-04-10. As shown in Table 4, results show statistically significant improvements ( $\dot { \boldsymbol { p } }$ -value $< 0 . 0 5$ across all key metrics, including a $+ 1 . 5 8 7 \%$ increase in expected revenue and $+ 1 . 1 5 5 \%$ in click-through rate (CTR). We also observed consistent gains in short-term user retention indicators, where P3s, P5s, and PEnd respectively denote the proportion of videos played for at least 3 seconds, 5 seconds, and until the end: $+ 0 . 1 0 5 \%$ $+ 0 . 3 1 7 \%$ ,and $+ 0 . 3 5 1 \%$ .

T0 statistically significant $\dot { \boldsymbol { p } }$ -value $< 0 . 0 5$ ). Latency is measured under identical hardware and quota settings.   

<table><tr><td>Method</td><td>REV (%)</td><td>CTR (%)</td><td>P3s (%)</td><td>P5s (%)</td><td>PEnd (%)</td><td>Pred. Latency (ms)</td><td>Train Latency (min)</td></tr><tr><td>Baseline</td><td></td><td></td><td></td><td></td><td></td><td>18.28</td><td>21.21</td></tr><tr><td>INFNET</td><td>+1.587</td><td>+1.155</td><td>+0.105</td><td>+0.317</td><td>+0.351</td><td>18.17</td><td>20.04</td></tr></table>

As shown by the latency metrics, our model achieves comparable efficiency to the baseline, with a slightly lower prediction latency (18.17 ms vs. $1 8 . 2 8 ~ \mathrm { m s }$ and reduced training latency (20.04 min vs. $2 1 . 2 1 \mathrm { m i n }$ ). The online ramp-up followed a fixed traffic ratio to avoid seasonality artifacts, and all comparisons were performed under the same hardware and quota settings to ensure comparability.

# 4.8 Conclusion

This paper proposes INFNeT, a large-scale multi-task feature interaction framework for recommendation. It treats task as a learnable feature and integrates sparse, sequential, and task features via bidirectional heterogeneous and homogeneous flows. Extensive offline experiments show significant gains across datasets and objectives. Online results confirm notable improvements in business metrics and user experience with efficient inference. Overall, INFNeT demonstrates strong potential and wide applicability in multi-source feature modeling and multi-task learning for largescale recommendation.

# References

[1] Qingpeng Cai, Shuchang Liu, Xueliang Wang, Tianyou Zuo, Wentao Xie, Bin Yang, Dong Zheng, Peng Jiang, and Kun Gai. 2023. Reinforcing user retention in a billion scale short video recommender system. In Companion Proceedings of the ACM Web Conference 2023. 421426.   
[2] Rich Caruana. 1997. Multitask learning. Machine learning 28 (1997), 4175.   
[3] Zho n, Zheng , Jan L Don og Han  en, Shuang Li, and Kun Gai. 2024. Multi-Epoch learning with Data Augmentation for Deep Click-Through Rate Prediction. arXiv preprint arXiv:2407.01607 (2024). Yang. 2019. Deep session interest network for click-through rate prediction. arXiv preprint arXiv:1905.06482 (2019).   
[5] Chongming Gao, Shijun Li, Yuan Zhang, Jiawei Chen, Biao Li, Wenqiang Lei, Peng Jiang, and Xiangnan He. 2022. Kuairand: An unbiased sequential recommendation dataset with randomly exposed videos. In Procedings of the 31st ACM International Conference on Information & Knowledge Management. 39533957.   
[6] Huan Gui, Ruoxi Wang, Ke Yin, Long Jin, Maciej Kula, Taibai Xu, Lichan Hong, and Ed H Chi. 2023. Hiformer: Heterogeneous feature interactions learning with transformers for recommender systems. arXiv preprint arXiv:2311.05884 (2023).   
[7] Huifeng Guo, Ruiming Tang, Yunming Ye, Zhenguo Li, and Xiuqiang He. 2017. DeepFM: a factorization-machine based neural network for CTR prediction. arXiv preprint arXiv:1703.04247 (2017).   
e Jiang, Fei Sun, and Wentao Zhang. 2024. MMGCL: Meta Knowledge-Enhanced Multi-view Graph Contrastive Learning for Recommendations. In Proceedings of the 18th ACM Conference on Recommender Systems. 538548.   
[9] Yuchin Juan, Yong Zhuang, Wei-Sheng Chin, and Chih-Jen Lin. 2016. Fieldaware factorization machines for CTR prediction. In Proceedings of the 10th ACM conference on recommender systems. 4350.   
[10] Honghao Li, Yiwen Zhang, Yi Zhang, Hanwei Li, and Lei Sang. 2024. Dcnv3: Towards next generation deep cross network for ctr prediction. arXiv e-prints (2024), arXiv-2407.   
[11] Jiacheng Li, Yujie Wang, and Julian McAuley. 2020. Time interval aware selfattention for sequential recommendation. In Proceedings of the 13th international conference on web search and data mining. 322330.   
[12] Jianxun Lian, Xiaohuan Zhou, Fuzheng Zhang, Zhongxia Chen, Xing Xie, and Guangzhong Sun. 2018. xdeepfm: Combining explicit and implicit feature interactions for recommender systems. In Proceedings of the 24th ACM SIGKDD international conference on knowledge discovery & data mining. 17541763.   
[13] Xiao Lin, Xiaokai Chen, Linfeng Song, Jingwei Liu, Biao Li, and Peng Jiang. 2023. Tree based progressive regression model for watch-time prediction in short-video recommendation. In Proceedings of the 29th ACM SIGKDD Conference on Knowledge Discovery and Data Mining. 44974506.   
[14] Jiaqi Ma, Zhe Zhao, Xinyang Yi, Jilin Chen, Lichan Hong, and Ed H Chi. 2018. Modeling task relationships in multi-task learning with multi-gate mixture-ofexperts. In Proceedings of the 24th ACM SIGKDD international conference on knowledge discovery & data mining. 19301939.   
[15] Junwei Pan, Jian Xu, Alfonso Lobos Ruiz, Wenliang Zhao, Shengjun Pan, Yu Sun, and Quan Lu. 2018. Field-weighted factorization machines for click-through rate prediction in display advertising. In Proceedings of the 2018 world wide web conference. 13491357.   
[16 StefenRendle. 010. Factorization machines. In 2010 IEEE Interational confrence on data mining. IEEE, 9951000.   
[17] Lei Sang, Qiuze Ru, Honghao Li, Yiwen Zhang, Qian Cao, and Xindong Wu. 2024. Feature Interaction Fusion Self-Distillation Network For CTR Prediction. arXiv preprint arXiv:2411.07508 (2024).   
[18] Liangcai Su, Junwei Pan, Ximei Wang, Xi Xiao, Shijie Quan, Xihua Chen, and Jie Jiang. 2024. STEM: unleashing the power of embeddings for multi-task recommendation. In Proceedings of the AÅAI Conference on Artificial Intelligence, Vol. 38. 90029010.   
[19] Hongyan Tang, Junning Liu, Ming Zhao, and Xudong Gong. 2020. Progressive layere extraction (ple): A novel multi-ask learning (mtl) model for personalized recommendations. In Proceedings of the 14th ACM conference on recommender systems. 269278.   
[20] Zhen Tian, Changwang Zhang, Wayne Xin Zhao, Xin Zhao, Ji-Rong Wen, and Zhao Cao. 2023. UFIN: Universal feature interaction network for multi-domain click-through rate prediction. arXiv preprint arXiv:2311.15493 (2023).   
[21] Fangye Wang, Hansu Gu, Dongsheng Li, Tun Lu, Peng Zhang, and Ning Gu. 2023. Towards deeper, lighter and interpretable cross network for CTR prediction. In Proceedings of the 32nd ACM international conference on information and knowledge management. 25232533.   
[22] Ruoxi Wang, Bin Fu, Gang Fu, and Mingliang Wang. 2017. Deep & cross network for ad click predictions. In Proceedings of the ADKDD'17. 17.   
[23] Ruoxi Wang, Rakeh Shivann, Derek Cheng, Sagar Jain, Dong Lin, Lichan Hong, and Ed Chi. 2021. Dcn v2: Improved deep & cross network and practical lessons for web-scale learning to rank systems. In Proceedings of the web conference 2021. 17851797.   
[24] Xu Wang, Jiangxia Cao, Zhiyi Fu, Kun Gai, and Guorui Zhou. 2024. HoME: Hierarchy of Multi-Gate Experts for Multi-Task Learning at Kuaishou. arXiv preprint arXiv:2408.05430 (2024).   
[25] Yachen Yan and Liubo Li. 2023. xDeepInt: a hybrid architecture for modeling the vector-wise and bit-wise feature interactions. arXiv preprint arXiv:2301.01089 (2023).   
[26] Yufei Ye, Wei Guo, Jin Yao Chin, Hao Wang, Hong Zhu, Xi Lin, Yuyang Ye, Yong Liu, Ruiming Tang, Defu Lian, et al. 2025. FuXi-alpha: Scaling Recommendation Model with Feature Interaction Enhanced Transformer. arXiv preprint arXiv:2502.03036 (2025).   
[27] Guanghu Yuan, Fajie Yuan, Yudong Li, Beibei Kong, Shujie Li, Lei Chen, Min Yang, Chenyun Yu, Bo Hu, Zang Li, et al. 2022. Tenrec: A large-scale multipurpose benchmark dataset for recommender systems. Advances in Neural Information Processing Systems 35 (2022), 1148011493.   
[28] Zhichen Zeng, Xiaolong Liu, Mengyue Hang, Xiaoyi Liu, Qinghai Zhou, Chaofei Yang, Yiqun Liu, Yichen Ruan, Laming Chen, Yuxin Chen, et al. 2024. InterFormer: Towards Effective Heterogeneous Interaction Learning for Click-Through Rate Prediction. arXiv preprint arXiv:2411.09852 (2024).   
[29] Jiaqi Zhai, Lucy Liao, Xing Liu, Yueming Wang, Rui Li, Xuan Cao, Leon Gao, Zhaojie Gong, Fangda Gu, Michael He, et al. 2024. Actions speak louder than words: Trillion-parameter sequential transducers for generative recommendations. arXiv preprint arXiv:2402.17152 (2024).   
[30] Buyun Zhang, Liang Luo, Yuxin Chen, Jade Nie, Xi Liu, Shen Li, Yanli Zhao, Yuchen Hao, Yantao Yao, Ellie Dingqiao Wen, et al. 2024. Wukong: towards a scaling law for large-scale recommendation. In Proceedings of the 41st International Conference on Machine Learning. 5942159434.   
[31] Pengtao Zhang, Zheng Zheng, and Junlin Zhang. 2023. Fibinet+ $+ ;$ Reducing model size by low rank feature interaction layer for ctr prediction. In Proceedings of the 32nd ACM International Conference on Information and Knowledge Management. 44254429.   
[32] Yang Zhang, Tianhao Shi, Fuli Feng, Wenjie Wang, Dingxian Wang, Xiangnan He, and Yongdong Zhang. 2023. Reformulating CTR prediction: Learning invariant feature interactions for recommendation. In Proceedings of the 46th International ACM SIGIR Conference on Research and Development in Information Retrieval. 13861395.   
[33] Zijian Zhang, Shuchang Liu, Jiaao Yu, Qingpeng Cai, Xiangyu Zhao, Chunxu Zhang, Ziru Liu, Qidong Liu, Hongwei Zhao, Lantao Hu, et al. 2024. M3oe: Multi-domain multi-task mixture-of experts recommendation framework. In Proceedings of the 47th International ACM SIGIR Conference on Research and Development in Information Retrieval. 893902.   
[34] Guorui Zhou, Na Mou, Ying Fan, Qi Pi, Weijie Bian, Chang Zhou, Xiaoqiang Zhu, and Kun Gai. 2019. Deep interest evolution network for click-through rate prediction. In Proceedings of the AAAI conference on artificial intelligence, Vol. 33. 59415948.   
[35] Guorui Zhou, Xiaoqiang Zhu, Chenru Song, Ying Fan, Han Zhu, Xiao Ma, Yanghui Yan, Junqi Jin, Han Li, and Kun Gai. 2018. Deep interest network for click-through rate prediction. In Proceedings of the 24th ACM SIGKDD international conference on knowledge discovery & data mining. 10591068.   
[36] Haolin Zhou, Junwei Pan, Xinyi Zhou, Xihua Chen, Jie Jiang, Xiaofeng Gao, and Guihai Chen. 2024. Temporal interest network for user response prediction. In Companion Proceedings of the ACM Web Conference 2024. 413422.   
[37] Jieming Zhu, Jinyang Liu, Shuai Yang, Qi Zhang, and Xiuqiang He. 2021. Open benchmarking for click-through rate prediction. In Proceedings of the 30th ACM international conference on information & knowledge management. 27592769.