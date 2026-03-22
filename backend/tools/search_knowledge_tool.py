"""知识库混合检索工具 - BM25 + 向量检索"""
import logging
from pathlib import Path
from typing import Optional

from langchain_core.tools import BaseTool
from pydantic import Field, PrivateAttr

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core import Settings
from llama_index.core.retrievers import QueryFusionRetriever

from utils.embedding import get_embedding_model

logger = logging.getLogger(__name__)


class SearchKnowledgeTool(BaseTool):
    """知识库混合检索工具（BM25 关键词检索 + 向量检索）
    
    实现 PRD 要求的 Hybrid Search：
    - BM25：基于关键词匹配，擅长精确词匹配
    - Vector Search：基于语义相似度，擅长理解同义词和语义关系
    - QueryFusionRetriever：融合两种检索结果，使用 Reciprocal Rank Fusion 算法
    """
    
    name: str = "search_knowledge_base"
    description: str = (
        "在知识库中搜索相关信息。"
        "输入应该是自然语言查询问题。"
        "系统会使用混合检索（关键词 + 语义）返回最相关的结果。"
        "示例：机器学习的基本原理是什么？"
    )
    
    knowledge_dir: Path = Field(description="知识库目录")
    storage_dir: Path = Field(description="索引存储目录")
    top_k: int = Field(default=3, description="返回结果数量")
    
    _index: Optional[VectorStoreIndex] = PrivateAttr(default=None)
    _bm25_retriever: Optional[object] = PrivateAttr(default=None)
    _hybrid_retriever: Optional[QueryFusionRetriever] = PrivateAttr(default=None)
    
    def _ensure_index(self) -> VectorStoreIndex:
        """确保索引已加载"""
        if self._index is not None:
            return self._index
        
        Settings.embed_model = get_embedding_model()
        
        if (self.storage_dir / "docstore.json").exists():
            try:
                storage_context = StorageContext.from_defaults(
                    persist_dir=str(self.storage_dir)
                )
                self._index = load_index_from_storage(storage_context)
                logger.info("[RAG] 从存储加载已有索引")
                return self._index
            except Exception as e:
                logger.warning(f"[RAG] 加载索引失败，将重建索引: {e}")
        
        self._index = self._build_index()
        return self._index
    
    def _build_index(self) -> VectorStoreIndex:
        """构建知识库索引"""
        files = list(self.knowledge_dir.glob("**/*"))
        files = [f for f in files if f.is_file() and f.suffix.lower() in ['.md', '.txt', '.pdf']]
        
        if not files:
            logger.info("[RAG] 知识库为空，创建空索引")
            index = VectorStoreIndex([])
        else:
            logger.info(f"[RAG] 正在索引 {len(files)} 个文档...")
            reader = SimpleDirectoryReader(
                input_dir=str(self.knowledge_dir),
                recursive=True,
                filename_as_id=True,
            )
            documents = reader.load_data()
            index = VectorStoreIndex.from_documents(documents)
            logger.info(f"[RAG] 索引构建完成")
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        index.storage_context.persist(persist_dir=str(self.storage_dir))
        
        return index
    
    def _get_hybrid_retriever(self) -> QueryFusionRetriever:
        """获取混合检索器（BM25 + Vector）"""
        if self._hybrid_retriever is not None:
            return self._hybrid_retriever
        
        index = self._ensure_index()
        
        if not index.docstore.docs():
            logger.warning("[RAG] 知识库为空，无法创建混合检索器")
            return None
        
        vector_retriever = index.as_retriever(similarity_top_k=self.top_k)
        
        try:
            from llama_index.retrievers.bm25 import BM25Retriever
            
            nodes = list(index.docstore.docs().values())
            self._bm25_retriever = BM25Retriever.from_defaults(
                nodes=nodes,
                similarity_top_k=self.top_k,
            )
            logger.info("[RAG] BM25 检索器创建成功")
            
            self._hybrid_retriever = QueryFusionRetriever(
                retrievers=[vector_retriever, self._bm25_retriever],
                similarity_top_k=self.top_k,
                num_queries=1,
                mode="reciprocal_rerank",
                use_async=False,
            )
            logger.info("[RAG] 混合检索器（BM25 + Vector）创建成功")
            
        except ImportError:
            logger.warning("[RAG] llama-index-retrievers-bm25 未安装，回退到纯向量检索")
            self._hybrid_retriever = vector_retriever
        except Exception as e:
            logger.warning(f"[RAG] 创建 BM25 检索器失败: {e}，回退到纯向量检索")
            self._hybrid_retriever = vector_retriever
        
        return self._hybrid_retriever
    
    def _run(self, query: str) -> str:
        """执行混合检索"""
        try:
            retriever = self._get_hybrid_retriever()
            
            if retriever is None:
                return "知识库为空，暂无可检索内容。请先在 knowledge/ 目录添加文档。"
            
            logger.info(f"[RAG] 执行混合检索: {query}")
            nodes = retriever.retrieve(query)
            
            if not nodes:
                return "知识库中没有找到相关信息。"
            
            results = []
            for i, node in enumerate(nodes, 1):
                if hasattr(node, 'node'):
                    text_node = node.node
                    score = node.score if hasattr(node, 'score') else 0.0
                else:
                    text_node = node
                    score = 0.0
                
                source = text_node.metadata.get('file_name', '未知来源')
                text = text_node.text[:500]
                
                results.append(
                    f"[结果 {i}] (来源: {source}, 相关度: {score:.3f})\n{text}\n"
                )
            
            logger.info(f"[RAG] 检索返回 {len(results)} 条结果")
            return "\n".join(results)
            
        except Exception as e:
            logger.error(f"[RAG] 检索失败: {e}")
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
