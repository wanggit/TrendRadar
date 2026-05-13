# TrendRadar SaaS 技术方案

> 基于现有代码 + payment_example.py（Z-Pay 统一支付网关）

---

## 一、架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│  技术栈                                                          │
├──────────────┬──────────────────────────────────────────────────┤
│ 后端         │ FastAPI + SQLAlchemy(async) + Celery + Redis     │
│ 前端         │ Vue 3 + Element Plus + Pinia + Vue Router        │
│ 支付         │ Z-Pay 统一网关（支付宝/微信通过 type 参数区分）    │
│ 数据库       │ PostgreSQL / SQLite (Alembic 迁移)               │
│ 定时任务     │ Celery Beat                                      │
└──────────────┴──────────────────────────────────────────────────┘
```

**关键发现**：payment_example.py 使用 Z-Pay 统一支付网关，不是原生支付宝/微信 SDK。这意味着：
- 只需一个 `zpay_service.py`，不需要分别写 `alipay_service.py` + `wechat_service.py`
- 支付宝/微信通过 `type='alipay'` / `type='wxpay'` 参数区分
- 签名算法统一（MD5），回调处理统一

---

## 二、数据库设计

### 2.1 User 模型扩展（修改现有）

```python
# backend/app/models/user.py — 新增字段
trial_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
trial_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
trial_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### 2.2 Order 模型（新建）

```python
# backend/app/models/order.py
class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"

class ProductType(str, enum.Enum):
    MONTHLY = "monthly"      # 30天
    QUARTERLY = "quarterly"  # 90天
    YEARLY = "yearly"        # 365天

class PaymentMethod(str, enum.Enum):
    ALIPAY = "alipay"
    WECHAT = "wxpay"

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    trade_no: Mapped[str | None] = mapped_column(String(128), nullable=True)  # Z-Pay 订单号
    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # 订单过期时间（30分钟未支付）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=...)
    
    user = relationship("User", back_populates="orders")
```

User 模型新增反向关系：
```python
orders = relationship("Order", back_populates="user")
```

### 2.3 AuditLog 模型（新建）

```python
# backend/app/models/audit_log.py
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # login, register, change_password, etc.
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=...)
```

### 2.4 Alembic 迁移脚本

需要 3 个 migration：
1. `add_trial_fields_to_users` — trial_start_at, trial_end_at, trial_used, expire_at
2. `create_orders_table` — 全新 orders 表
3. `create_audit_logs_table` — 全新 audit_logs 表

---

## 三、后端开发清单

### Phase 1：基础功能

#### 3.1.1 试用期管理

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/app/services/trial_service.py` | **新建** | 试用逻辑：创建试用、检查到期、降级 |
| `backend/app/services/email_service.py` | **新建** | 邮件发送：验证邮件、密码重置、试用提醒 |
| `backend/app/tasks/trial_reminder.py` | **新建** | Celery 定时任务：扫描即将到期用户发邮件 |
| `backend/app/models/user.py` | **修改** | 新增 4 个字段 |
| `backend/app/api/auth.py` | **修改** | 注册时自动创建试用 + 邮箱验证 + 密码重置 |

**trial_service.py 核心逻辑**：
```python
class TrialService:
    TRIAL_DAYS = 7
    
    async def create_trial(self, user: User) -> User:
        """新用户注册时创建 7 天试用"""
        if user.trial_used:
            return user  # 已用过试用，不创建
        now = datetime.now(timezone.utc)
        user.tier = UserTier.PRO
        user.trial_start_at = now
        user.trial_end_at = now + timedelta(days=7)
        user.trial_used = True
        return user
    
    async def check_and_expire_trials(self) -> int:
        """定时任务：扫描到期用户，降级为 free"""
        # SELECT users WHERE tier='pro' AND trial_end_at <= NOW()
        # 降级 tier=free，发送通知邮件
    
    async def is_trial_active(self, user: User) -> bool:
        """检查试用是否有效"""
```

**auth.py 修改点**：
- `register` 接口：注册后调用 `trial_service.create_trial()` + 发送验证邮件
- 新增 `GET /auth/verify-email?token=xxx` — 邮箱验证
- 新增 `POST /auth/forgot-password` — 发送密码重置邮件
- 新增 `POST /auth/reset-password` — 验证 token + 重置密码

#### 3.1.2 套餐限制执行

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/app/api/config.py` | **修改** | 添加套餐限制校验中间件/装饰器 |
| `backend/app/tasks/data_cleanup.py` | **新建** | 定时任务：按 tier 清理过期数据 |
| `backend/app/celery_app.py` | **修改** | 新增 priority 队列 |
| `backend/app/tasks/analyze.py` | **修改** | Free 用户跳过 AI 分析 |

**套餐限制常量**（建议放在 `core/config.py` 或新建 `constants.py`）：
```python
TIER_LIMITS = {
    UserTier.FREE: {
        "max_platforms": 3,
        "max_keyword_groups": 5,
        "max_push_per_day": 4,
        "max_notification_channels": 1,
        "ai_enabled": False,
        "data_retention_days": 7,
        "celery_queue": "default",
    },
    UserTier.PRO: {
        "max_platforms": 15,
        "max_keyword_groups": -1,  # 无限
        "max_push_per_day": 48,
        "max_notification_channels": 3,
        "ai_enabled": True,
        "data_retention_days": 30,
        "celery_queue": "priority",
    },
}
```

**config.py 修改**：在 `update_*` 接口中加校验。以平台数量为例：
```python
@router.put("/platforms")
async def update_platforms_config(...):
    # 新增：检查用户 tier 限制
    limits = TIER_LIMITS[current_user.tier]
    if limits["max_platforms"] > 0:
        current_count = count_enabled_platforms(config)
        if current_count >= limits["max_platforms"]:
            raise HTTPException(403, f"Free 用户最多 {limits['max_platforms']} 个平台")
```

**Celery 队列修改**：
```python
# celery_app.py — 新增 priority 队列
task_queues={
    ...
    "priority": {"exchange": "priority", "routing_key": "priority"},
    "default": {"exchange": "default", "routing_key": "default"},
}
```

#### 3.1.3 前端定价页面

| 文件 | 类型 | 说明 |
|------|------|------|
| `frontend/src/views/Pricing.vue` | **新建** | 定价页面：Free vs Pro 对比 |
| `frontend/src/components/Footer.vue` | **新建** | 底部组件：隐私政策/服务条款链接 |
| `frontend/src/router/index.js` | **修改** | 新增 /pricing 路由 |

### Phase 2：支付功能

#### 3.2.1 Z-Pay 支付服务

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/app/services/payment/__init__.py` | **新建** | 包初始化 |
| `backend/app/services/payment/zpay_service.py` | **新建** | 基于 payment_example.py 改造为 FastAPI 风格 |

**关键改造点**（payment_example.py → zpay_service.py）：
- 去掉 Flask 的 `current_app`，改用 Python `logging` 模块
- 保持签名算法不变（MD5 + ASCII 排序）
- 保持 `create_order`、`verify_callback`、`query_order` 三个核心方法
- 配置项从 `Settings` 读取：`ZPAY_UID`, `ZPAY_KEY`, `ZPAY_API_URL`

```python
# backend/app/core/config.py — 新增
ZPAY_UID: str = ""
ZPAY_KEY: str = ""
ZPAY_API_URL: str = "https://zpayz.cn"
```

#### 3.2.2 支付 API

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/app/api/payment.py` | **新建** | 全部支付相关接口 |
| `backend/app/schemas/payment.py` | **新建** | Pydantic schemas |
| `backend/app/tasks/subscription_check.py` | **新建** | 定时任务：订阅到期降级 |

**payment.py 接口清单**：
```
POST   /api/v1/payment/create              # 创建订单
POST   /api/v1/payment/callback/zpay       # Z-Pay 异步回调（统一处理支付宝/微信）
GET    /api/v1/payment/orders              # 当前用户订单列表
GET    /api/v1/payment/orders/{order_id}   # 订单详情
GET    /api/v1/payment/orders/{order_id}/status  # 轮询订单状态
```

**回调处理核心逻辑**：
```python
@router.post("/callback/zpay")
async def zpay_callback(request: Request, db: AsyncSession = Depends(get_db)):
    form_data = await request.form()
    data = dict(form_data)
    
    # 1. 验证签名
    zpay = ZPayService(...)
    if not zpay.verify_callback(data):
        return PlainTextResponse("fail")
    
    # 2. 幂等处理
    order = await get_order_by_no(data["out_trade_no"])
    if order.status == OrderStatus.PAID:
        return PlainTextResponse("success")
    
    # 3. 更新订单 + 升级用户
    order.status = OrderStatus.PAID
    order.paid_at = datetime.now(timezone.utc)
    order.trade_no = data["trade_no"]
    current_user.tier = UserTier.PRO
    current_user.expire_at = calculate_expire_date(order.product_type)
    
    return PlainTextResponse("success")
```

#### 3.2.3 前端购买页面

| 文件 | 类型 | 说明 |
|------|------|------|
| `frontend/src/views/Purchase.vue` | **新建** | 购买页面：选时长 + 选支付方式 + 支付流程 |
| `frontend/src/views/Orders.vue` | **新建** | 订单历史页面 |
| `frontend/src/api/payment.js` | **新建** | 支付 API 客户端 |
| `frontend/src/router/index.js` | **修改** | 新增 /purchase, /orders 路由 |

### Phase 3：完善

#### 3.3.1 速率限制

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/app/core/rate_limiter.py` | **新建** | Redis 滑动窗口限流 |
| `backend/app/main.py` | **修改** | 注册限流中间件 |

```python
# rate_limiter.py — 核心逻辑
async def rate_limit_middleware(request: Request, call_next):
    key = f"rate_limit:{request.client.host}:{request.url.path}"
    # Redis sliding window
    # 登录接口：5次/分钟，普通API：100次/分钟
    # 超限返回 429
```

#### 3.3.2 审计日志

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/app/api/audit.py` | **新建** | 审计日志查询接口（管理员） |
| `backend/app/main.py` | **修改** | 注册 audit router |
| 各 API 文件 | **修改** | 关键操作处调用 `create_audit_log()` |

#### 3.3.3 合规页面

| 文件 | 类型 | 说明 |
|------|------|------|
| `frontend/src/views/PrivacyPolicy.vue` | **新建** | 隐私政策静态页 |
| `frontend/src/views/TermsOfService.vue` | **新建** | 服务条款静态页 |
| `frontend/src/components/Footer.vue` | **修改** | 添加链接 |
| `frontend/src/router/index.js` | **修改** | 新增路由 |

---

## 四、前端开发清单

### 4.1 需要新建的文件

| 文件 | 阶段 | 说明 |
|------|------|------|
| `frontend/src/views/Pricing.vue` | Phase 1 | 定价页 |
| `frontend/src/views/Purchase.vue` | Phase 2 | 购买页 |
| `frontend/src/views/Orders.vue` | Phase 2 | 订单历史 |
| `frontend/src/views/PrivacyPolicy.vue` | Phase 3 | 隐私政策 |
| `frontend/src/views/TermsOfService.vue` | Phase 3 | 服务条款 |
| `frontend/src/components/Footer.vue` | Phase 1 | 底部组件 |
| `frontend/src/api/payment.js` | Phase 2 | 支付 API |

### 4.2 需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `frontend/src/router/index.js` | 新增 /pricing, /purchase, /orders, /privacy-policy, /terms-of-service 路由 |
| `frontend/src/stores/auth.js` | 新增 trial 相关计算属性（trialDaysLeft, isTrialActive, isTrialExpiringSoon） |
| `frontend/src/layouts/MainLayout.vue` | Header 添加 tier 徽章 + 试用倒计时 |
| `frontend/src/views/Dashboard.vue` | 顶部添加试用倒计时 Banner + 到期引导购买 |
| `frontend/src/views/config/ConfigPlatforms.vue` | 达到限制后禁用添加按钮 |
| `frontend/src/views/config/ConfigKeywords.vue` | 达到限制后禁用添加按钮 |
| `frontend/src/views/config/ConfigNotification.vue` | 达到限制后禁用添加按钮 |

### 4.3 前端路由最终清单

```
/login                  # 登录 (已有)
/register               # 注册 (已有)
/                       # → /dashboard (已有)
/dashboard              # 仪表盘 (已有)
/config                 # 配置管理 (已有)
/news                   # 新闻浏览 (已有)
/tasks                  # 任务调度 (已有)
/task-history           # 任务历史 (已有)
/account                # 账户设置 (已有)
/users                  # 用户管理 (已有)
/pricing                # 定价页面 (新建)
/purchase               # 购买页面 (新建)
/orders                 # 订单历史 (新建)
/privacy-policy         # 隐私政策 (新建)
/terms-of-service       # 服务条款 (新建)
```

---

## 五、与 website/ 官网的对接

`website/index.html` 是静态营销页，需要修改以下链接：

| 原链接 | 新链接 | 说明 |
|--------|--------|------|
| `href="#"` (登录) | `href="/login"` | 跳转 SPA 登录页 |
| `href="#"` (注册) | `href="/register"` | 跳转 SPA 注册页 |
| `href="#"` (隐私政策) | `href="/privacy-policy"` | 跳转 SPA 隐私页 |
| `href="#"` (服务条款) | `href="/terms-of-service"` | 跳转 SPA 条款页 |

**部署注意**：官网和 SPA 需要配置 nginx 路由，使 `/login`, `/register` 等路径指向 SPA，而 `/` 默认显示官网。

---

## 六、Celery Beat 定时任务配置

```python
# 需要在 celery_app.py 或 beat 配置中添加：
beat_schedule = {
    "check-trial-expiry": {
        "task": "app.tasks.trial_reminder.check_and_expire_trials",
        "schedule": crontab(hour=0, minute=0),  # 每日0点
    },
    "send-trial-reminder": {
        "task": "app.tasks.trial_reminder.send_trial_reminders",
        "schedule": crontab(hour=9, minute=0),  # 每日9点
    },
    "cleanup-expired-data": {
        "task": "app.tasks.data_cleanup.cleanup_expired_data",
        "schedule": crontab(hour=2, minute=0),  # 每日2点
    },
    "check-subscription-expiry": {
        "task": "app.tasks.subscription_check.check_and_expire_subscriptions",
        "schedule": crontab(hour=0, minute=0),  # 每日0点
    },
}
```

---

## 七、配置项清单（环境变量）

```bash
# 新增的环境变量
ZPAY_UID=              # Z-Pay 商户 ID
ZPAY_KEY=              # Z-Pay 商户密钥
ZPAY_API_URL=https://zpayz.cn  # Z-Pay API 地址

SMTP_HOST=             # 邮件服务器
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=             # 发件人邮箱

# 已有（不需新增）
REDIS_URL=             # 已存在，用于 Celery + 速率限制
DATABASE_URL=          # 已存在
```

---

## 八、开发顺序建议

```
Phase 1（2周）
├── Week 1
│   ├── Day 1-2: User 模型扩展 + trial_service.py + auth.py 修改
│   ├── Day 3: email_service.py + trial_reminder.py
│   ├── Day 4: config.py 套餐限制 + data_cleanup.py
│   └── Day 5: celery_app.py priority 队列 + analyze.py 门控
├── Week 2
│   ├── Day 1-2: Pricing.vue + Footer.vue + 路由
│   ├── Day 3: Dashboard.vue 试用倒计时 + MainLayout tier 徽章
│   ├── Day 4: auth.js 扩展 + 3 个 Config 页面限制
│   └── Day 5: 联调测试 + 数据库迁移

Phase 2（2周）
├── Week 3
│   ├── Day 1-2: zpay_service.py + payment schemas + Order 模型
│   ├── Day 3: payment.py API（创建订单 + 回调 + 查询）
│   ├── Day 4: subscription_check.py 定时任务
│   └── Day 5: Alembic 迁移 + 后端联调
├── Week 4
│   ├── Day 1-2: Purchase.vue（完整支付流程）
│   ├── Day 3: Orders.vue（订单历史）
│   ├── Day 4: payment.js API 客户端
│   └── Day 5: 端到端测试（沙箱环境）

Phase 3（1周）
├── Day 1: rate_limiter.py + 中间件注册
├── Day 2: audit_log.py 模型 + audit.py API
├── Day 3: 关键操作处加审计日志调用
├── Day 4: PrivacyPolicy.vue + TermsOfService.vue + Footer 链接
└── Day 5: website/index.html 链接更新 + 最终验收
```

---

## 九、风险点与注意事项

1. **Z-Pay 沙箱测试**：需要确认 Z-Pay 是否提供沙箱环境，测试支付回调需要公网可达（可用 ngrok）
2. **邮件服务**：需要可用的 SMTP 服务器，开发阶段可用 Mailtrap 等测试服务
3. **Celery Beat**：需要确保 Beat 进程在 production 中运行，否则定时任务不会触发
4. **数据库迁移**：trial 字段需要 nullable=True，因为老用户没有试用数据
5. **前端路由 history 模式**：需要 nginx 配置 `try_files $uri $uri/ /index.html`，否则刷新页面 404
6. **支付回调幂等**：Z-Pay 可能多次发送同一回调，必须做幂等处理
7. **试用与付费的关系**：用户试用结束后付费购买 Pro，expire_at 应从购买日算起，不与 trial_end_at 冲突
