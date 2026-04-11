"""MCP 连接管理器：管理所有 MCP Server 的连接、工具发现和生命周期"""
import asyncio
import json
import logging
import sys
import uuid
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool

from .mcp_tool_wrapper import create_mcp_tool

logger = logging.getLogger(__name__)


class _McpBackgroundLoop:
    """后台 ProactorEventLoop 线程，用于 Windows 上的 MCP 子进程支持。

    Windows 上 asyncio.create_subprocess_exec 需要 ProactorEventLoop。
    uvicorn 在 reload 模式下会使用 SelectorEventLoop，导致子进程无法创建。
    此类在单独的线程中运行 ProactorEventLoop，所有 MCP 操作都在此线程中执行。
    """

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started = False
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()  # 用于等待循环创建完成

    def start(self):
        """启动后台线程和事件循环"""
        if self._started:
            return

        def run_loop():
            if sys.platform == "win32":
                policy = asyncio.WindowsProactorEventLoopPolicy()
                self._loop = policy.new_event_loop()
            else:
                self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # 通知主线程循环已准备好
            self._ready_event.set()

            # 运行事件循环直到收到停止信号
            while not self._stop_event.is_set():
                # 运行所有待处理的任务
                self._loop.run_until_complete(asyncio.sleep(0.1))

            # 清理并关闭循环
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

        # 等待循环创建完成
        self._ready_event.wait(timeout=5)
        self._started = True
        logger.info("[MCP] 后台 ProactorEventLoop 线程已启动")

    def stop(self):
        """停止后台线程和事件循环"""
        if not self._started:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._started = False
        logger.info("[MCP] 后台 ProactorEventLoop 线程已停止")

    def run_coroutine(self, coro, timeout=60):
        """在后台循环中运行协程并返回结果"""
        if not self._started:
            self.start()

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """返回后台事件循环"""
        if not self._started:
            self.start()
        return self._loop


# 全局后台循环实例（用于 Windows）
_background_loop: Optional[_McpBackgroundLoop] = None


def get_background_loop() -> _McpBackgroundLoop:
    """获取全局后台循环实例"""
    global _background_loop
    if _background_loop is None:
        _background_loop = _McpBackgroundLoop()
    return _background_loop


class McpServerConnection:
    """单个 MCP Server 连接的状态容器"""

    def __init__(self, config: dict):
        self.config = config
        self.session: Any = None
        self.status: str = "disconnected"
        self.error: Optional[str] = None
        self.tools: List[dict] = []
        self._context_stack: Any = None
        self._session_stack: Any = None
        self._read_stream: Any = None
        self._write_stream: Any = None

    @property
    def server_id(self) -> str:
        return self.config.get("id", "")

    @property
    def enabled(self) -> bool:
        return self.config.get("enabled", True)


class McpManager:
    """MCP 连接管理器

    负责：
    - 读取 mcp_servers.json 配置
    - 为每个启用的 Server 建立连接
    - 发现并包装远端工具
    - 管理连接生命周期
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.config_path = base_dir / "mcp_servers.json"
        self.connections: Dict[str, McpServerConnection] = {}
        self.tools: List[BaseTool] = []

    def _load_config(self) -> List[dict]:
        """从 mcp_servers.json 加载配置"""
        if not self.config_path.exists():
            return []
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("servers", [])
        except Exception as e:
            logger.error(f"[MCP] 加载配置失败: {e}")
            return []

    def _save_config(self, servers: List[dict]) -> None:
        """保存配置到 mcp_servers.json"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"servers": servers}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[MCP] 保存配置失败: {e}")

    def get_all_configs(self) -> List[dict]:
        """获取所有 Server 配置（含运行时状态）"""
        configs = self._load_config()
        result = []
        for cfg in configs:
            sid = cfg.get("id", "")
            conn = self.connections.get(sid)
            entry = {**cfg}
            if conn:
                entry["status"] = conn.status
                entry["error"] = conn.error
                entry["tools"] = conn.tools
            else:
                entry["status"] = "disconnected"
                entry["error"] = None
                entry["tools"] = []
            result.append(entry)
        return result

    def add_server(self, server_config: dict) -> dict:
        """添加新的 MCP Server 配置"""
        servers = self._load_config()
        if "id" not in server_config or not server_config["id"]:
            server_config["id"] = str(uuid.uuid4())[:8]
        servers.append(server_config)
        self._save_config(servers)
        return server_config

    def update_server(self, server_id: str, updates: dict) -> Optional[dict]:
        """更新 MCP Server 配置"""
        servers = self._load_config()
        for i, s in enumerate(servers):
            if s.get("id") == server_id:
                servers[i] = {**s, **updates, "id": server_id}
                self._save_config(servers)
                return servers[i]
        return None

    def delete_server(self, server_id: str) -> bool:
        """删除 MCP Server 配置"""
        servers = self._load_config()
        new_servers = [s for s in servers if s.get("id") != server_id]
        if len(new_servers) == len(servers):
            return False
        self._save_config(new_servers)
        return True

    def toggle_server(self, server_id: str) -> Optional[dict]:
        """启用/禁用 MCP Server"""
        servers = self._load_config()
        for i, s in enumerate(servers):
            if s.get("id") == server_id:
                servers[i]["enabled"] = not s.get("enabled", True)
                self._save_config(servers)
                return servers[i]
        return None

    async def connect_all(self) -> None:
        """连接所有启用的 MCP Server"""
        servers = self._load_config()
        self.tools = []

        # 在 Windows 上使用后台 ProactorEventLoop
        if sys.platform == "win32":
            bg_loop = get_background_loop()
            bg_loop.start()
            # 在后台循环中执行连接（使用 asyncio.run_coroutine_threadsafe）
            # 注意：这里需要在 async 函数中等待后台线程完成
            future = asyncio.run_coroutine_threadsafe(
                self._connect_all_internal(servers), bg_loop.loop
            )
            # 使用 wait 而不是阻塞等待
            while not future.done():
                await asyncio.sleep(0.1)
            # 获取结果或异常
            try:
                future.result()
            except Exception as e:
                logger.error(f"[MCP] 连接过程中出错: {e}")
        else:
            # 非 Windows 平台直接执行
            await self._connect_all_internal(servers)

        logger.info(f"[MCP] 连接完成，共加载 {len(self.tools)} 个 MCP 工具")

    async def _connect_all_internal(self, servers: List[dict]) -> None:
        """内部连接逻辑"""
        for server_cfg in servers:
            if not server_cfg.get("enabled", True):
                logger.info(f"[MCP] 跳过已禁用的 Server: {server_cfg.get('name', server_cfg.get('id'))}")
                conn = McpServerConnection(server_cfg)
                conn.status = "disabled"
                self.connections[server_cfg["id"]] = conn
                continue

            await self._connect_server(server_cfg)

    async def _connect_server(self, server_cfg: dict) -> None:
        """连接单个 MCP Server"""
        server_id = server_cfg.get("id", "unknown")
        server_name = server_cfg.get("name", server_id)
        transport = server_cfg.get("transport", "stdio")

        conn = McpServerConnection(server_cfg)
        self.connections[server_id] = conn

        try:
            if transport == "stdio":
                await self._connect_stdio(conn, server_cfg)
            elif transport == "sse":
                await self._connect_sse(conn, server_cfg)
            else:
                raise ValueError(f"不支持的 transport 类型: {transport}")

            tools_response = await conn.session.list_tools()
            tool_infos = tools_response.tools if hasattr(tools_response, 'tools') else []

            conn.tools = [
                {"name": t.name, "description": t.description or ""}
                for t in tool_infos
            ]

            for tool_info in tool_infos:
                wrapper = create_mcp_tool(conn.session, server_id, tool_info)
                self.tools.append(wrapper)

            conn.status = "connected"
            conn.error = None
            logger.info(
                f"[MCP] Server '{server_name}' 连接成功，发现 {len(tool_infos)} 个工具"
            )

        except Exception as e:
            import traceback
            error_detail = str(e) if str(e) else f"{type(e).__name__}"
            conn.status = "error"
            conn.error = error_detail
            logger.error(f"[MCP] Server '{server_name}' 连接失败: {error_detail}")
            logger.error(f"[MCP] 异常详情:\n{traceback.format_exc()}")

    async def _connect_stdio(self, conn: McpServerConnection, cfg: dict) -> None:
        """建立 stdio 连接"""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        command = cfg.get("command", "")
        args = cfg.get("args", [])
        env = cfg.get("env") or None

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env,
        )

        transport_ctx = stdio_client(server_params)
        read_stream, write_stream = await transport_ctx.__aenter__()
        conn._context_stack = transport_ctx

        session_ctx = ClientSession(read_stream, write_stream)
        session = await session_ctx.__aenter__()
        conn._session_stack = session_ctx
        conn.session = session

        await session.initialize()

    async def _connect_sse(self, conn: McpServerConnection, cfg: dict) -> None:
        """建立 SSE 连接"""
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        url = cfg.get("url", "")
        headers = cfg.get("headers") or {}

        transport_ctx = sse_client(url=url, headers=headers)
        read_stream, write_stream = await transport_ctx.__aenter__()
        conn._context_stack = transport_ctx

        session_ctx = ClientSession(read_stream, write_stream)
        session = await session_ctx.__aenter__()
        conn._session_stack = session_ctx
        conn.session = session

        await session.initialize()

    async def disconnect_all(self) -> None:
        """断开所有连接，清理资源"""
        # 在 Windows 上使用后台循环执行断开操作
        if sys.platform == "win32":
            bg_loop = get_background_loop()
            if bg_loop._started:
                bg_loop.run_coroutine(self._disconnect_all_internal())
                bg_loop.stop()
        else:
            await self._disconnect_all_internal()

        self.connections.clear()
        self.tools.clear()
        logger.info("[MCP] 所有连接已断开")

    async def _disconnect_all_internal(self) -> None:
        """内部断开逻辑"""
        for server_id, conn in self.connections.items():
            await self._disconnect_server(conn)

    async def _disconnect_server(self, conn: McpServerConnection) -> None:
        """断开单个 Server 连接"""
        try:
            if conn._session_stack:
                await conn._session_stack.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"[MCP] 关闭 session 时出错: {e}")

        try:
            if conn._context_stack:
                await conn._context_stack.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"[MCP] 关闭 transport 时出错: {e}")

        conn.session = None
        conn.status = "disconnected"

    async def reload(self) -> Dict[str, Any]:
        """热重载：断开所有连接 -> 重新连接 -> 返回状态"""
        logger.info("[MCP] 开始热重载...")
        await self.disconnect_all()
        await self.connect_all()
        return {
            "tools_count": len(self.tools),
            "servers": self.get_all_configs(),
        }

    def get_mcp_tools(self) -> List[BaseTool]:
        """返回所有 MCP 工具（已包装为 LangChain BaseTool）"""
        return list(self.tools)