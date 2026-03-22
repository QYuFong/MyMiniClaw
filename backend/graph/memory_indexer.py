"""MEMORY.md 向量索引器"""
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any

from llama_index.core import (
    VectorStoreIndex,
    Document,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Settings

from utils.embedding import get_embedding_model


class MemoryIndexer:
    """为 MEMORY.md 构建专用的向量索引"""
    
    def __init__(self, base_dir: Path):
        self.memory_file = base_dir / "memory" / "MEMORY.md"
        self.storage_dir = base_dir / "storage" / "memory_index"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self._index: Optional[VectorStoreIndex] = None
        self._last_hash: Optional[str] = None
    
    def rebuild_index(self) -> None:
        """重建 MEMORY.md 索引"""
        # 配置 Embedding 模型（优先使用本地 Ollama，否则回退到 OpenAI 兼容模型）
        Settings.embed_model = get_embedding_model()
        
        # 读取 MEMORY.md
        if not self.memory_file.exists():
            # 创建空文件
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            self.memory_file.write_text("# 长期记忆\n\n这里存储你的长期记忆。", encoding='utf-8')
        
        with open(self.memory_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 计算哈希
        self._last_hash = hashlib.md5(content.encode()).hexdigest()
        
        # 构建文档
        document = Document(
            text=content,
            metadata={"source": "MEMORY.md"}
        )
        
        # 配置分块器
        splitter = SentenceSplitter(
            chunk_size=256,
            chunk_overlap=32
        )
        nodes = splitter.get_nodes_from_documents([document])
        
        # 构建索引
        self._index = VectorStoreIndex(nodes)
        
        # 持久化
        self._index.storage_context.persist(persist_dir=str(self.storage_dir))
        
        print(f"✓ MEMORY.md 索引已重建 ({len(nodes)} 个节点)")
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """检索 MEMORY.md 相关内容
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        # 检查是否需要重建索引
        self._maybe_rebuild()
        
        if self._index is None:
            return []
        
        # 执行检索
        retriever = self._index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)
        
        # 格式化结果
        results = []
        for node in nodes:
            results.append({
                "text": node.node.text,
                "score": node.score,
                "source": node.node.metadata.get("source", "MEMORY.md")
            })
        
        return results
    
    def _maybe_rebuild(self) -> None:
        """检查文件是否变更，变更则重建索引"""
        # 如果索引不存在，先尝试加载
        if self._index is None:
            if (self.storage_dir / "docstore.json").exists():
                try:
                    # 配置 Embedding 模型（优先使用本地 Ollama）
                    Settings.embed_model = get_embedding_model()
                    
                    storage_context = StorageContext.from_defaults(
                        persist_dir=str(self.storage_dir)
                    )
                    self._index = load_index_from_storage(storage_context)
                except Exception:
                    pass
        
        # 检查文件是否存在
        if not self.memory_file.exists():
            if self._index is None:
                self.rebuild_index()
            return
        
        # 计算当前哈希
        with open(self.memory_file, 'r', encoding='utf-8') as f:
            content = f.read()
        current_hash = hashlib.md5(content.encode()).hexdigest()
        
        # 如果哈希不同，重建索引
        if current_hash != self._last_hash:
            print("检测到 MEMORY.md 变更，正在重建索引...")
            self.rebuild_index()
