# 📋 Resume Matcher — AI 简历智能解析与岗位匹配系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-✓-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🎯 帮助 HR 从海量简历中快速筛选匹配岗位要求的候选人

## ✨ 核心特性

- 🔍 **智能简历解析** — 支持 PDF/DOCX/TXT，NER + LLM 三级提取策略
- 🧠 **AI Agent 编排** — 基于 LangGraph 的 4-Agent 协同工作流
- 📊 **多级匹配流水线** — 规则→TF-IDF→BERT→LLM 渐进式匹配
- 💬 **可解释匹配** — LLM 逐条生成匹配理由，可视化展示
- 🇨🇳 **中文深度优化** — BGE 中文向量 + GLiNER 零样本 NER
- 🐳 **一键部署** — Docker Compose 全栈部署

## 🏗️ 系统架构

```
┌──────────────┐    ┌─────────────────────────────────────┐    ┌──────────────┐
│   Next.js    │◄──►│           FastAPI Gateway            │◄──►│  PostgreSQL  │
│   Frontend   │    │  ┌─────────────────────────────┐    │    │   ChromaDB   │
│  (Antd+ECharts)   │  │   LangGraph Agent Pipeline  │    │    │    Redis     │
│               │    │  │  Parse→Analyze→Match→Explain│    │    │    MinIO     │
└──────────────┘    │  └─────────────────────────────┘    │    └──────────────┘
                     └─────────────────────────────────────┘
```

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- DeepSeek API Key（[免费注册](https://platform.deepseek.com/)）

### 一键启动

```bash
git clone <repo-url>
cd resume-matcher
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY
docker-compose up -d
```

访问：
- **前端界面**: http://localhost:3000
- **API 文档**: http://localhost:8000/docs
- **MinIO**: http://localhost:9001

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install && npm run dev
```

## 📖 API 核心端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/resumes/upload` | 上传简历 |
| `POST` | `/api/v1/jobs/` | 创建岗位 |
| `POST` | `/api/v1/matching/analyze` | 🔥 简历-岗位匹配分析 |
| `GET` | `/api/v1/reports/dashboard` | 仪表盘统计 |

## 🧪 示例

```bash
# 上传简历
curl -X POST http://localhost:8000/api/v1/resumes/upload \
  -F "file=@data/sample_resumes/sample_resume_zh.txt"

# 创建岗位
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Content-Type: application/json" \
  -d '{"title":"AI研发工程师","raw_text":"...岗位描述..."}'

# 匹配分析
curl -X POST http://localhost:8000/api/v1/matching/analyze \
  -H "Content-Type: application/json" \
  -d '{"resume_id":"xxx","job_id":"yyy","enable_llm":true}'
```

## 📊 匹配流程

```
简历上传 → NER提取 → LLM深度解析 → 结构化数据
                                          ↓
岗位输入 → JD解析 → 结构化需求
                     ↓
          ┌──────────────────────┐
          │ Stage 1: 硬性条件过筛 │ (学历/年限/必备技能)
          │ Stage 2: TF-IDF 关键词│ (覆盖率 + 模糊匹配)
          │ Stage 3: BERT 语义    │ (BGE 向量相似度)
          │ Stage 4: LLM 深度推理 │ (逐项分析 + 解释)
          └──────────────────────┘
                     ↓
          综合得分 + 匹配理由 + 优化建议
```

## 🛠️ 技术栈

| 层级 | 技术选型 |
|------|---------|
| **后端框架** | FastAPI (异步) |
| **Agent 编排** | LangGraph |
| **NER** | spaCy + GLiNER |
| **嵌入模型** | BAAI/bge-large-zh-v1.5 |
| **LLM** | DeepSeek-V3 / Qwen3 / OpenAI |
| **向量库** | ChromaDB |
| **数据库** | PostgreSQL 16 |
| **前端** | Next.js 14 + Ant Design + ECharts |
| **部署** | Docker Compose |

## 📁 项目结构

详细结构见 [CLAUDE.md](CLAUDE.md)

## 🤝 贡献

欢迎提交 Issue 和 PR！

## 📄 许可

MIT License
