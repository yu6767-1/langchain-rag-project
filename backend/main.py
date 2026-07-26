"""
FastAPI 应用入口
================
启动命令：uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

这个文件是整个后端的"大脑"，负责：
- 创建 FastAPI 应用实例
- 注册所有 API 路由
- 配置 CORS（跨域资源共享）
- 应用启动时初始化数据库和管理员账号
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import CORS_ORIGINS, ADMIN_USERNAME, ADMIN_PASSWORD
from backend.db.database import init_db, SessionLocal
from backend.db.repositories import UserRepository
from backend.core.security import hash_password
from backend.api import auth, conversations, chat, documents, stats


# ============================================================
# 应用生命周期管理
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 应用的生命周期管理器。

    启动时（yield 之前）：
    - 初始化数据库表
    - 创建默认管理员账号

    关闭时（yield 之后）：
    - 清理资源（目前无需特殊处理）
    """
    # ===== 启动时 =====
    print("正在初始化数据库...")
    init_db()
    print("数据库初始化完成")

    # 创建默认管理员账号（如果不存在）
    db = SessionLocal()
    try:
        admin = UserRepository.get_by_username(db, ADMIN_USERNAME)
        if not admin:
            UserRepository.create(
                db,
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                role="admin",
            )
            print(f"管理员账号已创建: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
        else:
            # 确保管理员角色正确
            if admin.role != "admin":
                admin.role = "admin"
                db.commit()
            print(f"管理员账号已存在: {ADMIN_USERNAME}")
    finally:
        db.close()

    print(f"后端服务启动成功！")
    print(f"API 文档: http://localhost:8000/docs")
    print(f"WebSocket: ws://localhost:8000/ws/chat/{{id}}?token=...")

    yield  # ← 应用运行期间

    # ===== 关闭时 =====
    print("应用正在关闭...")


# ============================================================
# 创建 FastAPI 应用
# ============================================================

app = FastAPI(
    title="RAG 企业级知识库问答系统",
    description="""
基于 LangChain + 阿里云通义千问 的 RAG（检索增强生成）知识库问答系统。

## 功能模块

- **认证系统**：用户注册/登录/修改密码，JWT Token 认证
- **知识库管理**：管理员上传/管理文档，自动向量化存储
- **智能问答**：基于知识库的 RAG 问答，流式输出，引用来源
- **多会话管理**：多用户多会话，历史记录持久化

## 技术栈

- 后端：FastAPI + LangChain + ChromaDB + SQLite
- 前端：Vue 3 + Element Plus + Vite
- 模型：阿里云百炼（通义千问 Qwen）
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================================
# CORS 中间件配置
# ============================================================

# 什么是 CORS？
# 浏览器有"同源策略"安全限制：前端(5173端口)不能直接请求后端(8000端口)。
# CORS 告诉浏览器："允许来自前端地址的请求"，从而突破这个限制。

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,        # 允许的前端地址
    allow_credentials=True,            # 允许携带 Cookie
    allow_methods=["*"],               # 允许所有 HTTP 方法
    allow_headers=["*"],               # 允许所有请求头
)

# ============================================================
# 注册路由
# ============================================================

app.include_router(auth.router)          # 认证相关
app.include_router(conversations.router) # 会话管理
app.include_router(chat.router)          # WebSocket 问答
app.include_router(documents.router)     # 知识库管理
app.include_router(stats.router)         # 统计


# ============================================================
# 根路径（健康检查）
# ============================================================

@app.get("/")
def root():
    """健康检查接口"""
    return {
        "message": "RAG 知识库问答系统运行中",
        "version": "1.0.0",
        "docs": "/docs",
    }
