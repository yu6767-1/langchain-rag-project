"""
数据访问层（Repository 模式）
============================
封装所有数据库的增删改查操作。
业务逻辑层不直接操作数据库，而是通过 Repository 来操作。
这样做的好处：便于测试、便于切换数据库、代码结构清晰。
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.db.models import User, Conversation, Message, KnowledgeDocument


def utcnow():
    return datetime.now(timezone.utc)


# ============================================================
# 用户相关操作
# ============================================================

class UserRepository:
    """用户数据访问"""

    @staticmethod
    def create(db: Session, username: str, password_hash: str, role: str = "user") -> User:
        """创建新用户"""
        user = User(
            username=username,
            password_hash=password_hash,
            role=role,
            created_at=utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """根据用户名查找用户"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """根据 ID 查找用户"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def update_password(db: Session, user: User, new_password_hash: str) -> User:
        """修改用户密码"""
        user.password_hash = new_password_hash
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_total_count(db: Session) -> int:
        """获取用户总数"""
        return db.query(User).count()


# ============================================================
# 会话相关操作
# ============================================================

class ConversationRepository:
    """会话数据访问"""

    @staticmethod
    def create(db: Session, user_id: int, title: str = "新建会话") -> Conversation:
        """创建新会话"""
        conversation = Conversation(
            user_id=user_id,
            title=title,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def get_by_id(db: Session, conversation_id: int) -> Optional[Conversation]:
        """根据 ID 获取会话"""
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    @staticmethod
    def get_by_user(db: Session, user_id: int) -> List[Conversation]:
        """获取用户的所有会话，按更新时间倒序"""
        return (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .all()
        )

    @staticmethod
    def update_title(db: Session, conversation: Conversation, title: str) -> Conversation:
        """更新会话标题"""
        conversation.title = title
        conversation.updated_at = utcnow()
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def touch(db: Session, conversation: Conversation) -> None:
        """更新会话的最后活跃时间"""
        conversation.updated_at = utcnow()
        db.commit()

    @staticmethod
    def delete(db: Session, conversation: Conversation) -> None:
        """删除会话（级联删除所有消息）"""
        db.delete(conversation)
        db.commit()

    @staticmethod
    def get_total_count(db: Session) -> int:
        """获取会话总数"""
        return db.query(Conversation).count()


# ============================================================
# 消息相关操作
# ============================================================

class MessageRepository:
    """消息数据访问"""

    @staticmethod
    def create(
        db: Session,
        conversation_id: int,
        role: str,
        content: str,
        sources: Optional[list] = None,
    ) -> Message:
        """创建新消息"""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources or [],
            created_at=utcnow(),
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_by_conversation(
        db: Session, conversation_id: int, limit: int = 50, offset: int = 0
    ) -> List[Message]:
        """获取会话的消息列表（分页）"""
        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_recent_by_conversation(
        db: Session, conversation_id: int, rounds: int = 10
    ) -> List[Message]:
        """
        获取会话最近 N 轮对话（用于上下文窗口）
        一轮 = 1条用户消息 + 1条AI回复 = 2条消息
        因此取 rounds * 2 条消息
        """
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(rounds * 2)
            .all()
        )
        # 反转回时间正序
        return list(reversed(messages))

    @staticmethod
    def update_feedback(db: Session, message: Message, feedback: str) -> Message:
        """更新消息的反馈（点赞/点踩）"""
        message.feedback = feedback
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_by_id(db: Session, message_id: int) -> Optional[Message]:
        """根据 ID 获取消息"""
        return db.query(Message).filter(Message.id == message_id).first()

    @staticmethod
    def get_total_count(db: Session) -> int:
        """获取消息总数"""
        return db.query(Message).count()


# ============================================================
# 文档相关操作
# ============================================================

class DocumentRepository:
    """知识库文档数据访问"""

    @staticmethod
    def create(
        db: Session,
        filename: str,
        file_type: str,
        file_size: int,
        chroma_collection: str = "",
    ) -> KnowledgeDocument:
        """创建文档记录（状态为 processing）"""
        doc = KnowledgeDocument(
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            chunk_count=0,
            status="processing",
            chroma_collection=chroma_collection,
            uploaded_at=utcnow(),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def mark_ready(db: Session, doc: KnowledgeDocument, chunk_count: int) -> KnowledgeDocument:
        """标记文档处理完成"""
        doc.status = "ready"
        doc.chunk_count = chunk_count
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def mark_error(db: Session, doc: KnowledgeDocument, error_message: str) -> KnowledgeDocument:
        """标记文档处理失败"""
        doc.status = "error"
        doc.error_message = error_message
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def get_all(db: Session) -> List[KnowledgeDocument]:
        """获取所有文档，按上传时间倒序"""
        return (
            db.query(KnowledgeDocument)
            .order_by(desc(KnowledgeDocument.uploaded_at))
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, doc_id: int) -> Optional[KnowledgeDocument]:
        """根据 ID 获取文档"""
        return db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()

    @staticmethod
    def delete(db: Session, doc: KnowledgeDocument) -> None:
        """删除文档记录"""
        db.delete(doc)
        db.commit()

    @staticmethod
    def get_total_count(db: Session) -> int:
        """获取文档总数"""
        return db.query(KnowledgeDocument).count()

    @staticmethod
    def get_total_chunks(db: Session) -> int:
        """获取所有文档的总片段数"""
        result = db.query(KnowledgeDocument).filter(KnowledgeDocument.status == "ready").all()
        return sum(doc.chunk_count for doc in result)
