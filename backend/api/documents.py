"""
知识库管理 API 路由（仅管理员可访问）
=====================================
处理文档的上传、列表、删除和片段预览。

文档处理流程：
1. 管理员上传文档文件
2. 系统保存文件到 uploads/ 目录
3. 后台异步处理：加载 → 切分 → 向量化 → 存入 ChromaDB
4. 前端通过轮询或 WebSocket 获取处理进度
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import User
from backend.db.repositories import DocumentRepository
from backend.api.auth import get_admin_user
from backend.config import UPLOAD_DIR, MAX_FILE_SIZE_MB, ALLOWED_FILE_TYPES
from backend.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    ChunkPreview,
    ChunkListResponse,
)
from backend.schemas.auth import MessageResponse

router = APIRouter(prefix="/api/documents", tags=["知识库管理"])


# ============================================================
# 辅助函数
# ============================================================

def validate_file(file: UploadFile) -> str:
    """验证上传文件的类型和大小"""
    # 检查文件名
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 检查文件类型
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: .{ext}，支持的类型: {', '.join(ALLOWED_FILE_TYPES)}"
        )
    return ext


def save_upload_file(file: UploadFile) -> tuple[str, str, int]:
    """
    保存上传的文件到 uploads/ 目录。

    Returns:
        (file_path, unique_filename, file_size)
    """
    # 生成唯一文件名（防止重名覆盖）
    ext = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_name

    # 写入文件
    file_size = 0
    with open(file_path, "wb") as f:
        content = file.file.read()
        f.write(content)
        file_size = len(content)

    return str(file_path), file.filename, file_size


def process_document_background(
    file_path: str,
    filename: str,
    doc_id: int,
    collection_name: str,
    db_session_factory,
):
    """
    后台处理文档：加载 → 切分 → 向量化 → 存入 ChromaDB。

    这个函数在后台线程中运行，不阻塞 API 响应。
    处理完成后更新数据库状态。
    """
    db = db_session_factory()
    try:
        from backend.core.document_processor import process_and_store_document

        chunk_count = process_and_store_document(
            file_path=file_path,
            filename=filename,
            collection_name=collection_name,
            progress_callback=None,  # 后续可增加进度回调
        )

        # 更新状态为 ready
        doc = DocumentRepository.get_by_id(db, doc_id)
        if doc:
            DocumentRepository.mark_ready(db, doc, chunk_count)

    except Exception as e:
        # 更新状态为 error
        doc = DocumentRepository.get_by_id(db, doc_id)
        if doc:
            DocumentRepository.mark_error(db, doc, str(e))
    finally:
        db.close()


# ============================================================
# API 接口
# ============================================================

@router.get("", response_model=DocumentListResponse)
def list_documents(
    current_admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取所有已上传的文档列表"""
    docs = DocumentRepository.get_all(db)
    result = []
    for doc in docs:
        result.append(DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            chunk_count=doc.chunk_count,
            file_size=doc.file_size,
            status=doc.status,
            error_message=doc.error_message,
            uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else "",
        ))
    return DocumentListResponse(documents=result, total=len(result))


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    上传文档到知识库。

    - 验证文件类型和大小
    - 保存文件
    - 创建数据库记录
    - 提交后台任务处理文档
    """
    # 验证
    ext = validate_file(file)

    # 保存文件
    file_path, original_filename, file_size = save_upload_file(file)

    # 检查文件大小
    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        os.remove(file_path)  # 删除超大文件
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({MAX_FILE_SIZE_MB}MB)"
        )

    # 生成 ChromaDB 集合名
    collection_name = f"doc_{uuid.uuid4().hex[:12]}"

    # 创建数据库记录
    doc = DocumentRepository.create(
        db,
        filename=original_filename,
        file_type=ext,
        file_size=file_size,
        chroma_collection=collection_name,
    )

    # 提交后台处理任务
    from backend.db.database import SessionLocal
    background_tasks.add_task(
        process_document_background,
        file_path,
        original_filename,
        doc.id,
        collection_name,
        SessionLocal,
    )

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        chunk_count=doc.chunk_count,
        file_size=doc.file_size,
        status=doc.status,
        error_message=doc.error_message,
        uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else "",
    )


@router.delete("/{doc_id}", response_model=MessageResponse)
def delete_document(
    doc_id: int,
    current_admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    删除知识库文档。

    同时清理：
    1. 数据库中的文档记录
    2. ChromaDB 中的向量数据
    3. uploads/ 中的原始文件
    """
    doc = DocumentRepository.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # 删除 ChromaDB 中的向量数据
    if doc.chroma_collection:
        from backend.core.document_processor import delete_collection
        delete_collection(doc.chroma_collection)

    # 删除数据库记录
    DocumentRepository.delete(db, doc)

    return {"message": f"文档 '{doc.filename}' 已删除"}


@router.get("/{doc_id}/chunks", response_model=ChunkListResponse)
def get_document_chunks(
    doc_id: int,
    limit: int = 20,
    current_admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    预览文档的切分片段（用于管理页面查看文档内容）。
    """
    doc = DocumentRepository.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    from backend.core.document_processor import get_collection_chunks
    chunks_data = get_collection_chunks(doc.chroma_collection, limit=limit)

    chunks = [
        ChunkPreview(content=c["content"], metadata=c["metadata"])
        for c in chunks_data
    ]
    return ChunkListResponse(chunks=chunks)
