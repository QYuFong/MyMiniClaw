"""MCP 配置管理 API"""
import logging
from typing import Optional, List, Dict

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from graph.agent import agent_manager

router = APIRouter()
logger = logging.getLogger(__name__)


class McpServerCreate(BaseModel):
    """创建 MCP Server 请求体"""
    name: str
    enabled: bool = True
    transport: str  # "stdio" | "sse"
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class McpServerUpdate(BaseModel):
    """更新 MCP Server 请求体"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    transport: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


def _get_mcp_manager(request: Request):
    """从 app.state 获取 McpManager"""
    mcp_mgr = getattr(request.app.state, "mcp_manager", None)
    if not mcp_mgr:
        raise HTTPException(status_code=500, detail="MCP Manager 未初始化")
    return mcp_mgr


@router.get("/mcp/servers")
async def get_mcp_servers(request: Request):
    """获取所有 MCP 服务器配置及连接状态"""
    mcp_mgr = _get_mcp_manager(request)
    return mcp_mgr.get_all_configs()


@router.post("/mcp/servers")
async def add_mcp_server(request: Request, body: McpServerCreate):
    """添加新的 MCP 服务器配置"""
    mcp_mgr = _get_mcp_manager(request)

    server_config = body.model_dump(exclude_none=True)
    result = mcp_mgr.add_server(server_config)
    return result


@router.put("/mcp/servers/{server_id}")
async def update_mcp_server(request: Request, server_id: str, body: McpServerUpdate):
    """修改 MCP 服务器配置"""
    mcp_mgr = _get_mcp_manager(request)

    updates = body.model_dump(exclude_none=True)
    result = mcp_mgr.update_server(server_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Server '{server_id}' 不存在")
    return result


@router.delete("/mcp/servers/{server_id}")
async def delete_mcp_server(request: Request, server_id: str):
    """删除 MCP 服务器配置"""
    mcp_mgr = _get_mcp_manager(request)

    success = mcp_mgr.delete_server(server_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Server '{server_id}' 不存在")
    return {"success": True}


@router.post("/mcp/servers/{server_id}/toggle")
async def toggle_mcp_server(request: Request, server_id: str):
    """启用/禁用 MCP 服务器"""
    mcp_mgr = _get_mcp_manager(request)

    result = mcp_mgr.toggle_server(server_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Server '{server_id}' 不存在")
    return result


@router.post("/mcp/reload")
async def reload_mcp(request: Request):
    """热重载所有 MCP 连接并刷新 Agent 工具列表"""
    mcp_mgr = _get_mcp_manager(request)

    result = await mcp_mgr.reload()

    agent_manager.refresh_tools()

    return result
