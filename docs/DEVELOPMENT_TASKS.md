# TrendRadar SaaS 开发任务清单

> 基于官网承诺功能，梳理现有代码已实现部分与待开发部分的差距。
> 本文档供开发 Agent 使用，按优先级分阶段实施。

---

## 项目现状

### 已完成功能（无需开发）
- 用户注册/登录（JWT + bcrypt）
- 完整配置管理（13个配置子页面）
- 热榜爬虫（11+平台）+ RSS爬虫
- AI 深度分析（5大板块）+ AI 智能筛选 + AI 翻译
- Celery 任务调度（爬取/分析/推送/翻译）
- 9种推送渠道配置（企业微信/飞书/钉钉/Telegram/邮件/ntfy/Bark/Slack/Webhook）
- 新闻数据浏览 + 任务管理 + 任务历史
- 管理员用户管理
- MCP 服务（26个工具）
- 用户模型已有 `tier` 字段（free/pro/enterprise）

### 排除项（不开发）
- Stripe 支付（仅国内市场）
- 发票管理
- 套餐升级/降级
- 企业版功能（多用户协作/API接入/定制开发）
- 用量统计页面
- 无需信用卡试用（国内不需要）

---

## Phase 1 - 基础功能（2周）

### 1.1 试用期管理

#### 1.1.1 7天免费试用逻辑
- **文件**: `backend/app/models/user.py`, `backend/app/api/auth.py`, `backend/app/services/trial_service.py`
- **需求**:
  - 新用户注册时自动设置 `tier='pro'`，记录 `trial_start_at` 和 `trial_end_at`（7天后）
  - 新增字段：`trial_start_at`, `trial_end_at`, `trial_used`（boolean）
  - 每日定时任务检查试用到期用户，自动降级为 `tier='free'`
  - 已使用过试用的用户再次注册不享受试用
- **验收标准**:
  - 新用户注册后 tier=pro，trial_end_at=7天后
  - 试用到期后自动降级为 free
  - 已用过试用的用户不再享受

#### 1.1.2 试用期倒计时显示
- **文件**: `frontend/src/views/Dashboard.vue`, `frontend/src/stores/user.js`
- **需求**:
  - 仪表盘顶部显示试用剩余天数（如"试用剩余 5 天"）
  - 到期前3天显示警告样式（橙色）
  - 到期后显示"试用已结束，请购买继续使用"
- **验收标准**: 仪表盘正确显示试用状态和倒计时

#### 1.1.3 试用到期提醒邮件
- **文件**: `backend/app/tasks/trial_reminder.py`, `backend/app/services/email_service.py`
- **需求**:
  - 每日定时任务扫描 trial_end_at 前3天和前1天的用户
  - 发送提醒邮件，包含购买链接
  - 邮件模板：试用即将到期提醒
- **验收标准**: 到期前3天和1天收到提醒邮件

#### 1.1.4 试用到期引导付费
- **文件**: `frontend/src/views/Dashboard.vue`, `frontend/src/views/Purchase.vue`
- **需求**:
  - 试用到期后，配置页面禁用编辑，显示"请购买后继续使用"
  - 仪表盘显示购买引导按钮
  - 点击引导按钮跳转到购买页面
- **验收标准**: 试用到期后无法修改配置，引导购买

---

### 1.2 套餐限制执行

#### 1.2.1 热榜平台数量限制
- **文件**: `backend/app/api/config.py`, `frontend/src/views/config/ConfigPlatforms.vue`
- **需求**:
  - Free: 最多3个平台，Pro: 最多15个
  - 后端 API 校验：添加平台时检查数量限制
  - 前端：达到限制后禁用"添加"按钮，显示提示
- **验收标准**: Free用户无法添加第4个平台

#### 1.2.2 关键词组数量限制
- **文件**: `backend/app/api/config.py`, `frontend/src/views/config/ConfigKeywords.vue`
- **需求**:
  - Free: 最多5个关键词组，Pro: 无限
  - 后端 API 校验
  - 前端：达到限制后禁用添加
- **验收标准**: Free用户无法添加第6个关键词组

#### 1.2.3 推送频率限制
- **文件**: `backend/app/celery_app.py`, `backend/app/tasks/scheduler.py`
- **需求**:
  - Free: 每日最多4次推送，Pro: 每日最多48次
  - 在推送任务执行前检查当日已推送次数
  - 超过限制则跳过执行，记录日志
- **验收标准**: Free用户每日推送不超过4次

#### 1.2.4 推送渠道数量限制
- **文件**: `backend/app/api/config.py`, `frontend/src/views/config/ConfigNotification.vue`
- **需求**:
  - Free: 最多1个渠道，Pro: 最多3个
  - 后端 API 校验
  - 前端：达到限制后禁用添加
- **验收标准**: Free用户无法配置第2个推送渠道

#### 1.2.5 AI 功能开关控制
- **文件**: `backend/app/api/config.py`, `backend/app/tasks/analyze.py`
- **需求**:
  - Free: AI分析/AI筛选/AI翻译全部禁用
  - Pro: 全部开启
  - 前端：Free用户看到AI配置项显示"专业版功能"并禁用
  - 后端：Free用户触发AI任务时返回错误
- **验收标准**: Free用户无法使用任何AI功能

#### 1.2.6 数据保留期限控制
- **文件**: `backend/app/tasks/data_cleanup.py`
- **需求**:
  - Free: 保留7天数据，Pro: 保留30天
  - 每日定时任务清理过期数据
- **验收标准**: Free用户7天前数据自动清理

#### 1.2.7 任务优先级队列
- **文件**: `backend/app/celery_app.py`
- **需求**:
  - Free: 使用 default 队列（低优先级）
  - Pro: 使用 priority 队列（高优先级）
  - Celery 配置不同队列的并发数
- **验收标准**: Pro用户任务优先执行

---

### 1.3 用户认证增强

#### 1.3.1 邮箱验证
- **文件**: `backend/app/api/auth.py`, `backend/app/services/email_service.py`
- **需求**:
  - 注册后发送验证邮件，包含验证链接（含token）
  - 新增字段：`email_verified`（默认false）
  - 验证接口：`GET /api/v1/auth/verify-email?token=xxx`
  - 未验证邮箱用户登录后提示验证
- **验收标准**: 注册后收到验证邮件，点击链接完成验证

#### 1.3.2 密码重置邮件
- **文件**: `backend/app/api/auth.py`, `backend/app/services/email_service.py`
- **需求**:
  - 忘记密码接口：`POST /api/v1/auth/forgot-password`（发送重置邮件）
  - 重置密码接口：`POST /api/v1/auth/reset-password`（验证token+新密码）
  - 重置token有效期24小时
- **验收标准**: 可通过邮件重置密码

---

### 1.4 前端定价页面

#### 1.4.1 定价页面
- **文件**: `frontend/src/views/Pricing.vue`
- **需求**:
  - 展示 Free 和 Pro 两档方案
  - Free: ¥0/月，3平台，5关键词，4次推送，1渠道，无AI
  - Pro: ¥49/月，15平台，无限关键词，48次推送，3渠道，AI全开
  - 每个方案显示功能对比列表
  - Free方案显示"当前方案"或"免费开始"按钮
  - Pro方案显示"购买"按钮（未登录跳转登录，已登录跳转购买页）
- **验收标准**: 页面正确展示两档方案和功能对比

---

## Phase 2 - 支付功能（2周）

### 2.1 支付宝支付

#### 2.1.1 支付宝 SDK 集成
- **文件**: `backend/app/services/payment/alipay_service.py`
- **需求**:
  - 集成支付宝电脑网站支付/手机网站支付
  - 配置项：APP_ID, 应用私钥, 支付宝公钥, 网关地址
  - 支持沙箱环境测试
- **验收标准**: 可生成支付宝支付链接

#### 2.1.2 支付宝订单创建
- **文件**: `backend/app/api/payment.py`
- **需求**:
  - 接口：`POST /api/v1/payment/create`
  - 参数：product_type（monthly/quarterly/yearly）, payment_method（alipay）
  - 创建订单记录，调用支付宝生成支付链接
  - 返回支付链接给前端
- **验收标准**: 调用接口返回支付宝支付链接

#### 2.1.3 支付宝回调处理
- **文件**: `backend/app/api/payment.py`
- **需求**:
  - 接口：`POST /api/v1/payment/callback/alipay`
  - 验证签名，更新订单状态
  - 支付成功后：更新用户 tier=pro，设置 expire_at
  - 幂等处理：同一订单多次回调只处理一次
- **验收标准**: 支付成功后用户自动升级为pro

---

### 2.2 微信支付

#### 2.2.1 微信支付 SDK 集成
- **文件**: `backend/app/services/payment/wechat_service.py`
- **需求**:
  - 集成微信支付 Native 支付（扫码支付）
  - 配置项：APP_ID, MCH_ID, API_KEY, 证书路径
  - 支持沙箱环境测试
- **验收标准**: 可生成微信支付二维码

#### 2.2.2 微信订单创建
- **文件**: `backend/app/api/payment.py`
- **需求**:
  - 在创建订单接口中支持 payment_method=wechat
  - 调用微信支付统一下单API
  - 返回支付二维码链接（code_url）
- **验收标准**: 调用接口返回微信支付二维码链接

#### 2.2.3 微信回调处理
- **文件**: `backend/app/api/payment.py`
- **需求**:
  - 接口：`POST /api/v1/payment/callback/wechat`
  - 验证签名，解密回调数据
  - 更新订单状态，升级用户
  - 幂等处理
- **验收标准**: 支付成功后用户自动升级为pro

---

### 2.3 订单管理

#### 2.3.1 订单模型
- **文件**: `backend/app/models/order.py`
- **需求**:
  - 字段：id, user_id, order_no, product_type, amount, payment_method, status, paid_at, expire_at, created_at
  - status: pending/paid/failed/expired
  - product_type: monthly(30天)/quarterly(90天)/yearly(365天)
- **验收标准**: 订单表结构正确

#### 2.3.2 订单查询接口
- **文件**: `backend/app/api/payment.py`
- **需求**:
  - `GET /api/v1/payment/orders` - 当前用户订单列表
  - `GET /api/v1/payment/orders/{order_id}` - 订单详情
  - `GET /api/v1/payment/orders/{order_id}/status` - 轮询订单状态（前端支付中轮询用）
- **验收标准**: 可正确查询订单状态

#### 2.3.3 到期自动降级
- **文件**: `backend/app/tasks/subscription_check.py`
- **需求**:
  - 每日定时任务检查 expire_at 到期的用户
  - 将 tier 降级为 free
  - 发送到期通知邮件
- **验收标准**: 到期后用户自动降级

---

### 2.4 前端购买页面

#### 2.4.1 购买页面
- **文件**: `frontend/src/views/Purchase.vue`
- **需求**:
  - 选择购买时长：月卡(¥49)/季卡(¥129)/年卡(¥399)
  - 选择支付方式：支付宝/微信
  - 点击支付后：
    - 支付宝：跳转支付宝支付页面
    - 微信：显示二维码，用户扫码
  - 支付中状态：轮询订单状态
  - 支付成功：跳转成功页面，提示"已升级为专业版"
  - 支付失败：显示失败原因，可重新支付
- **验收标准**: 完整的购买流程

#### 2.4.2 订单记录页面
- **文件**: `frontend/src/views/Orders.vue`
- **需求**:
  - 展示历史订单列表
  - 显示：订单号、购买时长、金额、支付方式、状态、购买时间
  - 状态标签：待支付/已支付/已失败/已过期
- **验收标准**: 正确展示订单历史

---

## Phase 3 - 完善（1周）

### 3.1 速率限制

#### 3.1.1 API 速率限制
- **文件**: `backend/app/core/rate_limiter.py`
- **需求**:
  - 登录接口：5次/分钟（防暴力破解）
  - 普通API：100次/分钟
  - 使用 Redis 实现滑动窗口限流
  - 超限返回 429 状态码
- **验收标准**: 超限请求被正确拦截

---

### 3.2 操作审计日志

#### 3.2.1 审计日志模型
- **文件**: `backend/app/models/audit_log.py`
- **需求**:
  - 字段：id, user_id, action, resource_type, resource_id, ip_address, user_agent, created_at
  - 记录关键操作：登录/注册/修改密码/修改配置/购买/支付
- **验收标准**: 关键操作有日志记录

#### 3.2.2 审计日志查询
- **文件**: `backend/app/api/audit.py`
- **需求**:
  - `GET /api/v1/audit/logs` - 管理员查看审计日志
  - 支持按用户/操作类型/时间范围筛选
- **验收标准**: 管理员可查询审计日志

---

### 3.3 隐私政策与服务条款

#### 3.3.1 隐私政策页面
- **文件**: `frontend/src/views/PrivacyPolicy.vue`
- **需求**:
  - 静态页面，说明数据收集、使用、存储政策
  - 路由：`/privacy-policy`
- **验收标准**: 页面可访问

#### 3.3.2 服务条款页面
- **文件**: `frontend/src/views/TermsOfService.vue`
- **需求**:
  - 静态页面，说明服务使用规则、免责声明
  - 路由：`/terms-of-service`
- **验收标准**: 页面可访问

#### 3.3.3 Footer 链接
- **文件**: `frontend/src/components/Footer.vue`
- **需求**:
  - Footer 添加"隐私政策"和"服务条款"链接
- **验收标准**: Footer 有正确链接

---

## 技术实现要点

### 数据库迁移
- 使用 Alembic 管理数据库迁移
- 新增字段需添加 migration script

### 配置管理
- 支付配置通过环境变量注入：
  - `ALIPAY_APP_ID`, `ALIPAY_PRIVATE_KEY`, `ALIPAY_PUBLIC_KEY`, `ALIPAY_GATEWAY`
  - `WECHAT_APP_ID`, `WECHAT_MCH_ID`, `WECHAT_API_KEY`, `WECHAT_CERT_PATH`
- 邮件配置：
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`

### 定时任务
- 使用 Celery Beat 配置定时任务：
  - `check_trial_expiry` - 每日0点检查试用到期
  - `send_trial_reminder` - 每日9点发送提醒
  - `cleanup_expired_data` - 每日2点清理过期数据
  - `check_subscription_expiry` - 每日0点检查订阅到期

### 前端路由
```
/login                  # 登录
/register               # 注册
/                       # 仪表盘
/pricing                # 定价页面
/purchase               # 购买页面
/orders                 # 订单记录
/news                   # 新闻浏览
/tasks                  # 任务管理
/tasks/history          # 任务历史
/config                 # 配置管理
/account                # 账户设置
/users                  # 用户管理（管理员）
/privacy-policy         # 隐私政策
/terms-of-service       # 服务条款
```

---

## 验收标准总览

| 模块 | 核心验收点 |
|------|-----------|
| 试用期 | 新用户自动7天Pro，到期自动降级Free |
| 套餐限制 | Free用户受限于平台数/关键词数/推送频率/渠道数/AI功能 |
| 邮箱验证 | 注册后收到验证邮件，点击完成验证 |
| 密码重置 | 可通过邮件重置密码 |
| 支付宝支付 | 可生成支付链接，回调后自动升级 |
| 微信支付 | 可生成支付二维码，回调后自动升级 |
| 订单管理 | 订单创建/查询/状态轮询正常 |
| 到期降级 | 购买到期后自动降为Free |
| 速率限制 | 超限请求返回429 |
| 审计日志 | 关键操作有日志记录 |
| 合规页面 | 隐私政策和服务条款可访问 |
