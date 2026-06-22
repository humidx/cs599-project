# cs599-project
# 顺路旅行规划 Agent

## 项目简介

一个实验性质的旅行规划 Web Agent：通过多轮对话收集约束，结合公开地点与天气数据，生成节奏合理、预算可核算的每日行程。

## 方向

企业级应用软件的 Agent 改造

## 技术栈

- AI IDE：Codex
- LLM：OpenAI 兼容 Chat Completions API（可选，未配置时自动使用本地规则引擎）
- 框架：Python 3.9+、FastAPI、Pydantic、HTTPX
- 前端：原生 HTML / CSS / JavaScript
- 外部工具：OpenStreetMap Nominatim、Open-Meteo
- 容器：Docker（规划项）

## 目录结构

```text
.
├── docs/
│   ├── architecture.md       # 架构、Agent 流程和数据流
│   └── course-report.md      # 大作业报告源文档
├── src/
│   ├── main.py               # FastAPI 路由与应用入口
│   ├── planner.py            # 信息抽取、状态、规划 Agent 与降级逻辑
│   ├── tools.py              # 地理编码与天气工具
│   ├── models.py             # API 和旅行画像模型
│   ├── config.py             # 环境变量配置
│   └── web/index.html        # 对话网页
└── tests/                    # 约束抽取与预算测试
```

## 环境搭建

1. 安装依赖（项目要求使用 `uv`）：

   ```bash
   uv venv
   uv pip install -e '.[dev]'
   ```

2. 配置环境变量。API Key 不得写入代码；LLM 配置完全可选：

   ```bash
   cp .env.example .env
   # 编辑 .env，填写 LLM_API_KEY、LLM_BASE_URL 和 LLM_MODEL
   # 可按需设置模型请求超时，例如 LLM_TIMEOUT=30
   ```

3. 启动：

   ```bash
   uv run uvicorn src.main:app --reload
   ```

   浏览器访问 <http://127.0.0.1:8000>，接口文档位于 <http://127.0.0.1:8000/docs>。

4. 测试：

   ```bash
   uv run pytest
   ```

## 工作模式与限制

- 未配置模型时仍可完成多轮信息收集、预算拆分和行程骨架生成。
- 配置模型后，Agent 会把经过验证的用户画像和工具上下文交给模型生成具体行程。
- 第三方公开数据可能延迟或不可用；系统会降级，不会把未知票价或营业时间当作事实。
- 当前会话存于进程内存，重启后清空；生产环境应替换为 Redis 或数据库。

## 项目状态

- [x] Proposal
- [x] MVP
- [ ] Final
