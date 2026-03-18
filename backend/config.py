"""全局配置管理"""
import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# 加载 .env 文件，明确指定路径（相对于本文件所在目录）
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)


class Config:
    """全局配置类，管理环境变量和持久化配置"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.config_file = base_dir / "config.json"
        
        # 环境变量配置
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        # 持久化配置
        self._persistent_config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """从 config.json 加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"警告：加载配置文件失败: {e}")
                return {}
        return {}
    
    def _save_config(self) -> None:
        """保存配置到 config.json"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._persistent_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"警告：保存配置文件失败: {e}")
    
    def get_rag_mode(self) -> bool:
        """获取 RAG 模式状态"""
        return self._persistent_config.get("rag_mode", False)
    
    def set_rag_mode(self, enabled: bool) -> None:
        """设置 RAG 模式状态"""
        self._persistent_config["rag_mode"] = enabled
        self._save_config()


# 全局配置实例（在 app.py 中初始化）
config: Config = None  # type: ignore


def init_config(base_dir: Path) -> Config:
    """初始化全局配置"""
    global config
    config = Config(base_dir)
    return config
