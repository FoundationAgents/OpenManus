# OpenManus Web 项目

## 项目介绍

嘿！欢迎来到 OpenManus Web 项目 👋

这是一个正在成长中的 AI Agent 开发平台的学习项目。作为一名个人开发者的作品，目前还处于起步阶段，希望能和对 AI Agent 感兴趣的小伙伴们一起学习和成长！

### 🌟 项目愿景

- 学习和探索 AI Agent 开发的最佳实践
- 尝试打造一个简单易用的 Agent 开发工具
- 与社区一起成长，共同建设开源生态

### 🎯 计划中的特性

- 🎨 直观的可视化界面：让扩展 Agent 能力变得更轻松
- 🔌 模块化设计：便于扩展和自定义
- 🛠 开发者友好：降低 AI Agent 开发的门槛
- 🤝 开源共建：欢迎所有对项目感兴趣的朋友参与贡献

### 🎁 一起来玩！

- 对 AI Agent 开发感兴趣的学习者
- 想要了解 AI 应用开发的新手
- 愿意分享经验的开发者
- 热爱开源社区的朋友们

这是一个学习和实验的项目，欢迎大家一起探讨、学习、贡献代码。项目可能还有很多不完善的地方，期待你的参与和建议！🌱

## 项目准备

### 环境要求

- Node.js (推荐 v20+)
- npm
- Docker 和 Docker Compose
- 数据库 (项目使用 PostgreSQL)

### 初始配置步骤

1. **安装依赖**

```bash
# 如果已经在 web 目录下忽略即可
cd web

# 安装项目依赖
npm install
```

2. **生成密钥对**
   项目需要一对公钥和私钥用于认证，可以通过以下命令生成（有自行生成证书能力的忽略即可）：

```bash
npm run generate-keys
```

这将在 `web/keys` 目录生成：

- `private.pem`: 私钥文件
- `public.pem`: 公钥文件

3. **数据库配置**

- 确保已正确配置数据库连接信息
- 在项目根目录创建 `.env` 文件，配置必要的环境变量

4. **生成 Prisma 客户端**

```bash
npx prisma generate
```

## 项目启动

### 使用 Docker Compose 启动（推荐）

1. 确保已配置所有必要的环境变量
2. 确保 `private.pem` 和 `public.pem` 证书文件已就位
3. 执行以下命令启动服务：

```bash
docker-compose up -d
```

### 本地开发环境启动

1. 安装依赖：

```bash
npm install
```

2. 生成 Prisma 客户端：

```bash
npx prisma generate
```

3. 启动开发服务器：

```bash
npm run dev
```

## 环境变量配置

创建 `.env` 文件，包含以下必要配置：

```env
# 数据库配置
DATABASE_URL="postgresql://user:password@localhost:5432/dbname"

# 其他配置
# ... 根据项目需求添加其他环境变量
```

## 开发调试

1. 确保已完成所有初始配置步骤
2. 使用您喜欢的 IDE 或编辑器（推荐 VS Code）
3. 可以使用内置的调试配置进行代码调试

## 常见问题

1. 如果遇到 Prisma 相关错误，请确保已执行 `npx prisma generate`
2. 确保所有环境变量都已正确配置
3. 检查数据库连接是否正常
4. 验证密钥对是否正确生成

## 技术支持

如有问题，请提交 Issue（也可以直接联系作者，Openmanus飞书交流群随时活跃哈）。
