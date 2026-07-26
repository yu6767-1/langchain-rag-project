"""
认证 API 路由
=============
处理用户注册、登录、修改密码、获取用户信息。
使用 JWT Token 进行身份认证。

什么是 JWT 认证？
登录成功后，后端返回一个 Token（加密的字符串）。
前端保存这个 Token，以后每次请求都带上。
后端通过验证 Token 来确认"你是谁"，无需每次都输入密码。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.repositories import UserRepository
from backend.core.security import hash_password, verify_password, create_access_token, decode_access_token
from backend.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ChangePasswordRequest,
    TokenResponse,
    UserInfoResponse,
    MessageResponse,
)
from backend.db.models import User

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ============================================================
# 依赖注入：获取当前登录用户
# ============================================================

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    从请求的 Authorization Header 中解析 JWT Token，获取当前用户。

    这是一个"依赖注入"函数。在需要登录才能访问的接口中，
    直接声明 `current_user: User = Depends(get_current_user)`，
    FastAPI 会自动调用此函数验证 Token 并返回用户对象。

    使用示例：
        @router.get("/profile")
        def profile(current_user: User = Depends(get_current_user)):
            return {"username": current_user.username}
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期，请重新登录",
        )

    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 格式错误")

    user = UserRepository.get_by_username(db, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    return user


def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    管理员权限检查。

    在 get_current_user 的基础上，额外检查用户角色是否为 admin。
    非管理员访问会收到 403 Forbidden 错误。
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可执行此操作",
        )
    return current_user


# ============================================================
# API 接口
# ============================================================

@router.post("/register", response_model=MessageResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    注册新用户。

    - 检查用户名是否已被注册
    - 对密码进行 bcrypt 哈希加密
    - 存入数据库
    """
    # 检查用户名是否已存在
    existing = UserRepository.get_by_username(db, request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该用户名已被注册",
        )

    # 创建用户
    UserRepository.create(
        db,
        username=request.username,
        password_hash=hash_password(request.password),
        role="user",
    )

    return {"message": "注册成功，请登录"}


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录。

    - 验证用户名和密码
    - 生成 JWT Token 返回给前端
    - Token 包含用户名和角色信息
    """
    # 查找用户
    user = UserRepository.get_by_username(db, request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 验证密码
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 生成 Token
    token = create_access_token(data={
        "sub": user.username,
        "role": user.role,
        "user_id": user.id,
    })

    return TokenResponse(
        access_token=token,
        username=user.username,
        role=user.role,
    )


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    修改密码（需要登录）。

    - 验证原密码是否正确
    - 用 bcrypt 加密新密码
    - 更新数据库
    """
    # 验证原密码
    if not verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )

    # 不能和原密码相同
    if request.old_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与原密码相同",
        )

    # 更新密码
    UserRepository.update_password(
        db,
        current_user,
        hash_password(request.new_password),
    )

    return {"message": "密码修改成功"}


@router.get("/me", response_model=UserInfoResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户的信息。

    前端在页面加载时调用此接口，确认 Token 是否有效，
    并获取用户的基本信息用于页面显示。
    """
    return UserInfoResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
    )
