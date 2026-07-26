# AI 知识库项目（RAG 系统）详细说明

## 什么是 RAG

RAG（Retrieval-Augmented Generation，检索增强生成）是一种让大模型"开卷考试"的技术。

**传统大模型的问题**：
- 知识有截止日期（训练的语料是某个时间点之前的）
- 容易"幻觉"（编造不存在的信息）
- 无法访问企业内部私有数据

**RAG 的解决方案**：
1. 用户提问
2. 系统先去知识库检索相关文档片段
3. 把检索到的片段 + 用户问题一起发给大模型
4. 大模型基于提供的资料回答，而不是凭记忆瞎猜

就像一个学生在开卷考试：先翻书找答案，再根据找到的内容答题。

## 系统的技术架构

### 前端（Vue 3 + Element Plus）

```
src/
  ├── App.vue          # 主布局（侧边栏 + 内容区）
  ├── main.js           # 入口文件
  ├── router/index.js   # 路由配置 + 导航守卫
  ├── stores/
  │   ├── auth.js       # 认证状态管理（Pinia）
  │   └── chat.js       # 聊天状态管理（Pinia）
  ├── api/
  │   ├── request.js    # Axios 实例（拦截器）
  │   ├── auth.js       # 认证 API
  │   ├── chat.js       # WebSocket 聊天 API
  │   ├── conversation.js # 会话管理 API
  │   └── document.js   # 文档管理 API
  └── views/
      ├── Login.vue      # 登录页
      ├── Register.vue   # 注册页
      ├── Chat.vue       # 聊天主界面（会话列表 + 消息区 + 输入框）
      ├── KnowledgeBase.vue # 知识库管理（文档上传/列表/统计）
      └── Profile.vue    # 个人中心（修改密码）
```

### 后端（FastAPI + LangChain）

```
backend/
  ├── main.py           # 应用入口
  ├── config.py          # 配置中心
  ├── api/
  │   ├── auth.py        # 认证接口
  │   ├── chat.py        # WebSocket 流式问答接口
  │   ├── conversations.py # 会话管理接口
  │   ├── documents.py   # 文档管理接口
  │   └── stats.py       # 统计接口
  ├── core/
  │   ├── rag_chain.py   # RAG 核心链（检索 + 生成）
  │   ├── hybrid_retriever.py # 混合检索器
  │   ├── document_processor.py # 文档处理（加载/切分/向量化）
  │   ├── llm_factory.py # LLM 和 Embedding 工厂
  │   ├── security.py    # 密码哈希 + JWT Token
  │   └── conversation_manager.py # 对话业务逻辑
  ├── db/
  │   ├── database.py    # 数据库连接 + UTC 时间类型
  │   ├── models.py      # ORM 数据模型
  │   └── repositories.py # Repository 数据访问层
  └── utils/
      ├── cache.py       # 检索缓存
      └── logger.py      # 日志配置
```

### 数据库设计（SQLite）

**users（用户表）**：id、username、password_hash、role（admin/user）、created_at

**conversations（会话表）**：id、user_id、title、created_at、updated_at

**messages（消息表）**：id、conversation_id、role（user/assistant）、content、sources（JSON）、feedback、created_at

**documents（文档表）**：id、filename、file_type、chunk_count、file_size、status（processing/ready/error）、chroma_collection、error_message、uploaded_at

## 关键实现细节

### 1. 混合检索策略

检索不是只用一种方式，而是结合了两种方法：

- **向量检索（语义搜索）**：把问题和文档都转成向量（Embedding），计算向量之间的余弦距离。能理解"续航"和"电池容量"是相似概念。
- **关键词检索（BM25 补充）**：精确匹配型号、规格等专有名词。问"iPhone 15"能精确找到包含这个型号的内容。
- **融合策略**：向量相似度 × 0.7 + 关键词匹配 × 0.3，按综合分数排序

### 2. 流式输出

使用 WebSocket 协议，LLM 每生成一个 Token 就推送给前端，用户看到文字一个个出现，体验流畅。

非流式的问题：用户等 5 秒看到完整回答，中间不知道系统在干嘛。
流式的优势：用户 0.5 秒就看到第一个字，知道系统在工作。

### 3. 文档处理流程

1. 用户上传文件（PDF/DOCX/XLSX/CSV/TXT/MD）
2. 根据文件类型选择合适的 Loader（PDF→PyPDFLoader、DOCX→docx2txt、XLSX→openpyxl）
3. 用 RecursiveCharacterTextSplitter 切分成小片段（500 字/段，100 字重叠）
4. 调用 Embedding 模型把每个片段转成向量
5. 存入 ChromaDB 向量数据库

### 4. 安全设计

- 密码用 bcrypt 哈希加密（不可逆，自带盐值）
- JWT Token 过期机制（默认 24 小时）
- 前端 XSS 防护（Markdown 渲染时过滤危险标签）
- 导航守卫实现页面级权限控制
