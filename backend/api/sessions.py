"""会话管理 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid

from graph.agent import agent_manager
from langchain_deepseek import ChatDeepSeek
import config as global_config


router = APIRouter()


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    title: str = "新对话"


class RenameSessionRequest(BaseModel):
    """重命名会话请求"""
    title: str


@router.get("/sessions")
async def list_sessions() -> List[Dict[str, Any]]:
    """列出所有会话"""
    return agent_manager.session_manager.list_sessions()


@router.post("/sessions")
async def create_session(request: CreateSessionRequest) -> Dict[str, Any]:
    """创建新会话"""
    session_id = str(uuid.uuid4())
    
    # 保存初始会话元数据
    agent_manager.session_manager.save_message(session_id, "user", "")
    agent_manager.session_manager.update_title(session_id, request.title)
    
    # 删除刚才的占位消息
    session = agent_manager.session_manager.load_session(session_id)
    if session and len(session) == 1 and session[0]["content"] == "":
        # 直接清空消息列表
        import json
        from pathlib import Path
        session_file = agent_manager.session_manager.sessions_dir / f"{session_id}.json"
        data = {
            "title": request.title,
            "created_at": agent_manager.session_manager._read_file(session_file)["created_at"],
            "updated_at": agent_manager.session_manager._read_file(session_file)["updated_at"],
            "messages": []
        }
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    return {
        "id": session_id,
        "title": request.title
    }


@router.put("/sessions/{session_id}")
async def rename_session(session_id: str, request: RenameSessionRequest) -> Dict[str, str]:
    """重命名会话"""
    agent_manager.session_manager.update_title(session_id, request.title)
    return {"status": "success"}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """删除会话"""
    success = agent_manager.session_manager.delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {"status": "success"}


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str) -> Dict[str, Any]:
    """获取完整消息（含 System Prompt）"""
    # 获取 System Prompt
    rag_mode = global_config.config.get_rag_mode()
    system_prompt = agent_manager.prompt_builder.build_system_prompt(rag_mode=rag_mode)
    
    # 获取消息
    messages = agent_manager.session_manager.load_session(session_id)
    
    return {
        "system_prompt": system_prompt,
        "messages": messages
    }


@router.get("/sessions/{session_id}/history")
async def get_history(session_id: str) -> List[Dict[str, Any]]:
    """获取对话历史（不含 System Prompt）"""
    return agent_manager.session_manager.load_session(session_id)


@router.post("/sessions/{session_id}/generate-title")
async def generate_title(session_id: str) -> Dict[str, str]:
    """AI 生成标题"""
    messages = agent_manager.session_manager.load_session(session_id)
    
    if not messages:
        raise HTTPException(status_code=400, detail="会话无消息")
    
    # 提取前两条消息
    user_msg = ""
    assistant_msg = ""
    
    for msg in messages:
        if msg["role"] == "user" and not user_msg:
            user_msg = msg["content"]
        elif msg["role"] == "assistant" and not assistant_msg:
            assistant_msg = msg["content"]
        
        if user_msg and assistant_msg:
            break
    
    # 生成标题
    llm = ChatDeepSeek(
        model=global_config.config.deepseek_model,
        api_key=global_config.config.deepseek_api_key,
        base_url=global_config.config.deepseek_base_url,
        temperature=0.3,
    )
    
    prompt = f"""根据以下对话内容，生成一个简短的中文标题（不超过10个字）：

用户：{user_msg[:200]}
助手：{assistant_msg[:200]}

只返回标题，不要其他内容。"""
    
    response = await llm.ainvoke(prompt)
    title = response.content.strip().strip('"').strip("'").strip("《》")
    
    if len(title) > 10:
        title = title[:10]
    
    # 更新标题
    agent_manager.session_manager.update_title(session_id, title)
    
    return {"title": title}
