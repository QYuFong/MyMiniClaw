"""记忆写入工具"""
from pathlib import Path
from typing import Optional, ClassVar, Dict
from datetime import datetime

from langchain_core.tools import BaseTool
from pydantic import Field, BaseModel


class WriteMemoryInput(BaseModel):
    """记忆写入工具输入"""
    category: str = Field(
        description="记忆分类：'user_info'（用户信息）、'important_events'（重要事件）、'long_term_goals'（长期目标和持续任务）、'other_notes'（其他备注）"
    )
    content: str = Field(
        description="记忆内容（简洁精准的短句，描述用户明确表述的事实）"
    )
    action: str = Field(
        default="append",
        description="操作类型：'append'（追加）、'update'（更新）、'delete'（删除）"
    )
    target_content: Optional[str] = Field(
        default=None,
        description="更新/删除操作的目标内容（用于匹配已有记忆条目）"
    )


class WriteMemoryTool(BaseTool):
    """直接写入长期记忆的工具

    用于处理用户明确表达的记忆主题信息，无需等待后续提取
    """

    name: str = "write_memory"
    description: str = (
        "将重要信息直接写入长期记忆。"
        "适用场景：用户明确表达了以下主题的信息时，应立即调用此工具：\n"
        "1. **核心身份与基础属性**：姓名、职业、行业、岗位、地区、时区、语言偏好、技术栈、能力标签\n"
        "2. **交互偏好与行为模式**：沟通风格、内容输出偏好、决策偏好、禁忌红线、反感内容\n"
        "3. **知识边界与经验教训**：精通/熟悉/陌生的领域、已解决的问题、踩过的坑、排过的故障、纠正的错误认知\n"
        "4. **价值观与核心诉求**：核心价值观、使用Agent的核心诉求、长期痛点、伦理与合规要求\n"
        "5. **长期目标与持续任务**：长期核心目标、持续推进的项目/任务、周期性需求、待办与承诺事项\n\n"
        "参数说明：\n"
        "- category: 选择最合适的记忆分类\n"
        "- content: 记忆内容，必须是用户明确表述的事实，简洁精准\n"
        "- action: 默认为'append'，表示追加新记忆；'update'表示更新已有记忆；'delete'表示删除过期记忆\n"
        "- target_content: 仅在update/delete操作时需要，用于定位目标记忆条目\n\n"
        "示例：\n"
        "- 用户说'我是程序员，主要用Go和Python' → write_memory(category='user_info', content='用户是程序员，主要技术栈为Go和Python')\n"
        "- 用户说'我不喜欢长篇大论' → write_memory(category='user_info', content='用户偏好简洁回复，不喜欢长篇大论')\n"
        "- 用户说'我最近在研究AI Agent项目' → write_memory(category='long_term_goals', content='用户当前正在研究AI Agent项目')"
    )

    args_schema: type[BaseModel] = WriteMemoryInput
    memory_file: Path = Field(description="MEMORY.md 文件路径")

    # 分类映射到 MEMORY.md 的二级标题（类常量，不是字段）
    CATEGORY_MAPPING: ClassVar[Dict[str, str]] = {
        "user_info": "## 用户信息",
        "important_events": "## 重要事件",
        "long_term_goals": "## 长期目标和持续任务",
        "other_notes": "## 其他备注"
    }

    def _run(
        self,
        category: str,
        content: str,
        action: str = "append",
        target_content: Optional[str] = None
    ) -> str:
        """执行记忆写入

        Args:
            category: 记忆分类
            content: 记忆内容
            action: 操作类型
            target_content: 目标内容

        Returns:
            操作结果描述
        """
        try:
            # 验证分类
            if category not in self.CATEGORY_MAPPING:
                return f"错误：无效的分类 '{category}'，支持的分类：{list(self.CATEGORY_MAPPING.keys())}"

            # 验证操作
            if action not in ["append", "update", "delete"]:
                return f"错误：无效的操作 '{action}'，支持的操作：append, update, delete"

            # 读取现有记忆
            if not self.memory_file.exists():
                return "错误：MEMORY.md 文件不存在"

            with open(self.memory_file, 'r', encoding='utf-8') as f:
                memory_content = f.read()

            # 获取当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")

            # 根据操作类型执行
            if action == "append":
                result = self._append_memory(memory_content, category, content, current_date)
            elif action == "update":
                if not target_content:
                    return "错误：update 操作需要提供 target_content 参数"
                result = self._update_memory(memory_content, category, target_content, content, current_date)
            elif action == "delete":
                if not target_content:
                    return "错误：delete 操作需要提供 target_content 参数"
                result = self._delete_memory(memory_content, category, target_content)
            else:
                return f"错误：未知的操作 '{action}'"

            # 写入文件
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                f.write(result)

            return f"成功：已将记忆写入 '{category}' 分类（{action} 操作）"

        except Exception as e:
            return f"错误：写入失败 - {str(e)}"

    def _append_memory(
        self,
        memory_content: str,
        category: str,
        content: str,
        date: str
    ) -> str:
        """追加记忆

        Args:
            memory_content: 现有记忆内容
            category: 分类
            content: 新内容
            date: 日期

        Returns:
            更新后的记忆内容
        """
        section_title = self.CATEGORY_MAPPING[category]

        # 格式化新记忆条目（带时间戳）
        new_entry = f"* {content} ({date})"

        # 查找分类位置
        lines = memory_content.split('\n')
        result_lines = []
        inserted = False
        skip_next = False

        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            result_lines.append(line)

            # 找到分类标题，在下一行或"暂无记忆内容"后插入
            if line.strip() == section_title and not inserted:
                # 检查下一行是否是"暂无记忆内容"
                if i + 1 < len(lines) and "暂无记忆内容" in lines[i + 1]:
                    # 替换"暂无记忆内容"
                    result_lines.append(new_entry)
                    skip_next = True  # 跳过下一行（暂无记忆内容）
                else:
                    # 在分类下第一行插入
                    result_lines.append(new_entry)
                inserted = True

        return '\n'.join(result_lines)

    def _update_memory(
        self,
        memory_content: str,
        category: str,
        target_content: str,
        new_content: str,
        date: str
    ) -> str:
        """更新记忆

        Args:
            memory_content: 现有记忆内容
            category: 分类
            target_content: 目标内容（用于匹配）
            new_content: 新内容
            date: 日期

        Returns:
            更新后的记忆内容
        """
        lines = memory_content.split('\n')
        result_lines = []
        updated = False

        # 查找目标条目并更新
        for line in lines:
            if target_content in line and line.strip().startswith('*'):
                # 找到目标条目，替换为新内容（带新时间戳）
                result_lines.append(f"* {new_content} ({date})")
                updated = True
            else:
                result_lines.append(line)

        if not updated:
            # 未找到目标，追加到对应分类
            return self._append_memory(memory_content, category, new_content, date)

        return '\n'.join(result_lines)

    def _delete_memory(
        self,
        memory_content: str,
        category: str,
        target_content: str
    ) -> str:
        """删除记忆

        Args:
            memory_content: 现有记忆内容
            category: 分类
            target_content: 目标内容（用于匹配）

        Returns:
            更新后的记忆内容
        """
        lines = memory_content.split('\n')
        result_lines = []
        deleted = False

        # 查找目标条目并删除
        for line in lines:
            if target_content in line and line.strip().startswith('*'):
                # 找到目标条目，跳过（删除）
                deleted = True
                continue
            else:
                result_lines.append(line)

        if not deleted:
            # 未找到目标，返回原内容并添加警告
            return memory_content + f"\n\n<!-- 警告：未找到目标内容 '{target_content}' -->"

        return '\n'.join(result_lines)


def create_write_memory_tool(base_dir: Path) -> BaseTool:
    """创建记忆写入工具

    Args:
        base_dir: 项目根目录

    Returns:
        WriteMemoryTool 实例
    """
    return WriteMemoryTool(
        memory_file=base_dir / "memory" / "MEMORY.md"
    )