# TrendRadar SaaS 改造计划

## 架构总览

```
┌─────────────────────────────────────────────────────┐
│                  Nginx / Reverse Proxy               │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐  ┌────────────┐  ┌──────────┐
   │  Web UI │  │ FastAPI    │  │  MCP     │
   │ (Vue3)  │  │ Backend    │  │ Server   │
   └────┬────┘  └─────┬──────┘  └────┬─────┘
        │             │              │
        └─────────────┼──────────────┘
                      ▼
            ┌──────────────────┐
            │   PostgreSQL     │
            │  (用户/配置/数据) │
            └────────┬─────────┘
                     ▼
            ┌──────────────────┐
            │  Redis           │
            │ (缓存/会话/队列) │
            └────────┬─────────┘
                     ▼
            ┌──────────────────┐
            │  Celery Worker   │
            │ (爬虫/AI分析推送) │
            └──────────────────┘
```

---

## Phase 1: 基础设施搭建（1-2 周）

**目标：建立 Web 后端框架、数据库、用户认证系统**

| 任务 | 详情 |
|------|------|
| 1.1 引入 FastAPI | 新增 `backend/` 目录，使用 FastAPI 作为 Web 框架 |
| 1.2 数据库选型 | 从 SQLite 迁移到 PostgreSQL，支持多用户并发 |
| 1.3 ORM 层 | 使用 SQLAlchemy 2.0 + Alembic 做数据库迁移管理 |
| 1.4 用户模型 | `User` 表：id, email, password_hash, nickname, created_at, status, tier |
| 1.5 JWT 认证 | 注册/登录/刷新 token，密码使用 bcrypt 加密 |
| 1.6 Redis 引入 | 会话管理、速率限制、任务队列 |
| 1.7 项目结构 | `backend/app/{api,models,schemas,services,core}` 分层架构 |

### 新增目录结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── models/
│   │   ├── user.py          # 用户模型
│   │   ├── user_config.py   # 用户配置模型
│   │   └── base.py          # SQLAlchemy 基类
│   ├── schemas/
│   │   ├── user.py          # Pydantic 请求/响应模型
│   │   └── auth.py
│   ├── api/
│   │   ├── auth.py          # 注册/登录接口
│   │   ├── users.py         # 用户管理接口
│   │   └── deps.py          # 依赖注入（获取当前用户）
│   ├── core/
│   │   ├── security.py      # JWT + 密码哈希
│   │   └── config.py        # 系统全局配置
│   └── db/
│       ├── session.py       # 数据库会话
│       └── init_db.py       # 初始化
├── alembic/                 # 数据库迁移
├── requirements.txt
└── Dockerfile
```

---

## Phase 2: 用户配置管理系统（2-3 周）

**目标：每个用户独立管理自己的配置，AI 模型使用全局设定**

| 任务 | 详情 |
|------|------|
| 2.1 用户配置表 | `user_config` 表存储用户个性化配置（platforms, rss, frequency_words, timeline, notification, report, filter, display 等） |
| 2.2 系统全局配置 | `system_config` 表：ai_model, ai_api_key, ai_base_url（仅管理员可改） |
| 2.3 配置 CRUD API | GET/PUT 用户配置，支持按模块获取 |
| 2.4 配置验证 | 复用现有 core/loader.py 和 core/config.py 的验证逻辑 |
| 2.5 预设模板 | 用户可选择预设 timeline 模板 |
| 2.6 配置版本管理 | 配置变更历史，支持回滚 |

### 核心设计原则

- `ai.api_key`, `ai.base_url`, `ai.model` 从 `system_config` 读取，**用户不可见不可改**
- 用户配置中只保留个性化部分（关注平台、关键词、推送渠道、报告模式等）
- 运行时动态合并：`system_config.ai` + `user_config.*` = 完整运行时配置

### 用户配置字段映射（来自 config.yaml）

| config.yaml 模块 | 用户可配置 | 说明 |
|------------------|-----------|------|
| app.timezone | ✅ | 时区 |
| schedule.preset | ✅ | 调度模板 |
| platforms.sources | ✅ | 热榜平台 |
| rss.feeds | ✅ | RSS 订阅源 |
| report.* | ✅ | 报告模式 |
| filter.* | ✅ | 筛选策略 |
| notification.channels | ✅ | 推送渠道 |
| display.* | ✅ | 展示区域 |
| ai_analysis.* | ✅ | AI 分析开关 |
| ai_translation.* | ✅ | AI 翻译开关 |
| **ai.model** | ❌ | 系统全局 |
| **ai.api_key** | ❌ | 系统全局 |
| **ai.api_base** | ❌ | 系统全局 |
| storage.* | ✅ | 存储配置 |

### 用户配置字段映射（来自 timeline.yaml）

| timeline.yaml 模块 | 用户可配置 | 说明 |
|-------------------|-----------|------|
| presets.* | ✅ | 时间段定义 |
| custom.* | ✅ | 自定义时间段 |

### 用户配置字段映射（来自 frequency_words.txt）

| 模块 | 用户可配置 | 说明 |
|------|-----------|------|
| GLOBAL_FILTER | ✅ | 全局过滤词 |
| WORD_GROUPS | ✅ | 关键词组 |

---

## Phase 3: 多租户数据隔离（2-3 周）

**目标：每个用户只能看到和操作自己的数据**

| 任务 | 详情 |
|------|------|
| 3.1 数据库多租户 | 所有数据表增加 `user_id` 外键 |
| 3.2 存储隔离 | 文件存储按 user_id 分目录，或统一用 PostgreSQL |
| 3.3 查询隔离 | ORM 层自动附加 `WHERE user_id = ?` |
| 3.4 爬虫隔离 | 每个用户的爬虫任务独立执行 |
| 3.5 推送隔离 | 通知推送只使用当前用户的配置 |

### 数据库 Schema 变更示例

```sql
-- 原有
CREATE TABLE news_items (id, title, url, platform_id, ...);

-- 改造后
CREATE TABLE news_items (
    id,
    user_id INTEGER REFERENCES users(id),
    title,
    url,
    platform_id,
    ...
);
CREATE INDEX idx_news_user_date ON news_items(user_id, crawl_date);
```

### 受影响的数据表

| 表名 | 变更 |
|------|------|
| news_items | + user_id |
| title_changes | + user_id |
| rank_history | + user_id |
| crawl_records | + user_id |
| rss_items | + user_id |
| rss_feeds | + user_id |
| ai_filter_tags | + user_id |
| period_executions | + user_id |

---

## Phase 4: 任务调度系统改造（2-3 周）

**目标：从 cron 触发改为 Celery 定时任务，支持每用户独立调度**

| 任务 | 详情 |
|------|------|
| 4.1 Celery 引入 | 替代 GitHub Actions / Docker cron |
| 4.2 定时任务生成 | 根据用户 timeline 配置动态生成 Celery beat 调度 |
| 4.3 任务类型 | crawl_task, analyze_task, push_task |
| 4.4 任务队列 | premium（付费优先）、free（普通） |
| 4.5 频率控制 | 免费版限制爬虫频率，付费版更高频 |
| 4.6 任务监控 | 执行状态、成功率、下次执行时间 |

### 任务流

```
Celery Beat → 根据用户 timeline 触发
    ↓
crawl_task(user_id) → 爬取热榜+RSS → 存入用户数据库
    ↓
analyze_task(user_id) → AI 筛选 + AI 分析（使用系统全局 AI 配置）
    ↓
push_task(user_id) → 生成报告 → 推送到用户的通知渠道
```

### 套餐频率限制

| 套餐 | 爬虫频率 | 推送频率 |
|------|---------|---------|
| Free | 每小时 1 次 | 每日 4 次 |
| Pro | 每 10 分钟 1 次 | 每日 48 次 |
| Enterprise | 每 5 分钟 1 次 | 每日 96 次 |

---

## Phase 5: 前端管理界面（3-4 周）

**目标：构建完整的 SaaS 用户界面**

| 任务 | 详情 |
|------|------|
| 5.1 技术选型 | Vue 3 + Vite + Element Plus + TailwindCSS |
| 5.2 登录注册页 | 邮箱+密码登录，忘记密码重置，邮箱验证 |
| 5.3 仪表盘 | 今日热点新闻概览、推送统计、爬虫状态 |
| 5.4 配置管理页 | 可视化编辑 platforms、RSS、关键词、timeline、推送渠道 |
| 5.5 新闻浏览页 | 按日期/平台/关键词浏览自己的热点新闻 |
| 5.6 推送历史 | 查看历史推送记录和内容 |
| 5.7 账户设置 | 修改密码、查看套餐、升级付费 |
| 5.8 管理员后台 | 用户管理、系统 AI 配置、全局监控、用量统计 |

### 页面路由规划

```
/login                  # 登录
/register               # 注册
/forgot-password        # 忘记密码
/dashboard              # 仪表盘
/config                 # 配置管理
  /config/platforms     # 热榜平台
  /config/rss           # RSS 订阅
  /config/keywords      # 关键词
  /config/schedule      # 调度时间线
  /config/notification  # 推送渠道
/news                   # 新闻浏览
  /news/:date           # 指定日期
/push-history           # 推送历史
/account                # 账户设置
  /account/billing      # 账单管理
/admin                  # 管理员后台（仅 admin）
  /admin/users          # 用户管理
  /admin/system-config  # 系统 AI 配置
  /admin/monitoring     # 全局监控
```

---

## Phase 6: 商业化功能（2-3 周）

**目标：实现 SaaS 商业模式的核心功能**

| 任务 | 详情 |
|------|------|
| 6.1 套餐体系 | Plan 表：free/pro/enterprise |
| 6.2 支付集成 | Stripe / 支付宝 / 微信支付 |
| 6.3 配额管理 | 按套餐限制功能使用量 |
| 6.4 用量统计 | API 调用、推送次数、存储空间 |
| 6.5 订阅管理 | 自动续费、取消、升降级 |
| 6.6 邀请码/优惠码 | 推广机制 |

### 套餐设计

| 功能 | Free | Pro ($9.9/月) | Enterprise ($49/月) |
|------|------|---------------|---------------------|
| 热榜平台数 | 3 | 15 | 不限 |
| RSS 源数 | 2 | 20 | 不限 |
| 关键词组 | 5 | 不限 | 不限 |
| 推送频率 | 4次/天 | 48次/天 | 96次/天 |
| AI 分析 | ✗ | ✓ | ✓ |
| AI 翻译 | ✗ | ✓ | ✓ |
| 推送渠道 | 1个 | 3个 | 不限 |
| 数据保留 | 7天 | 30天 | 永久 |
| 优先级 | 低 | 中 | 高 |

---

## Phase 7: 安全与运维（1-2 周）

| 任务 | 详情 |
|------|------|
| 7.1 速率限制 | 登录防暴力破解、API 调用限流 |
| 7.2 数据备份 | 定时备份 PostgreSQL，支持恢复 |
| 7.3 日志系统 | 结构化日志，用户操作审计日志 |
| 7.4 监控告警 | Prometheus + Grafana |
| 7.5 HTTPS | Let's Encrypt 自动证书 |
| 7.6 Docker Compose | 一键部署完整栈 |
| 7.7 CI/CD | GitHub Actions 自动测试 + 部署 |

---

## 迁移路径（现有用户兼容）

1. **配置导入工具**：脚本将现有 config.yaml + timeline.yaml + frequency_words.txt 导入数据库
2. **数据迁移工具**：将现有 SQLite 数据迁移到 PostgreSQL，附加 user_id
3. **向后兼容**：保留 CLI 模式，CLI 用户可继续使用原有方式运行

---

## 技术栈总结

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite + Element Plus + TailwindCSS |
| 后端 API | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| 数据库 | PostgreSQL 16 |
| 缓存/队列 | Redis 7 |
| 任务调度 | Celery + Celery Beat |
| 认证 | JWT (python-jose) + bcrypt |
| 支付 | Stripe / 支付宝 SDK |
| 部署 | Docker Compose / K8s |
| 反向代理 | Nginx |

---

## 现有代码复用策略

| 现有模块 | 复用方式 |
|---------|---------|
| trendradar/crawler/ | 直接复用，增加 user_id 参数 |
| trendradar/ai/ | 直接复用，AI 配置从系统全局读取 |
| trendradar/notification/ | 直接复用，使用用户自己的推送配置 |
| trendradar/report/ | 直接复用 |
| trendradar/core/loader.py | 改造为从数据库加载配置 |
| trendradar/core/scheduler.py | 改造为 Celery beat 调度器 |
| trendradar/core/frequency.py | 直接复用 |
| trendradar/core/analyzer.py | 直接复用 |
| mcp_server/ | 改造为多租户模式，增加 user_id 过滤 |

---

## 预计总工期

| 阶段 | 工期 |
|------|------|
| Phase 1: 基础设施 | 1-2 周 |
| Phase 2: 配置管理 | 2-3 周 |
| Phase 3: 数据隔离 | 2-3 周 |
| Phase 4: 任务调度 | 2-3 周 |
| Phase 5: 前端界面 | 3-4 周 |
| Phase 6: 商业化 | 2-3 周 |
| Phase 7: 安全运维 | 1-2 周 |
| **合计** | **13-20 周** |
