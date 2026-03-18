# Mini-OpenClaw 开发需求文档 (PRD)

# 一、项目介绍

## 1. 功能与目标定位

Mini-OpenClaw 是一个基于 Python 重构的、轻量级且高度透明的 AI Agent 系统，旨在复刻并优化 OpenClaw（原名 Moltbot/Clawdbot）的核心体验。

本项目不追求构建庞大的 SaaS 平台，而是致力于打造一个运行在本地的、拥有“真实记忆”的数字副手。其核心差异化定位在于：

- **文件即记忆 (File-first Memory)**：摒弃不透明的向量数据库，回归最原始、最通用的 Markdown/JSON 文件系统。用户的每一次对话、Agent 的每一次反思，都以人类可读的文件形式存在。

- **技能即插件 (Skills as Plugins)**：遵循 Anthropic 的 Agent Skills 范式，通过文件夹结构管理能力，实现“拖入即用”的技能扩展。

- **透明可控**：所有的 System Prompt 拼接逻辑、工具调用过程、记忆读写操作对开发者完全透明，拒绝“黑盒”Agent。

## 2. 项目核心技术架构

本项目要求完全采用 **前后端分离** 架构，后端作为纯 API 服务运行，整体技术栈规范如下：

- **后端语言**：Python 3.10+ (强制使用 Type Hinting)

- **Web 框架**：FastAPI (提供 RESTful 接口，支持异步处理)

- **Agent 编排引擎**：LangChain 1.x (Stable Release)
        

    - 核心 API：必须使用 `create_agent` API (`from langchain.agents import create_agent`)，这是 LangChain 1.0 版本发布的最新标准 API，用于构建基于 Graph 运行时的 Agent

    - 严禁使用旧版的 AgentExecutor 或早期的 create_react_agent（旧链式结构），create_agent 底层基于 LangGraph 运行时，接口更简洁标准化，项目需紧跟该范式

- **RAG 检索引擎**：LlamaIndex (LlamaIndex Core)，用于处理非结构化文档的混合检索（Hybrid Search），作为 Agent 的知识外挂

- **模型接口**：兼容 OpenAI API 格式（支持 OpenRouter, DeepSeek, Claude 等模型直连）

- **数据存储**：本地文件系统 (Local File System) 为主，不引入 MySQL/Redis 等重型依赖

# 二、内置工具

Mini-OpenClaw 启动时，除加载用户自定义 Skills 外，必须内置以下 5 个核心基础工具（Core Tools），遵循“优先使用 LangChain 原生工具”原则，技术选型与实现规范如下：

## 1. 命令行操作工具 (Command Line Interface)

- **功能描述**：允许 Agent 在受限的安全环境下执行 Shell 命令

- **实现逻辑**：直接使用 LangChain 内置工具 `langchain_community.tools.ShellTool`

- **配置要求**：初始化配置 `root_dir` 限制操作范围（沙箱化），防止修改系统关键文件；预置黑名单拦截高危指令（如 `rm -rf /`）

- **工具名称**：terminal

## 2. Python 代码解释器 (Python REPL)

- **功能描述**：赋予 Agent 逻辑计算、数据处理和脚本执行的能力

- **实现逻辑**：直接使用 LangChain 内置工具 `langchain_experimental.tools.PythonREPLTool`

- **配置要求**：自动创建临时 Python 交互环境，需确保 experimental 包依赖安装正确

- **工具名称**：python_repl

## 3. Fetch 网络信息获取

- **功能描述**：用于获取指定 URL 的网页内容，是 Agent 联网的核心工具

- **实现逻辑**：直接使用 LangChain 内置工具 `langchain_community.tools.RequestsGetTool`

- **增强配置**：原生工具返回原始 HTML，Token 消耗巨大，需封装 Wrapper，通过 BeautifulSoup 或 html2text 库清洗数据，仅返回 Markdown 或纯文本内容

- **工具名称**：fetch_url

## 4. 文件读取工具 (File Reader)

- **功能描述**：精准读取本地指定文件内容，是 Agent Skills 机制的核心依赖，用于读取 SKILL.md 详细说明

- **实现逻辑**：直接使用 LangChain 内置工具 `langchain_community.tools.file_management.ReadFileTool`

- **配置要求**：设置 `root_dir` 为项目根目录，严禁读取项目以外的系统文件

- **工具名称**：read_file

## 5. RAG 检索工具 (Hybrid Retrieval)

- **功能描述**：用户询问具体知识库内容（非对话历史）时，Agent 可调用此工具进行深度检索

- **技术选型**：LlamaIndex

- **实现逻辑**：支持扫描指定目录（如 `knowledge/`）下的 PDF/MD/TXT 文件构建本地索引；实现 Hybrid Search（关键词检索 BM25 + 向量检索 Vector Search）；索引文件持久化存储至本地 `storage/` 目录

- **工具名称**：search_knowledge_base

# 三、mini OpenClaw 的 Agent Skills 系统

## 1. Agent Skills 基础功能介绍

mini OpenClaw 的 Agent Skills 遵循 **"Instruction-following" (指令遵循)** 范式，而非传统的 "Function-calling" (函数调用) 范式。Skills 本质是教会 Agent 使用基础工具完成任务的说明书，而非预先编写的 Python 函数，所有技能以文件夹形式存放于`backend/skills/` 目录。

## 2. Agent Skills 载入与执行流程

### 2.1 Agent Skills 读取流程 (Bootstrap)

Agent 启动或会话开始时，系统自动扫描`skills` 文件夹，读取每个 `SKILL.md` 的元数据（Frontmatter），汇总生成 `SKILLS_SNAPSHOT.md`，文件示例如下：

```plaintext
<available_skills>
  <skill>
    <name>get_weather</name>
    <description>获取指定城市的实时天气信息</description>
    <location>./backend/skills/get_weather/SKILL.md</location>
  </skill>
</available_skills>
```

**注意**：location 字段统一使用相对路径。

### 2.2 Agent Skills 调用流程 (Execution)

该系统核心特色为“指令驱动执行”，完整流程分为四步：

1. **感知**：Agent 通过 System Prompt 获取 available_skills 列表

2. **决策**：用户发起请求后，Agent 匹配对应技能（如查询天气匹配 get_weather）

3. **行动**：Agent 不直接调用函数，而是通过 `read_file` 工具读取技能对应的 `SKILL.md` 文件

4. **学习与执行**：Agent 解析 Markdown 操作步骤，结合内置 Core Tools（terminal/python_repl/fetch_url）动态完成任务

# 四、mini OpenClaw 对话记忆管理系统设计

## 1. 本地优先原则

所有记忆文件（Markdown/JSON）均存储于本地文件系统，保障用户完全的数据主权和内容可解释性，无云端同步、无第三方数据采集。

## 2. 系统提示词 (System Prompt) 构成

System Prompt 按固定顺序动态拼接 6 部分内容，单文件字符上限 20k，超出部分自动截断并标注 `...[truncated]`，拼接顺序如下：

1. SKILLS_SNAPSHOT.md (能力列表)

2. SOUL.md (核心设定)

3. IDENTITY.md (自我认知)

4. USER.md (用户画像)

5. AGENTS.md (行为准则 & 记忆操作指南)

6. MEMORY.md (长期记忆)

## 3. AGENTS.md 的默认配置 (核心修正)

Agent 初始无技能读取认知，需初始化生成含明确元指令的 AGENTS.md，核心技能调用协议必须包含以下内容：

```plaintext
# 操作指南
## 技能调用协议 (SKILL PROTOCOL)
你拥有一个技能列表 (SKILLS_SNAPSHOT)，其中列出了你可以使用的能力及其定义文件的位置。
当你要使用某个技能时，必须严格遵守以下步骤：
1. 你的第一步行动永远是使用 `read_file` 工具读取该技能对应的 `location` 路径下的 Markdown 文件。
2. 仔细阅读文件中的内容、步骤和示例。
3. 根据文件中的指示，结合你内置的 Core Tools (terminal, python_repl, fetch_url) 来执行具体任务。
禁止直接猜测技能的参数或用法，必须先读取文件！

## 记忆协议
...
```

## 4. 会话存储 (Sessions)

- **存储路径**：`backend/sessions/{session_name}.json`

- **存储格式**：标准 JSON 数组，完整记录 user、assistant、tool (function calls) 三类消息，保留全量对话上下文

# 五、后端 API 接口规范 (FastAPI)

后端为独立运行进程，负责 Agent 逻辑、文件读写和状态管理，服务端口固定为 **8002**，基础 URL 为 `http://localhost:8002`。

## 1. 核心对话接口

- **Endpoint**：`POST /api/chat`

- **功能**：接收用户消息，返回 Agent 回复

- **请求体**：
        `{
  "message": "查询一下北京的天气",
  "session_id": "main_session",
  "stream": true
}`

- **响应格式**：支持 SSE (Server-Sent Events) 流式输出，实时推送 Agent 思考过程 (Thought/Tool Calls) 和最终回复

## 2. 文件管理接口 (前端编辑器专用)

- **读取文件**：`GET /api/files`，Query 参数 `path=memory/MEMORY.md`，返回指定文件内容

- **保存文件**：`POST /api/files`，请求体 `{"path": "...", "content": "..."}`，保存 Memory 或 Skill 文件修改

## 3. 会话管理接口

- **Endpoint**：`GET /api/sessions`

- **功能**：获取所有历史会话列表，支持按时间排序展示

# 六、前端开发要求

## 1. 设计理念与布局架构

前端采用**IDE 集成开发环境风格**，三栏式布局设计，各司其职：

- **左侧 (Sidebar)**：功能导航 (Chat/Memory/Skills) + 历史会话列表

- **中间 (Stage)**：对话流展示 + 可折叠思考链可视化 (Collapsible Thoughts)

- **右侧 (Inspector)**：Monaco 编辑器，实时查看/编辑当前使用的 SKILL.md 或 MEMORY.md

## 2. 技术栈

- **框架**：Next.js 14+ (App Router)、TypeScript

- **UI 组件**：Shadcn/UI、Tailwind CSS、Lucide Icons

- **编辑器**：Monaco Editor（默认配置 Light Theme）

## 3. UI/UX 风格规范

- **整体色调**：浅色 Apple 风格 (Frosty Glass)，背景为纯白/极浅灰 (#fafafa)，搭配高透毛玻璃效果；强调色选用克莱因蓝 (Klein Blue) 或活力橙

- **导航栏**：顶部固定、半透明设计，左侧展示“mini OpenClaw”标识，右侧放置“赋范空间”链接（跳转至 https://fufan.ai）

# 七、项目目录结构参考

```plaintext
mini-openclaw/
├── backend/                # FastAPI + LangChain/LangGraph 核心目录
│   ├── app.py              # 项目入口文件，绑定端口 8002
│   ├── memory/             # 长期记忆存储模块
│   │   ├── logs/           # 日常日志归档
│   │   └── MEMORY.md       # 核心长期记忆文件
│   ├── sessions/           # JSON 格式会话记录
│   ├── skills/             # Agent 自定义技能目录
│   │   └── get_weather/
│   │       └── SKILL.md    # 单技能说明书
│   ├── workspace/          # System Prompt 组件存放
│   │   ├── SOUL.md
│   │   ├── IDENTITY.md
│   │   ├── USER.md
│   │   └── AGENTS.md
│   ├── tools/              # 五大核心工具实现
│   ├── graph/              # LangGraph 状态机定义
│   └── requirements.txt     # Python 依赖清单
│
├── frontend/               # Next.js 14+ 前端项目
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── chat/       # 对话相关组件
│   │   │   └── editor/     # Monaco 编辑器封装组件
│   │   └── lib/
│   │       └── api.ts      # 后端 8002 端口接口封装
│   └── package.json        # 前端依赖清单
│
└── README.md               # 项目说明文档
```