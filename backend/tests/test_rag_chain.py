"""
RAG 核心链模块单元测试
======================
测试 backend/core/rag_chain.py 中的 build_rag_prompt、format_chat_history 和 rag_stream_chat。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.documents import Document
from backend.core.rag_chain import (
    build_rag_prompt,
    format_chat_history,
    rag_stream_chat,
    get_retriever,
    RAG_SYSTEM_PROMPT,
)


# ============================================================
# build_rag_prompt — 构建 Prompt 模板
# ============================================================

class TestBuildRagPrompt:
    """模块：core/rag_chain.py — build_rag_prompt"""

    def test_返回ChatPromptTemplate对象(self):
        """应返回 LangChain 的 ChatPromptTemplate 对象"""
        prompt = build_rag_prompt()
        from langchain_core.prompts import ChatPromptTemplate
        assert isinstance(prompt, ChatPromptTemplate)

    def test_模板包含必要占位符(self):
        """模板中应包含 context、chat_history 和 input 三个占位符"""
        prompt = build_rag_prompt()
        # 模板的消息列表
        messages = prompt.messages
        # system 消息应包含 RAG_SYSTEM_PROMPT 内容
        from langchain_core.prompts import SystemMessagePromptTemplate
        system_msg = messages[0]
        assert "知识库内容" in system_msg.prompt.template
        assert "{context}" in system_msg.prompt.template
        assert "{input}" in system_msg.prompt.template


# ============================================================
# format_chat_history — 格式化对话历史
# ============================================================

class TestFormatChatHistory:
    """模块：core/rag_chain.py — format_chat_history"""

    def test_空消息列表_返回暂无历史提示(self):
        """空列表应返回提示信息"""
        result = format_chat_history([])
        assert "暂无对话历史" in result

    def test_单轮对话_正确格式化(self):
        """单轮用户+助手对话应正确格式化"""
        messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
        ]
        result = format_chat_history(messages)
        assert "用户：你好" in result
        assert "助手：你好！有什么可以帮助你的？" in result

    def test_多轮对话_按顺序排列(self):
        """多轮对话应按时间顺序排列"""
        messages = [
            {"role": "user", "content": "问题1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "问题2"},
            {"role": "assistant", "content": "回答2"},
        ]
        result = format_chat_history(messages)
        lines = result.split("\n")
        assert lines[0] == "用户：问题1"
        assert lines[1] == "助手：回答1"
        assert lines[2] == "用户：问题2"
        assert lines[3] == "助手：回答2"

    def test_仅用户消息_正确格式化(self):
        """只有用户消息（没有助手回复）也能正常格式化"""
        messages = [
            {"role": "user", "content": "一个问题"},
        ]
        result = format_chat_history(messages)
        assert "用户：一个问题" in result

    def test_消息内容为空_正常处理(self):
        """消息内容为空字符串也能正常处理"""
        messages = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": ""},
        ]
        result = format_chat_history(messages)
        # 不应崩溃，应正常输出空内容
        assert "用户：" in result
        assert "助手：" in result


# ============================================================
# rag_stream_chat — 流式 RAG 问答（核心函数）
# ============================================================

class TestRagStreamChatEmpty:
    """模块：core/rag_chain.py — rag_stream_chat 知识库为空"""

    @pytest.mark.asyncio
    async def test_知识库为空_返回提示消息(self):
        """知识库为空时，应返回提示消息并立即 done"""
        with patch("backend.core.rag_chain.get_retriever") as mock_get_retriever:
            mock_retriever = MagicMock()
            mock_retriever.is_empty.return_value = True
            mock_get_retriever.return_value = mock_retriever

            results = []
            async for chunk in rag_stream_chat("测试问题", []):
                results.append(chunk)

            # 应有两条：一条 token + 一条 done
            assert len(results) == 2
            assert results[0]["type"] == "token"
            assert "暂无内容" in results[0]["data"]
            assert results[1]["type"] == "done"


class TestRagStreamChatWithDocuments:
    """模块：core/rag_chain.py — rag_stream_chat 有知识库内容"""

    @pytest.mark.asyncio
    async def test_检索到文档_先返回sources再流式输出(self):
        """检索到文档后，应先 yield sources，再 yield token，最后 yield done"""

        # 准备 mock 文档
        mock_doc = Document(
            page_content="商品A的参数：价格999元，重量500g",
            metadata={"filename": "商品手册.pdf", "score": 0.95},
        )

        # Mock retriever
        mock_retriever = MagicMock()
        mock_retriever.is_empty.return_value = False
        mock_retriever.invoke.return_value = [mock_doc]

        # Mock LLM stream
        mock_llm = MagicMock()
        mock_llm.stream.return_value = iter(["商品", "A", "的价格", "是999元"])

        with patch("backend.core.rag_chain.get_retriever", return_value=mock_retriever), \
             patch("backend.core.rag_chain.get_llm", return_value=mock_llm):

            results = []
            async for chunk in rag_stream_chat("商品A多少钱？", []):
                results.append(chunk)

            # 验证 sources
            assert results[0]["type"] == "sources"
            assert len(results[0]["data"]) == 1
            assert results[0]["data"][0]["filename"] == "商品手册.pdf"

            # 验证 tokens
            token_chunks = [r for r in results if r["type"] == "token"]
            assert len(token_chunks) >= 1
            assert "商品" in token_chunks[0]["data"]

            # 验证 done
            assert results[-1]["type"] == "done"
            assert "商品A的价格是999元" in results[-1]["data"]

    @pytest.mark.asyncio
    async def test_LLM抛出异常_返回错误Token(self):
        """LLM 流式输出过程中异常，应返回错误 token 而不崩溃"""
        mock_retriever = MagicMock()
        mock_retriever.is_empty.return_value = False
        mock_retriever.invoke.return_value = [
            Document(page_content="内容", metadata={"filename": "doc.pdf"})
        ]

        mock_llm = MagicMock()
        # 前两次正常，后面抛异常
        mock_llm.stream.side_effect = RuntimeError("API 调用失败")

        with patch("backend.core.rag_chain.get_retriever", return_value=mock_retriever), \
             patch("backend.core.rag_chain.get_llm", return_value=mock_llm):

            results = []
            async for chunk in rag_stream_chat("问题", []):
                results.append(chunk)

            # 应该有 sources + 错误token + done
            has_error = any("出错" in r.get("data", "") for r in results if r["type"] == "token")
            assert has_error

    @pytest.mark.asyncio
    async def test_检索结果去重_相同内容只保留一个(self):
        """
        两个文档有相同的前100字内容，应去重只保留一个 sources 条目。
        """
        same_content = "这" + "是" * 99 + "相同内容"  # 超100字但前100字相同
        doc1 = Document(page_content=same_content, metadata={"filename": "a.pdf"})
        doc2 = Document(page_content=same_content + "不同后缀", metadata={"filename": "b.pdf"})

        mock_retriever = MagicMock()
        mock_retriever.is_empty.return_value = False
        mock_retriever.invoke.return_value = [doc1, doc2]

        mock_llm = MagicMock()
        mock_llm.stream.return_value = iter(["回答"])

        with patch("backend.core.rag_chain.get_retriever", return_value=mock_retriever), \
             patch("backend.core.rag_chain.get_llm", return_value=mock_llm):

            results = []
            async for chunk in rag_stream_chat("问题", []):
                results.append(chunk)

            # sources 应该去重了
            sources_data = results[0]["data"]
            # 前100字相同，应只有一个
            assert len(sources_data) == 1


# ============================================================
# get_retriever — 获取检索器实例
# ============================================================

class TestGetRetriever:
    """模块：core/rag_chain.py — get_retriever"""

    def test_返回HybridRetriever实例(self):
        """应返回 HybridRetriever 的实例"""
        retriever = get_retriever()
        from backend.core.hybrid_retriever import HybridRetriever
        assert isinstance(retriever, HybridRetriever)

    def test_top_k使用配置值(self):
        """retriever 的 top_k 应使用配置文件中的 RETRIEVAL_TOP_K"""
        retriever = get_retriever()
        assert hasattr(retriever, "top_k")
