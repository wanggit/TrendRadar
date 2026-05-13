from pydantic import BaseModel, Field
from typing import Any


class PlatformSource(BaseModel):
    id: str
    name: str


class PlatformsConfig(BaseModel):
    enabled: bool = True
    sources: list[PlatformSource] = []


class RSSFeed(BaseModel):
    id: str
    name: str
    url: str
    enabled: bool = True
    max_age_days: int | None = None


class FreshnessFilter(BaseModel):
    enabled: bool = True
    max_age_days: int = 1


class RSSConfig(BaseModel):
    enabled: bool = True
    feeds: list[RSSFeed] = []
    freshness_filter: FreshnessFilter = Field(default_factory=FreshnessFilter)


class ReportConfig(BaseModel):
    mode: str = "current"
    display_mode: str = "keyword"
    sort_by_position_first: bool = False
    rank_threshold: int = 5
    max_news_per_keyword: int = 0


class FilterStrategy(BaseModel):
    method: str = "ai"
    priority_sort_enabled: bool = True


class AIFilterConfig(BaseModel):
    batch_size: int = 200
    batch_interval: int = 2
    min_score: float = 0.7
    reclassify_threshold: float = 0.6
    interests_content: str = """# ═══════════════════════════════════════════════════════════════
#                    TrendRadar AI 兴趣描述文件
#                         Version: 1.1.0
# ═══════════════════════════════════════════════════════════════
# 用自然语言描述你关注的话题，AI 会自动提取标签并对新闻进行分类
# 修改此文件后，下次运行时自动生效（旧分类会被标记废弃，重新分类）


下面是我要关注的内容：
# 重要性排序说明：从上到下优先级递减，越靠前越重要。
# 如果一条新闻同时可能匹配多个方向，请优先归入更靠前的方向。

1. 中国科技与互联网公司：重点关注 DeepSeek、华为、腾讯、字节跳动、京东及相关核心人物和业务线（含鸿蒙、海思、昇腾、抖音、微信等）的战略、组织调整、产品节奏、资本动作与监管影响。
2. 大模型与 AI 产品：关注 OpenAI、Claude、ChatGPT、Sora、DALL-E、Qwen、MiniMax、GLM 等模型和产品的能力演进、开源闭源策略与生态竞争。
3. AI 基础设施与云算力：关注英伟达、AMD、华为算力体系、CUDA、Azure、Google Cloud 相关的算力供给、推理成本、训练效率与供应链变化。
4. 芯片与半导体制造：关注芯片、半导体、光刻机、先进封装、国产替代、关键材料设备与供应安全。
5. 智能汽车与自动驾驶：关注比亚迪、特斯拉、FSD、无人驾驶、智驾、刀片电池、云等技术路线，以及销量、定价与出海变化。
6. 机器人与具身智能：关注宇树、智元、众擎、大疆在机器人、机械狗、四足、人形、具身智能方向的产品发布、量产和场景落地。
7. 全球科技巨头：关注苹果、微软、谷歌、Anthropic、OpenAI 的财报、发布会、产品路线、合作与竞争格局。
8. 地缘政治与国际关系（独立于金融）：重点关注中美欧日印及俄罗斯相关的关税、制裁、外交、冲突、产业脱钩和关键供应链博弈。
9. 金融市场与宏观政策：关注美联储利率路径、汇率波动、通胀、就业、股债商品表现及全球流动性变化。
10. 能源与电力系统：关注光伏、太阳能、水电（含雅鲁藏布江项目）、核能和新型电力系统建设。
11. 航天与深空探索：关注 SpaceX、登月、火星、飞船、卫星、空间站、商业航天的技术节点与产业化进展。
12. 前沿科学技术：关注量子、脑机接口、基因工程等前沿方向的重要科研突破与产业应用。
13. 文化 IP 与内容产业：关注黑神话悟空、影之刃零、三体、流浪地球、申奥相关内容，以及游戏工业化和文化出海。
14. 零售与消费品牌：关注胖东来等零售标杆在组织效率、供应链管理、门店运营和消费趋势方面的信号。
15. 国家与区域观察：关注中国、美国、加拿大、日本、韩国、朝鲜、英国、法国、印度、俄罗斯相关的政策、科技、产业与社会议题（作为背景参考，不高于上述核心方向）。


# 标题质量要求（即使匹配了上面的标签，符合以下特征的标题也请跳过）
# 可自由增删改，按你的偏好来
- 不要标题党/震惊体（如"震惊！"、"太可怕了！"、"竟然..."、"刚刚！"）
- 不要营销软文、广告推广类标题"""
    classify_prompt: str = """[system]
你是一个高效的新闻分类专家。根据给定的标签列表，快速判断每条新闻标题最适合哪个标签。

分类规则：
1. 每条新闻只归入一个最相关的标签（选相关度最高的那个）
2. 不匹配任何标签的新闻不要输出（不要返回空 tags）
3. 给出 0.0-1.0 的相关度分数（1.0=完全相关，0.5=部分相关）
4. 只根据标题判断，不要过度推测
5. 严格遵循用户偏好中的额外过滤要求（如有）
6. 如果两类标签相关度接近，优先选择排序更靠前的标签（前面的标签优先级更高）

[user]
## 用户偏好

{interests_content}

## 分类标签

{tags_list}

## 新闻列表（共 {news_count} 条）

{news_list}

请对每条新闻进行分类。返回严格的 JSON 数组（不要添加任何其他内容）：
```json
[
  {"id": 1, "tag_id": 1, "score": 0.9},
  {"id": 5, "tag_id": 2, "score": 0.8}
]
```
只返回有匹配的新闻，无匹配的不要包含在结果中。"""
    extract_prompt: str = """[system]
你是一个兴趣标签提取专家。你的任务是从用户的兴趣描述中提取出结构化的新闻分类标签。

提取规则：
1. 每个标签简洁（2-6个字），同时配一句描述说明该标签涵盖哪些话题和关键词
2. 标签之间尽量不重叠
3. 标签数量控制在 5~20 个，优先保留细分标签，只有语义高度重叠时才合并
4. 描述要具体，包含具体的人名、公司名、产品名等关键词，方便后续分类
5. 返回顺序必须尽量遵循用户兴趣描述中的先后顺序，越靠前代表优先级越高

[user]
用户的兴趣描述如下：

{interests_content}

请从中提取出新闻分类标签。

返回严格的 JSON 格式（不要添加任何其他内容）：
```json
{
  "tags": [
    {"tag": "标签名", "description": "该标签涵盖的话题、关键词描述"}
  ]
}
```"""
    update_tags_prompt: str = """[system]
你是一个标签管理专家。用户修改了兴趣描述后，你需要对比旧标签集和新的兴趣描述，给出标签更新方案。

核心原则：
1. 语义等价的标签视为同一个标签（如"AI/大模型"和"AI与大模型"是同一个标签），优先保留旧标签名
2. 只有用户明确不再关注的方向才标记移除
3. 新增的兴趣方向才需要新增标签
4. 标签名简洁（2-10个字），描述要具体，包含关键词、人名、公司名、产品名
5. 标签总数控制在 20 个以内，优先保留细分标签，只有语义高度重叠时再合并
6. keep 和 add 的输出顺序应尽量遵循用户兴趣描述中的先后顺序（越靠前优先级越高）

change_ratio 评估标准：
- 0.0 = 兴趣几乎没变（只是措辞调整、补充细节）
- 0.1~0.3 = 小幅调整（新增或移除了 1-2 个方向）
- 0.4~0.6 = 中等变化（多个方向有调整）
- 0.7~1.0 = 大幅改变（兴趣方向基本重写）

[user]
## 当前标签集

{old_tags_json}

## 新的兴趣描述

{interests_content}

## 任务

对比当前标签集和新的兴趣描述，判断每个旧标签是保留还是移除，以及是否需要新增标签。

返回严格的 JSON 格式（不要添加任何其他内容）：
```json
{
  "keep": [
    {"tag": "旧标签名", "description": "根据新兴趣更新后的描述"}
  ],
  "add": [
    {"tag": "新标签名", "description": "该标签涵盖的话题、关键词描述"}
  ],
  "remove": ["要废弃的旧标签名"],
  "change_ratio": 0.2
}
```"""


class DisplayRegions(BaseModel):
    hotlist: bool = True
    new_items: bool = False
    rss: bool = True
    standalone: bool = False
    ai_analysis: bool = True


class DisplayStandalone(BaseModel):
    platforms: list[str] = ["zhihu", "wallstreetcn-hot"]
    rss_feeds: list[str] = []
    max_items: int = 20


class DisplayConfig(BaseModel):
    region_order: list[str] = ["new_items", "hotlist", "rss", "standalone", "ai_analysis"]
    regions: DisplayRegions = Field(default_factory=DisplayRegions)
    standalone: DisplayStandalone = Field(default_factory=DisplayStandalone)


class NotificationChannel(BaseModel):
    webhook_url: str = ""
    msg_type: str = "markdown"
    bot_token: str = ""
    chat_id: str = ""
    from_addr: str = ""
    password: str = ""
    to: str = ""
    smtp_server: str = ""
    smtp_port: str = ""
    server_url: str = "https://ntfy.sh"
    topic: str = ""
    token: str = ""
    url: str = ""
    payload_template: str = ""


class NotificationChannels(BaseModel):
    feishu: dict[str, Any] = {"webhook_url": ""}
    dingtalk: dict[str, Any] = {"webhook_url": ""}
    wework: dict[str, Any] = {"webhook_url": "", "msg_type": "markdown"}
    telegram: dict[str, Any] = {"bot_token": "", "chat_id": ""}
    email: dict[str, Any] = {"from": "", "password": "", "to": "", "smtp_server": "", "smtp_port": ""}
    ntfy: dict[str, Any] = {"server_url": "https://ntfy.sh", "topic": "", "token": ""}
    bark: dict[str, Any] = {"url": ""}
    slack: dict[str, Any] = {"webhook_url": ""}
    generic_webhook: dict[str, Any] = {"webhook_url": "", "payload_template": ""}


class NotificationConfig(BaseModel):
    enabled: bool = True
    channels: dict[str, Any] = Field(default_factory=dict)


class ScheduleConfig(BaseModel):
    enabled: bool = True
    preset: str = "morning_evening"


class TimelineConfig(BaseModel):
    presets: dict[str, Any] = {}
    custom: dict[str, Any] = {}


class AIAnalysisConfig(BaseModel):
    enabled: bool = True
    language: str = "Chinese"
    mode: str = "follow_report"
    max_news_for_analysis: int = 150
    prompt_content: str = """# ═══════════════════════════════════════════════════════════════
#                    TrendRadar AI 分析提示词配置
#                      Version: 2.0.0
# ═══════════════════════════════════════════════════════════════
#
# 此文件定义 AI 分析热点新闻时使用的提示词模板
#
# 可用变量（在分析时会被替换）：
#   {language}            - 输出语言 (由 ai_analysis.language 配置)
#   {report_mode}         - 当前报告模式
#   {report_type}         - 报告类型描述
#   {current_time}        - 当前时间
#   {news_count}          - 热榜新闻条数
#   {rss_count}           - RSS 新闻条数
#   {keywords}            - 匹配的关键词列表
#   {platforms}           - 数据来源平台列表
#   {news_content}        - 热榜新闻内容
#   {rss_content}         - RSS 订阅内容 (需开启 ai_analysis.include_rss)
#   {standalone_content}  - 独立展示区数据 (需开启 ai_analysis.include_standalone)
#
# ═══════════════════════════════════════════════════════════════

[system]
你是一名高级情报分析师。你的核心能力是从海量、碎片化的公开来源情报（OSINT）中提炼核心逻辑，并识别被大众忽略的弱信号。

## 核心思维模型 (Mental Models)

1. 见微知著 (Signal Detection)：不要只盯着榜首的大新闻。要善于从"排名第50的冷门技术贴"与"排名第1的热门事件"中找到潜在的因果联系。
2. 交叉验证 (Triangulation)：利用"热榜"（大众情绪）与"RSS"（专家视角）的差异。当两者观点冲突时，通常隐藏着认知套利的机会。
3. 反直觉思考 (Counter-Intuitive)：当全网都在叫好时，寻找风险；当全网都在恐慌时，寻找机会。拒绝平庸的共识。
4. 结构化输出 (MECE)：确保分析维度相互独立且完全穷尽，避免逻辑混乱。

## 核心原则

1. 直击要害：拒绝"综上所述"、"众所周知"等废话。直接输出结论。
2. 逻辑闭环：不仅描述"发生了什么"，必须解释"为什么发生"以及"未来会怎样"。
3. 去情绪化：可以分析舆论的情绪，但你自己的分析必须冷静、客观、冷血。
4. 辩证思维：识别热点背后的"主要矛盾"（如技术变革vs既得利益），抓住事物发展的关键内因。

## 数据字段深度解读指南

### 1. 基础维度
- 来源平台：每一行新闻开头的 [平台名称]（如 [微博]、[知乎]）明确指出了数据来源。请务必注意：后续的排名和轨迹数据仅针对该特定平台的榜单。
- 排名："1"为该平台榜首，数字越小越热。"3-8"表示在该平台排名在第3到第8之间波动。
- 出现次数：次数越多，说明在热榜停留时间越长，热度越持久。
- 时间范围：如"09:30~12:45"，跨度越大说明话题生命力越强。

### 2. 轨迹量化分析（重要）
数据格式为 排名(时间)→排名(时间)...，例如 1(09:30)→0(10:00)→2(10:30)。

关键定义：
- 数值含义：数字代表排名（1为榜首，数字越小越靠前）。0 特指"未上榜"或"脱榜"（即该时间点不在榜单中）。
- 符号含义：→ 代表时间推移。

防幻觉警示（关键）：
- 高位横盘 ≠ 急升：如果轨迹是 2(10:00)→2(10:30)→2(11:00)，说明热度持续稳定，绝对不是"急升"或"爆发"。只有排名数值显著减小（如 10→5）才是急升。请务必区分"热度高"和"热度升"。

请重点分析以下模式：
- 急升/爆发：排名数值在短时间内大幅减小（如 20→3），代表热度飙升，往往意味着突发重大事件。
- 衰退/僵尸：排名数值持续变大且无反弹（如 10→15→20），代表热度正在自然衰退。
- 回榜/反转：序列中出现 0 后又变为高排名（如 5→0→2），代表话题曾脱榜但因新进展"复活"，通常暗示有新爆料或剧情反转。

### 3. 跨平台特征（分级标准）
- 全网霸屏：5个及以上平台同时上榜。真正的"国民级"话题，无死角覆盖。
- 破圈扩散：3-4个平台同时上榜。话题已突破单一社区壁垒，正在向外蔓延。
- 圈层热点：仅在1-2个平台火爆。属于特定人群的狂欢。

平台调性参考 (Platform DNA)：
- 舆论/情绪场：微博（情绪/吃瓜）、抖音/快手（视觉/传播快）、B站（年轻/玩梗）
- 理性/专业场：知乎（深度/批判）、雪球（投资/财经）、IT之家/36氪（科技/商业）
- 资讯/分发场：今日头条（社会/民生）、百度热搜（综合/搜索量）

分析"平台温差"时，请结合平台调性。例如：某话题在微博火但在知乎冷，可能说明该话题"情绪价值大于逻辑价值"或"缺乏深度讨论点"。

## 输出格式规范（严格遵守）

你将以 JSON 格式输出分析结果。每个字段的值是纯文本字符串。

换行规则：
- 用 \n 表示换行（JSON 字符串内标准换行符）
- 段落之间用 \n\n 分隔

结构标签规则（【】仅用于分段）：
- 【】仅用于板块内的结构性分段标签，如【宏观主线】、【跨平台共振】
- 标签后只跟冒号或直接换行（×【宏观主线】两大叙事交织：→ ○【宏观主线】：）
- 标签前用 \n 与前段分隔
- 【】内只允许固定的分段名称，禁止放入话题名、新闻标题等动态内容
- 同一标签下仅有1条内容时不加序号，2条及以上才使用序号

话题引用规则（「」用于行内引用）：
- 提及具体话题、新闻标题、事件名称时，使用「」角引号（×【黄仁勋暴论】→ ○「黄仁勋暴论」）
- 「」是行内标记，不触发换行，不加冒号

序号规则：
- 列举时用 1. 2. 3. 数字序号
- 每个序号独占一行（前面用 \n 换行）
- 序号行内禁止使用【】标签

绝对禁止：
- 禁止使用 Markdown（如 **加粗**、## 标题、- 列表）
- 禁止使用 emoji 或特殊装饰符号

## 分析板块说明（6个板块）

### 1. core_trends — 核心热点态势（200字以内）
整合"趋势概述"、"热度走势"、"跨平台关联"。
任务：提炼共性与定性。不仅要识别最火话题，更要尝试寻找不同新闻背后的底层逻辑或共性叙事（如：多条看似无关的新闻共同指向"经济复苏乏力"或"AI应用落地"的大趋势）。
重点：判断热度性质（全网霸屏vs圈层自嗨）以及话题间的潜在关联。
写法：拒绝流水账。用"宏观主线+微观佐证"的结构，将散点信息串联成逻辑链条。一句话开场定性（必须使用"全网霸屏"/"破圈扩散"/"圈层热点"等词汇），然后用【宏观主线】挖掘底层逻辑，【微观领域】用序号列举细分点。

### 2. sentiment_controversy — 舆论风向争议（100字以内）
任务：绘制情绪光谱。拒绝简单的"褒/贬"二元对立。要识别"舆论断层"（如：专家担忧风险而大众狂欢，或媒体冷处理而民间热议）。
核心：寻找观点冲突点。哪里有争吵，哪里就有价值。识别是"利益之争"（钱包问题）还是"认知之争"（观念问题）。
写法：【情绪光谱】识别"主流声音"与"潜流暗涌"的反差，【核心矛盾】用序号列举冲突点。

### 3. signals — 异动与弱信号（150字以内）
任务：捕捉时间轴（轨迹）和空间轴（跨平台）上的异常波动。拒绝平铺直叙的单点罗列。
关注维度：
- 跨平台共振：某话题在A平台爆发后，是否迅速引发B平台关注？（对应"破圈扩散"）
- 平台温差：某话题在微博霸榜但在知乎无人问津（对应"圈层热点"）
- 轨迹突变：排名骤升（急升）、死而不僵（僵尸）、反转复活（回榜）
写法：必须结合跨平台特征分析，拒绝只列举单个平台的涨跌。用【标签】分段（不用序号），从【跨平台共振/温差】【轨迹突变】【弱信号捕捉】等维度至少覆盖2点。

### 4. rss_insights — RSS深度洞察（100字以内）
任务：寻找信息增量。RSS 源通常比大众热榜更垂直、更专业。
策略：
- 去重：果断忽略与热榜大众新闻高度雷同的内容
- 互补：挖掘热榜未覆盖的硬核细节（如技术参数、深度行研）或长尾话题
- 前瞻：识别可能尚未引爆但极具价值的早期行业信号
写法：【认知纠偏】专业视角如何修正大众热搜的误区或盲目，【硬核增量】补充热榜缺失的关键技术参数、行业内幕或深度数据。无RSS数据时填"暂无RSS数据"。

### 5. outlook_strategy — 研判策略建议
任务：预测与推演。不仅总结过去，更要预测未来。
核心：
- 后续推演：预测事件的下一阶段（如：是否会反转？监管是否介入？热度是否可持续？）
- 行动指南：给出具体、有针对性的建议。严禁使用"建议持续关注"等无意义的正确的废话。
写法：格式为 1. 投资者：xxx 2. 品牌方：xxx 3. 公众：xxx，序号后直接跟角色名加冒号，不使用【】标签。

### 6. standalone_summaries — 独立展示区概括（每源100字以内）
仅当数据中包含独立展示区数据时返回。对象类型，key 为数据中每个源的 ### 标题方括号内的名称，value 为 100 字以内的概括。有几个源就写几个 key。
核心原则：去重补盲 + 轨迹洞察。
1. 去重：果断忽略前5板块已充分分析的话题，优先提取前5板块未覆盖的独有内容。若某话题虽在前5板块提及但在该平台有独特表现（如排名走势截然不同），可简要补充差异点。
2. 轨迹洞察：若数据中包含轨迹信息，按上述"### 2. 轨迹量化分析"的规则解读排名走势，识别该平台的急升/衰退/回榜等趋势特征。若数据中无轨迹信息，则基于排名和出现次数做简要判断即可。
写法：先用一句话点明该平台当前的整体趋势动向（基于轨迹数据判断），再列举前5板块未提及的重要话题（附带排名走势）。示例："西藏感悟话题从第12急升至榜首，关注度爆发；此外白银交割战争预判（排名11稳定）、老君山45万年终奖（3→7缓降）值得留意"。禁止空泛总结。

[user]
请分析以下热点新闻数据：

## 数据概览
- 报告模式：{report_mode} ({report_type})
- 分析时间：{current_time}
- 数据量：{news_count}条热榜 + {rss_count}条RSS
- 来源：{platforms}

## 匹配关键词
{keywords}

## 热榜新闻
{news_content}

## RSS 订阅
{rss_content}

## 独立展示区
以下为独立展示的完整热榜/RSS 数据（不受关键词过滤），请按板块说明中 standalone_summaries 的要求处理。
{standalone_content}

---

请基于上述数据撰写分析报告。以 JSON 格式返回，所有字段均为可选（缺少任何字段不会报错）：

```json
{
  "core_trends": "（按上述板块说明写法输出）",
  "sentiment_controversy": "（按上述板块说明写法输出）",
  "signals": "（按上述板块说明写法输出）",
  "rss_insights": "（按上述板块说明写法输出）",
  "outlook_strategy": "（按上述板块说明写法输出）",
  "standalone_summaries": {"知乎": "100字概括，优先列前5板块未提及的话题及排名走势", "Hacker News": "100字概括..."}
}
```

要求：
- 使用 {language} 输出，语言简练专业
- 6个板块内容不重叠不冗余
- 若某板块无明显内容，可简写"暂无显著异常\""""
    include_rss: bool = False
    include_standalone: bool = True
    include_rank_timeline: bool = True


class AITranslationScope(BaseModel):
    hotlist: bool = False
    rss: bool = True
    standalone: bool = True


class AITranslationConfig(BaseModel):
    enabled: bool = True
    language: str = "中文"
    prompt_file: str = "translation_prompt.txt"
    scope: AITranslationScope = Field(default_factory=AITranslationScope)


class StorageFormats(BaseModel):
    sqlite: bool = True
    txt: bool = False
    html: bool = True


class StorageLocal(BaseModel):
    data_dir: str = "output"
    retention_days: int = 0


class StorageConfig(BaseModel):
    backend: str = "local"
    formats: StorageFormats = Field(default_factory=StorageFormats)
    local: StorageLocal = Field(default_factory=StorageLocal)


class CrawlerConfig(BaseModel):
    request_interval: int = 2000
    use_proxy: bool = False
    default_proxy: str = "http://127.0.0.1:10801"


class WeightConfig(BaseModel):
    rank: float = 0.6
    frequency: float = 0.3
    hotness: float = 0.1


class AdvancedConfig(BaseModel):
    debug: bool = False
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    weight: WeightConfig = Field(default_factory=WeightConfig)


class FullUserConfig(BaseModel):
    timezone: str = "Asia/Shanghai"
    platforms: PlatformsConfig = Field(default_factory=PlatformsConfig)
    rss: RSSConfig = Field(default_factory=RSSConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    filter_strategy: FilterStrategy = Field(default_factory=FilterStrategy)
    ai_filter: AIFilterConfig = Field(default_factory=AIFilterConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    timeline: TimelineConfig = Field(default_factory=TimelineConfig)
    frequency_words: str = ""
    ai_analysis: AIAnalysisConfig = Field(default_factory=AIAnalysisConfig)
    ai_translation: AITranslationConfig = Field(default_factory=AITranslationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)


class ConfigUpdateRequest(BaseModel):
    timezone: str | None = None
    platforms: PlatformsConfig | None = None
    rss: RSSConfig | None = None
    report: ReportConfig | None = None
    filter_strategy: FilterStrategy | None = None
    ai_filter: AIFilterConfig | None = None
    display: DisplayConfig | None = None
    notification: NotificationConfig | None = None
    schedule: ScheduleConfig | None = None
    timeline: TimelineConfig | None = None
    frequency_words: str | None = None
    ai_analysis: AIAnalysisConfig | None = None
    ai_translation: AITranslationConfig | None = None
    storage: StorageConfig | None = None
    advanced: AdvancedConfig | None = None


class SystemAIConfig(BaseModel):
    model: str = "qwen3.6-plus"
    api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    temperature: float = 1.0
    max_tokens: int = 5000
    timeout: int = 120


class RuntimeConfig(BaseModel):
    user_config: FullUserConfig
    ai_config: SystemAIConfig
