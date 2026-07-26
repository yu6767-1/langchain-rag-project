"""
安全认证模块
============
处理用户密码加密和 JWT Token 的生成与验证。

核心概念：
- bcrypt: 一种密码哈希算法，将密码变成不可逆的"乱码"。即使数据库泄露，也无法还原密码。
- JWT (JSON Web Token): 登录后发给前端的"通行证"，前端每次请求带上它，后端验证身份。
  Token 由三部分组成：Header.Payload.Signature，用密钥签名防止伪造。
"""

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS


# ============================================================
# 密码处理（直接用 bcrypt，避免 passlib 兼容性问题）
# ============================================================

def hash_password(password: str) -> str:
    """
    将明文密码转为 bcrypt 哈希值。

    什么是 bcrypt？
    bcrypt 是一种专门用于密码哈希的算法，特点：
    1. 单向不可逆：无法从哈希值反推原文
    2. 自带"盐值"：相同的密码每次哈希结果不同，防止彩虹表攻击
    3. 计算慢：故意设计成计算密集型，防止暴力破解

    示例: "123456" → "$2b$12$K8v...很长的乱码..."
    """
    # bcrypt 要求输入 bytes，且密码长度需截断到 72 字节
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码是否与哈希值匹配。

    Args:
        plain_password: 用户输入的明文密码
        hashed_password: 数据库中存储的哈希密码

    Returns:
        True 表示密码正确，False 表示密码错误
    """
    password_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ============================================================
# JWT Token 处理
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT Token。

    Args:
        data: 要存入 Token 的数据（如 {"sub": "admin", "role": "admin"}）
        expires_delta: 过期时间，默认使用配置中的 JWT_EXPIRE_HOURS

    Returns:
        编码后的 JWT Token 字符串，如 "eyJhbGciOi..."

    使用示例：
        token = create_access_token({"sub": "admin", "role": "admin"})
    """
    to_encode = data.copy()
    # 设置过期时间
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    # 用密钥签名
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码并验证 JWT Token。

    Args:
        token: JWT Token 字符串

    Returns:
        成功返回 Token 中的数据字典，失败（过期/伪造）返回 None
    """
    if token is None:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
