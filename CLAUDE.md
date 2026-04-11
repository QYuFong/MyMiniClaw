# CLAUDE.md

本文档为 Claude Code 提供项目入口指引。

> **完整项目指南请参阅 [AGENTS.md](AGENTS.md)**

## 快速参考

### 项目定位

Mini OpenClaw - 轻量级全透明 AI Agent 系统（文件驱动、指令式技能、透明可控）

### 环境启动

```bash
# 必须先激活 Conda 环境
conda activate miniclaw

# 一键启动
start.bat  # Windows
./start.sh # Linux/macOS

# 或手动启动后端（需先 conda activate miniclaw）
cd backend && uvicorn app:app --port 8002 --reload
cd frontend && npm run dev
```

### 环境约束

**所有 Python 依赖安装在 `miniclaw` Conda 环境，启动前必须先激活：**

```bash
conda activate miniclaw  # 必须步骤
```

### 关键路径

| 路径 | 用途 |
|------|------|
| [backend/app.py](backend/app.py) | FastAPI 入口 |
| [backend/graph/agent.py](backend/graph/agent.py) | Agent 主循环 |
| [backend/tools/](backend/tools/) | 六大核心工具 |
| [backend/tools/mcp_manager.py](backend/tools/mcp_manager.py) | MCP 连接管理器 |
| [backend/tools/mcp_tool_wrapper.py](backend/tools/mcp_tool_wrapper.py) | MCP 工具包装器 |
| [backend/mcp_servers.json](backend/mcp_servers.json) | MCP Server 配置 |
| [backend/workspace/](backend/workspace/) | System Prompt 组件 |
| [backend/skills/](backend/skills/) | 技能目录 |
| [backend/api/mcp.py](backend/api/mcp.py) | MCP 管理 API |

### 开发约定

- Python 3.12 + PEP 8
- 技能文件必须有 frontmatter（name, description）
- 工具实现 LangChain Tool 接口
- 所有数据以文件形式存储

### 必读文档

- [AGENTS.md](AGENTS.md) - 完整项目指南
- [README.md](README.md) - 项目介绍与快速开始