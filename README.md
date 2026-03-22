# Mini OpenClaw：轻量级全透明 AI Agent 系统

一个轻量级、全透明的 AI Agent 系统。强调文件驱动（Markdown/JSON 取代向量数据库）、指令式技能（而非 function-calling）、以及 Agent 全部操作过程的可视化。

## 快速开始

### 1. 环境要求

- **Anaconda / Miniconda**（推荐）：后端使用名为 **`miniclaw`** 的 Conda 虚拟环境（Python **3.12**）
- Node.js 18+
- npm

若尚未创建该环境，在终端执行：

```bash
conda create -n miniclaw python=3.12
```

激活后安装依赖并运行后端：

```bash
conda activate miniclaw
```

### 2. 一键启动（推荐）

| 平台 | 脚本 | 说明 |
|------|------|------|
| Windows | `start.bat` | 检查 Conda / Node；若不存在 **miniclaw**，会自动执行 `conda create -n miniclaw python=3.12 -y`；随后在 **miniclaw** 中安装后端依赖并启动前后端 |
| Linux / macOS | `start.sh` | 同上 |

```bash
# Windows（双击或在 cmd 中运行）
start.bat

# Linux / macOS
chmod +x start.sh
./start.sh
```

### 3. 手动配置后端（Conda：`miniclaw`）

```bash
conda activate miniclaw
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Keys

# 启动后端服务（端口 8002）
uvicorn app:app --port 8002 --host 0.0.0.0 --reload
```

**重要**：请确保在 `.env` 文件中配置以下 API Keys：
- `DEEPSEEK_API_KEY`: DeepSeek API Key（Agent 主模型）
- `OPENAI_API_KEY`: OpenAI 兼容 Embedding（RAG；可选配合本地 Ollama，见 `.env.example`）

### 4. 手动配置前端

```bash
cd frontend

# 安装依赖
npm install

# 启动前端服务（端口 3000）
npm run dev
```

### 5. 访问应用

- 本机访问：http://localhost:3000
- 局域网访问：http://<本机IP>:3000

## 项目特色

### 1. 文件驱动的记忆系统

- 所有记忆都存储在 `memory/MEMORY.md` 中，完全透明可编辑
- 支持 RAG 模式，自动检索相关记忆片段

### 2. 指令式技能系统

- 技能以 Markdown 文件形式存储在 `skills/` 目录
- Agent 通过 `read_file` 工具读取技能说明，动态学习如何使用
- 无需编写 Python 代码即可扩展新能力

### 3. 五大核心工具

- **terminal**: 沙箱化的命令行操作
- **python_repl**: Python 代码解释器
- **fetch_url**: 网页内容获取（自动转 Markdown）
- **read_file**: 安全的文件读取
- **search_knowledge_base**: 知识库检索

### 4. 全透明的 System Prompt

System Prompt 由 6 个组件动态拼接：
1. SKILLS_SNAPSHOT.md（技能列表）
2. workspace/SOUL.md（人格设定）
3. workspace/IDENTITY.md（身份认知）
4. workspace/USER.md（用户画像）
5. workspace/AGENTS.md（操作指南）
6. memory/MEMORY.md（长期记忆）

所有组件都可以通过前端编辑器实时修改。

### 5. IDE 风格的前端

- 三栏布局：会话列表 / 聊天面板 / 文件编辑器
- 支持可视化工具调用链（Thought Chain）
- 支持对话历史压缩
- 内置 Monaco 编辑器，在线编辑配置文件

## 技术栈

### 后端

- **框架**: FastAPI + Uvicorn
- **Agent 引擎**: LangChain 1.x
- **LLM**: DeepSeek（通过 langchain-deepseek）
- **RAG**: LlamaIndex Core（BM25 + 向量混合检索）
- **Embedding**: 优先本地 Ollama（如 `bge-m3`），否则 OpenAI 兼容 API（见 `.env.example`）

### 前端

- **框架**: Next.js 14 App Router
- **UI**: Tailwind CSS + Lucide Icons
- **编辑器**: Monaco Editor
- **状态管理**: React Context

## 项目结构

```
mini-openclaw/
├── backend/                # 后端
│   ├── app.py              # FastAPI 入口
│   ├── config.py           # 配置管理
│   ├── api/                # API 路由
│   ├── graph/              # Agent 核心逻辑
│   ├── tools/              # 五大核心工具
│   ├── workspace/          # System Prompt 组件
│   ├── memory/             # 长期记忆
│   ├── skills/             # 技能目录
│   ├── sessions/           # 会话存储
│   └── storage/            # 索引存储
│
└── frontend/               # 前端
    └── src/
        ├── app/            # Next.js 应用
        ├── components/     # React 组件
        └── lib/            # API 客户端 & 状态管理
```

## 使用技巧

### 1. 添加新技能

在 `backend/skills/` 目录下创建新文件夹，添加 `SKILL.md` 文件：

```markdown
---
name: 技能名称
description: 技能描述
---

## 步骤

1. 第一步...
2. 第二步...
```

重启后端，Agent 会自动识别新技能。

### 2. 编辑记忆

在前端编辑器中打开 `MEMORY.md`，编辑后保存，系统会自动重建索引。

### 3. 开启 RAG 模式

点击左侧边栏的 "RAG: OFF" 按钮，切换到 "RAG: ON"，Agent 会自动从记忆库中检索相关内容。

### 4. 压缩对话历史

当对话过长时，点击左侧边栏的 "压缩历史" 按钮，系统会将前 50% 的消息归档并生成摘要。

## 开发说明

本项目完全基于 Python 重构，遵循以下设计原则：

1. **文件优先**：所有数据以文件形式存储，拒绝黑盒数据库
2. **透明可控**：所有 System Prompt 组件和工具调用过程对用户完全可见
3. **轻量部署**：无需 MySQL/Redis 等重型依赖，开箱即用
4. **技能扩展**：通过 Markdown 文件即可添加新能力，无需编写代码

## 许可证

MIT License

## 致谢

本项目受 Anthropic 的 Agent Skills 范式启发，感谢 OpenClaw/Moltbot 项目的设计思想。
