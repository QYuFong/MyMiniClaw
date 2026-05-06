"""MEMORY.md 向量索引器"""
import hashlib
import re
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
from llama_index.core.schema import TextNode

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
        """重建 MEMORY.md 索引（Markdown-aware chunking）"""
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

        # Markdown-aware 分块
        nodes = self._markdown_chunking(content)

        # 构建索引
        self._index = VectorStoreIndex(nodes)

        # 持久化
        self._index.storage_context.persist(persist_dir=str(self.storage_dir))

        print(f"✓ MEMORY.md 索引已重建 ({len(nodes)} 个节点)")

    def _markdown_chunking(self, content: str) -> List[TextNode]:
        """Markdown-aware 分块策略

        1. 按 ## 二级标题分割成 sections
        2. 每个 section 内按句子递归划分
        3. 每个 chunk 保留所属 section 的标题 metadata

        Args:
            content: MEMORY.md 内容

        Returns:
            分块后的节点列表
        """
        nodes = []

        # 按 ## 二级标题分割
        # 匹配模式：## 标题 + 后续内容（直到下一个 ## 或文档结束）
        section_pattern = r'(##\s+[^\n]+)\n(.*?)(?=##\s+[^\n]+|$)'
        sections = re.findall(section_pattern, content, re.DOTALL)

        # 如果没有找到二级标题，使用一级标题或整体内容
        if not sections:
            # 尝试按一级标题分割
            section_pattern = r'(#\s+[^\n]+)\n(.*?)(?=#\s+[^\n]+|$)'
            sections = re.findall(section_pattern, content, re.DOTALL)

            if not sections:
                # 没有任何标题，整体作为一个 section
                sections = [("长期记忆", content)]

        # 配置句子分割器（用于 section 内递归划分）
        sentence_splitter = SentenceSplitter(
            chunk_size=256,
            chunk_overlap=32
        )

        # 处理每个 section
        for section_title, section_content in sections:
            # 清理标题（去掉 ## 符号）
            clean_title = section_title.strip().replace('##', '').strip()

            # 如果 section 内容为空或只有占位符，跳过
            section_text = section_content.strip()
            if not section_text or "暂无" in section_text:
                continue

            # 创建 section 文档
            section_doc = Document(
                text=section_text,
                metadata={
                    "source": "MEMORY.md",
                    "section": clean_title  # 保留所属 section 信息
                }
            )

            # 在 section 内按句子分割
            section_nodes = sentence_splitter.get_nodes_from_documents([section_doc])

            # 为每个节点添加 section metadata
            for node in section_nodes:
                node.metadata["section"] = clean_title
                nodes.append(node)

        return nodes
    
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
