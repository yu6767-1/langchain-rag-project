"""
对话管理器单元测试
==================
测试 backend/core/conversation_manager.py 中的 ConversationManager 业务逻辑。
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.core.conversation_manager import ConversationManager
from backend.db.models import Conversation, Message


class TestConversationManager:
    """模块：core/conversation_manager.py — ConversationManager"""

    # ============================================================
    # create_conversation
    # ============================================================

    @patch("backend.core.conversation_manager.ConversationRepository")
    def test_create_conversation_调用仓库创建(self, mock_repo):
        """创建会话应调用 ConversationRepository.create"""
        db = MagicMock()
        mock_conv = MagicMock(spec=Conversation)
        mock_repo.create.return_value = mock_conv

        manager = ConversationManager(db)
        result = manager.create_conversation(user_id=1, title="测试会话")

        mock_repo.create.assert_called_once_with(db, user_id=1, title="测试会话")
        assert result is mock_conv

    @patch("backend.core.conversation_manager.ConversationRepository")
    def test_create_conversation_默认标题(self, mock_repo):
        """不传标题时，使用默认标题'新建会话'"""
        db = MagicMock()
        mock_repo.create.return_value = MagicMock()

        manager = ConversationManager(db)
        manager.create_conversation(user_id=1)

        mock_repo.create.assert_called_once_with(db, user_id=1, title="新建会话")

    # ============================================================
    # get_user_conversations
    # ============================================================

    @patch("backend.core.conversation_manager.ConversationRepository")
    def test_get_user_conversations_返回会话列表(self, mock_repo):
        """获取用户会话列表"""
        db = MagicMock()
        convs = [MagicMock(spec=Conversation) for _ in range(3)]
        mock_repo.get_by_user.return_value = convs

        manager = ConversationManager(db)
        result = manager.get_user_conversations(user_id=1)

        mock_repo.get_by_user.assert_called_once_with(db, user_id=1)
        assert len(result) == 3

    # ============================================================
    # delete_conversation（安全检查）
    # ============================================================

    @patch("backend.core.conversation_manager.ConversationRepository")
    def test_delete_conversation_是自己的会话_返回True(self, mock_repo):
        """删除自己的会话，应返回 True"""
        db = MagicMock()
        mock_conv = MagicMock(spec=Conversation)
        mock_conv.user_id = 1
        mock_repo.get_by_id.return_value = mock_conv

        manager = ConversationManager(db)
        result = manager.delete_conversation(conversation_id=5, user_id=1)

        assert result is True
        mock_repo.delete.assert_called_once_with(db, mock_conv)

    @patch("backend.core.conversation_manager.ConversationRepository")
    def test_delete_conversation_不是自己的会话_返回False(self, mock_repo):
        """删除别人的会话，应拒绝并返回 False（安全检查）"""
        db = MagicMock()
        mock_conv = MagicMock(spec=Conversation)
        mock_conv.user_id = 2  # 属于用户2
        mock_repo.get_by_id.return_value = mock_conv

        manager = ConversationManager(db)
        result = manager.delete_conversation(conversation_id=5, user_id=1)

        assert result is False
        # delete 不应该被调用
        mock_repo.delete.assert_not_called()

    @patch("backend.core.conversation_manager.ConversationRepository")
    def test_delete_conversation_会话不存在_返回False(self, mock_repo):
        """删除不存在的会话，应返回 False"""
        db = MagicMock()
        mock_repo.get_by_id.return_value = None

        manager = ConversationManager(db)
        result = manager.delete_conversation(conversation_id=999, user_id=1)

        assert result is False
        mock_repo.delete.assert_not_called()

    # ============================================================
    # update_conversation_title
    # ============================================================

    @patch("backend.core.conversation_manager.ConversationRepository")
    def test_update_title_成功_返回更新后的会话(self, mock_repo):
        """更新已存在的会话标题，应返回更新后的 Conversation"""
        db = MagicMock()
        mock_conv = MagicMock(spec=Conversation)
        mock_repo.get_by_id.return_value = mock_conv
        updated_conv = MagicMock(spec=Conversation)
        updated_conv.title = "新标题"
        mock_repo.update_title.return_value = updated_conv

        manager = ConversationManager(db)
        result = manager.update_conversation_title(conversation_id=1, title="新标题")

        assert result.title == "新标题"
        mock_repo.update_title.assert_called_once_with(db, mock_conv, "新标题")

    @patch("backend.core.conversation_manager.ConversationRepository")
    def test_update_title_会话不存在_返回None(self, mock_repo):
        """更新不存在的会话，应返回 None"""
        db = MagicMock()
        mock_repo.get_by_id.return_value = None

        manager = ConversationManager(db)
        result = manager.update_conversation_title(conversation_id=999, title="不存在")

        assert result is None
        mock_repo.update_title.assert_not_called()

    # ============================================================
    # add_message
    # ============================================================

    @patch("backend.core.conversation_manager.ConversationRepository")
    @patch("backend.core.conversation_manager.MessageRepository")
    def test_add_message_成功_更新活跃时间(self, mock_msg_repo, mock_conv_repo):
        """添加消息后，应更新会话活跃时间 + 创建消息"""
        db = MagicMock()
        mock_conv = MagicMock(spec=Conversation)
        mock_conv_repo.get_by_id.return_value = mock_conv
        mock_msg = MagicMock(spec=Message)
        mock_msg_repo.create.return_value = mock_msg

        manager = ConversationManager(db)
        result = manager.add_message(
            conversation_id=1,
            role="user",
            content="你好",
            sources=None,
        )

        # 验证调用
        mock_conv_repo.get_by_id.assert_called_with(db, 1)
        mock_conv_repo.touch.assert_called_once_with(db, mock_conv)
        mock_msg_repo.create.assert_called_once_with(
            db, conversation_id=1, role="user", content="你好", sources=None,
        )
        assert result is mock_msg

    @patch("backend.core.conversation_manager.ConversationRepository")
    @patch("backend.core.conversation_manager.MessageRepository")
    def test_add_message_会话不存在_不崩溃(self, mock_msg_repo, mock_conv_repo):
        """会话不存在时，仍可创建消息（跳过 touch），不崩溃"""
        db = MagicMock()
        mock_conv_repo.get_by_id.return_value = None  # 会话不存在
        mock_msg_repo.create.return_value = MagicMock()

        manager = ConversationManager(db)
        # 不应抛出异常
        result = manager.add_message(conversation_id=999, role="user", content="hi")
        assert result is not None
        mock_conv_repo.touch.assert_not_called()

    # ============================================================
    # get_conversation_messages
    # ============================================================

    @patch("backend.core.conversation_manager.MessageRepository")
    def test_get_messages_分页查询(self, mock_repo):
        """获取会话消息，支持分页参数"""
        db = MagicMock()
        msgs = [MagicMock(spec=Message) for _ in range(10)]
        mock_repo.get_by_conversation.return_value = msgs

        manager = ConversationManager(db)
        result = manager.get_conversation_messages(
            conversation_id=1, limit=20, offset=10,
        )

        mock_repo.get_by_conversation.assert_called_once_with(
            db, conversation_id=1, limit=20, offset=10,
        )
        assert len(result) == 10

    # ============================================================
    # get_recent_messages
    # ============================================================

    @patch("backend.core.conversation_manager.MessageRepository")
    def test_get_recent_messages_返回正确格式(self, mock_repo):
        """
        获取最近消息，返回格式应为：
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        db = MagicMock()
        msg1 = MagicMock(spec=Message)
        msg1.role = "user"
        msg1.content = "你好"
        msg2 = MagicMock(spec=Message)
        msg2.role = "assistant"
        msg2.content = "你好！"
        mock_repo.get_recent_by_conversation.return_value = [msg1, msg2]

        manager = ConversationManager(db)
        result = manager.get_recent_messages(conversation_id=1, rounds=1)

        assert result == [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"},
        ]

    # ============================================================
    # update_feedback
    # ============================================================

    @patch("backend.core.conversation_manager.MessageRepository")
    def test_update_feedback_成功_返回更新后的消息(self, mock_repo):
        """更新消息反馈（点赞/点踩）"""
        db = MagicMock()
        mock_msg = MagicMock(spec=Message)
        mock_repo.get_by_id.return_value = mock_msg
        updated_msg = MagicMock(spec=Message)
        mock_repo.update_feedback.return_value = updated_msg

        manager = ConversationManager(db)
        result = manager.update_feedback(message_id=1, feedback="like")

        assert result is updated_msg
        mock_repo.update_feedback.assert_called_once_with(db, mock_msg, "like")

    @patch("backend.core.conversation_manager.MessageRepository")
    def test_update_feedback_消息不存在_返回None(self, mock_repo):
        """反馈消息不存在，应返回 None"""
        db = MagicMock()
        mock_repo.get_by_id.return_value = None

        manager = ConversationManager(db)
        result = manager.update_feedback(message_id=999, feedback="like")

        assert result is None
        mock_repo.update_feedback.assert_not_called()
