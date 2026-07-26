"""
文档处理器模块单元测试
======================
测试 backend/core/document_processor.py 中的文档加载和切分功能。
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open, PropertyMock
from langchain_core.documents import Document as LangchainDocument
from backend.core.document_processor import (
    load_document,
    split_documents,
    get_chroma_client,
    delete_collection,
)


# ============================================================
# split_documents — 文档切分
# ============================================================

class TestSplitDocuments:
    """模块：core/document_processor.py — split_documents"""

    def test_单个文档_切分为多个片段(self):
        """一个较长的文档应被切分成多个片段"""
        # 创建一个超长文档（2000字），chunk_size=500, overlap=100
        long_text = "测试商品信息。" * 200  # 约1400字
        doc = LangchainDocument(
            page_content=long_text,
            metadata={"filename": "商品.pdf"},
        )

        with patch("backend.core.document_processor.CHUNK_SIZE", 500), \
             patch("backend.core.document_processor.CHUNK_OVERLAP", 100):
            result = split_documents([doc])

        assert len(result) > 1  # 被切分成多段
        # 每个 fragment 的 metadata 应保留
        for chunk in result:
            assert chunk.metadata["filename"] == "商品.pdf"

    def test_文档很短_不需要切分_返回原文档(self):
        """文档内容少于 chunk_size 时，不应被切分，直接返回"""
        short_text = "这是一个很短的文档，只有一句话。"
        doc = LangchainDocument(
            page_content=short_text,
            metadata={"filename": "短文档.txt"},
        )

        with patch("backend.core.document_processor.CHUNK_SIZE", 500):
            result = split_documents([doc])

        # 文本很短，切分后应该仍是 1 个片段
        assert len(result) >= 1
        assert short_text in result[0].page_content

    def test_空文档列表_返回空列表(self):
        """传入空列表，应返回空列表"""
        result = split_documents([])
        assert result == []

    def test_多文档_每个都被切分(self):
        """传入多个文档，每个都会被切分处理"""
        texts = ["文档A内容。" * 100, "文档B内容。" * 100]
        docs = [
            LangchainDocument(page_content=t, metadata={"filename": f"doc{i}.txt"})
            for i, t in enumerate(texts)
        ]

        with patch("backend.core.document_processor.CHUNK_SIZE", 300):
            result = split_documents(docs)

        assert len(result) > 2  # 两个文档都被切分了


# ============================================================
# load_document — 文档加载
# ============================================================

class TestLoadDocument:
    """模块：core/document_processor.py — load_document"""

    def test_不支持的文件类型_抛出ValueError(self):
        """传入不支持的文件类型，应抛出 ValueError"""
        with pytest.raises(ValueError, match="不支持的文件类型"):
            load_document("test.xyz")

    def test_无后缀文件名_抛出ValueError(self):
        """没有后缀的文件名，也应抛出 ValueError"""
        with pytest.raises(ValueError, match="不支持的文件类型"):
            load_document("test_no_ext")

    @patch("backend.core.document_processor.TextLoader")
    def test_TXT文件_使用TextLoader加载(self, mock_loader):
        """txt 文件应使用 TextLoader 加载（utf-8 编码）"""
        mock_loader.return_value.load.return_value = [
            LangchainDocument(page_content="文本内容", metadata={})
        ]
        result = load_document("test.txt")
        # 验证使用 utf-8 编码
        mock_loader.assert_called_once_with("test.txt", encoding="utf-8")
        assert len(result) == 1

    @patch("backend.core.document_processor.CSVLoader")
    def test_CSV文件_使用CSVLoader加载(self, mock_loader):
        """csv 文件应使用 CSVLoader 加载（utf-8 编码）"""
        mock_loader.return_value.load.return_value = [
            LangchainDocument(page_content="col1,col2\na,b", metadata={})
        ]
        result = load_document("data.csv")
        mock_loader.assert_called_once_with("data.csv", encoding="utf-8")
        assert len(result) == 1

    @patch("backend.core.document_processor.PyPDFLoader")
    def test_PDF文件_使用PyPDFLoader加载(self, mock_loader):
        """pdf 文件应使用 PyPDFLoader 加载"""
        mock_loader.return_value.load.return_value = [
            LangchainDocument(page_content="PDF内容", metadata={"page": 0})
        ]
        result = load_document("document.pdf")
        mock_loader.assert_called_once_with("document.pdf")
        assert len(result) == 1

    @patch("backend.core.document_processor.UnstructuredMarkdownLoader")
    def test_MD文件_使用MarkdownLoader加载(self, mock_loader):
        """md 文件应使用 UnstructuredMarkdownLoader 加载"""
        mock_loader.return_value.load.return_value = [
            LangchainDocument(page_content="# Markdown 标题", metadata={})
        ]
        result = load_document("README.md")
        assert len(result) == 1

    @patch("backend.core.document_processor._load_office_document")
    def test_DOCX文件_调用内部加载函数(self, mock_load_office):
        """docx 文件应委托给 _load_office_document 处理"""
        mock_load_office.return_value = [
            LangchainDocument(page_content="Word文档内容", metadata={"source": "report.docx"})
        ]
        result = load_document("report.docx")
        mock_load_office.assert_called_once_with("report.docx", ".docx")
        assert len(result) == 1
        assert "Word文档内容" in result[0].page_content

    @patch("backend.core.document_processor._load_office_document")
    def test_XLSX文件_调用内部加载函数(self, mock_load_office):
        """xlsx 文件应委托给 _load_office_document 处理"""
        mock_load_office.return_value = [
            LangchainDocument(page_content="=== Sheet: Sheet1 ===\n商品名称 | 价格\n手机A | 999", metadata={"source": "products.xlsx"})
        ]
        result = load_document("products.xlsx")
        mock_load_office.assert_called_once_with("products.xlsx", ".xlsx")
        assert len(result) >= 1
        content = result[0].page_content
        assert "Sheet1" in content

    @patch("backend.core.document_processor._load_office_document")
    def test_DOCX提取为空_抛出ValueError(self, mock_load_office):
        """当 _load_office_document 抛出 ValueError，load_document 应透传"""
        mock_load_office.side_effect = ValueError("无法从文件中提取文本内容: empty.docx")
        with pytest.raises(ValueError, match="无法从文件中提取文本内容"):
            load_document("empty.docx")

    @patch("backend.core.document_processor._load_office_document")
    def test_XLSX全空表格_抛出ValueError(self, mock_load_office):
        """当 _load_office_document 抛出 ValueError，load_document 应透传"""
        mock_load_office.side_effect = ValueError("无法从文件中提取文本内容: empty.xlsx")
        with pytest.raises(ValueError, match="无法从文件中提取文本内容"):
            load_document("empty.xlsx")


# ============================================================
# get_chroma_client — ChromaDB 客户端（单例）
# ============================================================

class TestGetChromaClient:
    """模块：core/document_processor.py — get_chroma_client"""

    @patch("backend.core.document_processor.PersistentClient")
    def test_首次调用_创建新客户端(self, mock_client_class):
        """首次调用 get_chroma_client 应创建新的 PersistentClient"""
        # 重置全局变量以模拟首次调用
        import backend.core.document_processor as dp
        dp._chroma_client = None

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result = dp.get_chroma_client()

        mock_client_class.assert_called_once()
        assert result is mock_client

    @patch("backend.core.document_processor.PersistentClient")
    def test_第二次调用_返回单例不重新创建(self, mock_client_class):
        """第二次调用应返回同一个实例（单例模式），不会创建新客户端"""
        import backend.core.document_processor as dp
        dp._chroma_client = None

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result1 = dp.get_chroma_client()
        result2 = dp.get_chroma_client()

        # 只应调用一次 PersistentClient()
        assert mock_client_class.call_count == 1
        assert result1 is result2


# ============================================================
# delete_collection — 删除集合
# ============================================================

class TestDeleteCollection:
    """模块：core/document_processor.py — delete_collection"""

    @patch("backend.core.document_processor.get_chroma_client")
    def test_集合存在_正常删除(self, mock_get_client):
        """集合存在时，正常调用 delete_collection"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # 不应抛出异常
        delete_collection("test_collection")
        mock_client.delete_collection.assert_called_once_with("test_collection")

    @patch("backend.core.document_processor.get_chroma_client")
    def test_集合不存在_静默忽略异常(self, mock_get_client):
        """集合不存在时，delete_collection 应静默忽略，不抛出异常"""
        mock_client = MagicMock()
        mock_client.delete_collection.side_effect = Exception("集合不存在")
        mock_get_client.return_value = mock_client

        # 不应抛出异常，静默忽略
        delete_collection("nonexistent_collection")
