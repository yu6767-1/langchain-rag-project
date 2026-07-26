# LangChain RAG 企业级知识库问答系统

基于 LangChain + 阿里云通义千问 的 RAG（检索增强生成）知识库问答系统。支持多格式文档上传、自动向量化、混合检索、流式问答，同时集成了**王雨的个人 AI 简历知识库**。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI + Uvicorn |
| AI 框架 | LangChain |
| 大模型 | 阿里云通义千问 Qwen（qwen-turbo / qwen-plus） |
| 向量数据库 | ChromaDB |
| 数据库 | SQLite + SQLAlchemy ORM |
| 前端 | Vue 3 + Element Plus + Pinia |
| 通信 | RESTful API + WebSocket（流式输出） |
| 测试 | pytest（129 个单元测试） |

## 功能模块

- **用户认证系统**：注册/登录/修改密码，JWT Token 认证，admin/user 角色权限
- **知识库管理**：支持 PDF、Word(.docx)、Excel(.xlsx)、CSV、TXT、Markdown 格式上传，自动向量化存储
- **智能问答**：基于 RAG 的流式问答，WebSocket 逐字推送，引用来源标注
- **混合检索**：向量检索（语义）+ 关键词检索 + 加权融合（0.7:0.3）
- **多会话管理**：多用户多会话，历史记录持久化
- **个人 AI 简历**：王雨的技术能力、项目经历、成长故事知识库

## 项目架构

```
langchain-rag-project/
├── backend/                  # Python 后端
│   ├── api/                  # API 路由
│   │   ├── auth.py           # 用户认证
│   │   ├── chat.py           # WebSocket 流式问答
│   │   ├── conversations.py  # 会话管理
│   │   ├── documents.py      # 文档管理
│   │   └── stats.py          # 统计接口
│   ├── core/                 # 核心业务逻辑
│   │   ├── rag_chain.py      # RAG 核心链
│   │   ├── hybrid_retriever.py   # 混合检索器
│   │   ├── document_processor.py # 文档处理
│   │   ├── llm_factory.py    # LLM 工厂
│   │   ├── security.py       # 安全认证
│   │   └── conversation_manager.py # 对话管理
│   ├── db/                   # 数据库层
│   │   ├── database.py       # 连接 + UTC 时间类型
│   │   ├── models.py         # ORM 模型
│   │   └── repositories.py   # 数据访问层
│   ├── schemas/              # Pydantic 数据模型
│   ├── utils/                # 工具
│   │   ├── cache.py          # 检索缓存
│   │   └── logger.py         # 日志配置
│   ├── tests/                # 单元测试（129个）
│   └── config.py             # 配置中心
├── frontend/                 # Vue 3 前端
│   └── src/
│       ├── api/              # API 调用层
│       ├── stores/           # Pinia 状态管理
│       ├── router/           # 路由 + 导航守卫
│       ├── views/            # 页面组件
│       │   ├── Chat.vue          # 聊天主界面
│       │   ├── KnowledgeBase.vue # 知识库管理
│       │   ├── Login.vue         # 登录
│       │   ├── Register.vue      # 注册
│       │   └── Profile.vue       # 个人中心
│       └── App.vue           # 主布局
└── data/
    └── personal_kb/          # 个人 AI 简历知识库
        ├── 01_AboutMe.md         # 个人介绍
        ├── 02_TechSkills.md      # 技术能力
        ├── 03_Projects.md        # 项目经历
        ├── 04_RAGProject.md      # AI 知识库项目
        ├── 05_LearningPath.md    # 学习路线
        ├── 06_TechThoughts.md    # 技术思考
        ├── 07_Growth.md          # 成长经历
        ├── 08_FuturePlan.md      # 未来规划
        └── 09_InterviewQA.md     # 面试问答
```

## 快速启动

### 1. 环境要求

- Python 3.10+
- Node.js 22+
- 阿里云百炼 API Key ([获取地址](https://bailian.console.aliyun.com/))

### 2. 后端启动

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 配置 API Key（创建 backend/.env 文件）
echo "DASHSCOPE_API_KEY=你的API Key" > .env

# 启动服务
cd ..
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 4. 访问

- 前端页面：http://localhost:5173
- API 文档：http://localhost:8000/docs
- 默认管理员：admin / 123456

### 5. 运行测试

```bash
cd "d:/langchainRAG项目"
PYTHONPATH="d:/langchainRAG项目" python -m pytest backend/tests/ -v
```

## 个人 AI 简历知识库

登录后在知识库管理页面上传 `data/personal_kb/` 下的 9 份 Markdown 文档，即可在聊天页面询问关于王雨的任何问题：

- "王雨的技术栈是什么？"
- "王雨做过什么项目？"
- "王雨怎么理解 RAG 技术？"
- "王雨未来有什么规划？"

## License

MIT
