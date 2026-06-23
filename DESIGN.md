# US Government — Public Company Monitoring System

## 项目目标

构建一个全栈监控系统，持续追踪美国政府与上市公司之间的资本/资金关联，并通过 Web 面板呈现：

1. 联邦政府直接持股 / 救助股权
2. 美国政府合同 / 拨款流向上市公司
3. 美国国会议员与联邦高官的股票交易
4. 外国政府主体在美国上市公司的持股
5. 数据新鲜度与质量监控（Data Monitor、Pipeline Monitor）
6. 跨渠道投资组合分析（Portfolio Analysis）与自动文字总结

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 API | FastAPI + Pydantic |
| ORM / 模型 | SQLModel (SQLAlchemy 2.x) |
| 数据库 | PostgreSQL（开发期可用 SQLite 过渡） |
| 任务调度 | APScheduler |
| 前端 | React + Vite + Tailwind CSS + Recharts |
| 部署 | Docker Compose |
| 原始数据存储 | PostgreSQL JSONB |

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (React/Next.js)                │
│   Dashboard │ 搜索 │ 时间线 │ 告警配置 │ 数据明细 │ 图表 │ Pipeline │ Portfolio │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST/WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                     FastAPI 后端服务                          │
│  /api/v1/contracts  /api/v1/trades  /api/v1/stakes          │
│  /api/v1/foreign-holdings  /api/v1/alerts  /api/v1/metrics   │
│  /api/v1/dashboard/*  /api/v1/portfolio/*                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   PostgreSQL         Redis(可选)        文件/对象存储
   (结构化数据)      (缓存/任务队列)     (原始 PDF/HTML)
        ▲                  ▲
        └──────────────────┘
                   APScheduler / Celery Beat
                   定时拉取 + 增量解析 + 告警触发
```

## 目录结构

```
.
├── DESIGN.md                 # 本设计文档
├── README.md                 # 项目说明与启动指南
├── docker-compose.yml        # 一键启动
├── .env.example              # 环境变量模板
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py           # FastAPI 入口
│       ├── config.py         # 配置与环境变量
│       ├── database.py       # 数据库连接与 session
│       ├── models/           # SQLModel 数据模型
│       ├── fetchers/         # 外部数据源拉取器
│       ├── parsers/          # 原始数据解析器
│       ├── mappers/          # 公司名/CIK/DUNS → ticker 映射
│       ├── jobs/             # 定时任务与调度器
│       └── api/              # API 路由
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── components/
        └── pages/
```

## 数据模型（核心）

### 统一事件表 Event

所有四类信息最终都归一化为 `Event`，便于全局时间线、搜索、告警。

```python
class Event(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    event_type: str          # contract / trade / stake / foreign_holding
    source: str              # usaspending / house / senate / treasury / edgar
    source_id: str | None    # 源系统原始 ID
    occurred_at: date | None
    ticker: str | None
    company_name: str | None
    government_party: str | None   # 部门 / 官员 / 外国政府主体
    amount: float | None
    currency: str = "USD"
    description: str | None
    url: str | None
    raw_data: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 明细表

每类事件有自己的明细表，通过 `event_id` 与 `Event` 一对一关联。

- `ContractDetail`：合同/拨款明细（agency、award_type、award_id、UEI/DUNS 等）
- `OfficialTradeDetail`：官员交易明细（official_name、chamber、transaction_type、amount_min/max 等）
- `GovernmentStakeDetail`：政府持股明细（government_entity、stake_type、share_percent 等）
- `ForeignHoldingDetail`：外国政府持仓明细（filer_name、shares、value、period 等）

## 四类监控模块

### P0 — 政府合同 / 拨款流向上市公司

- **数据源**：USASpending.gov API / 月度全量 CSV
- **API 入口**：`https://api.usaspending.gov/api/v2/search/spending_by_award/`
- **更新频率**：每日增量
- **关键字段**：recipient_name、UEI、DUNS、award_amount、awarding_agency、period_of_performance_start_date
- **核心挑战**：子公司/UEI 聚合到母公司并映射 ticker

### P1 — 国会议员 / 高官股票交易

- **数据源**：
  - Kadoa Congress Trading Monitor（GitHub JSON，聚合 House + Senate + OGE）
  - Senate Stock Watcher 历史镜像（fallback）
- **更新频率**：每日
- **关键字段**：official_name、ticker、transaction_date、filing_date、transaction_type、amount_range_low/high
- **核心挑战**：披露文件为扫描件/OCR 需清洗；上游数据集存在 1-5 天延迟
- **网络注意**：macOS / Docker Desktop 环境下容器出站 TLS 可能失败，已通过 `scripts/host_connect_proxy.py` + `HTTPS_PROXY` 方案解决

### P2 — 联邦政府直接持股 / 救助

- **数据源**：
  - Treasury.gov Press Releases / RSS
  - Federal Reserve H.4.1 周度报告
  - GAO 报告
  - EDGAR 8-K（关键词：U.S. Treasury、government investment、bailout、warrant）
- **更新频率**：事件驱动 / 每日扫描
- **核心挑战**：非结构化文本，需要 NLP/关键词 + 人工审核

### P3 — 外国政府在美上市公司持股

- **数据源**：SEC EDGAR 13F / 13D / 13G filings
- **更新频率**：季度
- **关键字段**：filer_name（识别主权财富基金）、shares、value、ticker/CUSIP
- **核心挑战**：主权基金实体识别、CUSIP → ticker 映射

## 监控与投资分析

### Data Monitor

- **接口**：`GET /api/v1/dashboard/monitor`
- **内容**：按 `event_type` 统计最新事件发生时间、事件总数、金额缺失率、ticker 缺失率、重复 `source_id` 数量、综合健康分
- **前端**：Data Monitor 标签页，展示 freshness cards、quality bars、missing-rate charts

### Pipeline Monitor

- **接口**：`GET /api/v1/dashboard/pipelines`
- **内容**：读取 APScheduler 任务，返回每个 pipeline 的 schedule、next_run_at、最后摄入时间、事件数、健康状态（healthy / stale / idle / info）
- **前端**：Pipeline Monitor 标签页，卡片展示任务状态

### Portfolio Analysis

- **接口**：
  - `GET /api/v1/portfolio/snapshot` — 全量跨渠道敞口快照
  - `GET /api/v1/portfolio/changes?days=7` — 近期变化
- **计算逻辑**：
  - Contracts / Stakes / Foreign Holdings 按正金额计入敞口
  - Trades 按交易方向折算：purchase +，sale -，exchange/other 0
  - 按 ticker 聚合 total exposure、各渠道贡献、事件数
- **前端**：Portfolio Analysis 标签页，包含汇总卡、Executive Summary、渠道敞口饼图、Top 10 Tickers、30 日活动趋势、近期 Gainers/Losers、最新事件表

## 通用服务

### Company Mapping 服务

```python
class CompanyMapping(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    canonical_name: str
    ticker: str | None
    cik: str | None
    cusip: str | None
    uei: str | None
    duns: str | None
    aliases: list[str] = Field(default_factory=list, sa_column=Column(JSONB))
    source: str
    confidence: str  # high / medium / low / manual
```

映射优先级：
1. 精确 ticker/CIK/CUSIP 匹配
2. SEC CIK↔Ticker 映射文件
3. OpenFIGI / CUSIP 服务
4. 模糊名称匹配 + 人工兜底

### Alert 服务

```python
class AlertRule(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    event_type: str | None      # 为空则匹配全部
    ticker: str | None
    government_party: str | None
    amount_threshold: float | None
    enabled: bool = True

class AlertHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    rule_id: int = Field(foreign_key="alertrule.id")
    event_id: int = Field(foreign_key="event.id")
    triggered_at: datetime
    notified: bool = False
```

触发方式：
- 新记录落入规则范围
- 某 ticker 在统计周期内金额突增（如周环比 > 100%）
- 多名官员同时交易同一 ticker

## 实施路线图

### Phase 0：项目骨架
- [x] 创建项目目录
- [x] FastAPI 入口、配置、数据库连接
- [x] Docker Compose（FastAPI + PostgreSQL）
- [x] React + Vite 前端壳
- [x] 统一事件模型基类

### Phase 1：政府合同监控（USASpending）
- [x] USASpending fetcher
- [x] 合同解析器
- [x] 公司 → ticker 映射服务初版
- [x] `/api/v1/contracts` 路由
- [x] 前端合同列表与筛选面板
- [x] 每日增量同步任务

### Phase 2：议员/高官交易监控
- [x] House / Senate / Kadoa 数据源 fetcher
- [x] 交易解析与清洗
- [x] `/api/v1/trades` 路由
- [x] 官员交易时间线页面

### Phase 3：联邦直接持股/救助
- [x] SEC EDGAR 8-K 关键词搜索
- [x] 事件抽取（关键词/正则 + 置信度）
- [x] `/api/v1/stakes` 路由与前端面板

### Phase 4：外国政府在美持股
- [x] SEC EDGAR 13F/13D/13G 下载解析
- [x] 主权财富基金实体识别表
- [x] 持仓变化对比 / 前端 Foreign Government Holdings 面板

### Phase 5：数据质量、Pipeline 与投资分析
- [x] Data Monitor：新鲜度、质量、健康分
- [x] Pipeline Monitor：调度任务状态与摄入时间
- [x] Portfolio Analysis：跨渠道敞口、近期变化、自动文字总结

## 关键难点与策略

| 难点 | 策略 |
|---|---|
| 公司名 → ticker | SEC CIK-Ticker 映射 + OpenFIGI + 人工别名表 |
| 子公司聚合 | UEI/DUNS → ultimate parent |
| 非结构化公告 | LLM NER 抽取 + 人工确认队列 |
| EDGAR 限速 | User-Agent、指数退避、缓存 |
| 告警疲劳 | 规则可按 ticker/机构/金额/官员白名单配置 |

## 安全与合规

- SEC EDGAR 请求遵守 [公平访问政策](https://www.sec.gov/os/webmaster-faq)
- USASpending API 遵守调用频率限制
- 不存储个人隐私信息，官员交易数据来自公开披露
- 生产环境使用 `.env` 管理密钥，不提交敏感配置

## 未来扩展

- 接入 WebSocket 实现实时告警推送
- 引入 Airflow 替代 APScheduler 管理复杂依赖
- 增加用户认证与订阅管理
- 接入 n8n/Zapier 做外部通知
- 增加数据质量评分与置信度展示
