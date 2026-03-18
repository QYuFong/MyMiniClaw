"""网页内容获取工具"""
import requests
from bs4 import BeautifulSoup
import html2text
from typing import Optional

from langchain_core.tools import BaseTool


class FetchURLTool(BaseTool):
    """获取网页内容并转换为 Markdown 格式"""
    
    name: str = "fetch_url"
    description: str = (
        "获取指定 URL 的网页内容，自动转换为 Markdown 格式。"
        "输入应该是完整的 URL（包含 http:// 或 https://）。"
        "返回清洗后的文本内容，方便 AI 理解。"
        "示例：https://example.com"
    )
    
    def _run(self, url: str) -> str:
        """获取网页内容"""
        try:
            # 发送请求
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # 检测内容类型
            content_type = response.headers.get('Content-Type', '').lower()
            
            # 如果是 JSON，直接返回
            if 'application/json' in content_type:
                return response.text
            
            # 如果是 HTML，转换为 Markdown
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 移除 script 和 style 标签
                for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                
                # 转换为 Markdown
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                h.ignore_emphasis = False
                h.body_width = 0  # 不自动换行
                
                markdown_text = h.handle(str(soup))
                
                # 截断输出
                if len(markdown_text) > 5000:
                    markdown_text = markdown_text[:5000] + "\n...[内容被截断]"
                
                return markdown_text
            
            # 其他类型，返回纯文本
            text = response.text
            if len(text) > 5000:
                text = text[:5000] + "\n...[内容被截断]"
            return text
            
        except requests.Timeout:
            return "错误：请求超时（15秒）"
        except requests.RequestException as e:
            return f"错误：无法获取网页内容 - {str(e)}"
        except Exception as e:
            return f"错误：{str(e)}"


def create_fetch_url_tool() -> BaseTool:
    """创建网页获取工具
    
    Returns:
        FetchURLTool 实例
    """
    return FetchURLTool()
