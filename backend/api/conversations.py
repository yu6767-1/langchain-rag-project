"""
会话管理 API 路由
=================
处理会话的创建、列表、删除和消息历史的获取。
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import User
from backend.api.auth import get_current_user
from backend.core.conversation_manager import ConversationManager
from backend.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    MessageResponse,
    MessageListResponse,
    FeedbackRequest,
    SourceInfo,
)
from backend.schemas.auth import MessageResponse as SimpleMessageResponse

router = APIRouter(prefix="/api/conversations", tags=["会话"])


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的所有会话列表。

    按最后活跃时间倒序排列，最近聊的会话排在最前面。
    每个会话附带消息总数和最后一条消息预览。
    """
    manager = ConversationManager(db)
    conversations = manager.get_user_conversations(current_user.id)

    result = []
    for conv in conversations:
        messages = manager.get_conversation_messages(conv.id, limit=1, offset=0)
        # 获取消息总数
        from backend.db.repositories import MessageRepository
        all_msgs = MessageRepository.get_by_conversation(db, conv.id, limit=1000)
        message_count = len(all_msgs)
        last_msg = all_msgs[-1].content[:50] + "..." if len(all_msgs) > 0 and len(all_msgs[-1].content) > 50 else (all_msgs[-1].content[:50] if all_msgs else None)

        result.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at.isoformat() if conv.created_at else "",
            updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
            message_count=message_count,
            last_message=last_msg,
        ))

    return ConversationListResponse(conversations=result)


@router.post("", response_model=ConversationResponse)
def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新会话"""
    manager = ConversationManager(db)
    conv = manager.create_conversation(current_user.id, title=request.title)

    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat() if conv.created_at else "",
        updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
        message_count=0,
        last_message=None,
    )


@router.delete("/{conversation_id}", response_model=SimpleMessageResponse)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除会话（只能删除自己的会话）"""
    manager = ConversationManager(db)
    success = manager.delete_conversation(conversation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return {"message": "会话已删除"}


@router.put("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    request: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新会话标题"""
    manager = ConversationManager(db)
    conv = manager.update_conversation_title(conversation_id, request.title)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此会话")

    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat() if conv.created_at else "",
        updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
        message_count=0,
        last_message=None,
    )


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
def get_messages(
    conversation_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取会话的消息历史（分页）"""
    manager = ConversationManager(db)
    # 检查会话所有权
    from backend.db.repositories import ConversationRepository
    conv = ConversationRepository.get_by_id(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此会话")

    messages = manager.get_conversation_messages(conversation_id, limit=limit, offset=offset)

    # 获取总数
    from backend.db.repositories import MessageRepository
    all_msgs = MessageRepository.get_by_conversation(db, conversation_id, limit=10000)
    total = len(all_msgs)

    msg_list = []
    for msg in messages:
        # 转换 sources 为 SourceInfo 列表
        sources = []
        if msg.sources:
            for s in msg.sources:
                sources.append(SourceInfo(
                    content=s.get("content", ""),
                    filename=s.get("filename", "未知"),
                    score=s.get("score", 0),
                ))

        msg_list.append(MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            sources=sources if sources else None,
            feedback=msg.feedback,
            created_at=msg.created_at.isoformat() if msg.created_at else "",
        ))

    return MessageListResponse(messages=msg_list, total=total)


@router.post("/messages/{message_id}/feedback", response_model=SimpleMessageResponse)
def update_feedback(
    message_id: int,
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """对消息点赞或点踩"""
    manager = ConversationManager(db)
    msg = manager.update_feedback(message_id, request.feedback)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    return {"message": "反馈已记录"}
