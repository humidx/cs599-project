# 系统架构说明

## 总体架构

```mermaid
flowchart LR
    U[用户] --> W[Web 对话界面]
    W --> A[FastAPI /api/chat]
    A --> O[PlannerAgent 编排器]
    O --> S[会话画像状态]
    O --> T[工具层]
    T --> N[Nominatim 地理编码]
    T --> M[Open-Meteo 天气]
    O --> L{LLM 已配置?}
    L -- 是 --> C[OpenAI 兼容模型]
    L -- 否或失败 --> R[本地规则规划器]
    C --> V[Markdown 行程]
    R --> V
    V --> W
```

## Agent 交互流程

```mermaid
sequenceDiagram
    actor User as 用户
    participant API as Web/API
    participant Agent as PlannerAgent
    participant Tool as 地点/天气工具
    participant Model as LLM/规则引擎
    User->>API: 自然语言旅行要求
    API->>Agent: message + session_id
    Agent->>Agent: 抽取并合并 TravelProfile
    alt 核心字段缺失
        Agent-->>User: 针对缺失字段追问
    else 核心字段完整
        Agent->>Tool: 查询目的地坐标和天气
        Tool-->>Agent: 可验证上下文/失败降级
        Agent->>Model: 画像 + 工具结果 + 规划约束
        Model-->>Agent: 每日行程与预算
        Agent-->>User: Markdown 结果 + 来源
    end
```

## 数据模型

核心状态 `TravelProfile` 包含目的地、天数、预算、人数、偏好、出发地和日期。服务端只按 `session_id` 保存结构化画像，不依赖完整对话历史，从而降低提示词长度并减少旧信息干扰。

## 关键设计决定

- 先结构化、后规划：缺少目的地、天数、预算或偏好时不生成伪精确行程。
- 工具失败可降级：网络服务或模型失败时，返回明确标注的规则化行程骨架。
- 预算守恒：分项预算由总预算按固定比例拆分，尾差进入机动金。
- 实时事实有边界：模型只能把工具结果作为实时依据，未知营业状态与票价必须提示复核。
- API Key 仅从环境变量读取，`.env` 被 Git 忽略。

## API Spec

### `POST /api/chat`

请求：

```json
{"message": "两人去杭州3天，预算5000元，喜欢自然和人文", "session_id": null}
```

响应包含 `session_id`、`reply`、状态 `collecting|complete`、结构化 `profile` 和 `sources`。

### `GET /api/health`

返回服务健康状态与当前规划器模式 `local|llm`。

