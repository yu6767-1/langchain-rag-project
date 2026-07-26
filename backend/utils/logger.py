"""
日志配置模块
============
使用 loguru 库记录系统运行日志。
日志输出到控制台和文件，方便排查问题。
"""

import sys
from pathlib import Path
from loguru import logger

# 移除默认的 handler
logger.remove()

# 控制台日志（开发环境使用彩色格式）
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# 文件日志（记录所有 INFO 级别以上的日志）
LOG_DIR = Path(__file__).parent.parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger.add(
    LOG_DIR / "app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="10 MB",   # 日志文件超过 10MB 自动轮转
    retention="7 days", # 保留最近 7 天的日志
    encoding="utf-8",
)


def get_logger():
    """获取 logger 实例"""
    return logger
