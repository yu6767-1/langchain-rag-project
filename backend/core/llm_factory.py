"""
LLM 工厂模块
============
统一创建和管理大语言模型（LLM）和 Embedding 模型的实例。
支持阿里云百炼（DashScope）平台。

为什么要用"工厂模式"？
- 如果要切换模型（如从通义千问换到 OpenAI），只需改这个文件，其他代码不受影响。
- 统一管理 API Key 和模型参数，避免散落在各处。
"""

from langchain_community.llms import Tongyi
from langchain_community.embeddings import DashScopeEmbeddings
from backend.config import (
    DASHSCOPE_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    EMBEDDING_MODEL,
)


def get_llm() -> Tongyi:
    """
    获取通义千问 LLM 实例。

    什么是 LLM (Large Language Model)？
    大语言模型，就是"会聊天的AI大脑"。你给它一个问题，它生成回答。
    通义千问是阿里云的大模型，类似于 OpenAI 的 GPT。

    Returns:
        配置好的 Tongyi LLM 实例，可用于 LangChain 的各种链中。

    使用示例：
        llm = get_llm()
        response = llm.invoke("你好，请介绍一下你自己")
    """
    if not DASHSCOPE_API_KEY or DASHSCOPE_API_KEY == "your-dashscope-api-key-here":
        raise ValueError(
            "请先配置阿里云百炼 API Key！\n"
            "1. 访问 https://bailian.console.aliyun.com/ 开通服务\n"
            "2. 获取 API Key\n"
            "3. 填入 backend/.env 文件中的 DASHSCOPE_API_KEY"
        )

    return Tongyi(
        model=LLM_MODEL,            # 模型名称（qwen-turbo / qwen-plus / qwen-max）
        temperature=LLM_TEMPERATURE, # 温度参数（0=稳定，1=创意）
        max_tokens=LLM_MAX_TOKENS,   # 最大输出长度
        dashscope_api_key=DASHSCOPE_API_KEY,
        streaming=True,              # 启用流式输出
    )


def get_embeddings() -> DashScopeEmbeddings:
    """
    获取阿里云 DashScope Embedding 实例。

    什么是 Embedding？
    把一段文字转换成一串数字（向量），这串数字能代表文字的"语义"。
    比如"苹果手机"和"iPhone"转换后的向量会很接近。
    这样计算机就能"理解"文字的意思，找到意思相近的内容。

    Returns:
        DashScopeEmbeddings 实例，用于文档向量化和查询向量化。
    """
    if not DASHSCOPE_API_KEY or DASHSCOPE_API_KEY == "your-dashscope-api-key-here":
        raise ValueError("请先配置阿里云百炼 API Key！")

    return DashScopeEmbeddings(
        model=EMBEDDING_MODEL,
        dashscope_api_key=DASHSCOPE_API_KEY,
    )
