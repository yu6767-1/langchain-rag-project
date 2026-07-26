"""
问答 WebSocket API 路由
========================
使用 WebSocket 协议实现流式问答。

为什么用 WebSocket 而不是普通 HTTP？
LLM 生成回答需要几秒钟，如果用普通 HTTP：
- 用户看着白屏等待 → 体验差
- 不知道系统是在工作还是卡住了

WebSocket 可以逐字推送回答 → 用户看到文字一个个出现 → 体验流畅。
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from backend.db.database import SessionLocal
from backend.core.security import decode_access_token
from backend.db.repositories import UserRepository
from backend.core.rag_chain import rag_stream_chat
from backend.core.conversation_manager import ConversationManager
from backend.config import CONVERSATION_HISTORY_ROUNDS

router = APIRouter(tags=["问答"])


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: int,
    token: str = Query(...),
):
    """
    WebSocket 流式问答接口。

    连接方式：
        ws://localhost:8000/ws/chat/1?token=eyJhbG...

    消息格式（前端发送）：
        {"question": "这款商品的参数是什么？"}

    消息格式（后端推送）：
        {"type": "sources", "data": [...]}     — 引用的知识库片段
        {"type": "token", "data": "文字"}      — 逐字推送的回答
        {"type": "done", "data": "完整回答"}    — 完成信号
        {"type": "error", "data": "错误信息"}   — 错误

    Token 验证方式：
    WebSocket 握手时无法使用 HTTP Header，所以 Token 通过 URL 参数传递。
    """
    # 1. 验证 Token
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4001, reason="Token无效或已过期")
        return

    username = payload.get("sub")
    if not username:
        await websocket.close(code=4001, reason="Token格式错误")
        return

    # 2. 获取数据库会话
    db = SessionLocal()
    try:
        user = UserRepository.get_by_username(db, username)
        if not user:
            await websocket.close(code=4001, reason="用户不存在")
            return

        # 3. 验证会话所有权
        from backend.db.repositories import ConversationRepository
        conv = ConversationRepository.get_by_id(db, conversation_id)
        if not conv:
            await websocket.close(code=4004, reason="会话不存在")
            return
        if conv.user_id != user.id:
            await websocket.close(code=4003, reason="无权访问此会话")
            return

        # 4. 接受 WebSocket 连接
        await websocket.accept()

        # 5. 对话管理器
        manager = ConversationManager(db)

        # 6. 等待用户消息并处理
        while True:
            try:
                # 接收前端发来的问题
                data = await websocket.receive_text()
                request = json.loads(data)
                question = request.get("question", "").strip()

                if not question:
                    await websocket.send_json({"type": "error", "data": "问题不能为空"})
                    continue

                # 保存用户消息
                manager.add_message(conversation_id, "user", question)

                # 获取对话历史
                chat_history = manager.get_recent_messages(
                    conversation_id,
                    rounds=CONVERSATION_HISTORY_ROUNDS,
                )

                # 加载 RAG 流式问答
                full_response = ""
                async for chunk in rag_stream_chat(question, chat_history):
                    await websocket.send_json(chunk)
                    if chunk["type"] == "done":
                        full_response = chunk["data"]

                # 收集 sources（从 chunk 流中已发送，这里从 done 前的 sources 提取）
                sources = []
                # sources 已经在 streaming 时通过 type:sources 发送了

                # 保存助手回答到数据库
                if full_response:
                    manager.add_message(
                        conversation_id,
                        "assistant",
                        full_response,
                        sources=sources,
                    )

                # 自动生成会话标题（如果是第一条消息）
                if conv.title == "新建会话":
                    # 用前30个字做标题
                    title = question[:30] + ("..." if len(question) > 30 else "")
                    manager.update_conversation_title(conversation_id, title)

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": "消息格式错误"})
            except Exception as e:
                await websocket.send_json({"type": "error", "data": str(e)})

    finally:
        db.close()
