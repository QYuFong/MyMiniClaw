"""知识库检索工具"""
from pathlib import Path
from typing import List, Dict, Optional

from langchain_core.tools import BaseTool
from pydantic import Field, PrivateAttr

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
)
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings

import config as global_config


class SearchKnowledgeTool(BaseTool):
    """知识库混合检索工具（基于 LlamaIndex）"""
    
    name: str = "search_knowledge_base"
    description: str = (
        "在知识库中搜索相关信息。"
        "输入应该是自然语言查询问题。"
        "系统会返回最相关的 3 条结果。"
        "示例：机器学习的基本原理是什么？"
    )
    
    knowledge_dir: Path = Field(description="知识库目录")
    storage_dir: Path = Field(description="索引存储目录")
    
    _index: Optional[VectorStoreIndex] = PrivateAttr(default=None)
    
    def _ensure_index(self) -> VectorStoreIndex:
        """确保索引已加载"""
        if self._index is not None:
            return self._index
        
        # 配置 Embedding 模型
        try:
            Settings.embed_model = OpenAIEmbedding(
                api_key=global_config.config.openai_api_key,
                api_base=global_config.config.openai_base_url,
                model_name=global_config.config.embedding_model,
            )
        except ValueError:
            # 如果模型名称不被识别，尝试使用 text-embedding-3-small 作为默认值
            # 但实际 API 调用时会使用配置的模型
            Settings.embed_model = OpenAIEmbedding(
                api_key=global_config.config.openai_api_key,
                api_base=global_config.config.openai_base_url,
                model_name="text-embedding-3-small",
            )
            # 手动覆盖模型名称
            Settings.embed_model.model_name = global_config.config.embedding_model
        
        # 尝试加载已有索引
        if (self.storage_dir / "docstore.json").exists():
            try:
                storage_context = StorageContext.from_defaults(
                    persist_dir=str(self.storage_dir)
                )
                self._index = load_index_from_storage(storage_context)
                return self._index
            except Exception as e:
                print(f"警告：加载索引失败，将重建索引: {e}")
        
        # 构建新索引
        self._index = self._build_index()
        return self._index
    
    def _build_index(self) -> VectorStoreIndex:
        """构建知识库索引"""
        # 检查知识库目录是否为空
        files = list(self.knowledge_dir.glob("**/*"))
        files = [f for f in files if f.is_file() and f.suffix in ['.md', '.txt', '.pdf']]
        
        if not files:
            # 创建空索引
            index = VectorStoreIndex([])
        else:
            # 读取文档
            reader = SimpleDirectoryReader(
                input_dir=str(self.knowledge_dir),
                recursive=True,
                filename_as_id=True,
            )
            documents = reader.load_data()
            
            # 构建索引
            index = VectorStoreIndex.from_documents(documents)
        
        # 持久化
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        index.storage_context.persist(persist_dir=str(self.storage_dir))
        
        return index
    
    def _run(self, query: str) -> str:
        """检索知识库"""
        try:
            # 确保索引已加载
            index = self._ensure_index()
            
            # 执行检索
            retriever = index.as_retriever(similarity_top_k=3)
            nodes = retriever.retrieve(query)
            
            if not nodes:
                return "知识库中没有找到相关信息。"
            
            # 格式化结果
            results = []
            for i, node in enumerate(nodes, 1):
                source = node.node.metadata.get('file_name', '未知来源')
                text = node.node.text[:500]  # 截断文本
                score = node.score
                
                results.append(
                    f"[结果 {i}] (来源: {source}, 相关度: {score:.3f})\n{text}\n"
                )
            
            return "\n".join(results)
            
        except Exception as e:
            return f"错误：检索失败 - {str(e)}"


def create_search_knowledge_tool(base_dir: Path) -> BaseTool:
    """创建知识库检索工具
    
    Args:
        base_dir: 项目根目录
        
    Returns:
        SearchKnowledgeTool 实例
    """
    return SearchKnowledgeTool(
        knowledge_dir=base_dir / "knowledge",
        storage_dir=base_dir / "storage" / "knowledge_index",
    )
