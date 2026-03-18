"""System Prompt 组装器"""
from pathlib import Path
from typing import Optional


class PromptBuilder:
    """System Prompt 组装器，按固定顺序拼接 6 个组件"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.max_length = 20000  # 单个组件最大字符数
    
    def build_system_prompt(self, rag_mode: bool = False) -> str:
        """构建完整的 System Prompt
        
        Args:
            rag_mode: 是否启用 RAG 模式
            
        Returns:
            完整的 System Prompt
        """
        components = []
        
        # 1. SKILLS_SNAPSHOT.md（技能列表）
        components.append(self._load_component(
            self.base_dir / "SKILLS_SNAPSHOT.md",
            "Skills Snapshot",
            required=False
        ))
        
        # 2. workspace/SOUL.md（人格、语气、边界）
        components.append(self._load_component(
            self.base_dir / "workspace" / "SOUL.md",
            "Soul"
        ))
        
        # 3. workspace/IDENTITY.md（名称、风格）
        components.append(self._load_component(
            self.base_dir / "workspace" / "IDENTITY.md",
            "Identity"
        ))
        
        # 4. workspace/USER.md（用户画像）
        components.append(self._load_component(
            self.base_dir / "workspace" / "USER.md",
            "User Profile"
        ))
        
        # 5. workspace/AGENTS.md（操作指南 & 协议）
        components.append(self._load_component(
            self.base_dir / "workspace" / "AGENTS.md",
            "Agents Guide"
        ))
        
        # 6. memory/MEMORY.md（长期记忆）或 RAG 引导语
        if rag_mode:
            components.append(self._build_rag_guidance())
        else:
            components.append(self._load_component(
                self.base_dir / "memory" / "MEMORY.md",
                "Long-term Memory"
            ))
        
        # 过滤空组件并拼接
        components = [c for c in components if c]
        return "\n\n".join(components)
    
    def _load_component(
        self,
        file_path: Path,
        label: str,
        required: bool = True
    ) -> Optional[str]:
        """加载单个组件
        
        Args:
            file_path: 文件路径
            label: 组件标签
            required: 是否必需
            
        Returns:
            组件内容（带标签）
        """
        if not file_path.exists():
            if required:
                return f"<!-- {label} -->\n[文件不存在: {file_path.name}]"
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 截断过长内容
            if len(content) > self.max_length:
                content = content[:self.max_length] + "\n\n...[truncated]"
            
            return f"<!-- {label} -->\n{content}"
            
        except Exception as e:
            return f"<!-- {label} -->\n[读取失败: {str(e)}]"
    
    def _build_rag_guidance(self) -> str:
        """构建 RAG 引导语"""
        return """<!-- RAG Memory Mode -->
# 记忆检索模式

你的长期记忆（MEMORY.md）现在通过 RAG 检索系统动态加载。当用户提问时，系统会自动从记忆库中检索相关内容，并以「[记忆检索结果]」的形式注入到对话上下文中。

你无需主动请求记忆内容，系统会智能判断并自动提供。请根据检索结果回答用户问题。"""
