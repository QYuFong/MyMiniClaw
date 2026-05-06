"""聊天 API"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncGenerator, List, Dict, Any
import json

from graph.agent import agent_manager
from langchain_deepseek import ChatDeepSeek
import config as global_config


router = APIRouter()
logger = logging.getLogger(__name__)

# 日志文件
log_file = Path(__file__).parent.parent / "debug.log"


def log_to_file(msg: str):
    """直接写入日志文件"""
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {msg}\n")
            f.flush()
    except Exception as e:
        print(f"Log error: {e}")


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: str
    stream: bool = True


async def trigger_memory_extraction(messages: List[Dict[str, Any]]) -> str:
    """触发记忆提取

    使用 compress.py 中的 _evolve_memory 函数

    Args:
        messages: 会话消息列表

    Returns:
        提取后的记忆内容
    """
    from api.compress import _evolve_memory

    try:
        log_to_file(f"[MEMORY] 开始自动记忆提取，消息数量: {len(messages)}")
        latest_memory = await _evolve_memory(messages)
        log_to_file(f"[MEMORY] 记忆提取完成，长度: {len(latest_memory)} 字符")
        return latest_memory
    except Exception as e:
        log_to_file(f"[MEMORY] 记忆提取失败: {str(e)}")
        return ""


async def event_generator(
    message: str,
    session_id: str
) -> AsyncGenerator[str, None]:
    """SSE 事件生成器"""
    try:
        log_to_file(f"\n{'='*60}")
        log_to_file(f"[API] event_generator 被调用")
        log_to_file(f"[API] Session ID: {session_id}")
        log_to_file(f"[API] 消息内容: {message}")
        log_to_file(f"{'='*60}\n")
        
        # 加载会话历史
        history = agent_manager.session_manager.load_session_for_agent(session_id)
        log_to_file(f"[API] 加载历史消息: {len(history)} 条")
        
        # 判断是否为首条消息
        is_first_message = len(history) == 0
        
        # 保存用户消息
        agent_manager.session_manager.save_message(
            session_id,
            "user",
            message
        )
        log_to_file(f"[API] 用户消息已保存")
        
        # 流式调用 Agent
        log_to_file(f"[API] 开始调用 Agent.astream...")
        full_content = ""
        
        async for event in agent_manager.astream(message, history):
            event_type = event["type"]
            
            if event_type == "retrieval":
                # RAG 检索结果
                log_to_file(f"[API] 收到 RAG 检索结果")
                yield f"event: retrieval\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            elif event_type == "token":
                # Token 流
                content = event["content"]
                full_content += content
                yield f"event: token\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            elif event_type == "tool_start":
                # 工具调用开始
                yield f"event: tool_start\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            elif event_type == "tool_end":
                # 工具调用结束
                yield f"event: tool_end\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            elif event_type == "assistant_message":
                # assistant 消息（可能带 tool_calls）- 用于前端展示，不在这里保存
                yield f"event: assistant_message\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            elif event_type == "tool_message":
                # tool 消息 - 用于前端展示，不在这里保存
                yield f"event: tool_message\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            elif event_type == "new_response":
                # 新的响应段开始
                yield f"event: new_response\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            elif event_type == "done":
                # 响应完成
                # 从 agent 返回的 messages 列表中保存所有消息
                generated_messages = event.get("messages", [])
                log_to_file(f"[API] 收到 {len(generated_messages)} 条生成的消息")

                for msg in generated_messages:
                    role = msg.get("role", "assistant")
                    content = msg.get("content", "")

                    if role == "assistant":
                        tool_calls = msg.get("tool_calls")
                        agent_manager.session_manager.save_message(
                            session_id,
                            "assistant",
                            content,
                            tool_calls if tool_calls else None
                        )
                    elif role == "tool":
                        # 保存 tool 消息
                        agent_manager.session_manager.save_tool_message(
                            session_id,
                            tool_call_id=msg.get("tool_call_id", ""),
                            name=msg.get("name", ""),
                            content=content
                        )

                # === 轮次计数与记忆提取 ===
                # 增加轮次计数
                current_turn = agent_manager.session_manager.increment_turn_count(session_id)
                log_to_file(f"[API] 当前轮次: {current_turn}")

                # 检查是否需要触发记忆提取（每5轮）
                if agent_manager.session_manager.should_trigger_memory_extraction(session_id):
                    log_to_file(f"[API] 触发自动记忆提取（每5轮）")

                    # 获取当前会话所有消息
                    all_messages = agent_manager.session_manager.load_session(session_id)

                    # 调用记忆提取
                    memory_result = await trigger_memory_extraction(all_messages)

                    # 更新上次提取轮次
                    agent_manager.session_manager.update_last_memory_turn(session_id, current_turn)

                    # 通知前端记忆已更新
                    if memory_result:
                        yield f"event: memory_updated\ndata: {json.dumps({'turn': current_turn}, ensure_ascii=False)}\n\n"

                yield f"event: done\ndata: {json.dumps({'content': full_content, 'session_id': session_id}, ensure_ascii=False)}\n\n"
            
            elif event_type == "error":
                # 错误
                yield f"event: error\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                return
        
        # 如果是首条消息，生成标题
        if is_first_message:
            try:
                title = await _generate_title(message, full_content)
                agent_manager.session_manager.update_title(session_id, title)
                yield f"event: title\ndata: {json.dumps({'session_id': session_id, 'title': title}, ensure_ascii=False)}\n\n"
            except Exception as e:
                print(f"生成标题失败: {e}")
    
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"


async def _generate_title(user_message: str, assistant_response: str) -> str:
    """生成会话标题
    
    Args:
        user_message: 用户消息
        assistant_response: 助手回复
        
    Returns:
        标题（≤10 字）
    """
    llm = ChatDeepSeek(
        model=global_config.config.deepseek_model,
        api_key=global_config.config.deepseek_api_key,
        base_url=global_config.config.deepseek_base_url,
        temperature=0.3,
    )
    
    prompt = f"""根据以下对话内容，生成一个简短的中文标题（不超过10个字）：

用户：{user_message[:200]}
助手：{assistant_response[:200]}

只返回标题，不要其他内容。"""
    
    response = await llm.ainvoke(prompt)
    title = response.content.strip()
    
    # 去掉可能的引号
    title = title.strip('"').strip("'").strip("《》")
    
    # 限制长度
    if len(title) > 10:
        title = title[:10]
    
    return title


@router.post("/chat")
async def chat(request: ChatRequest):
    """聊天接口（SSE 流式）"""
    msg = f"\n{'='*60}\n[ENDPOINT] /chat 接收到 POST 请求\n[ENDPOINT] Message: {request.message}\n[ENDPOINT] Session ID: {request.session_id}\n[ENDPOINT] Stream: {request.stream}\n{'='*60}\n"
    logger.info(msg)
    log_to_file(msg)
    log_to_file(f"[ENDPOINT] 开始处理请求...")
    
    if request.stream:
        log_to_file(f"[ENDPOINT] 返回 StreamingResponse")
        return StreamingResponse(
            event_generator(request.message, request.session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # 非流式模式（暂不实现）
        log_to_file(f"[ENDPOINT] 非流式模式")
        return {"error": "Non-streaming mode not implemented"}
