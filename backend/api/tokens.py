"""Token 统计 API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import tiktoken

from graph.agent import agent_manager
import config as global_config


router = APIRouter()


class TokenFilesRequest(BaseModel):
    """批量统计文件 Token 请求"""
    paths: List[str]


# 使用 cl100k_base 编码器（与 GPT-4 系列一致）
encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """统计文本 Token 数"""
    return len(encoder.encode(text))


@router.get("/tokens/session/{session_id}")
async def get_session_tokens(session_id: str) -> Dict[str, int]:
    """获取会话 Token 统计"""
    # 获取 System Prompt
    rag_mode = global_config.config.get_rag_mode()
    system_prompt = agent_manager.prompt_builder.build_system_prompt(rag_mode=rag_mode)
    system_tokens = count_tokens(system_prompt)
    
    # 获取消息
    messages = agent_manager.session_manager.load_session(session_id)
    message_tokens = sum(count_tokens(msg["content"]) for msg in messages)
    
    return {
        "system_tokens": system_tokens,
        "message_tokens": message_tokens,
        "total_tokens": system_tokens + message_tokens
    }


@router.post("/tokens/files")
async def get_files_tokens(request: TokenFilesRequest) -> Dict[str, Dict[str, int]]:
    """批量统计文件 Token 数"""
    result = {}
    
    for path in request.paths:
        file_path = agent_manager.base_dir / path
        
        if not file_path.exists() or not file_path.is_file():
            result[path] = {"tokens": 0, "error": "文件不存在"}
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tokens = count_tokens(content)
            result[path] = {"tokens": tokens}
        
        except Exception as e:
            result[path] = {"tokens": 0, "error": str(e)}
    
    return result
