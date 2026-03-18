# Mini-OpenClaw 快速开始指南

## 第一步：环境准备

### 必需软件

1. **Python 3.10+**
   - Windows: https://www.python.org/downloads/
   - Mac/Linux: 通常已预装，或使用包管理器安装

2. **Node.js 18+**
   - https://nodejs.org/

3. **pip 和 npm**
   - 通常随 Python 和 Node.js 一起安装

## 第二步：配置 API Keys

### 1. 获取 DeepSeek API Key

- 访问 https://platform.deepseek.com/
- 注册账号并创建 API Key
- DeepSeek 提供较低的调用费用

### 2. 获取 OpenAI API Key（用于 Embedding）

- 访问 https://platform.openai.com/
- 创建 API Key
- 或使用兼容 OpenAI API 的其他服务（如 OpenRouter）

### 3. 配置环境变量

进入 `backend` 目录：

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Keys：

```
DEEPSEEK_API_KEY=sk-your-deepseek-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

OPENAI_API_KEY=sk-your-openai-key
OPENAI_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
```

## 第三步：安装依赖

### 后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 前端依赖

```bash
cd frontend
npm install
```

## 第四步：启动服务

### 方法 1：使用启动脚本（推荐）

**Windows:**
```bash
双击 start.bat
```

**Mac/Linux:**
```bash
chmod +x start.sh
./start.sh
```

### 方法 2：手动启动

**启动后端：**
```bash
cd backend
uvicorn app:app --port 8002 --host 0.0.0.0 --reload
```

**启动前端（新终端）：**
```bash
cd frontend
npm run dev
```

## 第五步：访问应用

- 本机访问：http://localhost:3000
- 局域网访问：http://<你的IP>:3000

## 第六步：开始使用

### 1. 创建新对话

点击左侧边栏的 "新建对话" 按钮。

### 2. 发送消息

在底部输入框输入消息，按 Enter 发送。

### 3. 查看工具调用

Agent 在执行任务时会显示工具调用链，点击可展开查看详情。

### 4. 编辑配置文件

在右侧面板选择文件（如 MEMORY.md），编辑后点击 "保存"。

### 5. 启用 RAG 模式

点击左侧边栏的 "RAG: OFF" 按钮，切换到 "RAG: ON"。

RAG 模式会自动从 MEMORY.md 中检索相关内容。

## 常见问题

### Q: 启动后端时报错"No module named 'xxx'"

A: 依赖未正确安装，重新运行：
```bash
pip install -r requirements.txt
```

### Q: 前端启动失败

A: 删除 `node_modules` 和 `package-lock.json`，重新安装：
```bash
rm -rf node_modules package-lock.json
npm install
```

### Q: Agent 无法调用工具

A: 检查 System Prompt 中的 AGENTS.md 文件，确保包含技能调用协议。

### Q: 如何添加新技能？

A: 在 `backend/skills/` 目录下创建新文件夹，添加 `SKILL.md` 文件，参考 `get_weather` 示例。

### Q: 如何清空对话历史？

A: 删除 `backend/sessions/` 目录下的会话文件即可。

### Q: 如何备份数据？

A: 备份以下目录即可：
- `backend/sessions/` - 会话历史
- `backend/memory/` - 长期记忆
- `backend/workspace/` - 配置文件
- `backend/skills/` - 自定义技能

## 进阶使用

### 自定义 System Prompt

编辑 `backend/workspace/` 目录下的文件：
- `SOUL.md` - 人格设定
- `IDENTITY.md` - 身份认知
- `USER.md` - 用户画像
- `AGENTS.md` - 操作指南

### 添加知识库文档

将 PDF/Markdown/TXT 文件放入 `backend/knowledge/` 目录，Agent 可以通过 `search_knowledge_base` 工具检索。

### 对话历史压缩

当对话过长时，点击左侧边栏的 "压缩历史" 按钮，系统会归档旧消息并生成摘要。

## 技术支持

如有问题，请访问项目仓库提交 Issue。

祝你使用愉快！🎉
