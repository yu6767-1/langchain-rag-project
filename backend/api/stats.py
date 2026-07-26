"""
统计 API 路由（仅管理员可访问）
===============================
提供系统概览统计数据，用于管理后台的统计面板。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import User
from backend.db.repositories import (
    UserRepository,
    ConversationRepository,
    MessageRepository,
    DocumentRepository,
)
from backend.api.auth import get_admin_user
from backend.schemas.document import StatsOverviewResponse

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/overview", response_model=StatsOverviewResponse)
def get_overview(
    current_admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    获取系统概览统计。

    返回数据：
    - 用户总数
    - 会话总数
    - 消息总数
    - 文档总数
    - 总片段数
    - 各状态的文档数量（就绪/处理中/失败）
    """
    # 统计用户数
    total_users = UserRepository.get_total_count(db)

    # 统计会话数
    total_conversations = ConversationRepository.get_total_count(db)

    # 统计消息数
    total_messages = MessageRepository.get_total_count(db)

    # 统计文档
    docs = DocumentRepository.get_all(db)
    total_documents = len(docs)
    total_chunks = DocumentRepository.get_total_chunks(db)

    ready = sum(1 for d in docs if d.status == "ready")
    processing = sum(1 for d in docs if d.status == "processing")
    error = sum(1 for d in docs if d.status == "error")

    return StatsOverviewResponse(
        total_users=total_users,
        total_conversations=total_conversations,
        total_messages=total_messages,
        total_documents=total_documents,
        total_chunks=total_chunks,
        ready_documents=ready,
        processing_documents=processing,
        error_documents=error,
    )
