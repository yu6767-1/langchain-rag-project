"""
RAG 核心链模块
==============
这是整个系统最核心的模块，实现了"检索增强生成"的完整流程。

RAG (Retrieval-Augmented Generation) 是什么？
可以理解为：AI回答之前，先去知识库"查资料"，然后结合资料回答问题。
就像一个学生在开卷考试：先翻书找相关内容，再根据找到的内容写答案。

效果：AI的回答不再是"凭记忆瞎猜"，而是有据可查、可追溯来源的。
"""

from typing import List, Dict, Any, AsyncIterator
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document as LCDocument
from backend.config import RETRIEVAL_TOP_K, CONVERSATION_HISTORY_ROUNDS
from backend.core.llm_factory import get_llm
from backend.core.hybrid_retriever import HybridRetriever
from backend.utils.cache import make_cache_key, RetrievalCache

# 检索结果缓存：重复或相似的问题跳过检索，直接返回缓存
_retrieval_cache = RetrievalCache(max_size=256)


# ============================================================
# RAG Prompt 模板
# ============================================================

# 系统提示词：告诉 AI 它的角色和行为规则
RAG_SYSTEM_PROMPT = """你是一个智能客服助手，名为"RAG 知识库问答助手"。你运行在基于 LangChain + 阿里云通义千问大模型的 RAG（检索增强生成）系统上。你的职责是帮助用户解答问题。

## 你的身份
当你被问到"你是谁"、"你是什么模型"、"你是什么大模型"等问题时，请这样介绍自己：
"我是 RAG 知识库问答助手，基于 LangChain 框架 + 阿里云通义千问大模型构建。我会先在知识库中检索相关资料，再结合大模型的理解能力为你提供准确的回答。我背后使用的是通义千问（Qwen）系列模型。"

## 回答规则
1. **商品相关的问题**：必须基于下面提供的"知识库内容"来回答。如果知识库中没有相关信息，请诚实地说"知识库中暂无此商品的相关信息，建议联系客服获取更多帮助"，不要编造商品信息。
2. **非商品类问题**（如问候、自我介绍、闲聊、技术问题等）：可以直接用自己的知识回答，不需要引用知识库内容。
3. **引用来源**：在引用知识库内容时，使用 [来源: 文件名] 的格式标注出来源。
4. **保持中立**：仅提供客观的商品信息，不要做出主观的价值判断。
5. **结构化回答**：如果问题涉及多个方面，请用清晰的结构分点回答。
6. **友好礼貌**：使用专业但亲切的语气。

---

知识库内容：
{context}

---

当前对话历史：
{chat_history}

---

用户问题：{input}

请回答用户的问题："""


def build_rag_prompt() -> ChatPromptTemplate:
    """
    构建 RAG 的 Prompt 模板。

    什么是 Prompt 模板？
    Prompt 就是给 AI 的"指令"。模板中的 {context}、{chat_history}、{input}
    是占位符，在运行时会被替换成实际的内容。
    """
    return ChatPromptTemplate.from_messages([
        ("system", RAG_SYSTEM_PROMPT),
        # 对话历史会通过 MessagesPlaceholder 注入
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
    ])


# ============================================================
# 检索器
# ============================================================

def get_retriever() -> HybridRetriever:
    """
    获取混合检索器。

    什么是检索器（Retriever）？
    检索器负责从知识库中找到和问题最相关的文档片段。
    就像一个"搜索引擎"，但它搜的是你的知识库，而不是全网。

    为什么用混合检索？
    - 向量检索（语义）：能找到意思相近但用词不同的内容
      例：问"续航"能找到"电池容量"相关的内容
    - BM25（关键词）：能精确匹配型号、规格等专有名词
      例：问"iPhone 15"能精确找到这个型号的内容
    """
    return HybridRetriever(top_k=RETRIEVAL_TOP_K)


# ============================================================
# 格式化对话历史
# ============================================================

def format_chat_history(messages: List[Dict[str, Any]]) -> str:
    """
    将消息列表格式化为可放入 Prompt 的对话历史字符串。

    输入格式：
        [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好！"}]

    输出格式：
        用户：你好
        助手：你好！
    """
    if not messages:
        return "（暂无对话历史）"

    lines = []
    for msg in messages:
        role_label = "用户" if msg["role"] == "user" else "助手"
        lines.append(f"{role_label}：{msg['content']}")
    return "\n".join(lines)


# ============================================================
# RAG 流式问答
# ============================================================

async def rag_stream_chat(
    question: str,
    chat_history: List[Dict[str, Any]],
) -> AsyncIterator[Dict[str, Any]]:
    """
    RAG 流式问答：检索 → 构建Prompt → 流式生成。

    工作流程：
    1. 用混合检索器在知识库中找到最相关的片段
    2. 将片段+对话历史+问题组装成完整的 Prompt
    3. 调用 LLM 逐字流式输出回答
    4. 每次输出一个 token 就立即返回给前端

    Args:
        question: 用户的问题
        chat_history: 最近的对话历史

    Yields:
        {"type": "sources", "data": [...]}  - 先返回引用的知识库来源
        {"type": "token", "data": "文字"}   - 逐字返回回答内容
        {"type": "done", "data": "完整回答"} - 完成信号
    """
    # 步骤1：检查是否有知识库内容
    retriever = get_retriever()
    if retriever.is_empty():
        # 知识库为空，直接回答
        yield {
            "type": "token",
            "data": "知识库中暂无内容，请先由管理员上传商品文档。"
        }
        yield {"type": "done", "data": "知识库中暂无内容，请先由管理员上传商品文档。"}
        return

    # 步骤2：检索相关文档（优先从缓存获取）
    cache_key = make_cache_key(question, top_k=RETRIEVAL_TOP_K)
    cached = _retrieval_cache.get(cache_key)
    if cached is not None:
        retrieved_docs = cached
    else:
        retrieved_docs = retriever.invoke(question)
        _retrieval_cache.set(cache_key, retrieved_docs)

    # 步骤3：提取引用来源
    sources = []
    seen = set()
    for doc in retrieved_docs:
        filename = doc.metadata.get("filename", "未知文档")
        content = doc.page_content
        # 去重（相同内容只保留一个）
        key = content[:100]
        if key not in seen:
            seen.add(key)
            sources.append({
                "content": content[:300],  # 截取前300字用于展示
                "filename": filename,
                "score": doc.metadata.get("score", 0),
            })

    # 先返回来源信息
    yield {"type": "sources", "data": sources}

    # 步骤4：构建上下文
    if not retrieved_docs:
        # 知识库中没找到相关内容，明确告知 LLM 可以自由回答
        context = "（知识库中未找到与当前问题匹配的内容。对于商品相关问题请如实告知用户暂未收录；对于问候、自我介绍、闲聊等非商品问题，请直接回答。）"
    else:
        context = "\n\n---\n\n".join([
            f"[来源: {doc.metadata.get('filename', '未知')}]\n{doc.page_content}"
            for doc in retrieved_docs
        ])

    # 步骤5：格式化对话历史
    history_str = format_chat_history(chat_history)

    # 步骤6：构建完整 Prompt
    prompt_text = RAG_SYSTEM_PROMPT.format(
        context=context,
        chat_history=history_str,
        input=question,
    )

    # 步骤7：流式调用 LLM
    llm = get_llm()
    full_response = ""

    try:
        # LangChain 的 stream 方法返回一个迭代器，每次产生一个 token
        for chunk in llm.stream(prompt_text):
            if chunk:
                full_response += chunk
                yield {"type": "token", "data": chunk}
    except Exception as e:
        yield {"type": "token", "data": f"\n\n[生成回答时出错：{str(e)}]"}

    # 步骤8：完成
    yield {"type": "done", "data": full_response}
