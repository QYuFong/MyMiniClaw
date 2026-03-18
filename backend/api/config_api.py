"""配置管理 API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

import config as global_config


router = APIRouter()


class RAGModeRequest(BaseModel):
    """RAG 模式请求"""
    enabled: bool


@router.get("/config/rag-mode")
async def get_rag_mode() -> Dict[str, bool]:
    """获取 RAG 模式状态"""
    return {"enabled": global_config.config.get_rag_mode()}


@router.put("/config/rag-mode")
async def set_rag_mode(request: RAGModeRequest) -> Dict[str, str]:
    """切换 RAG 模式"""
    global_config.config.set_rag_mode(request.enabled)
    return {"status": "success"}
