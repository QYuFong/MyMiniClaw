"""Agent 管理器"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, AsyncGenerator, Optional

import config as global_config
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_deepseek import ChatDeepSeek
from tools import get_all_tools

from .memory_indexer import MemoryIndexer
from .prompt_builder import PromptBuilder
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class AgentManager:
    """Agent 核心管理器"""
    
    def __init__(self):
        self.base_dir: Optional[Path] = None
        self.llm: Optional[ChatDeepSeek] = None
        self.tools: List[BaseTool] = []
        self.prompt_builder: Optional[PromptBuilder] = None
        self.session_manager: Optional[SessionManager] = None
        self.memory_indexer: Optional[MemoryIndexer] = None
    
    def initialize(self, base_dir: Path) -> None:
        """初始化 Agent
        
        Args:
            base_dir: 项目根目录
        """
        self.base_dir = base_dir
        
        # 加载工具
        self.tools = get_all_tools(base_dir)
        
        # 创建 LLM（绑定工具以支持 function calling）
        self.llm = ChatDeepSeek(
            model=global_config.config.deepseek_model,
            api_key=global_config.config.deepseek_api_key,
            base_url=global_config.config.deepseek_base_url,
            temperature=0.7,
            streaming=True,
        )
        
        # 尝试绑定工具（如果 DeepSeek 支持 function calling）
        try:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            logger.info(f"✓ Agent 初始化完成，加载了 {len(self.tools)} 个工具 (Function Calling 模式)")
        except Exception as e:
            logger.info(f"✓ Agent 初始化完成，加载了 {len(self.tools)} 个工具 (文本解析模式)")
            self.llm_with_tools = None
        
        # 初始化组件
        self.prompt_builder = PromptBuilder(base_dir)
        self.session_manager = SessionManager(base_dir)
        self.memory_indexer = MemoryIndexer(base_dir)
    
    async def astream(
        self,
        message: str,
        history: List[Dict[str, Any]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式处理用户消息
        
        Args:
            message: 用户消息
            history: 对话历史
            
        Yields:
            事件字典：
            - {"type": "retrieval", "query": str, "results": List[Dict]}
            - {"type": "token", "content": str}
            - {"type": "tool_start", "tool": str, "input": str}
            - {"type": "tool_end", "tool": str, "output": str}
            - {"type": "tool_message", "tool": str, "tool_call_id": str, "output": str}
            - {"type": "assistant_message", "content": str, "tool_calls": List}
            - {"type": "new_response", "segment": int}
            - {"type": "done", "content": str, "messages": List}
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"[AGENT] 收到用户消息: {message}")
        logger.info(f"[AGENT] 历史消息数量: {len(history)}")
        logger.info(f"{'='*60}\n")
        
        # 构建 Agent
        rag_mode = global_config.config.get_rag_mode()
        
        # RAG 模式：先检索记忆
        retrieval_results = []
        if rag_mode:
            retrieval_results = self.memory_indexer.retrieve(message, top_k=3)
            
            if retrieval_results:
                logger.info(f"[RAG] 检索到 {len(retrieval_results)} 条相关记忆")
                yield {
                    "type": "retrieval",
                    "query": message,
                    "results": retrieval_results
                }
                
                # 将检索结果追加到历史（仅本次请求）
                retrieval_text = "[记忆检索结果]\n\n"
                for i, result in enumerate(retrieval_results, 1):
                    retrieval_text += f"[片段 {i}] (相关度: {result['score']:.3f})\n{result['text']}\n\n"
                
                history = history + [{
                    "role": "assistant",
                    "content": retrieval_text
                }]
        
        # 构建 System Prompt
        system_prompt = self.prompt_builder.build_system_prompt(rag_mode=rag_mode)
        
        # 只有在不支持原生 function calling 时才添加工具使用说明
        if not self.llm_with_tools:
            system_prompt += self._build_tools_prompt()
        
        logger.info(f"[AGENT] System Prompt 长度: {len(system_prompt)} 字符")
        
        # 构建消息列表
        messages = self._build_messages(history, message)
        logger.info(f"[AGENT] 构建的消息列表长度: {len(messages)}")
        
        # ReAct Agent 循环：最多执行 10 轮
        max_iterations = 10
        full_response = ""
        generated_messages = []  # 记录本次对话生成的所有消息
        
        for iteration in range(max_iterations):
            logger.info(f"\n{'='*60}")
            logger.info(f"[AGENT] 开始第 {iteration + 1} 轮 (最多 {max_iterations} 轮)")
            logger.info(f"{'='*60}\n")
            
            # 添加系统消息
            all_messages = [SystemMessage(content=system_prompt)] + messages
            
            # 选择使用带工具的 LLM 或普通 LLM
            llm_to_use = self.llm_with_tools if self.llm_with_tools else self.llm
            logger.info(f"[LLM] 使用 {'带工具' if self.llm_with_tools else '普通'} LLM 模式")
            
            # 流式调用 LLM
            current_response = ""
            aggregated_message: Optional[AIMessageChunk] = None  # 用于聚合流式消息
            
            logger.info(f"[LLM] 开始流式调用...")
            try:
                chunk_count = 0
                async for chunk in llm_to_use.astream(all_messages):
                    chunk_count += 1
                    
                    # 使用 LangChain 的聚合功能，自动处理流式 tool_calls
                    if aggregated_message is None:
                        aggregated_message = chunk
                    else:
                        aggregated_message = aggregated_message + chunk
                    
                    # 普通文本内容（实时输出给前端）
                    content = chunk.content
                    if content:
                        if chunk_count <= 3 or chunk_count % 10 == 0:
                            logger.info(f"[LLM] Chunk #{chunk_count} 内容: {content[:50]}...")
                        current_response += content
                        full_response += content
                        yield {
                            "type": "token",
                            "content": content
                        }
                
                logger.info(f"[LLM] 流式调用完成，共 {chunk_count} 个 chunk")
                logger.info(f"[LLM] 完整响应长度: {len(current_response)} 字符")
                logger.info(f"[LLM] 完整响应内容:\n{'-'*60}\n{current_response}\n{'-'*60}")
                
                # 检查聚合后的 tool_calls
                if aggregated_message and aggregated_message.tool_calls:
                    logger.info(f"[LLM] 聚合后的 tool_calls: {aggregated_message.tool_calls}")
                
            except Exception as e:
                logger.info(f"[ERROR] LLM 调用失败: {str(e)}")
                import traceback
                traceback.print_exc()
                yield {
                    "type": "error",
                    "error": str(e)
                }
                return
            
            # 优先处理 function calling 模式的工具调用（使用聚合后的消息）
            tool_calls = aggregated_message.tool_calls if aggregated_message else []
            
            if tool_calls:
                logger.info(f"[TOOL] 检测到 {len(tool_calls)} 个 Function Call")
                logger.info(f"[TOOL] Function Calls: {tool_calls}")
                
                # 构建 AI 消息（包含 tool_calls）用于历史记录
                ai_message_with_tools = AIMessage(
                    content=current_response,
                    tool_calls=tool_calls
                )
                messages.append(ai_message_with_tools)
                
                # 记录 assistant 消息（带 tool_calls）
                assistant_msg = {
                    "role": "assistant",
                    "content": current_response,
                    "tool_calls": [
                        {
                            "id": tc.get('id', ''),
                            "name": tc.get('name', ''),
                            "args": tc.get('args', {})
                        }
                        for tc in tool_calls
                    ]
                }
                generated_messages.append(assistant_msg)
                
                # 通知前端 assistant 消息（带 tool_calls）
                yield {
                    "type": "assistant_message",
                    "content": current_response,
                    "tool_calls": assistant_msg["tool_calls"]
                }
                
                for tool_call in tool_calls:
                    tool_name = tool_call.get('name', '')
                    tool_args = tool_call.get('args', {})
                    tool_call_id = tool_call.get('id', '')
                    
                    logger.info(f"[TOOL] 工具名称: {tool_name}")
                    logger.info(f"[TOOL] 工具参数: {tool_args}")
                    logger.info(f"[TOOL] Tool Call ID: {tool_call_id}")
                    
                    # 提取工具输入（通常是第一个参数值，如 query）
                    if isinstance(tool_args, dict):
                        tool_input = tool_args.get('query') or tool_args.get('path') or tool_args.get('input') or list(tool_args.values())[0] if tool_args else ""
                    else:
                        tool_input = str(tool_args)
                    
                    logger.info(f"[TOOL] 工具输入 (处理后): {tool_input}")
                    
                    # 通知前端工具调用开始
                    yield {
                        "type": "tool_start",
                        "tool": tool_name,
                        "input": str(tool_input)
                    }
                    
                    # 执行工具
                    logger.info(f"[TOOL] 开始执行工具: {tool_name}")
                    tool_output = await self._execute_tool(tool_name, str(tool_input))
                    logger.info(f"[TOOL] 工具执行完成，输出长度: {len(tool_output)} 字符")
                    logger.info(f"[TOOL] 工具输出:\n{'-'*60}\n{tool_output[:500]}...\n{'-'*60}")
                    
                    # 通知前端工具调用结束
                    yield {
                        "type": "tool_end",
                        "tool": tool_name,
                        "output": tool_output
                    }
                    
                    # 将工具输出添加到消息历史（ToolMessage 需要 tool_call_id）
                    messages.append(ToolMessage(
                        content=tool_output,
                        tool_call_id=tool_call_id
                    ))
                    
                    # 记录 tool 消息
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": tool_output
                    }
                    generated_messages.append(tool_msg)
                    
                    # 通知前端 tool 消息
                    yield {
                        "type": "tool_message",
                        "tool": tool_name,
                        "tool_call_id": tool_call_id,
                        "output": tool_output
                    }
                    
                    full_response += f"\n\n[Tool: {tool_name}]\nInput: {tool_input}\nOutput: {tool_output}\n\n"
                
                # 通知前端新的响应段开始
                yield {
                    "type": "new_response",
                    "segment": iteration + 1
                }
                
                # 继续下一轮循环，让 AI 根据工具输出生成回答
                logger.info(f"[AGENT] 继续下一轮，让 AI 根据工具输出生成回答")
                continue
            
            # 如果没有原生 function calling，尝试文本解析模式（fallback）
            if not self.llm_with_tools:
                logger.info(f"[TOOL] 尝试文本解析模式...")
                parsed_tool_call = self._parse_tool_call(current_response)
                
                if parsed_tool_call:
                    tool_name = parsed_tool_call["tool"]
                    tool_input = parsed_tool_call["input"]
                    fake_tool_call_id = f"text_parse_{iteration}_{tool_name}"
                    
                    logger.info(f"[TOOL] ✓ 检测到文本格式工具调用")
                    logger.info(f"[TOOL] 工具名称: {tool_name}")
                    logger.info(f"[TOOL] 工具输入: {tool_input}")
                    
                    # 记录 assistant 消息（带模拟的 tool_calls）
                    assistant_msg = {
                        "role": "assistant",
                        "content": current_response,
                        "tool_calls": [
                            {
                                "id": fake_tool_call_id,
                                "name": tool_name,
                                "args": {"input": tool_input}
                            }
                        ]
                    }
                    generated_messages.append(assistant_msg)
                    
                    # 通知前端 assistant 消息
                    yield {
                        "type": "assistant_message",
                        "content": current_response,
                        "tool_calls": assistant_msg["tool_calls"]
                    }
                    
                    # 通知前端工具调用开始
                    yield {
                        "type": "tool_start",
                        "tool": tool_name,
                        "input": tool_input
                    }
                    
                    # 执行工具
                    logger.info(f"[TOOL] 开始执行工具: {tool_name}")
                    tool_output = await self._execute_tool(tool_name, tool_input)
                    logger.info(f"[TOOL] 工具执行完成，输出长度: {len(tool_output)} 字符")
                    logger.info(f"[TOOL] 工具输出:\n{'-'*60}\n{tool_output[:500]}...\n{'-'*60}")
                    
                    # 通知前端工具调用结束
                    yield {
                        "type": "tool_end",
                        "tool": tool_name,
                        "output": tool_output
                    }
                    
                    # 将工具输出添加到消息历史（文本模式使用 HumanMessage 传递工具结果）
                    messages.append(AIMessage(content=current_response))
                    messages.append(HumanMessage(content=f"[工具执行结果]\n工具: {tool_name}\n输出:\n{tool_output}\n\n请根据以上工具输出继续回答。"))
                    
                    # 记录 tool 消息
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": fake_tool_call_id,
                        "name": tool_name,
                        "content": tool_output
                    }
                    generated_messages.append(tool_msg)
                    
                    # 通知前端 tool 消息
                    yield {
                        "type": "tool_message",
                        "tool": tool_name,
                        "tool_call_id": fake_tool_call_id,
                        "output": tool_output
                    }
                    
                    # 通知前端新的响应段开始
                    yield {
                        "type": "new_response",
                        "segment": iteration + 1
                    }
                    
                    full_response += f"\n\n[Tool: {tool_name}]\nInput: {tool_input}\nOutput: {tool_output}\n\n"
                    
                    # 继续下一轮循环
                    logger.info(f"[AGENT] 继续下一轮，让 AI 根据工具输出生成回答")
                    continue
            
            # 没有工具调用，对话完成
            logger.info(f"[TOOL] ✗ 未检测到工具调用")
            logger.info(f"[AGENT] 对话完成，无需进一步工具调用")
            
            # 记录最终的 assistant 融合答复消息
            if current_response.strip():
                final_assistant_msg = {
                    "role": "assistant",
                    "content": current_response
                }
                generated_messages.append(final_assistant_msg)
                
                # 通知前端最终的 assistant 消息
                yield {
                    "type": "assistant_message",
                    "content": current_response,
                    "tool_calls": []
                }
            
            break
        
        # 完成
        logger.info(f"\n{'='*60}")
        logger.info(f"[AGENT] 对话完成，总响应长度: {len(full_response)} 字符")
        logger.info(f"[AGENT] 生成的消息数量: {len(generated_messages)}")
        logger.info(f"{'='*60}\n")
        
        yield {
            "type": "done",
            "content": full_response,
            "messages": generated_messages
        }
    
    def _build_tools_prompt(self) -> str:
        """构建工具使用说明"""
        tools_desc = "\n\n## 可用工具\n\n你可以使用以下工具来完成任务：\n\n"
        
        for tool in self.tools:
            tools_desc += f"### {tool.name}\n"
            tools_desc += f"{tool.description}\n\n"
        
        tools_desc += """
## 工具调用格式

当你需要使用工具时，请直接以以下格式调用（系统会自动识别并执行）：

```
<tool_name> <input>
```

例如：
```
read_file skills/get_weather/SKILL.md
```

或者使用标准格式：
```
ACTION: read_file
INPUT: skills/get_weather/SKILL.md
```

系统会执行工具并返回结果，然后你需要根据结果继续回答用户的问题。

**重要**：当你写出工具调用时，系统会立即执行它并返回结果。请等待工具结果后再继续回答。
"""
        
        return tools_desc
    
    def _parse_tool_call(self, text: str) -> Optional[Dict[str, str]]:
        """解析文本中的工具调用
        
        Args:
            text: AI 生成的文本
            
        Returns:
            工具调用字典，如果没有工具调用则返回 None
        """
        import re
        
        logger.info(f"[PARSE] 开始解析工具调用...")
        logger.info(f"[PARSE] 文本长度: {len(text)} 字符")
        
        # 方式 1: 匹配 ACTION: <tool_name> 和 INPUT: <input>
        pattern1 = r'ACTION:\s*([^\n]+)\s*\n\s*INPUT:\s*(.+?)(?:\n|$)'
        match = re.search(pattern1, text, re.DOTALL | re.IGNORECASE)
        
        if match:
            tool_name = match.group(1).strip()
            tool_input = match.group(2).strip()
            
            # 移除可能的代码块标记
            tool_input = tool_input.strip('`').strip()
            
            logger.info(f"[PARSE] ✓ 方式1 匹配成功: ACTION/INPUT 格式")
            logger.info(f"[PARSE] 工具名称: {tool_name}")
            logger.info(f"[PARSE] 工具输入: {tool_input}")
            
            return {
                "tool": tool_name,
                "input": tool_input
            }
        
        logger.info(f"[PARSE] 方式1 未匹配")
        
        # 获取工具名称列表
        tool_names = [t.name for t in self.tools]
        logger.info(f"[PARSE] 尝试其他方式，可用工具: {tool_names}")
        
        for tool_name in tool_names:
            # 方式 2: 匹配函数调用格式 tool_name("input") 或 tool_name('input')
            pattern2 = rf'\b{re.escape(tool_name)}\s*\(\s*["\']([^"\']+)["\']\s*\)'
            match = re.search(pattern2, text, re.IGNORECASE)
            
            if match:
                tool_input = match.group(1).strip()
                
                logger.info(f"[PARSE] ✓ 方式2 匹配成功: 函数调用格式")
                logger.info(f"[PARSE] 工具名称: {tool_name}")
                logger.info(f"[PARSE] 工具输入: {tool_input}")
                
                return {
                    "tool": tool_name,
                    "input": tool_input
                }
            
            # 方式 3: 匹配直接调用格式 tool_name input
            pattern3 = rf'\b{re.escape(tool_name)}\s+([^\n]+)'
            match = re.search(pattern3, text, re.IGNORECASE)
            
            if match:
                tool_input = match.group(1).strip()
                # 移除可能的代码块标记和括号
                tool_input = tool_input.strip('`').strip('"').strip("'").strip('(').strip(')')
                
                logger.info(f"[PARSE] ✓ 方式3 匹配成功: 直接调用格式")
                logger.info(f"[PARSE] 工具名称: {tool_name}")
                logger.info(f"[PARSE] 工具输入: {tool_input}")
                
                return {
                    "tool": tool_name,
                    "input": tool_input
                }
        
        logger.info(f"[PARSE] ✗ 所有方式均未匹配到工具调用")
        logger.info(f"[PARSE] 文本预览: {text[:200]}...")
        return None
    
    async def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        """执行工具
        
        Args:
            tool_name: 工具名称
            tool_input: 工具输入
            
        Returns:
            工具输出
        """
        # 查找工具
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break
        
        if not tool:
            return f"错误：工具 '{tool_name}' 不存在"
        
        try:
            # 执行工具（同步）
            result = tool._run(tool_input)
            return result
        except Exception as e:
            return f"错误：工具执行失败 - {str(e)}"
    
    def _build_messages(
        self,
        history: List[Dict[str, Any]],
        current_message: str
    ) -> List[Any]:
        """将历史消息转换为 LangChain 消息对象
        
        支持的消息角色：
        - user: 用户消息 → HumanMessage
        - assistant: 助手消息 → AIMessage（可能带 tool_calls）
        - tool: 工具执行结果 → ToolMessage
        
        Args:
            history: 历史消息
            current_message: 当前用户消息
            
        Returns:
            LangChain 消息列表
        """
        messages = []
        
        # 转换历史消息
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    # 带 tool_calls 的 assistant 消息
                    # 转换为 LangChain 格式的 tool_calls
                    lc_tool_calls = [
                        {
                            "id": tc.get("id", ""),
                            "name": tc.get("name", ""),
                            "args": tc.get("args", {})
                        }
                        for tc in tool_calls
                    ]
                    messages.append(AIMessage(content=content, tool_calls=lc_tool_calls))
                else:
                    messages.append(AIMessage(content=content))
            elif role == "tool":
                # 工具执行结果消息
                tool_call_id = msg.get("tool_call_id", "")
                messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))
        
        # 添加当前消息
        messages.append(HumanMessage(content=current_message))
        
        return messages


# 全局 Agent 实例
agent_manager = AgentManager()
