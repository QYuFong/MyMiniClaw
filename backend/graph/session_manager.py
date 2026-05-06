"""会话持久化管理器"""
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil


class SessionManager:
    """管理会话的持久化存储"""

    def __init__(self, base_dir: Path):
        self.sessions_dir = base_dir / "sessions"
        self.archive_dir = self.sessions_dir / "archive"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    # ==================== 轮次计数相关方法 ====================

    def increment_turn_count(self, session_id: str) -> int:
        """增加轮次计数并返回当前轮次

        Args:
            session_id: 会话 ID

        Returns:
            当前轮次号（新增后的）
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            # 新会话，轮次为 1
            return 1

        data = self._read_file(session_file)
        current_turn = data.get("turn_count", 0) + 1
        data["turn_count"] = current_turn
        data["updated_at"] = time.time()

        self._write_file(session_file, data)
        return current_turn

    def get_turn_count(self, session_id: str) -> int:
        """获取当前轮次

        Args:
            session_id: 会话 ID

        Returns:
            当前轮次号（如果新会话返回 0）
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return 0

        data = self._read_file(session_file)
        return data.get("turn_count", 0)

    def update_last_memory_turn(self, session_id: str, turn: int) -> None:
        """更新上次记忆提取时的轮次

        Args:
            session_id: 会话 ID
            turn: 提取时的轮次号
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return

        data = self._read_file(session_file)
        data["last_memory_turn"] = turn
        data["updated_at"] = time.time()

        self._write_file(session_file, data)

    def should_trigger_memory_extraction(self, session_id: str) -> bool:
        """判断是否应该触发记忆提取

        触发条件：每 5 轮触发一次

        Args:
            session_id: 会话 ID

        Returns:
            是否应该触发
        """
        current_turn = self.get_turn_count(session_id)
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return False

        data = self._read_file(session_file)
        last_memory_turn = data.get("last_memory_turn", 0)

        # 计算距离上次提取的轮次差
        turns_since_last_extraction = current_turn - last_memory_turn

        # 每 5 轮触发
        return turns_since_last_extraction >= 5

    # ==================== 会话管理方法 ====================
    
    def load_session(self, session_id: str) -> List[Dict[str, Any]]:
        """加载会话的原始消息列表
        
        Args:
            session_id: 会话 ID
            
        Returns:
            消息列表
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return []
        
        data = self._read_file(session_file)
        return data.get("messages", [])
    
    def load_session_for_agent(self, session_id: str) -> List[Dict[str, Any]]:
        """加载会话消息，为 LLM 优化：保留完整的消息角色结构
        
        消息角色流转规则：
        - 单工具调用：user → assistant(带tool_call) → tool → assistant(融合答复)
        - 多工具调用：user → (assistant(带tool_call) → tool) × n → assistant(融合答复)
        
        压缩后的会话：messages 只包含一条 assistant 摘要消息
        
        Args:
            session_id: 会话 ID
            
        Returns:
            消息列表
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return []
        
        data = self._read_file(session_file)
        messages = data.get("messages", [])
        
        # 保留完整的消息结构
        result_messages = []
        for msg in messages:
            result_messages.append(msg.copy())
        
        # 兼容旧格式：如果存在 compressed_context，将其作为首条摘要消息注入
        # 新格式下 compressed_context 应为空
        compressed_context = data.get("compressed_context", "")
        if compressed_context:
            summary_msg = {
                "role": "assistant",
                "content": f"[以下是之前对话的摘要]\n\n{compressed_context}"
            }
            result_messages.insert(0, summary_msg)
        
        return result_messages
    
    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """追加消息到会话文件
        
        Args:
            session_id: 会话 ID
            role: 消息角色（user/assistant/tool）
            content: 消息内容
            tool_calls: 工具调用列表（仅 assistant 角色使用）
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        # 读取现有数据
        if session_file.exists():
            data = self._read_file(session_file)
        else:
            data = {
                "title": "新对话",
                "created_at": time.time(),
                "updated_at": time.time(),
                "messages": []
            }
        
        # 构建消息
        message = {
            "role": role,
            "content": content
        }
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        # 追加消息
        data["messages"].append(message)
        data["updated_at"] = time.time()
        
        # 保存
        self._write_file(session_file, data)
    
    def save_tool_message(
        self,
        session_id: str,
        tool_call_id: str,
        name: str,
        content: str
    ) -> None:
        """保存工具执行结果消息
        
        Args:
            session_id: 会话 ID
            tool_call_id: 工具调用 ID
            name: 工具名称
            content: 工具输出内容
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        # 读取现有数据
        if session_file.exists():
            data = self._read_file(session_file)
        else:
            data = {
                "title": "新对话",
                "created_at": time.time(),
                "updated_at": time.time(),
                "messages": []
            }
        
        # 构建 tool 消息
        message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        }
        
        # 追加消息
        data["messages"].append(message)
        data["updated_at"] = time.time()
        
        # 保存
        self._write_file(session_file, data)
    
    def update_title(self, session_id: str, title: str) -> None:
        """更新会话标题
        
        Args:
            session_id: 会话 ID
            title: 新标题
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return
        
        data = self._read_file(session_file)
        data["title"] = title
        data["updated_at"] = time.time()
        
        self._write_file(session_file, data)
    
    def compress_history(
        self,
        session_id: str,
        summary: str,
        num_messages: int
    ) -> None:
        """压缩历史消息（归档部分消息）
        
        Args:
            session_id: 会话 ID
            summary: 压缩摘要
            num_messages: 要归档的消息数量
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return
        
        data = self._read_file(session_file)
        messages = data.get("messages", [])
        
        if len(messages) < num_messages:
            return
        
        # 分割消息
        archived_messages = messages[:num_messages]
        remaining_messages = messages[num_messages:]
        
        # 归档旧消息
        timestamp = int(time.time())
        archive_file = self.archive_dir / f"{session_id}_{timestamp}.json"
        self._write_file(archive_file, {
            "session_id": session_id,
            "archived_at": timestamp,
            "messages": archived_messages
        })
        
        # 更新会话文件
        existing_context = data.get("compressed_context", "")
        if existing_context:
            data["compressed_context"] = f"{existing_context}\n\n---\n\n{summary}"
        else:
            data["compressed_context"] = summary
        
        data["messages"] = remaining_messages
        data["updated_at"] = time.time()
        
        self._write_file(session_file, data)
    
    def replace_with_summary(
        self,
        session_id: str,
        summary: str
    ) -> None:
        """将所有消息替换为一条 assistant 摘要消息

        用于完全压缩对话历史，保留用户提问和核心上下文
        压缩后 messages 只保留一条 assistant 消息，内容是摘要

        Args:
            session_id: 会话 ID
            summary: 压缩摘要内容
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return

        data = self._read_file(session_file)
        original_messages = data.get("messages", [])

        # 归档原始消息
        timestamp = int(time.time())
        archive_file = self.archive_dir / f"{session_id}_{timestamp}.json"
        self._write_file(archive_file, {
            "session_id": session_id,
            "archived_at": timestamp,
            "messages": original_messages,
            "compressed_context": data.get("compressed_context", ""),
            "turn_count": data.get("turn_count", 0),  # 归档时保存轮次
            "last_memory_turn": data.get("last_memory_turn", 0)  # 归档时保存提取轮次
        })

        # 用一条 assistant 摘要消息替换所有消息
        data["messages"] = [
            {
                "role": "assistant",
                "content": summary
            }
        ]

        # 清空 compressed_context（摘要已经在 messages 里了）
        data["compressed_context"] = ""

        # 关键：保留轮次计数字段（新一轮继续累加）
        # turn_count 和 last_memory_turn 保持不变

        data["updated_at"] = time.time()

        self._write_file(session_file, data)
    
    def get_compressed_context(self, session_id: str) -> str:
        """获取压缩摘要
        
        Args:
            session_id: 会话 ID
            
        Returns:
            压缩摘要
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return ""
        
        data = self._read_file(session_file)
        return data.get("compressed_context", "")
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话
        
        Returns:
            会话列表（按更新时间倒序）
        """
        sessions = []
        
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                data = self._read_file(session_file)
                sessions.append({
                    "id": session_file.stem,
                    "title": data.get("title", "新对话"),
                    "created_at": data.get("created_at", 0),
                    "updated_at": data.get("updated_at", 0),
                    "message_count": len(data.get("messages", []))
                })
            except Exception:
                pass
        
        # 按更新时间倒序排序
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            是否删除成功
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if session_file.exists():
            session_file.unlink()
            return True
        
        return False
    
    def _read_file(self, file_path: Path) -> Dict[str, Any]:
        """读取会话文件（兼容 v1/v2/v3 格式）"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # v1 兼容：如果是纯数组，转换为 v2 格式
        if isinstance(data, list):
            data = {
                "title": "新对话",
                "created_at": file_path.stat().st_ctime,
                "updated_at": file_path.stat().st_mtime,
                "messages": data
            }

        # v2 兼容：添加轮次计数字段（默认值）
        if "turn_count" not in data:
            data["turn_count"] = 0
        if "last_memory_turn" not in data:
            data["last_memory_turn"] = 0

        return data
    
    def _write_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """写入会话文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
