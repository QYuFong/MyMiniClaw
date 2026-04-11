# AGENTS.md - Mini OpenClaw 项目指南

本文档是 Mini OpenClaw 项目的完整指南，涵盖项目架构、环境配置、开发规范等内容，供开发者和 AI 助手（如 Claude Code）参考。

## 项目概述

Mini OpenClaw 是一个轻量级、全透明的 AI Agent 系统，具有以下核心特性：

- **文件驱动**：所有数据以 Markdown/JSON 文件形式存储，拒绝黑盒数据库
- **指令式技能**：技能以 Markdown 文件定义，无需编写代码即可扩展
- **透明可控**：所有 System Prompt 组件和工具调用过程完全可见
- **轻量部署**：无需 MySQL/Redis 等重型依赖，开箱即用

## 环境配置

### 系统要求

- Python 3.12（Conda 环境：`miniclaw`）
- Node.js 18+
- npm

### Conda 环境

```bash
conda create -n miniclaw python=3.12
conda activate miniclaw
```

### 环境约束（重要）

**所有 Python 依赖必须安装在 `miniclaw` Conda 虚拟环境中，项目启动前必须先激活该环境。**

```bash
# 安装依赖前
conda activate miniclaw
pip install -r requirements.txt

# 启动服务前
conda activate miniclaw
uvicorn app:app --port 8002 --reload
```

**禁止**在系统全局或其他环境中安装 Python 依赖或运行后端服务。

### 后端启动

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 配置 API Keys
uvicorn app:app --port 8002 --host 0.0.0.0 --reload
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 一键启动脚本

| 平台 | 脚本 | 说明 |
|------|------|------|
| Windows | `start.bat` | 自动检查环境并启动 |
| Linux/macOS | `start.sh` | 同上 |

### 必需环境变量

在 `backend/.env` 中配置：

- `DEEPSEEK_API_KEY`: DeepSeek API Key（Agent 主模型）
- `OPENAI_API_KEY`: OpenAI 兼容 Embedding（可选，配合本地 Ollama）

## 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| FastAPI + Uvicorn | Web 框架 |
| LangChain 1.x | Agent 引擎 |
| DeepSeek | 主模型 LLM |
| LlamaIndex Core | RAG（BM25 + 向量混合检索） |
| Ollama / OpenAI API | Embedding |

### 前端

| 技术 | 用途 |
|------|------|
| Next.js 14 App Router | 应用框架 |
| Tailwind CSS + Lucide Icons | UI |
| Monaco Editor | 代码编辑器 |
| React Context | 状态管理 |

### 端口配置

- 后端: 8002
- 前端: 3000

## 核心架构

### 1. System Prompt 组件

System Prompt 由 6 个组件动态拼接：

| 组件 | 路径 | 用途 |
|------|------|------|
| SKILLS_SNAPSHOT.md | skills/ | 技能列表索引 |
| SOUL.md | workspace/ | 人格设定与价值观 |
| IDENTITY.md | workspace/ | 身份认知与定位 |
| USER.md | workspace/ | 用户画像 |
| AGENTS.md | workspace/ | 操作指南 |
| MEMORY.md | memory/ | 长期记忆 |

### 2. 五大核心工具

| 工具 | 功能 | 使用场景 |
|------|------|----------|
| terminal | 沙箱化命令行 | 系统操作、文件管理 |
| python_repl | Python 解释器 | 数学计算、数据处理 |
| fetch_url | 网页获取 | 获取网页内容（自动转 Markdown） |
| read_file | 文件读取 | 读取技能文件、配置文件 |
| search_knowledge_base | 知识库检索 | RAG 模式下检索相关内容 |

### 3. 技能系统

技能存放在 `backend/skills/` 目录，每个技能是一个文件夹，包含 `SKILL.md` 文件：

```
backend/skills/
├── get_weather/
│   └── SKILL.md
├── your_new_skill/
│   └── SKILL.md
```

技能文件格式：

```markdown
---
name: 技能名称
description: 技能描述
---

# 技能标题

## 功能说明
...

## 使用步骤
...

## 示例
...
```

### 4. 记忆系统

- **长期记忆**：存储在 `memory/MEMORY.md`，可通过前端编辑器修改
- **RAG 检索**：开启后自动从记忆库检索相关内容
- **对话压缩**：支持将早期对话归档并生成摘要

## 开发指南

### 添加新技能

1. 在 `backend/skills/` 下创建新文件夹
2. 添加 `SKILL.md` 文件，包含 frontmatter 和详细步骤
3. 重启后端，Agent 自动识别新技能

### 扩展工具

1. 在 `backend/tools/` 创建新工具文件
2. 实现 LangChain Tool 接口
3. 在 `backend/tools/__init__.py` 注册工具

### 修改 System Prompt

直接编辑 `backend/workspace/` 下的 Markdown 文件，前端编辑器支持实时修改。

## 行为准则

### 技能调用协议

1. **必须先读取**：使用技能前，先用 `read_file` 读取对应的 SKILL.md
2. **禁止猜测**：不得凭推测使用技能，必须按文件指示执行
3. **透明沟通**：告知用户正在执行的操作和原因

### 记忆管理协议

1. **重要信息记录**：将关键信息写入 MEMORY.md
2. **索引自动更新**：文件保存后系统自动重建索引
3. **RAG 模式**：开启时优先检索相关记忆

### 错误处理规范

1. 分析错误原因，不盲目重试
2. 尝试替代方案
3. 坦诚告知用户能力边界

## 技术约束

- **沙箱限制**：terminal 工具仅能在项目根目录内操作
- **危险命令拦截**：rm -rf、sudo 等命令会被自动拦截
- **会话隔离**：不同会话的记忆相互独立
- **模型依赖**：主模型使用 DeepSeek，Embedding 优先本地 Ollama

## 文件结构参考

```
mini-openclaw/
├── backend/
│   ├── app.py              # FastAPI 入口
│   ├── config.py           # 配置管理
│   ├── api/                # API 路由
│   │   ├── chat.py         # 聊天接口
│   │   ├── compress.py     # 对话压缩
│   │   ├── sessions.py     # 会话管理
│   │   └── files.py        # 文件操作
│   ├── graph/              # Agent 核心逻辑
│   │   ├── agent.py        # Agent 主循环
│   │   ├── prompt_builder.py  # Prompt 构建
│   │   └── session_manager.py # 会话存储
│   ├── tools/              # 五大核心工具
│   ├── workspace/          # System Prompt 组件
│   ├── memory/             # 长期记忆
│   ├── skills/             # 技能目录
│   ├── sessions/           # 会话存储
│   └── storage/            # 索引存储
│
└── frontend/
    └── src/
        ├── app/            # Next.js 应用
        ├── components/     # React 组件
        └── lib/            # API 客户端
```

## 版本与许可

- 许可证：MIT License
- Python 版本：3.12
- Node.js 版本：18+