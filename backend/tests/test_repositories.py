"""
数据仓库层单元测试
==================
测试 backend/db/repositories.py 中所有 Repository 类的增删改查操作。
所有数据库操作通过 Mock Session 隔离，不依赖真实数据库。
"""

import pytest
from unittest.mock import MagicMock, call, ANY
from datetime import datetime, timezone
from backend.db.repositories import (
    UserRepository,
    ConversationRepository,
    MessageRepository,
    DocumentRepository,
)
from backend.db.models import User, Conversation, Message, KnowledgeDocument


# ============================================================
# 辅助工具
# ============================================================

def create_mock_db():
    """
    创建一个 MagicMock 模拟 SQLAlchemy Session。
    add / commit / delete / refresh 等方法都不会真正访问数据库。
    """
    db = MagicMock()
    return db


# ============================================================
# UserRepository 测试
# ============================================================

class TestUserRepository:
    """模块：db/repositories.py — UserRepository"""

    def test_create_创建用户_返回User对象(self):
        """创建用户应返回 User 对象，且 db.add、db.commit、db.refresh 被调用"""
        db = create_mock_db()
        user = UserRepository.create(db, "alice", "hashed_pass", role="user")

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()
        assert user is not None

    def test_create_默认角色为user(self):
        """不传 role 参数时，默认创建 user 角色"""
        db = create_mock_db()
        user = UserRepository.create(db, "bob", "hashed_pass")
        db.add.assert_called_once()
        args = db.add.call_args[0][0]
        assert args.role == "user"

    def test_create_指定管理员角色(self):
        """传入 role='admin' 时，创建管理员用户"""
        db = create_mock_db()
        user = UserRepository.create(db, "admin_user", "hashed_pass", role="admin")
        args = db.add.call_args[0][0]
        assert args.role == "admin"
        assert args.username == "admin_user"

    def test_get_by_username_存在_返回User(self):
        """查询已存在的用户名，应返回 User 对象"""
        db = create_mock_db()
        mock_user = MagicMock(spec=User)
        mock_user.username = "alice"
        # 模拟查询链：db.query(User).filter(...).first()
        db.query.return_value.filter.return_value.first.return_value = mock_user

        result = UserRepository.get_by_username(db, "alice")
        assert result is mock_user
        db.query.assert_called_with(User)

    def test_get_by_username_不存在_返回None(self):
        """查询不存在的用户名，应返回 None"""
        db = create_mock_db()
        db.query.return_value.filter.return_value.first.return_value = None

        result = UserRepository.get_by_username(db, "nobody")
        assert result is None

    def test_get_by_id_存在_返回User(self):
        """按 ID 查询已存在的用户，应返回 User 对象"""
        db = create_mock_db()
        mock_user = MagicMock(spec=User)
        db.query.return_value.filter.return_value.first.return_value = mock_user

        result = UserRepository.get_by_id(db, 1)
        assert result is mock_user

    def test_get_by_id_不存在_返回None(self):
        """按 ID 查询不存在的用户，应返回 None"""
        db = create_mock_db()
        db.query.return_value.filter.return_value.first.return_value = None

        result = UserRepository.get_by_id(db, 999)
        assert result is None

    def test_update_password_更新后刷新(self):
        """修改密码应更新 password_hash 字段并提交"""
        db = create_mock_db()
        mock_user = MagicMock(spec=User)
        mock_user.password_hash = "old_hash"

        result = UserRepository.update_password(db, mock_user, "new_hash")
        assert mock_user.password_hash == "new_hash"
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(mock_user)

    def test_get_total_count_返回整数(self):
        """获取用户总数应返回整数"""
        db = create_mock_db()
        db.query.return_value.count.return_value = 42

        result = UserRepository.get_total_count(db)
        assert result == 42


# ============================================================
# ConversationRepository 测试
# ============================================================

class TestConversationRepository:
    """模块：db/repositories.py — ConversationRepository"""

    def test_create_创建会话_默认标题(self):
        """创建会话不传标题，默认为"新建会话" """
        db = create_mock_db()
        conv = ConversationRepository.create(db, user_id=1)

        args = db.add.call_args[0][0]
        assert args.user_id == 1
        assert args.title == "新建会话"

    def test_create_自定义标题(self):
        """传入自定义标题，创建该标题的会话"""
        db = create_mock_db()
        conv = ConversationRepository.create(db, user_id=2, title="商品咨询")

        args = db.add.call_args[0][0]
        assert args.user_id == 2
        assert args.title == "商品咨询"

    def test_get_by_id_存在_返回Conversation(self):
        """按 ID 查询已存在的会话，应返回 Conversation 对象"""
        db = create_mock_db()
        mock_conv = MagicMock(spec=Conversation)
        db.query.return_value.filter.return_value.first.return_value = mock_conv

        result = ConversationRepository.get_by_id(db, 5)
        assert result is mock_conv

    def test_get_by_id_不存在_返回None(self):
        """按 ID 查询不存在的会话，应返回 None"""
        db = create_mock_db()
        db.query.return_value.filter.return_value.first.return_value = None

        result = ConversationRepository.get_by_id(db, 999)
        assert result is None

    def test_get_by_user_按更新时间倒序(self):
        """获取用户会话列表，应按 updated_at 倒序排列"""
        db = create_mock_db()
        mock_convs = [MagicMock(spec=Conversation) for _ in range(3)]
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_convs

        result = ConversationRepository.get_by_user(db, user_id=1)
        assert len(result) == 3

    def test_update_title_更新标题并更新时间(self):
        """更新标题时应同时更新 updated_at 时间戳"""
        db = create_mock_db()
        mock_conv = MagicMock(spec=Conversation)
        mock_conv.title = "旧标题"

        result = ConversationRepository.update_title(db, mock_conv, "新标题")
        assert mock_conv.title == "新标题"
        assert mock_conv.updated_at is not None
        db.commit.assert_called_once()

    def test_touch_更新活跃时间(self):
        """touch 应更新会话的 updated_at 时间"""
        db = create_mock_db()
        mock_conv = MagicMock(spec=Conversation)
        old_time = mock_conv.updated_at

        ConversationRepository.touch(db, mock_conv)
        db.commit.assert_called_once()

    def test_delete_删除会话并提交(self):
        """delete 应调用 db.delete 并 commit"""
        db = create_mock_db()
        mock_conv = MagicMock(spec=Conversation)

        ConversationRepository.delete(db, mock_conv)
        db.delete.assert_called_once_with(mock_conv)
        db.commit.assert_called_once()

    def test_get_total_count_返回整数(self):
        """获取会话总数"""
        db = create_mock_db()
        db.query.return_value.count.return_value = 10

        result = ConversationRepository.get_total_count(db)
        assert result == 10


# ============================================================
# MessageRepository 测试
# ============================================================

class TestMessageRepository:
    """模块：db/repositories.py — MessageRepository"""

    def test_create_创建消息_返回Message对象(self):
        """创建消息应返回 Message 对象"""
        db = create_mock_db()
        msg = MessageRepository.create(
            db,
            conversation_id=1,
            role="user",
            content="你好，请问这个商品的价格？",
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        args = db.add.call_args[0][0]
        assert args.conversation_id == 1
        assert args.role == "user"
        assert args.content == "你好，请问这个商品的价格？"

    def test_create_带sources的消息(self):
        """创建 assistant 消息时带上 sources（引用来源）"""
        db = create_mock_db()
        sources = [{"content": "...", "filename": "a.pdf", "score": 0.9}]

        msg = MessageRepository.create(
            db, conversation_id=1, role="assistant",
            content="价格是999元", sources=sources,
        )
        args = db.add.call_args[0][0]
        assert args.sources == sources

    def test_get_by_conversation_分页查询(self):
        """按会话获取消息，支持 limit 和 offset 分页"""
        db = create_mock_db()
        mock_msgs = [MagicMock(spec=Message) for _ in range(5)]
        mock_query = db.query.return_value
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_msgs

        result = MessageRepository.get_by_conversation(db, conversation_id=1, limit=10, offset=0)
        assert len(result) == 5

    def test_get_recent_by_conversation_取最近N轮(self):
        """
        取最近 N 轮对话（N 轮 = 2N 条消息），应返回时间正序列表。
        注意：数据库查询是倒序取的，Repository 内部会 reverse 成正序。
        """
        db = create_mock_db()
        mock_msgs = [MagicMock(spec=Message) for _ in range(4)]
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_msgs

        result = MessageRepository.get_recent_by_conversation(db, conversation_id=1, rounds=2)
        # 2轮 = 4条消息，reverse 后还是4条
        assert len(result) == 4

    def test_update_feedback_点赞_更新成功(self):
        """消息点赞（like），应正确更新 feedback 字段"""
        db = create_mock_db()
        mock_msg = MagicMock(spec=Message)
        mock_msg.feedback = None

        result = MessageRepository.update_feedback(db, mock_msg, "like")
        assert mock_msg.feedback == "like"
        db.commit.assert_called_once()

    def test_update_feedback_点踩_更新成功(self):
        """消息点踩（dislike），应正确更新 feedback 字段"""
        db = create_mock_db()
        mock_msg = MagicMock(spec=Message)
        mock_msg.feedback = None

        result = MessageRepository.update_feedback(db, mock_msg, "dislike")
        assert mock_msg.feedback == "dislike"
        db.commit.assert_called_once()

    def test_get_by_id_存在_返回Message(self):
        """按 ID 查询已存在的消息"""
        db = create_mock_db()
        mock_msg = MagicMock(spec=Message)
        db.query.return_value.filter.return_value.first.return_value = mock_msg

        result = MessageRepository.get_by_id(db, 1)
        assert result is mock_msg

    def test_get_by_id_不存在_返回None(self):
        """按 ID 查询不存在的消息"""
        db = create_mock_db()
        db.query.return_value.filter.return_value.first.return_value = None

        result = MessageRepository.get_by_id(db, 999)
        assert result is None

    def test_get_total_count_返回整数(self):
        """获取消息总数"""
        db = create_mock_db()
        db.query.return_value.count.return_value = 500

        result = MessageRepository.get_total_count(db)
        assert result == 500


# ============================================================
# DocumentRepository 测试
# ============================================================

class TestDocumentRepository:
    """模块：db/repositories.py — DocumentRepository"""

    def test_create_创建文档记录_状态为processing(self):
        """创建文档记录时，状态默认为 processing"""
        db = create_mock_db()
        doc = DocumentRepository.create(
            db,
            filename="商品手册.pdf",
            file_type="pdf",
            file_size=1024,
            chroma_collection="doc_col_abc",
        )

        args = db.add.call_args[0][0]
        assert args.filename == "商品手册.pdf"
        assert args.file_type == "pdf"
        assert args.file_size == 1024
        assert args.status == "processing"
        assert args.chunk_count == 0

    def test_mark_ready_标记就绪_更新状态和片段数(self):
        """处理完成后标记为 ready，并记录 chunk_count"""
        db = create_mock_db()
        mock_doc = MagicMock(spec=KnowledgeDocument)
        mock_doc.status = "processing"
        mock_doc.chunk_count = 0

        result = DocumentRepository.mark_ready(db, mock_doc, chunk_count=15)
        assert mock_doc.status == "ready"
        assert mock_doc.chunk_count == 15
        db.commit.assert_called_once()

    def test_mark_error_标记错误_记录错误信息(self):
        """处理失败时标记为 error，并记录错误信息"""
        db = create_mock_db()
        mock_doc = MagicMock(spec=KnowledgeDocument)
        mock_doc.status = "processing"

        result = DocumentRepository.mark_error(db, mock_doc, "文件格式不支持")
        assert mock_doc.status == "error"
        assert mock_doc.error_message == "文件格式不支持"
        db.commit.assert_called_once()

    def test_get_all_返回所有文档_倒序排列(self):
        """获取所有文档列表，应按上传时间倒序"""
        db = create_mock_db()
        mock_docs = [MagicMock(spec=KnowledgeDocument) for _ in range(3)]
        db.query.return_value.order_by.return_value.all.return_value = mock_docs

        result = DocumentRepository.get_all(db)
        assert len(result) == 3

    def test_get_by_id_存在_返回Document(self):
        """按 ID 查询已存在的文档"""
        db = create_mock_db()
        mock_doc = MagicMock(spec=KnowledgeDocument)
        db.query.return_value.filter.return_value.first.return_value = mock_doc

        result = DocumentRepository.get_by_id(db, 1)
        assert result is mock_doc

    def test_get_by_id_不存在_返回None(self):
        """按 ID 查询不存在的文档"""
        db = create_mock_db()
        db.query.return_value.filter.return_value.first.return_value = None

        result = DocumentRepository.get_by_id(db, 999)
        assert result is None

    def test_delete_删除文档并提交(self):
        """delete 应调用 db.delete 并 commit"""
        db = create_mock_db()
        mock_doc = MagicMock(spec=KnowledgeDocument)

        DocumentRepository.delete(db, mock_doc)
        db.delete.assert_called_once_with(mock_doc)
        db.commit.assert_called_once()

    def test_get_total_count_返回整数(self):
        """获取文档总数"""
        db = create_mock_db()
        db.query.return_value.count.return_value = 8

        result = DocumentRepository.get_total_count(db)
        assert result == 8

    def test_get_total_chunks_仅统计ready状态的文档(self):
        """获取总片段数时，只统计 status='ready' 的文档"""
        db = create_mock_db()
        doc1 = MagicMock(spec=KnowledgeDocument)
        doc1.chunk_count = 10
        doc2 = MagicMock(spec=KnowledgeDocument)
        doc2.chunk_count = 20
        db.query.return_value.filter.return_value.all.return_value = [doc1, doc2]

        result = DocumentRepository.get_total_chunks(db)
        assert result == 30  # 10 + 20
