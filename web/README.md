# OpenManus Web Project

## Project Introduction

Hey! Welcome to the OpenManus Web Project 👋

This is a learning project for an AI Agent development platform that's still in its early stages. As a personal developer's work, it's currently taking its first steps, and I hope to learn and grow together with others who are interested in AI Agent development!

### 🚀 Project Features

- 💫 **Simple yet Sophisticated Interface**

  - Clean interface built with Next.js and Shadcn UI
  - User experience-focused interaction design

- 📦 **Data Persistence Capability**

  - Database integration with Prisma for persistent storage of task details

- 👥 **User Data Isolation**

  - Support for independent multi-user usage
  - Ensures data security for each user

- 🔄 **Full Agent Execution Visibility**

  - Modified official source code with event system for execution tracking and structured output
  - Real-time status feedback
  - In OpenManus Core, use `agent.on()` for easier execution detail monitoring

- 🎯 **Prompt Engineering Optimization**
  - Continuous improvement based on official prompts for more stable output

### 🌟 Project Vision

- Learn and explore best practices in AI Agent development
- Try to create a simple and easy-to-use Agent development tool
- Grow with the community and build an open-source ecosystem together

### 🎯 Planned Features

- 🎨 Intuitive Visual Interface: Making it easier to extend Agent capabilities
- 🔌 Modular Design: Easy to extend and customize
- 🛠 Developer-Friendly: Lower the barrier to AI Agent development
- 🤝 Open Source Collaboration: Welcome all interested friends to contribute

### 🎁 Join Us!

- Learners interested in AI Agent development
- Beginners wanting to understand AI application development
- Developers willing to share their experience
- Friends who love the open-source community

This is a learning and experimental project. Everyone is welcome to discuss, learn, and contribute code. The project may still have many areas for improvement, and we look forward to your participation and suggestions! 🌱

## Project Setup

### Requirements

- Node.js (v20+ recommended)
- npm
- Docker and Docker Compose
- Database (Project uses PostgreSQL)

### Initial Configuration Steps

#### 0. **OpenManus Core**

The current `/web` project only starts the application layer, OpenManus Core needs to be configured separately:

1. No need to configure LLM parameters in `config` (this configuration will be written directly to the database through the page's bottom-left corner configuration after project startup and login, rather than being stored locally in the project)
2. Start command is `python run_api.py`

#### 1. **Install Dependencies**

```bash
# Skip if already in web directory
cd web

# Install project dependencies
npm install
```

#### 2. **Generate Key Pair**

The project needs a pair of public and private keys for authentication. You can generate them using the following command (ignore if you can generate certificates yourself):

```bash
npm run generate-keys
```

This will generate in the `web/keys` directory:

- `private.pem`: Private key file
- `public.pem`: Public key file

#### 3. **Environment Variables**

- Create a `.env` file in the project root directory and configure necessary environment variables (refer to `/web/.env.example`)
- Ensure database connection information is properly configured

#### 4. **Generate Prisma Client & Initialize Database**

```bash
# Run this command to update Prisma Client if:
# - First time starting the project
# - Dependencies reinstalled
# - schema.prisma has updates
npx prisma generate

# For first time project setup, initialize the database
# This command will automatically sync table structure to the configured database
npx prisma db push
```

## Project Launch

### Launch Using Docker Compose (Recommended)

1. Ensure all necessary environment variables are configured
2. Ensure `private.pem` and `public.pem` certificate files are in place
3. Execute the following command to start services:

```bash
docker-compose up -d
```

### Local Development Environment Launch

1. Install dependencies:

```bash
npm install
```

2. Generate Prisma client:

```bash
npx prisma generate
```

3. Start development server:

```bash
npm run dev
```

## Environment Variable Configuration

Create a `.env` file with the following necessary configurations:

```env
# Database configuration
DATABASE_URL="postgresql://user:password@localhost:5432/dbname"

# Other configurations
# ... Add other environment variables according to project requirements
```

## Development and Debugging

1. Ensure all initial configuration steps are completed
2. Use your preferred IDE or editor (VS Code recommended)
3. Use built-in debug configurations for code debugging

## Common Issues

1. If encountering Prisma-related errors, ensure `npx prisma generate` has been executed
2. Verify all environment variables are correctly configured
3. Check if database connection is working properly
4. Verify key pair is correctly generated

## Technical Support

If you have any questions, please submit an Issue (or feel free to contact me directly - I'm always active in the OpenManus Feishu chat group).
