"""
数据库连接和会话管理
====================
使用 SQLAlchemy 管理 SQLite 数据库。
- engine: 数据库引擎（连接池配置）
- SessionLocal: 每次请求使用的数据库会话
- Base: 所有模型的基类
"""

from datetime import datetime, timezone
from sqlalchemy import create_engine, event, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.types import TypeDecorator
from backend.config import DATABASE_URL


# ============================================================
# UTC DateTime 类型（SQLite 不保留时区，这里自动补回 UTC）
# ============================================================

class UTCDateTime(TypeDecorator):
    """
    确保从数据库读取的 datetime 始终带有 UTC 时区信息。
    SQLite 不存储时区，所以存入的是 UTC 数值，读出时补上 +00:00。
    这样子后端 .isoformat() 会输出 "2026-07-26T05:41:50+00:00"，
    前端 JavaScript 就能正确识别为 UTC 时间并转为本地时间显示。
    """
    impl = DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


# ============================================================
# 数据库引擎和连接
# ============================================================

# 创建数据库引擎
# SQLite 需要 check_same_thread=False 才能在 FastAPI 异步环境中使用
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 特有配置
    pool_size=10,        # 连接池大小
    pool_pre_ping=True,  # 每次使用前检测连接是否有效
    echo=False,          # 设为 True 可看到 SQL 语句日志
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 所有 ORM 模型的基类
Base = declarative_base()


def get_db():
    """
    获取数据库会话的依赖注入函数。

    FastAPI 的依赖注入用法：
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            ...

    每次请求自动创建会话，请求结束后自动关闭。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库：创建所有表。
    在应用启动时调用一次。
    """
    Base.metadata.create_all(bind=engine)
