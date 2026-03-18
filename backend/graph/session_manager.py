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
        """加载会话消息，为 LLM 优化：合并连续 assistant 消息、注入压缩摘要
        
        Args:
            session_id: 会话 ID
            
        Returns:
            优化后的消息列表
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return []
        
        data = self._read_file(session_file)
        messages = data.get("messages", [])
        
        # 合并连续的 assistant 消息
        merged_messages = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            
            if msg["role"] == "assistant":
                # 收集连续的 assistant 消息
                assistant_segments = [msg["content"]]
                tool_calls = msg.get("tool_calls", [])
                
                j = i + 1
                while j < len(messages) and messages[j]["role"] == "assistant":
                    assistant_segments.append(messages[j]["content"])
                    tool_calls.extend(messages[j].get("tool_calls", []))
                    j += 1
                
                # 合并为一条消息
                merged_msg = {
                    "role": "assistant",
                    "content": "\n\n".join(assistant_segments)
                }
                if tool_calls:
                    merged_msg["tool_calls"] = tool_calls
                
                merged_messages.append(merged_msg)
                i = j
            else:
                merged_messages.append(msg)
                i += 1
        
        # 注入压缩摘要
        compressed_context = data.get("compressed_context", "")
        if compressed_context:
            # 在消息列表头部插入摘要
            summary_msg = {
                "role": "assistant",
                "content": f"[以下是之前对话的摘要]\n\n{compressed_context}"
            }
            merged_messages.insert(0, summary_msg)
        
        return merged_messages
    
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
            role: 消息角色（user/assistant）
            content: 消息内容
            tool_calls: 工具调用列表
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
        """压缩历史消息
        
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
        """读取会话文件（兼容 v1 格式）"""
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
        
        return data
    
    def _write_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """写入会话文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
