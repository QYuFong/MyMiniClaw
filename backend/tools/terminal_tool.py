"""命令行操作工具"""
import subprocess
from pathlib import Path
from typing import Optional, ClassVar, List

from langchain_core.tools import BaseTool
from pydantic import Field


class TerminalTool(BaseTool):
    """受限的命令行操作工具，在沙箱环境中执行命令"""
    
    name: str = "terminal"
    description: str = (
        "在受限的沙箱环境中执行 Shell 命令。"
        "输入应该是有效的 shell 命令字符串。"
        "命令将在项目根目录下执行，输出会被截断到 5000 字符以内。"
        "危险命令（如 rm -rf /）会被拦截。"
    )
    
    root_dir: Path = Field(description="工作根目录")
    
    # 黑名单命令
    BLACKLIST: ClassVar[List[str]] = [
        "rm -rf /",
        "mkfs",
        "dd if=",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "init 0",
        "init 6",
        ":(){ :|:& };:",  # Fork bomb
        "> /dev/sda",
        "mv /* ",
    ]
    
    def _run(self, command: str) -> str:
        """执行命令"""
        # 检查黑名单
        for dangerous_cmd in self.BLACKLIST:
            if dangerous_cmd in command.lower():
                return f"错误：命令被拦截，包含危险操作: {dangerous_cmd}"
        
        try:
            # 执行命令，设置工作目录和超时
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )
            
            # 合并标准输出和标准错误
            output = result.stdout
            if result.stderr:
                output += f"\n[STDERR]\n{result.stderr}"
            
            if result.returncode != 0:
                output = f"[Exit Code: {result.returncode}]\n{output}"
            
            # 截断输出
            if len(output) > 5000:
                output = output[:5000] + "\n...[输出被截断]"
            
            return output or "[命令执行成功，无输出]"
            
        except subprocess.TimeoutExpired:
            return "错误：命令执行超时（30秒）"
        except Exception as e:
            return f"错误：{str(e)}"


def create_terminal_tool(base_dir: Path) -> BaseTool:
    """创建终端工具
    
    Args:
        base_dir: 项目根目录
        
    Returns:
        TerminalTool 实例
    """
    return TerminalTool(root_dir=base_dir)
