# 技术能力

## 编程语言

| 语言 | 熟练度 | 使用场景 |
|------|--------|----------|
| Python | ⭐⭐⭐⭐ | 后端开发、AI 应用、数据处理 |
| JavaScript | ⭐⭐⭐ | Vue 前端开发、WebSocket 通信 |
| HTML/CSS | ⭐⭐⭐ | 页面布局、样式设计 |
| SQL | ⭐⭐⭐ | SQLite 数据库操作、ORM 查询 |

## 后端技术栈

### Web 框架
- **FastAPI**：精通。使用 FastAPI 构建 RESTful API 和 WebSocket 服务
- 理解异步编程（async/await）
- 熟练使用依赖注入（Depends）、中间件（CORS）、路由注册

### 数据库
- **SQLAlchemy ORM**：熟练。定义数据模型、管理数据库会话、编写 Repository 层
- **SQLite**：精通。用于开发和轻量级部署
- 理解 Repository 模式，将数据访问与业务逻辑分离

### 认证与安全
- **JWT（JSON Web Token）**：理解 Token 的生成、验证、过期机制
- **bcrypt**：理解密码哈希原理（盐值、不可逆加密）
- 实现基于 Token 的无状态认证方案

### AI/LLM 技术栈
- **LangChain**：熟练。使用 LangChain 构建 RAG 链
  - ChatPromptTemplate：构建结构化提示词
  - Document Loader：多格式文档加载（PDF、DOCX、CSV、MD、XLSX）
  - Text Splitter：递归字符切分（RecursiveCharacterTextSplitter）
  - Vector Store：ChromaDB 向量存储和检索
- **通义千问（Qwen）**：通过阿里云百炼平台调用
  - 模型选型：qwen-turbo（最快）/ qwen-plus / qwen-max
  - 流式输出（Streaming）：体验流畅的文字生成
- **Embedding（向量化）**：理解文本转向量的原理
  - 使用 DashScope Embedding 模型
  - 理解余弦相似度、向量距离

### 向量数据库
- **ChromaDB**：精通。用于 RAG 系统的文档向量存储和语义检索
  - 持久化存储（PersistentClient）
  - Collection 管理（创建、查询、删除）
  - 理解向量检索和关键词检索的互补关系

## 前端技术栈

### 框架和库
- **Vue 3**：熟练。使用 Composition API（`<script setup>`）开发
- **Pinia**：熟练。管理全局状态（用户认证、聊天会话）
- **Vue Router 5**：熟练。路由配置、导航守卫、权限控制
- **Element Plus**：熟练。UI 组件库，构建管理后台界面

### 通信
- **Axios**：HTTP 请求拦截器、响应拦截器、错误统一处理
- **WebSocket**：实时流式通信，逐字推送 AI 回答
- **Vite**：构建工具，代理配置解决跨域问题

## 开发工具

- **VS Code**：主力编辑器
- **Git / GitHub**：版本控制和代码托管
- **Postman / curl**：API 测试
- **Chrome DevTools**：前端调试
- **pytest**：Python 单元测试框架

## 技术视野

- 理解 RAG（检索增强生成）的完整架构和工作原理
- 理解向量检索、关键词检索、混合检索的优缺点
- 理解 LLM 的 Token 概念、Prompt Engineering（提示词工程）
- 了解 AI Agent（智能体）的基本概念
- 关注大模型应用的最新发展趋势
