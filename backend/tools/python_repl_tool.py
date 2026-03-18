"""Python 代码解释器"""
from langchain_core.tools import BaseTool
from langchain_experimental.tools import PythonREPLTool as LangChainPythonREPL


def create_python_repl_tool() -> BaseTool:
    """创建 Python REPL 工具
    
    Returns:
        PythonREPLTool 实例
    """
    tool = LangChainPythonREPL()
    tool.name = "python_repl"
    tool.description = (
        "Python 代码解释器。用于执行 Python 代码并返回结果。"
        "输入应该是有效的 Python 代码字符串。"
        "可以用于数学计算、数据处理、文本处理等任务。"
        "示例输入：print(2 + 2)"
    )
    
    return tool
