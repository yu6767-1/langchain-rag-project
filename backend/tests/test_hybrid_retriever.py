"""
混合检索器模块单元测试
======================
测试 backend/core/hybrid_retriever.py 中的 _text_similarity 和 HybridRetriever。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from backend.core.hybrid_retriever import _text_similarity, HybridRetriever


# ============================================================
# _text_similarity — 文本相似度
# ============================================================

class TestTextSimilarity:
    """模块：core/hybrid_retriever.py — _text_similarity"""

    def test_完全相同的文本_相似度为1(self):
        """两个完全相同的文本，相似度应为 1.0（100%）"""
        result = _text_similarity("手机电池续航", "手机电池续航")
        assert result == 1.0

    def test_完全不同文本_相似度为0(self):
        """两个完全没有共同字符的文本，相似度应为 0.0"""
        result = _text_similarity("abc", "xyz")
        assert result == 0.0

    def test_部分重叠_返回合理相似度(self):
        """
        两个有一半字符重叠的文本，相似度应在 0 到 1 之间。
        基于集合计算："abcde" 和 "abcxy" → 交集 = {a,b,c}，并集大小 = 5，
        相似度 ≈ 3/5 = 0.6
        """
        result = _text_similarity("abcde", "abcxy")
        assert 0.0 < result < 1.0

    def test_两个都是空字符串_返回0(self):
        """两个空字符串，相似度应为 0（没有有效字符可比较）"""
        result = _text_similarity("", "")
        assert result == 0.0

    def test_一个空字符串_返回0(self):
        """一个空字符串和一个非空字符串，相似度应为 0"""
        result = _text_similarity("hello", "")
        assert result == 0.0

    def test_一个大集合子集关系_返回正确比例(self):
        """
        "ab" 的字符集合是 "abc" 的子集。
        交集 = {a,b} = 2，并集大小 = max(2,3) = 3 → 2/3 ≈ 0.667
        """
        result = _text_similarity("ab", "abc")
        assert result == 2.0 / 3.0


# ============================================================
# HybridRetriever.is_empty — 检查知识库是否为空
# ============================================================

class TestHybridRetrieverIsEmpty:
    """模块：core/hybrid_retriever.py — HybridRetriever.is_empty"""

    @patch("backend.core.hybrid_retriever.get_chroma_client")
    def test_没有集合_返回True(self, mock_client):
        """知识库中没有任何 Collection，is_empty 返回 True"""
        mock_client.return_value.list_collections.return_value = []
        retriever = HybridRetriever(top_k=8)
        result = retriever.is_empty()
        assert result is True

    @patch("backend.core.hybrid_retriever.get_chroma_client")
    def test_集合都存在但都为空_返回True(self, mock_client):
        """有 Collection 但每个都 count()=0，is_empty 返回 True"""
        col1 = MagicMock()
        col1.count.return_value = 0
        col2 = MagicMock()
        col2.count.return_value = 0
        mock_client.return_value.list_collections.return_value = [col1, col2]
        retriever = HybridRetriever(top_k=8)
        result = retriever.is_empty()
        assert result is True

    @patch("backend.core.hybrid_retriever.get_chroma_client")
    def test_有集合且有数据_返回False(self, mock_client):
        """至少有一个 Collection 的 count()>0，is_empty 返回 False"""
        col1 = MagicMock()
        col1.count.return_value = 0
        col2 = MagicMock()
        col2.count.return_value = 5  # 有数据
        mock_client.return_value.list_collections.return_value = [col1, col2]
        retriever = HybridRetriever(top_k=8)
        result = retriever.is_empty()
        assert result is False

    @patch("backend.core.hybrid_retriever.get_chroma_client")
    def test_数据库连接异常_返回True(self, mock_client):
        """ChromaDB 连接异常时，is_empty 应安全返回 True（不崩溃）"""
        mock_client.side_effect = Exception("连接失败")
        retriever = HybridRetriever(top_k=8)
        result = retriever.is_empty()
        assert result is True


# ============================================================
# HybridRetriever._get_relevant_documents — 检索
# ============================================================

class TestHybridRetrieverGetDocuments:
    """模块：core/hybrid_retriever.py — HybridRetriever._get_relevant_documents"""

    @patch("backend.core.hybrid_retriever.get_chroma_client")
    def test_知识库为空_返回空列表(self, mock_client):
        """知识库为空时，检索应返回空列表"""
        mock_client.return_value.list_collections.return_value = []
        retriever = HybridRetriever(top_k=8)
        result = retriever._get_relevant_documents("测试问题")
        assert result == []

    @patch("backend.core.hybrid_retriever.get_chroma_client")
    @patch.object(HybridRetriever, "is_empty", return_value=False)
    def test_检索异常_返回空列表不崩溃(self, mock_is_empty, mock_client):
        """检索过程中发生异常，应返回空列表而不崩溃"""
        mock_client.side_effect = Exception("数据库崩溃")
        retriever = HybridRetriever(top_k=8)
        result = retriever._get_relevant_documents("测试")
        assert result == []

    @patch("backend.core.hybrid_retriever.get_chroma_client")
    @patch("backend.core.hybrid_retriever.get_embeddings")
    def test_检索成功_返回Document列表(self, mock_embeddings, mock_client):
        """正常检索应返回 LangChain Document 对象列表"""
        # Mock embedding
        mock_embeddings.return_value.embed_query.return_value = [0.1] * 768

        # Mock collection with data
        mock_col = MagicMock()
        mock_col.count.return_value = 1
        mock_col.query.return_value = {
            "documents": [["这是一段测试商品内容，包含详细参数"]],
            "metadatas": [[{"filename": "商品手册.pdf", "page": 1}]],
            "distances": [[0.3]],
        }
        mock_client.return_value.list_collections.return_value = [mock_col]

        retriever = HybridRetriever(top_k=8)
        result = retriever._get_relevant_documents("测试商品")

        assert len(result) == 1
        assert result[0].page_content == "这是一段测试商品内容，包含详细参数"
        assert result[0].metadata["filename"] == "商品手册.pdf"

    @patch("backend.core.hybrid_retriever.get_chroma_client")
    @patch("backend.core.hybrid_retriever.get_embeddings")
    def test_检索到多个结果_返回TopK条(self, mock_embeddings, mock_client):
        """检索到多个文档时，应返回不超过 top_k 条结果"""
        mock_embeddings.return_value.embed_query.return_value = [0.1] * 768

        # 创建多个返回文档
        doc_texts = [f"商品内容{i}" for i in range(10)]
        mock_col = MagicMock()
        mock_col.count.return_value = 10
        mock_col.query.return_value = {
            "documents": [doc_texts],
            "metadatas": [[{"filename": f"doc{i}.pdf"} for i in range(10)]],
            "distances": [[i * 0.1 for i in range(10)]],
        }
        mock_client.return_value.list_collections.return_value = [mock_col]

        retriever = HybridRetriever(top_k=4)
        result = retriever._get_relevant_documents("测试")

        # 应返回不超过 top_k 条
        assert len(result) <= 4

    @patch.object(HybridRetriever, "is_empty", return_value=True)
    def test_invoke_空知识库_返回空列表(self, mock_is_empty):
        """invoke 方法在知识库为空时也应返回空列表"""
        retriever = HybridRetriever(top_k=8)
        result = retriever.invoke("测试问题")
        assert result == []
