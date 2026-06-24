# Resume Matcher 部署指南

本文档涵盖 3 种部署方案，从简单到生产级。

---

## 方案对比

| 方案 | 适用场景 | 月成本 | 复杂度 |
|------|----------|--------|--------|
| A: Docker Compose 单机 | 内网部署、POC | 仅服务器 | ⭐⭐ |
| B: Vercel + Render | 中小规模 SaaS | ~$25 | ⭐⭐⭐ |
| C: 全托管云原生 | 大规模生产 | ~$100+ | ⭐⭐⭐⭐⭐ |

---

## A: Docker Compose 单机部署

### 前置条件
- Linux 服务器 (Ubuntu 22.04+ / CentOS 8+)
- Docker 24+ & Docker Compose v2
- 至少 4GB RAM, 2 CPU 核心

### 步骤

```bash
# 1. 克隆仓库
git clone <repo-url> && cd resume-matcher

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入:
#   - SECRET_KEY: 随机字符串 (openssl rand -hex 32)
#   - LLM_API_KEY: DeepSeek / OpenAI API Key
#   - POSTGRES_PASSWORD: 强密码
#   - MINIO_PASSWORD: 强密码
#   - DEBUG: false

# 3. 构建并启动
docker-compose -f docker-compose.prod.yml up -d --build

# 4. 数据库迁移
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 5. 验证
curl http://localhost:8000/api/v1/health
# 访问 http://<server-ip>:3000
```

### 生产建议
- 使用 Nginx/Caddy 反向代理，配置 HTTPS
- 设置 firewall：仅开放 80/443 端口
- 配置日志轮转 `/var/log/resume-matcher/`
- 添加 cron 定时备份 PostgreSQL 数据

### Nginx 反向代理示例
```nginx
server {
    listen 443 ssl;
    server_name resume-matcher.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 20m;  # 简历文件上传限制
    }

    # 证书配置...
}
```

---

## B: Vercel + Render (推荐中小规模)

### 架构
```
┌─────────────┐     ┌──────────────────────┐
│  Vercel     │────▶│  Render Web Service  │
│  Next.js    │     │  FastAPI (Singapore) │
│  (HKG)      │     └──────────┬───────────┘
└─────────────┘                │
                               ├──▶ Render PostgreSQL 16
                               ├──▶ Upstash Redis (free tier)
                               ├──▶ Qdrant Cloud (vector DB)
                               └──▶ Cloudflare R2 (file storage)
```

### 步骤

#### 1. 后端着陆 Render

```bash
# render.yaml 已在 backend/ 目录，直接关联 Git 仓库即可
```

- 登录 [Render Dashboard](https://dashboard.render.com)
- 新建 **Blueprint** → 连接 Git 仓库
- Render 自动读取 `backend/render.yaml` 创建服务
- 在 Render Dashboard 设置环境变量:
  - `LLM_API_KEY`: DeepSeek API Key
  - `LLM_PROVIDER`: deepseek
  - `LLM_MODEL`: deepseek-chat
  - `CORS_ORIGINS`: `https://your-app.vercel.app`

#### 2. 外部服务配置

**Redis → Upstash** (免费 256MB)
```bash
# 在 Upstash Console 创建 Redis 实例，复制连接 URL
# 在 Render env vars 设置:
REDIS_URL=redis://default:xxx@xxx.upstash.io:6379
```

**ChromaDB → Qdrant Cloud** (免费 1GB)
```bash
# 或与 FastAPI 同容器部署 (小规模):
# 在 Render 的 startCommand 中添加:
# chroma run --path /tmp/chroma &
# uvicorn app.main:app ...
```

**文件存储 → Cloudflare R2** (免费 10GB)
```bash
# 更新 .env 中的 MinIO 配置指向 R2 (S3-compatible endpoint)
```

#### 3. 前端着陆 Vercel

```bash
# frontend/vercel.json 已配置好
```

- 登录 [Vercel](https://vercel.com)
- Import 项目 → 选择 `frontend/` 目录
- 设置环境变量:
  - `NEXT_PUBLIC_API_URL`: Render backend URL (例如 `https://resume-matcher-api.onrender.com`)
- Deploy → 自动构建 Next.js standalone

---

## C: 全托管云原生 (大规模生产)

### 组件映射

| 组件 | 阿里云 | AWS | 月估算成本 |
|------|--------|-----|-----------|
| 前端 CDN | OSS + CDN | S3 + CloudFront | ~$5 |
| 后端计算 | ECS 2c4g ×2 | ECS Fargate ×2 | ~$50 |
| PostgreSQL | RDS pgvector | RDS pgvector | ~$30 |
| Redis | Tair 1GB | ElastiCache t3.micro | ~$15 |
| 向量数据库 | AnalyticDB | 自建 Qdrant | ~$20 |
| 文件存储 | OSS | S3 | ~$5 |
| LLM Gateway | 百炼 API | Bedrock | 按量 |

### 关键区别
- 所有服务使用托管版本（非容器化数据库）
- 后端水平扩展：`--workers` 按 CPU 核数设置
- 数据库连接池：SQLAlchemy `pool_size=20, max_overflow=10`
- 缓存层：Redis 缓存岗位解析结果（TTL 30min）
- 监控：Prometheus + Grafana / 阿里云 ARMS

---

## 环境变量参考

| 变量 | 必需 | 生产建议 |
|------|------|----------|
| `SECRET_KEY` | ✅ | `openssl rand -hex 32` |
| `LLM_API_KEY` | ✅ | 妥善保管，不要提交到 Git |
| `POSTGRES_PASSWORD` | ✅ | 16+ 字符，包含大小写数字 |
| `MINIO_PASSWORD` | ✅ | 强密码 |
| `CORS_ORIGINS` | ✅ | 前端域名，逗号分隔 |
| `DEBUG` | ✅ | **必须设为 false** |
| `REDIS_URL` | ⚠️ | 异步任务必需 |
| `EMBEDDING_DEVICE` | 可选 | 服务器部署设 `cpu`，GPU 设 `cuda` |

---

## 备份策略

```bash
# PostgreSQL 备份 (每日 cron)
pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d).sql.gz

# 恢复
gunzip -c backup_20260101.sql.gz | psql $DATABASE_URL
```

---

## 健康检查

```bash
# API 健康检查
curl https://your-domain/api/v1/health
# → {"status":"healthy","version":"1.0.0"}

# Docker 容器状态
docker-compose -f docker-compose.prod.yml ps
```

---

## 故障排查

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| 502 Bad Gateway | Backend 未启动 | `docker logs rm-prod-backend` |
| 仪表盘"加载出错" | 数据库连接失败 | 检查 `DATABASE_URL`，确认 pgvector 扩展已安装 |
| 简历解析失败 | LLM API Key 无效 | `curl -H "Authorization: Bearer $LLM_API_KEY" https://api.deepseek.com/v1/models` |
| ChromaDB 连接失败 | 向量库未初始化 | 检查 `CHROMA_HOST:CHROMA_PORT` 可达性 |
| 文件上传 500 | MinIO bucket 未创建 | 首次启动后端会自动创建 bucket |
| 匹配超时 | LLM 响应慢 | 减小 `LLM_MAX_TOKENS`，使用更快的模型 |
