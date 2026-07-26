"""
缓存工具模块单元测试
====================
测试 backend/utils/cache.py 中的 make_cache_key 和 RetrievalCache。
"""

import pytest
from backend.utils.cache import make_cache_key, RetrievalCache, retrieval_cache


# ============================================================
# make_cache_key — 缓存键生成
# ============================================================

class TestMakeCacheKey:
    """模块：utils/cache.py — make_cache_key"""

    def test_相同问题相同参数_生成相同Key(self):
        """相同的问题和参数，多次调用应生成完全相同的 Key"""
        key1 = make_cache_key("这个商品多少钱？", product_id=1)
        key2 = make_cache_key("这个商品多少钱？", product_id=1)
        assert key1 == key2
        assert len(key1) == 32  # MD5 哈希是32位十六进制字符串

    def test_不同问题_生成不同Key(self):
        """不同的问题应生成不同的 Key"""
        key1 = make_cache_key("价格多少？")
        key2 = make_cache_key("库存多少？")
        assert key1 != key2

    def test_空字符串问题_正常生成Key(self):
        """空字符串也能正常生成 Key"""
        key = make_cache_key("")
        assert isinstance(key, str)
        assert len(key) == 32

    def test_特殊字符问题_正常生成Key(self):
        """包含中文和特殊字符的问题也能正常生成 Key"""
        key = make_cache_key("你好🌟🚀！@#$%")
        assert isinstance(key, str)
        assert len(key) == 32

    def test_相同问题不同参数_生成不同Key(self):
        """相同问题但不同 kwargs 参数，应生成不同的 Key"""
        key1 = make_cache_key("多少钱？", category="手机")
        key2 = make_cache_key("多少钱？", category="电脑")
        assert key1 != key2


# ============================================================
# RetrievalCache — 检索缓存
# ============================================================

class TestRetrievalCacheBasic:
    """模块：utils/cache.py — RetrievalCache 基本操作"""

    def test_存入后取出_获取正确值(self):
        """set 存入后 get 取出，应获取到相同的值"""
        cache = RetrievalCache(max_size=10)
        cache.set("key1", {"answer": "hello"})
        result = cache.get("key1")
        assert result == {"answer": "hello"}

    def test_不存在的Key_返回None(self):
        """get 一个从未存入的 Key，应返回 None"""
        cache = RetrievalCache(max_size=10)
        result = cache.get("nonexistent")
        assert result is None

    def test_多次存入相同Key_更新值(self):
        """对相同 Key 多次 set，get 应获取到最新值"""
        cache = RetrievalCache(max_size=10)
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        result = cache.get("key1")
        assert result == "value2"

    def test_清空缓存后_get返回None(self):
        """clear 后，之前存入的所有 Key 都应该 get 不到"""
        cache = RetrievalCache(max_size=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_存入不同类型数据_均可取出(self):
        """支持存入 int、list、dict、None 等各种类型"""
        cache = RetrievalCache(max_size=10)
        cache.set("int_key", 42)
        cache.set("list_key", [1, 2, 3])
        cache.set("none_key", None)
        cache.set("str_key", "hello")

        assert cache.get("int_key") == 42
        assert cache.get("list_key") == [1, 2, 3]
        assert cache.get("none_key") is None
        assert cache.get("str_key") == "hello"


class TestRetrievalCacheEviction:
    """模块：utils/cache.py — RetrievalCache LRU 淘汰策略"""

    def test_超出容量_淘汰最久未使用的(self):
        """
        LRU（最近最少使用）策略：当缓存满了，淘汰最久没被访问的那个。
        这里 max_size=3，存入 key1, key2, key3 后，
        访问 key1（使其变为最近使用），再存入 key4，
        此时应淘汰最久未使用的 key2。
        """
        cache = RetrievalCache(max_size=3)
        cache.set("key1", "v1")
        cache.set("key2", "v2")
        cache.set("key3", "v3")

        # 访问 key1，使其成为"最近使用"
        cache.get("key1")

        # 存入 key4，超容量，淘汰最久未使用的 key2
        cache.set("key4", "v4")

        assert cache.get("key1") == "v1"  # 被访问过，还在
        assert cache.get("key2") is None   # 最久未使用，被淘汰
        assert cache.get("key3") == "v3"  # 还在
        assert cache.get("key4") == "v4"  # 新存入的

    def test_连续写入超出容量_正确淘汰(self):
        """连续写入超过 max_size 的数据，旧的按顺序被淘汰"""
        cache = RetrievalCache(max_size=2)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")  # k1 被淘汰
        cache.set("k4", "v4")  # k2 被淘汰

        assert cache.get("k1") is None
        assert cache.get("k2") is None
        assert cache.get("k3") == "v3"
        assert cache.get("k4") == "v4"

    def test_默认容量128_可正常使用(self):
        """使用默认 max_size=128 创建缓存，应能正常存取"""
        cache = RetrievalCache()  # 默认 128
        for i in range(200):
            cache.set(f"key{i}", f"value{i}")
        # 第128个之后的应该还在，最早的前72个应该被淘汰
        assert cache.get("key0") is None   # 最早存入的，被淘汰
        assert cache.get("key199") == "value199"  # 最后存入的，还在


class TestGlobalCache:
    """模块：utils/cache.py — 全局 retrieval_cache 实例"""

    def test_全局缓存实例_可用(self):
        """全局 retrieval_cache 是 RetrievalCache 的实例，可正常使用"""
        from backend.utils.cache import retrieval_cache
        retrieval_cache.set("__test_key__", "test_value")
        result = retrieval_cache.get("__test_key__")
        assert result == "test_value"
        # 清理，避免影响其他测试
        retrieval_cache.clear()
