"""
缓存工具模块
============
提供检索结果缓存和 LLM 响应缓存。

为什么需要缓存？
- 用户可能反复问相同的问题（如"这个商品多少钱？"）
- 每次都重新检索 + 调用LLM 既慢又浪费API费用
- 缓存可以在内存中记住之前的答案，相同问题秒回

使用 LRU (Least Recently Used) 策略：
- 最近使用过的结果保留在内存中
- 当缓存满了，最早不用的结果被淘汰
"""

from functools import lru_cache
from typing import Dict, Any
import hashlib
import json


def make_cache_key(question: str, **kwargs) -> str:
    """
    根据问题生成缓存 Key。

    使用 MD5 哈希来确保 Key 长度可控且唯一。
    相同的问题产生相同的 Key → 命中缓存。
    """
    data = json.dumps({"question": question, **kwargs}, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(data.encode("utf-8")).hexdigest()


class RetrievalCache:
    """
    检索结果缓存。

    缓存策略：最多缓存 128 个检索结果
    缓存时间：与 Python 进程生命周期一致（重启后清空）
    """

    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
        self._access_order: list = []  # 记录访问顺序

    def get(self, key: str) -> Any:
        """从缓存获取"""
        if key in self._cache:
            # 更新访问顺序（移到末尾 = 最近使用）
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """存入缓存"""
        if key in self._cache:
            # 更新已有项
            self._access_order.remove(key)
        elif len(self._cache) >= self.max_size:
            # 淘汰最久未使用的项
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]

        self._cache[key] = value
        self._access_order.append(key)

    def clear(self) -> None:
        """清空缓存（知识库更新后需要清空）"""
        self._cache.clear()
        self._access_order.clear()


# 全局检索缓存实例
retrieval_cache = RetrievalCache()
