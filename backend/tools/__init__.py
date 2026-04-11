"""工具注册工厂"""
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from langchain_core.tools import BaseTool

from .terminal_tool import create_terminal_tool
from .python_repl_tool import create_python_repl_tool
from .fetch_url_tool import create_fetch_url_tool
from .read_file_tool import create_read_file_tool
from .search_knowledge_tool import create_search_knowledge_tool

if TYPE_CHECKING:
    from .mcp_manager import McpManager


def get_all_tools(base_dir: Path, mcp_manager: Optional["McpManager"] = None) -> List[BaseTool]:
    """获取所有工具（内建 + MCP）
    
    Args:
        base_dir: 项目根目录
        mcp_manager: MCP 连接管理器（可选）
        
    Returns:
        工具列表
    """
    tools = [
        create_terminal_tool(base_dir),
        create_python_repl_tool(),
        create_fetch_url_tool(),
        create_read_file_tool(base_dir),
        create_search_knowledge_tool(base_dir),
    ]
    
    if mcp_manager:
        mcp_tools = mcp_manager.get_mcp_tools()
        tools.extend(mcp_tools)
    
    return tools
