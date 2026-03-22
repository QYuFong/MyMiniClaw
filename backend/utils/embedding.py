"""Embedding 模型初始化工具

优先使用本地 Ollama 模型，如果不可用则回退到 OpenAI 兼容的远程模型。
"""
import logging
import httpx
from typing import Optional

from llama_index.core.embeddings import BaseEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding

import config as global_config

logger = logging.getLogger(__name__)

_cached_embedding_model: Optional[BaseEmbedding] = None
_use_ollama: Optional[bool] = None


def _check_ollama_available() -> bool:
    """检查 Ollama 服务是否可用"""
    try:
        base_url = global_config.config.ollama_base_url
        response = httpx.get(f"{base_url}/api/tags", timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            target_model = global_config.config.ollama_embedding_model
            for model in models:
                if target_model in model:
                    logger.info(f"[EMBEDDING] Ollama 服务可用，找到模型: {model}")
                    return True
            logger.warning(f"[EMBEDDING] Ollama 服务可用，但未找到模型 {target_model}")
            logger.info(f"[EMBEDDING] 可用模型: {models}")
            return False
        return False
    except Exception as e:
        logger.warning(f"[EMBEDDING] Ollama 服务不可用: {e}")
        return False


def _create_ollama_embedding() -> BaseEmbedding:
    """创建 Ollama embedding 模型"""
    try:
        from llama_index.embeddings.ollama import OllamaEmbedding
        
        model = OllamaEmbedding(
            model_name=global_config.config.ollama_embedding_model,
            base_url=global_config.config.ollama_base_url,
        )
        logger.info(f"[EMBEDDING] 使用本地 Ollama 模型: {global_config.config.ollama_embedding_model}")
        return model
    except ImportError:
        logger.warning("[EMBEDDING] llama_index.embeddings.ollama 未安装，回退到 OpenAI 兼容模型")
        raise


def _create_openai_embedding() -> BaseEmbedding:
    """创建 OpenAI 兼容的 embedding 模型"""
    try:
        model = OpenAIEmbedding(
            api_key=global_config.config.openai_api_key,
            api_base=global_config.config.openai_base_url,
            model_name=global_config.config.embedding_model,
        )
        logger.info(f"[EMBEDDING] 使用 OpenAI 兼容模型: {global_config.config.embedding_model}")
        return model
    except ValueError:
        model = OpenAIEmbedding(
            api_key=global_config.config.openai_api_key,
            api_base=global_config.config.openai_base_url,
            model_name="text-embedding-3-small",
        )
        model.model_name = global_config.config.embedding_model
        logger.info(f"[EMBEDDING] 使用 OpenAI 兼容模型 (fallback): {global_config.config.embedding_model}")
        return model


def get_embedding_model(force_refresh: bool = False) -> BaseEmbedding:
    """获取 embedding 模型
    
    优先使用本地 Ollama 模型，如果不可用则回退到 OpenAI 兼容的远程模型。
    
    Args:
        force_refresh: 是否强制重新检测和创建模型
        
    Returns:
        BaseEmbedding 实例
    """
    global _cached_embedding_model, _use_ollama
    
    if _cached_embedding_model is not None and not force_refresh:
        return _cached_embedding_model
    
    if _use_ollama is None or force_refresh:
        _use_ollama = _check_ollama_available()
    
    if _use_ollama:
        try:
            _cached_embedding_model = _create_ollama_embedding()
            return _cached_embedding_model
        except Exception as e:
            logger.warning(f"[EMBEDDING] 创建 Ollama 模型失败: {e}，回退到 OpenAI 兼容模型")
            _use_ollama = False
    
    _cached_embedding_model = _create_openai_embedding()
    return _cached_embedding_model


def is_using_local_embedding() -> bool:
    """检查当前是否使用本地 embedding 模型"""
    return _use_ollama is True
