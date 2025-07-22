# OpenManus 事件总线系统

## 概述

OpenManus 事件总线系统是一个基于分层架构设计的轻量级、高性能事件处理框架。它提供了装饰器自动注册、通配符匹配、优先级执行、依赖关系管理、错误隔离和重试机制等高级功能。

## 核心特性

### ✨ 主要功能
- **装饰器自动注册** - 使用 `@event_handler` 装饰器自动注册处理器
- **通配符匹配** - 支持 `user.*`, `agent.step.*` 等模式匹配
- **优先级执行** - 按优先级顺序执行处理器（数字越大优先级越高）
- **依赖关系管理** - 支持处理器间的依赖关系，确保执行顺序
- **错误隔离** - 一个处理器失败不影响其他处理器
- **重试机制** - 可配置的重试次数和延迟策略
- **中间件支持** - 可插拔的中间件链，支持日志、指标、错误处理等
- **异步处理** - 完全异步设计，支持高并发

### 🏗️ 架构设计

系统采用分层架构，从底层到上层分为：

```
应用层 (Application Layer)
├── 事件工厂函数 (Event Factories)
├── 领域事件 (Domain Events)
└── 事件处理器 (Event Handlers)

服务层 (Service Layer)
├── 简单事件总线 (SimpleEventBus)
├── 全局事件总线 (Global Bus Functions)
└── 事件总线管理 (Bus Management)

实现层 (Implementation Layer)
├── 处理器注册系统 (Registry System)
├── 中间件系统 (Middleware System)
└── 事件路由 (Event Routing)

核心层 (Core Layer)
├── 基础事件类 (BaseEvent)
├── 基础处理器类 (BaseEventHandler)
└── 基础总线类 (BaseEventBus)
```

## 核心组件

### 1. 基础组件 (`base.py`)

#### BaseEvent
事件基类，提供事件的基本属性和状态管理：

```python
class BaseEvent(BaseModel):
    event_id: str           # 唯一事件标识
    event_type: str         # 事件类型
    timestamp: datetime     # 创建时间
    source: Optional[str]   # 事件源
    status: EventStatus     # 事件状态
    priority: int           # 执行优先级
    data: Dict[str, Any]    # 事件数据
    metadata: Dict[str, Any] # 元数据
```

**状态管理方法：**
- `mark_processing(handler_name)` - 标记为处理中
- `mark_completed()` - 标记为完成
- `mark_failed(error)` - 标记为失败
- `mark_cancelled()` - 标记为取消

#### BaseEventHandler
处理器基类，定义处理器的基本接口：

```python
class BaseEventHandler(ABC):
    name: str                    # 处理器名称
    description: Optional[str]   # 描述
    enabled: bool               # 是否启用
    supported_events: List[str] # 支持的事件类型

    @abstractmethod
    async def handle(self, event: BaseEvent) -> bool:
        """处理事件的核心方法"""
        pass
```

#### BaseEventBus
事件总线基类，定义总线的基本接口：

```python
class BaseEventBus(ABC):
    @abstractmethod
    async def publish(self, event: BaseEvent) -> bool:
        """发布事件"""
        pass

    @abstractmethod
    async def subscribe(self, handler: BaseEventHandler) -> bool:
        """订阅处理器"""
        pass

    @abstractmethod
    async def unsubscribe(self, handler_name: str) -> bool:
        """取消订阅"""
        pass
```
### 2. 注册系统 (`registry.py`)

#### EventHandlerRegistry
处理器注册管理器，负责处理器的注册、匹配和执行顺序解析：

**核心功能：**
- **通配符匹配** - 使用 `fnmatch` 实现模式匹配
- **依赖解析** - 拓扑排序解决依赖关系
- **优先级排序** - 在满足依赖的前提下按优先级排序
- **执行缓存** - 缓存事件类型的处理器执行顺序

```python
# 注册处理器
registry.register_handler(
    name="user_logger",
    handler=log_user_events,
    patterns=["user.*"],
    priority=100,
    depends_on=[],
    retry_count=3,
    retry_delay=1.0
)

# 获取匹配的处理器
handlers = registry.get_handlers_for_event("user.input")
```

#### @event_handler 装饰器
提供声明式的处理器注册方式：

```python
@event_handler("user.*", priority=100, name="user_logger")
async def log_user_events(event):
    """处理所有用户事件"""
    return True

@event_handler("user.input", depends_on=["user_logger"], priority=50)
async def process_user_input(event):
    """处理用户输入，依赖于用户日志记录器"""
    return True
```

**装饰器参数：**
- `patterns` - 事件类型模式（支持通配符）
- `priority` - 优先级（默认0，数字越大优先级越高）
- `depends_on` - 依赖的处理器名称列表
- `retry_count` - 重试次数（默认3）
- `retry_delay` - 重试延迟（默认1.0秒）
- `name` - 处理器名称（默认使用函数名）
- `enabled` - 是否启用（默认True）

### 3. 中间件系统 (`middleware.py`)

中间件系统提供可插拔的事件处理增强功能：

#### BaseMiddleware
中间件基类：

```python
class BaseMiddleware(ABC):
    @abstractmethod
    async def process(self, context: MiddlewareContext, next_middleware: Callable) -> bool:
        """处理中间件逻辑"""
        pass
```

#### 内置中间件

**LoggingMiddleware** - 日志记录
- 记录处理开始、成功、失败和执行时间
- 可配置日志级别

**RetryMiddleware** - 重试机制
- 支持指数退避重试策略
- 可配置最大重试次数和基础延迟

**ErrorIsolationMiddleware** - 错误隔离
- 防止单个处理器的错误影响其他处理器
- 自动标记失败事件状态

**MetricsMiddleware** - 指标收集
- 收集处理统计信息
- 按处理器和事件类型分类统计

#### MiddlewareChain
中间件链管理器：

```python
# 创建中间件链
chain = MiddlewareChain([
    LoggingMiddleware("INFO"),
    MetricsMiddleware(),
    ErrorIsolationMiddleware(),
    RetryMiddleware(max_retries=3, base_delay=1.0)
])

# 处理事件
await chain.process(context, handler)
```

### 4. 简单事件总线 (`simple_bus.py`)

#### SimpleEventBus
主要的事件总线实现，整合了注册系统和中间件：

```python
class SimpleEventBus(BaseEventBus):
    def __init__(
        self,
        name: str = "SimpleEventBus",
        max_concurrent_events: int = 10,
        registry: Optional[EventHandlerRegistry] = None,
        middleware_chain: Optional[MiddlewareChain] = None
    ):
        # 初始化配置
```

**核心方法：**
- `publish(event)` - 发布事件进行处理
- `subscribe(handler)` - 订阅处理器
- `unsubscribe(handler_name)` - 取消订阅
- `get_event_stats()` - 获取事件统计
- `get_metrics()` - 获取处理指标

#### 全局事件总线函数

```python
# 获取全局总线实例
bus = get_global_bus()

# 发布事件
await publish_event(event)

# 订阅处理器
await subscribe_handler(handler)

# 获取统计信息
stats = get_bus_stats()
```

## 领域事件 (`events.py`)

系统预定义了多种领域事件类型：

### 对话事件
- `ConversationCreatedEvent` - 对话创建
- `ConversationClosedEvent` - 对话关闭
- `UserInputEvent` - 用户输入
- `InterruptEvent` - 中断事件

### 智能体事件
- `AgentStepStartEvent` - 智能体开始处理
- `AgentStepCompleteEvent` - 智能体完成处理
- `AgentResponseEvent` - 智能体响应
- `LLMStreamEvent` - LLM流式响应

### 工具事件
- `ToolExecutionEvent` - 工具执行
- `ToolResultEvent` - 工具结果
- `ToolResultDisplayEvent` - 工具结果显示

### 系统事件
- `SystemErrorEvent` - 系统错误

### 事件工厂函数

```python
# 创建用户输入事件
event = create_user_input_event("conv1", "user1", "Hello")

# 创建智能体开始事件
event = create_agent_step_start_event("claude", "assistant", 1, "conv1")

# 创建工具执行事件
event = create_tool_execution_event("web_search", "search", "started", {"query": "python"})
```

## 使用指南

### 快速开始

1. **定义事件处理器**

```python
from app.event import event_handler, BaseEvent

@event_handler("user.*", priority=100)
async def log_user_events(event: BaseEvent) -> bool:
    print(f"User event: {event.event_type}")
    return True

@event_handler("user.input", depends_on=["log_user_events"], priority=50)
async def process_user_input(event: BaseEvent) -> bool:
    message = event.data.get('message', '')
    print(f"Processing: {message}")
    return True
```

2. **发布事件**

```python
from app.event import publish_event, create_user_input_event

# 创建并发布事件
event = create_user_input_event("conv1", "user1", "Hello World")
success = await publish_event(event)
```

3. **获取统计信息**

```python
from app.event import get_bus_stats

stats = get_bus_stats()
print(f"Total events: {stats['total_events']}")
print(f"Registered handlers: {stats['registered_handlers']}")
```

### 高级用法

#### 自定义中间件

```python
from app.event.middleware import BaseMiddleware, MiddlewareContext

class CustomMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__("custom")

    async def process(self, context: MiddlewareContext, next_middleware: Callable) -> bool:
        # 前置处理
        print(f"Before processing: {context.event.event_type}")

        # 调用下一个中间件
        result = await next_middleware(context)

        # 后置处理
        print(f"After processing: {result}")

        return result
```

#### 自定义事件总线

```python
from app.event import SimpleEventBus, EventHandlerRegistry, MiddlewareChain

# 创建自定义注册器
registry = EventHandlerRegistry()

# 创建自定义中间件链
middleware_chain = MiddlewareChain([
    CustomMiddleware(),
    LoggingMiddleware("DEBUG")
])

# 创建自定义事件总线
bus = SimpleEventBus(
    name="CustomBus",
    max_concurrent_events=20,
    registry=registry,
    middleware_chain=middleware_chain
)
```

#### 条件处理器

```python
@event_handler("user.*", priority=50)
async def conditional_handler(event: BaseEvent) -> bool:
    # 根据条件决定是否处理
    if event.data.get('urgent', False):
        print("Processing urgent user event")
        return True
    else:
        print("Skipping non-urgent event")
        return False
```

## 设计原理

### 1. 分层架构原理

**职责分离**：每一层都有明确的职责，降低耦合度
- 核心层：定义基础接口和抽象
- 实现层：提供具体的功能实现
- 服务层：整合各组件提供完整服务
- 应用层：面向业务的具体应用

**依赖倒置**：高层模块不依赖低层模块，都依赖抽象

### 2. 事件驱动架构

**解耦合**：事件发布者和处理者之间松耦合
**可扩展**：新增处理器不影响现有代码
**异步处理**：支持高并发和非阻塞处理

### 3. 中间件模式

**横切关注点**：日志、指标、错误处理等横切关注点统一处理
**可插拔**：中间件可以灵活组合和配置
**责任链**：请求沿着中间件链传递，每个中间件处理特定职责

### 4. 注册器模式

**自动发现**：通过装饰器自动注册处理器
**模式匹配**：支持灵活的事件类型匹配
**依赖管理**：自动解析和管理处理器依赖关系

## 性能特性

### 并发控制
- 使用信号量限制并发事件数量
- 异步处理避免阻塞
- 支持配置最大并发数

### 缓存优化
- 执行顺序缓存：避免重复计算处理器执行顺序
- 模式匹配缓存：提高事件类型匹配效率

### 内存管理
- 事件历史大小限制：防止内存泄漏
- 及时清理已完成事件

## 错误处理策略

### 错误隔离
- 单个处理器失败不影响其他处理器
- 错误信息记录在事件状态中

### 重试机制
- 指数退避重试策略
- 可配置重试次数和延迟
- 重试失败后标记事件失败

### 日志记录
- 详细的错误日志记录
- 处理时间和性能指标
- 分级日志输出

## 监控和指标

### 事件统计
- 总事件数量
- 活跃事件数量
- 事件状态分布

### 处理器性能
- 成功率统计
- 平均处理时间
- 失败次数统计

### 系统健康度
- 注册处理器数量
- 中间件执行状态
- 错误率监控

## 最佳实践

### 1. 处理器设计
- **单一职责**：每个处理器只处理一种类型的逻辑
- **幂等性**：处理器应该是幂等的，重复执行不会产生副作用
- **快速失败**：尽早检测和报告错误

### 2. 事件设计
- **语义明确**：事件类型应该语义明确，便于理解
- **数据完整**：事件数据应该包含处理所需的所有信息
- **版本兼容**：考虑事件结构的向后兼容性

### 3. 依赖管理
- **最小依赖**：尽量减少处理器间的依赖关系
- **循环检测**：避免循环依赖
- **清晰文档**：明确记录依赖关系和原因

### 4. 性能优化
- **批量处理**：对于大量相似事件，考虑批量处理
- **异步优先**：优先使用异步处理器
- **资源限制**：合理设置并发限制和超时时间

## 故障排查

### 常见问题

1. **处理器未执行**
   - 检查事件类型是否匹配模式
   - 确认处理器是否启用
   - 验证依赖关系是否满足

2. **性能问题**
   - 检查并发设置
   - 分析处理器执行时间
   - 优化中间件配置

3. **内存泄漏**
   - 检查事件历史大小设置
   - 确认事件是否正确清理
   - 监控活跃事件数量

### 调试技巧

1. **启用详细日志**
```python
# 设置日志级别为DEBUG
middleware_chain = create_default_middleware_chain(log_level="DEBUG")
```

2. **监控事件状态**
```python
# 定期检查事件统计
stats = get_bus_stats()
print(f"Failed events: {stats.get('status_distribution', {}).get('failed', 0)}")
```

3. **性能分析**
```python
# 分析处理器性能
metrics = bus.get_metrics()
for handler, stats in metrics.get('handler_stats', {}).items():
    if stats['avg_duration'] > 1.0:  # 超过1秒的处理器
        print(f"Slow handler: {handler} - {stats['avg_duration']:.3f}s")
```

## 扩展指南

### 添加新的中间件

1. 继承 `BaseMiddleware`
2. 实现 `process` 方法
3. 添加到中间件链

### 添加新的事件类型

1. 继承 `BaseEvent` 或相应的领域事件基类
2. 定义事件数据结构
3. 创建事件工厂函数

### 自定义事件总线

1. 继承 `BaseEventBus`
2. 实现抽象方法
3. 集成所需的组件

---

## 总结

OpenManus 事件总线系统提供了一个完整、灵活、高性能的事件处理框架。通过分层架构、装饰器注册、中间件模式等设计，实现了高度的可扩展性和易用性。系统支持复杂的事件处理场景，同时保持了简单的使用接口，是构建事件驱动应用的理想选择。
