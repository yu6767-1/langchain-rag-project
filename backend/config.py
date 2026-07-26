"""
应用配置文件
============
集中管理所有配置项：API Key、数据库路径、模型参数等。
敏感信息（如API Key）从 .env 环境变量中读取，不硬编码在代码中。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
# .env 文件放在 backend/ 目录下
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ============ 项目路径 ============
# backend/ 目录
BACKEND_DIR = Path(__file__).parent
# 项目根目录 (langchainRAG项目/)
PROJECT_ROOT = BACKEND_DIR.parent
# data/ 目录
DATA_DIR = PROJECT_ROOT / "data"
# 上传文件存储目录
UPLOAD_DIR = DATA_DIR / "uploads"
# ChromaDB 向量数据目录
CHROMA_DIR = DATA_DIR / "chroma_db"
# SQLite 数据库文件路径
DATABASE_URL = f"sqlite:///{DATA_DIR / 'app.db'}"

# 确保目录存在
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# ============ 阿里云百炼 API 配置 ============
# 在阿里云百炼平台 https://bailian.console.aliyun.com/ 获取 API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# 模型配置
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-turbo")  # 通义千问模型：qwen-turbo(最快) / qwen-plus / qwen-max
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v2")  # Embedding模型

# LLM 参数
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))  # 温度：越低越稳定，越高越有创意
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))  # 最大输出Token数（减少可提速）

# ============ JWT 认证配置 ============
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "langchain-rag-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))  # Token 过期时间（小时）

# ============ 管理员配置 ============
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")

# ============ 文档处理配置 ============
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))  # 文档切分大小（字符数）
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))  # 相邻片段重叠大小
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))  # 单文件最大大小（MB）
ALLOWED_FILE_TYPES = ["pdf", "txt", "csv", "md", "docx", "xlsx"]

# ============ RAG 检索配置 ============
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))  # 向量检索返回数量（减少可提速）
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "4"))  # 重排序后保留数量
CONVERSATION_HISTORY_ROUNDS = int(os.getenv("CONVERSATION_HISTORY_ROUNDS", "10"))  # 对话历史轮数

# ============ 服务配置 ============
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
