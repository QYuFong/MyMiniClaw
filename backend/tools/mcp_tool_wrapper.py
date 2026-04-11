"""MCP 工具到 LangChain BaseTool 的适配器"""
import asyncio
import logging
import sys
from typing import Any, Dict, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, create_model

logger = logging.getLogger(__name__)


def _get_mcp_background_loop():
    """获取 MCP 后台 ProactorEventLoop（用于 Windows）"""
    # 导入后台循环管理器
    from .mcp_manager import get_background_loop
    return get_background_loop()


def _build_pydantic_model(tool_name: str, input_schema: dict) -> Type[BaseModel]:
    """根据 MCP tool 的 inputSchema (JSON Schema) 动态生成 Pydantic model"""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    field_definitions: Dict[str, Any] = {}
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    for prop_name, prop_schema in properties.items():
        prop_type = type_map.get(prop_schema.get("type", "string"), str)
        description = prop_schema.get("description", "")

        if prop_name in required:
            field_definitions[prop_name] = (prop_type, ...)
        else:
            default = prop_schema.get("default", None)
            field_definitions[prop_name] = (Optional[prop_type], default)

    model_name = f"McpInput_{tool_name}"
    return create_model(model_name, **field_definitions)


class McpToolWrapper(BaseTool):
    """将 MCP Server 暴露的工具包装为 LangChain BaseTool"""

    name: str
    description: str
    args_schema: Optional[Type[BaseModel]] = None

    mcp_session: Any = None
    mcp_tool_name: str = ""
    server_id: str = ""

    class Config:
        arbitrary_types_allowed = True

    def _run(self, input: Any = None, **kwargs: Any) -> str:
        """同步调用（在已有事件循环中通过 asyncio 桥接）

        LangChain BaseTool 调用 _run(input) 时传递位置参数，
        所以需要接受 input 参数。同时保留 **kwargs 以兼容其他调用方式。
        """
        # 确定最终参数
        final_kwargs = {}
        if input is not None:
            if isinstance(input, dict):
                final_kwargs = input
            else:
                # 如果 input 不是字典，可能是错误调用，记录警告
                logger.warning(f"[MCP] 工具 {self.mcp_tool_name} 收到非字典输入: {input}")
                final_kwargs = {"input": input}
        if kwargs:
            final_kwargs = {**final_kwargs, **kwargs}

        # Windows 上必须使用后台 ProactorEventLoop，因为 MCP session 在那里创建
        if sys.platform == "win32":
            bg_loop = _get_mcp_background_loop()
            if bg_loop._started:
                # 使用 run_coroutine_threadsafe 在后台循环中执行
                future = asyncio.run_coroutine_threadsafe(
                    self._arun(**final_kwargs), bg_loop.loop
                )
                try:
                    return future.result(timeout=60)
                except Exception as e:
                    logger.error(f"[MCP] 工具执行超时或异常: {e}")
                    return f"错误：工具执行失败 - {str(e)}"
            else:
                logger.warning("[MCP] 后台循环未启动，尝试直接执行")
                return asyncio.run(self._arun(**final_kwargs))

        # 非 Windows 平台
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self._arun(**final_kwargs))
                return future.result(timeout=60)
        else:
            return asyncio.run(self._arun(**final_kwargs))

    async def _arun(self, **kwargs: Any) -> str:
        """异步调用 MCP session.call_tool()"""
        try:
            logger.info(f"[MCP] 调用工具 {self.mcp_tool_name}@{self.server_id}, 参数: {kwargs}")
            result = await self.mcp_session.call_tool(self.mcp_tool_name, arguments=kwargs)
            return self._format_result(result)
        except Exception as e:
            error_msg = f"MCP 工具调用失败 [{self.mcp_tool_name}@{self.server_id}]: {e}"
            logger.error(error_msg)
            return f"错误：{error_msg}"

    @staticmethod
    def _format_result(result: Any) -> str:
        """将 MCP ToolResult 格式化为文本"""
        if not result or not result.content:
            return "(无输出)"

        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
            elif hasattr(block, "data"):
                parts.append(f"[二进制数据: {block.mimeType}]")
            else:
                parts.append(str(block))

        output = "\n".join(parts)
        if len(output) > 10000:
            output = output[:10000] + "\n...[输出被截断]"
        return output


def create_mcp_tool(
    session: Any,
    server_id: str,
    tool_info: Any,
) -> McpToolWrapper:
    """根据 MCP tool 信息创建 LangChain 工具包装器

    Args:
        session: MCP ClientSession
        server_id: MCP Server 的 ID
        tool_info: MCP list_tools 返回的 tool 对象

    Returns:
        McpToolWrapper 实例
    """
    prefixed_name = f"mcp_{server_id}_{tool_info.name}"

    input_schema = {}
    if hasattr(tool_info, "inputSchema") and tool_info.inputSchema:
        input_schema = tool_info.inputSchema
    elif hasattr(tool_info, "input_schema") and tool_info.input_schema:
        input_schema = tool_info.input_schema

    args_model = None
    if input_schema and input_schema.get("properties"):
        try:
            args_model = _build_pydantic_model(prefixed_name, input_schema)
        except Exception as e:
            logger.warning(f"[MCP] 无法为 {prefixed_name} 生成 args_schema: {e}")

    description = tool_info.description or f"MCP tool: {tool_info.name}"
    description = f"[MCP:{server_id}] {description}"

    wrapper = McpToolWrapper(
        name=prefixed_name,
        description=description,
        args_schema=args_model,
        mcp_session=session,
        mcp_tool_name=tool_info.name,
        server_id=server_id,
    )

    logger.info(f"[MCP] 创建工具: {prefixed_name}")
    return wrapper
