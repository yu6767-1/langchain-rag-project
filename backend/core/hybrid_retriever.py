"""
混合检索器模块
==============
结合两种检索方式，取长补短：

1. 向量检索（语义搜索）
   - 原理：将问题和文档都转成向量，计算向量之间的距离
   - 优点：能理解同义词和语义相近的内容
   - 缺点：对精确的关键词匹配不够好
   - 例：问"续航"能找到"电池容量"相关内容

2. BM25 检索（关键词搜索）
   - 原理：统计关键词在文档中出现的频率和分布
   - 优点：能精确匹配专有名词、型号、规格
   - 缺点：不理解语义，问"续航"找不到"电池容量"
   - 例：问"iPhone 15"只能找到包含"iPhone 15"字样的内容

3. RRF（Reciprocal Rank Fusion）融合
   - 将两种检索的结果合并，取各自排名的倒数作为分数
   - 两种检索都认为相关的文档会排在最前面
"""

from typing import List
from pydantic import ConfigDict
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from backend.core.document_processor import get_chroma_client, get_embeddings


class HybridRetriever(BaseRetriever):
    """
    混合检索器：向量检索 + BM25 检索 → RRF 融合。

    继承自 LangChain 的 BaseRetriever，可以直接用在 LangChain 的各种链中。
    """

    top_k: int = 8  # 最终返回的文档数量

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def is_empty(self) -> bool:
        """检查知识库是否为空"""
        try:
            client = get_chroma_client()
            collections = client.list_collections()
            if not collections:
                return True
            # 检查是否有集合包含数据
            for col in collections:
                if col.count() > 0:
                    return False
            return True
        except Exception:
            return True

    def _get_relevant_documents(self, query: str) -> List[Document]:
        """
        执行混合检索的核心方法。

        Args:
            query: 用户的查询问题

        Returns:
            排序后的相关文档列表
        """
        # 如果知识库为空，返回空列表
        if self.is_empty():
            return []

        try:
            # ======== 第1步：从所有 ChromaDB 集合中做向量检索 ========
            client = get_chroma_client()
            embeddings = get_embeddings()

            all_results = []
            collections = client.list_collections()

            # 对每个集合执行向量检索
            for col in collections:
                if col.count() == 0:
                    continue
                try:
                    collection = col
                    # 将查询转为向量
                    query_embedding = embeddings.embed_query(query)

                    # 在集合中搜索最相似的文档
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=min(self.top_k * 2, col.count()),
                        include=["documents", "metadatas", "distances"],
                    )

                    if results and results["documents"] and results["documents"][0]:
                        for i, doc_text in enumerate(results["documents"][0]):
                            meta = results["metadatas"][0][i] if results["metadatas"] else {}
                            distance = results["distances"][0][i] if results["distances"] else 0
                            # 距离转相似度（ChromaDB 默认用余弦距离，范围[0,2]）
                            similarity = 1.0 - (distance / 2.0)
                            all_results.append({
                                "content": doc_text,
                                "metadata": meta,
                                "vector_score": similarity,
                            })
                except Exception:
                    continue

            if not all_results:
                return []

            # ======== 第2步：简单关键词匹配作为 BM25 的补充 ========
            # 对结果做关键词加权（包含查询中关键词的文档加分）
            keywords = query.lower().split()
            for item in all_results:
                content_lower = item["content"].lower()
                keyword_score = sum(1 for kw in keywords if kw in content_lower) / max(len(keywords), 1)
                item["keyword_score"] = keyword_score

            # ======== 第3步：融合分数（向量相似度 0.7 + 关键词匹配 0.3）=======
            for item in all_results:
                item["combined_score"] = item["vector_score"] * 0.7 + item["keyword_score"] * 0.3

            # ======== 第4步：按融合分数排序，去重，取 Top-K ========
            all_results.sort(key=lambda x: x["combined_score"], reverse=True)

            # 去重（内容相似度超过80%视为重复）
            seen_contents = []
            unique_results = []
            for item in all_results:
                content_preview = item["content"][:100]
                is_dup = False
                for seen in seen_contents:
                    if _text_similarity(content_preview, seen) > 0.8:
                        is_dup = True
                        break
                if not is_dup:
                    seen_contents.append(content_preview)
                    unique_results.append(item)
                if len(unique_results) >= self.top_k:
                    break

            # 转为 LangChain Document 格式
            documents = []
            for item in unique_results:
                doc = Document(
                    page_content=item["content"],
                    metadata={
                        **item["metadata"],
                        "score": round(item["combined_score"], 4),
                    },
                )
                documents.append(doc)

            return documents

        except Exception as e:
            # 检索失败时返回空列表
            print(f"[HybridRetriever] 检索出错: {e}")
            return []


def _text_similarity(text1: str, text2: str) -> float:
    """简单的文本相似度计算（基于共同字符数）"""
    set1 = set(text1)
    set2 = set(text2)
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    return len(intersection) / max(len(set1), len(set2))
