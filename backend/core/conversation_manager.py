"""
对话管理模块
============
管理多用户多会话的创建、切换和历史记录。

每个用户可以有多个会话，每个会话有独立的聊天记录。
会话之间互不干扰，用户可以随时切换会话继续对话。
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.db.repositories import (
    ConversationRepository,
    MessageRepository,
)
from backend.db.models import Conversation, Message


class ConversationManager:
    """
    对话管理器

    封装会话和消息的业务逻辑，协调 Repository 层的操作。
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # 会话操作
    # ============================================================

    def create_conversation(self, user_id: int, title: str = "新建会话") -> Conversation:
        """创建新会话"""
        return ConversationRepository.create(self.db, user_id=user_id, title=title)

    def get_user_conversations(self, user_id: int) -> List[Conversation]:
        """获取用户的所有会话列表"""
        return ConversationRepository.get_by_user(self.db, user_id=user_id)

    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """
        删除会话（安全检查：只能删除自己的会话）

        Returns:
            True 表示删除成功，False 表示会话不存在或不属于该用户
        """
        conv = ConversationRepository.get_by_id(self.db, conversation_id)
        if not conv or conv.user_id != user_id:
            return False
        ConversationRepository.delete(self.db, conv)
        return True

    def update_conversation_title(self, conversation_id: int, title: str) -> Optional[Conversation]:
        """更新会话标题"""
        conv = ConversationRepository.get_by_id(self.db, conversation_id)
        if not conv:
            return None
        return ConversationRepository.update_title(self.db, conv, title)

    # ============================================================
    # 消息操作
    # ============================================================

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None,
    ) -> Message:
        """
        添加一条消息到会话。

        同时更新会话的最后活跃时间（用于排序）。
        """
        # 更新会话活跃时间
        conv = ConversationRepository.get_by_id(self.db, conversation_id)
        if conv:
            ConversationRepository.touch(self.db, conv)

        return MessageRepository.create(
            self.db,
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources,
        )

    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Message]:
        """获取会话的消息历史（分页）"""
        return MessageRepository.get_by_conversation(
            self.db,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
        )

    def get_recent_messages(
        self,
        conversation_id: int,
        rounds: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取最近 N 轮对话（用于构建上下文窗口）。

        返回格式：
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
        """
        messages = MessageRepository.get_recent_by_conversation(
            self.db,
            conversation_id=conversation_id,
            rounds=rounds,
        )
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def update_feedback(self, message_id: int, feedback: str) -> Optional[Message]:
        """更新消息的反馈"""
        msg = MessageRepository.get_by_id(self.db, message_id)
        if not msg:
            return None
        return MessageRepository.update_feedback(self.db, msg, feedback)
