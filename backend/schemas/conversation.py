"""会话相关的 Pydantic 数据模型"""

from typing import Optional, List
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """创建会话请求"""
    title: str = Field(default="新建会话", max_length=200, description="会话标题")


class ConversationUpdate(BaseModel):
    """更新会话请求"""
    title: str = Field(..., min_length=1, max_length=200, description="新标题")


class SourceInfo(BaseModel):
    """引用来源信息"""
    content: str
    filename: str
    score: float


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    conversation_id: int
    role: str
    content: str
    sources: Optional[List[SourceInfo]] = None
    feedback: Optional[str] = None
    created_at: str


class ConversationResponse(BaseModel):
    """会话响应"""
    id: int
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0  # 该会话的消息总数
    last_message: Optional[str] = None  # 最后一条消息预览


class ConversationListResponse(BaseModel):
    """会话列表响应"""
    conversations: List[ConversationResponse]


class MessageListResponse(BaseModel):
    """消息列表响应"""
    messages: List[MessageResponse]
    total: int


class FeedbackRequest(BaseModel):
    """消息反馈请求"""
    feedback: str = Field(..., pattern="^(like|dislike)$", description="like 或 dislike")
