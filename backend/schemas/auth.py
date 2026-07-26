"""
认证相关的 Pydantic 数据模型
=============================
Pydantic 是 Python 的数据校验库，可以自动验证请求数据格式是否正确。
比如：密码太短、用户名格式不对等，都能自动检测并返回错误信息。
"""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码（至少6位）")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="原密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码（至少6位）")


class TokenResponse(BaseModel):
    """登录成功返回的 Token"""
    access_token: str = Field(..., description="JWT Token")
    token_type: str = Field(default="bearer", description="Token 类型")
    username: str = Field(..., description="用户名")
    role: str = Field(..., description="用户角色")


class UserInfoResponse(BaseModel):
    """用户信息"""
    id: int
    username: str
    role: str
    created_at: str


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
