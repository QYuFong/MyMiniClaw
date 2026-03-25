"""对话压缩 API"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from graph.agent import agent_manager
from langchain_deepseek import ChatDeepSeek
import config as global_config


router = APIRouter()


def _format_messages_for_compression(messages: List[Dict[str, Any]]) -> str:
    """将消息列表格式化为可读文本，用于 LLM 压缩
    
    规则：
    1. 保留所有用户消息的完整内容
    2. 工具调用过程用自然语言概括
    3. 保留 assistant 最终答复的核心内容
    
    Args:
        messages: 消息列表
        
    Returns:
        格式化后的文本
    """
    formatted_parts = []
    i = 0
    
    while i < len(messages):
        msg = messages[i]
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "user":
            # 用户消息：完整保留
            formatted_parts.append(f"【用户提问】\n{content}")
            i += 1
            
        elif role == "assistant":
            tool_calls = msg.get("tool_calls", [])
            
            if tool_calls:
                # assistant 带 tool_calls：收集后续的工具执行和最终答复
                tool_descriptions = []
                
                # 收集工具调用信息
                for tc in tool_calls:
                    tool_name = tc.get("name", "未知工具")
                    tool_args = tc.get("args", {})
                    tool_descriptions.append(f"调用工具 [{tool_name}]")
                
                # 跳过当前 assistant 消息
                i += 1
                
                # 收集后续的 tool 消息
                while i < len(messages) and messages[i].get("role") == "tool":
                    tool_msg = messages[i]
                    tool_name = tool_msg.get("name", "工具")
                    tool_content = tool_msg.get("content", "")
                    # 截取工具输出的核心部分（前 200 字符）
                    tool_summary = tool_content[:200] + "..." if len(tool_content) > 200 else tool_content
                    tool_descriptions.append(f"工具 [{tool_name}] 返回结果摘要: {tool_summary}")
                    i += 1
                
                # 查找最终的 assistant 融合答复
                final_response = ""
                if i < len(messages) and messages[i].get("role") == "assistant" and not messages[i].get("tool_calls"):
                    final_response = messages[i].get("content", "")
                    i += 1
                
                # 构建工具调用摘要
                tool_summary_text = "\n".join(tool_descriptions)
                if final_response:
                    # 截取最终答复的核心部分（前 500 字符）
                    response_summary = final_response[:500] + "..." if len(final_response) > 500 else final_response
                    formatted_parts.append(f"【助手操作】\n{tool_summary_text}\n【助手答复摘要】\n{response_summary}")
                else:
                    formatted_parts.append(f"【助手操作】\n{tool_summary_text}")
            else:
                # 纯文本 assistant 消息（无工具调用）
                # 截取核心内容（前 500 字符）
                response_summary = content[:500] + "..." if len(content) > 500 else content
                formatted_parts.append(f"【助手回复】\n{response_summary}")
                i += 1
                
        elif role == "tool":
            # 单独的 tool 消息（理论上不应该单独出现，但防御性处理）
            tool_name = msg.get("name", "工具")
            tool_content = content[:200] + "..." if len(content) > 200 else content
            formatted_parts.append(f"【工具结果】[{tool_name}]: {tool_content}")
            i += 1
            
        else:
            # 未知角色
            i += 1
    
    return "\n\n".join(formatted_parts)


@router.post("/sessions/{session_id}/compress")
async def compress_session(session_id: str) -> Dict[str, Any]:
    """压缩对话历史
    
    压缩策略：
    1. 将所有消息融合为一条 assistant 摘要消息
    2. 完整保留用户的所有提问
    3. 工具调用过程用自然语言概括
    4. 压缩后的摘要直接替换原消息列表
    """
    # 获取消息
    messages = agent_manager.session_manager.load_session(session_id)
    
    if len(messages) < 4:
        raise HTTPException(status_code=400, detail="消息数量不足，无法压缩（至少需要 4 条消息）")
    
    # 格式化消息用于压缩
    conversation_text = _format_messages_for_compression(messages)
    
    # 构建压缩提示
    prompt = f"""请将以下对话历史总结为一段结构化的中文摘要。

对话内容：
{conversation_text}

摘要要求：
1. **必须完整保留所有用户提问的原文**（用【用户提问】标注）
2. 对于涉及工具调用的操作，简洁描述调用了什么工具、核心结果是什么
3. 保留助手答复的关键信息和结论
4. 摘要格式示例：
   ---
   【用户提问 1】<完整的用户原文>
   【助手处理】<简述操作和结果>
   
   【用户提问 2】<完整的用户原文>
   【助手处理】<简述操作和结果>
   ---
5. 只返回摘要内容，不要其他说明"""
    
    # 调用 LLM 生成摘要
    llm = ChatDeepSeek(
        model=global_config.config.deepseek_model,
        api_key=global_config.config.deepseek_api_key,
        base_url=global_config.config.deepseek_base_url,
        temperature=0.3,
    )
    
    response = await llm.ainvoke(prompt)
    summary = response.content.strip()
    
    # 完全替换消息列表（而不是归档部分消息）
    agent_manager.session_manager.replace_with_summary(
        session_id,
        summary
    )
    
    return {
        "original_count": len(messages),
        "compressed_to": 1,
        "summary": summary
    }
