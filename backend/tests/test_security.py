"""
安全模块单元测试
================
测试 backend/core/security.py 中的密码哈希和 JWT Token 功能。
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta, datetime, timezone
from backend.core.security import hash_password, verify_password, create_access_token, decode_access_token


# ============================================================
# hash_password — 密码哈希
# ============================================================

class TestHashPassword:
    """模块：core/security.py — hash_password"""

    def test_正常密码_返回bcrypt哈希字符串(self):
        """传入正常密码，应返回 bcrypt 格式的哈希值（以 $2b$ 开头）"""
        result = hash_password("123456")
        assert result.startswith("$2b$")
        assert len(result) > 20

    def test_密码为空字符串_正常哈希不报错(self):
        """传入空字符串，bcrypt 仍能正常哈希"""
        result = hash_password("")
        assert result.startswith("$2b$")

    def test_密码含特殊字符_正常哈希(self):
        """传入包含特殊字符的密码，应正常哈希"""
        result = hash_password("p@ss!你好🌟")
        assert result.startswith("$2b$")

    def test_密码超长_截断到72字节后正常哈希(self):
        """
        传入超长密码（超过bcrypt的72字节限制），应被截断后正常哈希。
        bcrypt 会将密码截断到 72 字节，这是设计行为——验证时也会截断。
        """
        long_password = "a" * 100  # 100个字符的密码
        result = hash_password(long_password)
        assert result.startswith("$2b$")

    def test_相同密码两次哈希_结果不同(self):
        """
        相同的密码哈希两次，结果不同。
        这是因为 bcrypt 每次生成不同的"盐值"（salt），
        防止攻击者通过预计算的方式破解密码。
        """
        hash1 = hash_password("mypassword")
        hash2 = hash_password("mypassword")
        assert hash1 != hash2


# ============================================================
# verify_password — 密码验证
# ============================================================

class TestVerifyPassword:
    """模块：core/security.py — verify_password"""

    def test_密码正确_返回True(self):
        """输入正确的明文密码，应与哈希值匹配，返回 True"""
        hashed = hash_password("correct123")
        result = verify_password("correct123", hashed)
        assert result is True

    def test_密码错误_返回False(self):
        """输入错误的明文密码，应返回 False"""
        hashed = hash_password("correct123")
        result = verify_password("wrongpassword", hashed)
        assert result is False

    def test_哈希值被篡改_返回False或抛出异常(self):
        """
        传入被篡改的哈希值时，bcrypt 可能返回 False 或抛出 ValueError（Invalid salt）。
        这两种行为都是合理的安全处理方式（不通过验证）。
        """
        try:
            result = verify_password("anything", "not-a-valid-bcrypt-hash")
            assert result is False
        except ValueError:
            # bcrypt 也可以选择抛出异常，这也是合理的安全行为
            pass

    def test_超长密码哈希后验证_正确匹配(self):
        """
        超长密码（>72字节）在哈希和验证时都会被截断到72字节，
        因此验证应该通过。
        """
        long_pw = "a" * 100
        hashed = hash_password(long_pw)
        result = verify_password(long_pw, hashed)
        assert result is True


# ============================================================
# create_access_token — JWT Token 创建
# ============================================================

class TestCreateAccessToken:
    """模块：core/security.py — create_access_token"""

    def test_正常创建Token_返回字符串(self):
        """传入用户数据，应返回一个 JWT Token 字符串"""
        token = create_access_token({"sub": "admin", "role": "admin"})
        assert isinstance(token, str)
        assert token.count(".") == 2  # JWT 由三段组成，用 . 分隔

    def test_自定义过期时间_Token中包含过期声明(self):
        """传入自定义过期时间，Token 应包含正确的 exp 声明"""
        token = create_access_token(
            {"sub": "testuser"},
            expires_delta=timedelta(hours=1),
        )
        # 解码验证
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_不同用户数据_生成不同Token(self):
        """不同的输入数据应生成不同的 Token"""
        token1 = create_access_token({"sub": "alice"})
        token2 = create_access_token({"sub": "bob"})
        assert token1 != token2

    def test_Token中可存储自定义字段(self):
        """Token 中存入的自定义字段应能被解码恢复"""
        token = create_access_token({
            "sub": "admin",
            "role": "admin",
            "extra_field": "custom_value",
        })
        payload = decode_access_token(token)
        assert payload["extra_field"] == "custom_value"


# ============================================================
# decode_access_token — JWT Token 解码
# ============================================================

class TestDecodeAccessToken:
    """模块：core/security.py — decode_access_token"""

    def test_有效Token_返回数据字典(self):
        """传入有效 Token，应返回包含原始数据的字典"""
        token = create_access_token({"sub": "user1", "role": "user"})
        payload = decode_access_token(token)
        assert isinstance(payload, dict)
        assert payload["sub"] == "user1"
        assert payload["role"] == "user"

    def test_被篡改的Token_返回None(self):
        """传入被篡改的 Token（如改了某个字符），应返回 None"""
        token = create_access_token({"sub": "user1"})
        # 修改最后一字符，Signature 验证会失败
        tampered = token[:-1] + "X"
        result = decode_access_token(tampered)
        assert result is None

    def test_空字符串_返回None(self):
        """传入空字符串，应返回 None 而不是崩溃"""
        result = decode_access_token("")
        assert result is None

    def test_过期Token_返回None(self):
        """传入已过期的 Token，应返回 None"""
        # 创建一个已经过期的 Token（过期时间为过去）
        token = create_access_token(
            {"sub": "expired_user"},
            expires_delta=timedelta(seconds=-1),  # 1秒前过期
        )
        result = decode_access_token(token)
        assert result is None

    def test_None值传入_返回None(self):
        """传入 None，应安全返回 None（不崩溃）"""
        result = decode_access_token(None)
        assert result is None

    def test_格式错误的字符串_返回None(self):
        """传入非 JWT 格式的随机字符串，应返回 None"""
        result = decode_access_token("not-a-jwt-token-at-all")
        assert result is None
