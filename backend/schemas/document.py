"""知识库文档相关的 Pydantic 数据模型"""

from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """文档信息响应"""
    id: int
    filename: str
    file_type: str
    chunk_count: int
    file_size: int
    status: str
    error_message: Optional[str] = None
    uploaded_at: str


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: List[DocumentResponse]
    total: int


class ChunkPreview(BaseModel):
    """文档片段预览"""
    content: str
    metadata: dict


class ChunkListResponse(BaseModel):
    """片段列表响应"""
    chunks: List[ChunkPreview]


class StatsOverviewResponse(BaseModel):
    """系统统计概览"""
    total_users: int
    total_conversations: int
    total_messages: int
    total_documents: int
    total_chunks: int
    ready_documents: int
    processing_documents: int
    error_documents: int
