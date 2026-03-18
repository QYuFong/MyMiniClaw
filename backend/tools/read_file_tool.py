"""文件读取工具"""
from pathlib import Path
from typing import Optional

from langchain_core.tools import BaseTool
from pydantic import Field


class ReadFileTool(BaseTool):
    """安全的文件读取工具，只能读取项目目录内的文件"""
    
    name: str = "read_file"
    description: str = (
        "读取项目目录内的文件内容。"
        "输入应该是相对于项目根目录的文件路径。"
        "例如：skills/get_weather/SKILL.md 或 memory/MEMORY.md"
        "输出会被截断到 10000 字符以内。"
    )
    
    root_dir: Path = Field(description="项目根目录")
    
    def _run(self, file_path: str) -> str:
        """读取文件"""
        try:
            # 构建完整路径
            full_path = (self.root_dir / file_path).resolve()
            
            # 安全检查：确保路径在根目录内
            if not str(full_path).startswith(str(self.root_dir.resolve())):
                return f"错误：路径遍历攻击被拦截，不允许访问项目外的文件"
            
            # 检查文件是否存在
            if not full_path.exists():
                return f"错误：文件不存在: {file_path}"
            
            if not full_path.is_file():
                return f"错误：路径不是文件: {file_path}"
            
            # 读取文件
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # 截断输出
            if len(content) > 10000:
                content = content[:10000] + "\n...[文件内容被截断]"
            
            return content
            
        except UnicodeDecodeError:
            return f"错误：文件不是文本文件或编码不支持: {file_path}"
        except Exception as e:
            return f"错误：{str(e)}"


def create_read_file_tool(base_dir: Path) -> BaseTool:
    """创建文件读取工具
    
    Args:
        base_dir: 项目根目录
        
    Returns:
        ReadFileTool 实例
    """
    return ReadFileTool(root_dir=base_dir)
