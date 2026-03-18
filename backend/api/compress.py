"""对话压缩 API"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from graph.agent import agent_manager
from langchain_deepseek import ChatDeepSeek
import config as global_config


router = APIRouter()


@router.post("/sessions/{session_id}/compress")
async def compress_session(session_id: str) -> Dict[str, Any]:
    """压缩对话历史"""
    # 获取消息
    messages = agent_manager.session_manager.load_session(session_id)
    
    if len(messages) < 4:
        raise HTTPException(status_code=400, detail="消息数量不足，无法压缩（至少需要 4 条消息）")
    
    # 计算要压缩的消息数量（前 50%，至少 4 条）
    num_to_compress = max(4, len(messages) // 2)
    messages_to_compress = messages[:num_to_compress]
    
    # 构建压缩提示
    conversation_text = ""
    for msg in messages_to_compress:
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg["content"][:500]  # 截断过长内容
        conversation_text += f"{role}：{content}\n\n"
    
    prompt = f"""请将以下对话历史总结为一段简洁的中文摘要（不超过500字）：

{conversation_text}

要求：
1. 保留关键信息和上下文
2. 简洁明了，便于后续对话参考
3. 只返回摘要内容，不要其他说明"""
    
    # 调用 LLM 生成摘要
    llm = ChatDeepSeek(
        model=global_config.config.deepseek_model,
        api_key=global_config.config.deepseek_api_key,
        base_url=global_config.config.deepseek_base_url,
        temperature=0.3,
    )
    
    response = await llm.ainvoke(prompt)
    summary = response.content.strip()
    
    # 压缩历史
    agent_manager.session_manager.compress_history(
        session_id,
        summary,
        num_to_compress
    )
    
    return {
        "archived_count": num_to_compress,
        "remaining_count": len(messages) - num_to_compress,
        "summary": summary
    }
