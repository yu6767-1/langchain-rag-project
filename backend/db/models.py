"""
SQLAlchemy ORM 数据模型定义
===========================
定义了 4 张数据库表的结构：
- User: 用户表
- Conversation: 会话表
- Message: 消息表
- Document: 文档表（知识库管理）
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship
from backend.db.database import Base, UTCDateTime


def utcnow():
    """返回当前 UTC 时间"""
    return datetime.now(timezone.utc)


class User(Base):
    """
    用户表

    存储所有用户信息。密码使用 bcrypt 哈希后存储，不存明文。
    role 字段控制权限：admin 可管理知识库，user 只能问答。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # admin / user
    created_at = Column(UTCDateTime, nullable=False, default=utcnow)

    # 关系：一个用户有多个会话
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    """
    会话表

    每个用户可以创建多个会话，每个会话独立维护聊天记录。
    title 字段可通过 LLM 自动生成（取首条用户消息的前几个字或让模型总结）。
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False, default="新建会话")
    created_at = Column(UTCDateTime, nullable=False, default=utcnow)
    updated_at = Column(UTCDateTime, nullable=False, default=utcnow)

    # 关系
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.created_at")


class Message(Base):
    """
    消息表

    存储每一轮对话的消息记录。
    - role: user 或 assistant
    - sources: 只有 assistant 消息才有值，存 JSON 数组，记录引用的知识库片段
    - feedback: 用户可选地点赞/点踩
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)  # [{content, filename, score, chunk_id}]
    feedback = Column(String(10), nullable=True)  # like / dislike
    created_at = Column(UTCDateTime, nullable=False, default=utcnow)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")


class KnowledgeDocument(Base):
    """
    知识库文档表

    记录上传到知识库的文档信息。
    - status: processing（处理中）/ ready（就绪）/ error（失败）
    - chroma_collection: 该文档在 ChromaDB 中对应的 Collection 名称，方便删除时定位
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    file_size = Column(Integer, nullable=False, default=0)  # 字节
    status = Column(String(20), nullable=False, default="processing")  # processing / ready / error
    chroma_collection = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(UTCDateTime, nullable=False, default=utcnow)
