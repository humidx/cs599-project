from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date

import httpx

from src.config import settings
from src.models import TravelProfile
from src.tools import enrich_destination

logger = logging.getLogger(__name__)


PREFERENCE_WORDS = {
    "自然": ["自然", "山", "海", "户外", "风景", "徒步"],
    "人文": ["人文", "历史", "古迹", "老街"],
    "艺术": ["艺术", "博物馆", "美术馆"],
    "美食": ["美食", "吃", "餐厅", "小吃"],
    "亲子": ["亲子", "孩子", "儿童"],
    "购物": ["购物", "买买买", "商场"],
}

CHINESE_NUMBERS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def _parse_small_number(value: str) -> int:
    if value.isdigit():
        return int(value)
    if value in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[value]
    if value.startswith("十"):
        return 10 + CHINESE_NUMBERS.get(value[1:], 0)
    if value.endswith("十"):
        return CHINESE_NUMBERS.get(value[0], 0) * 10
    tens, ones = value.split("十", 1)
    return CHINESE_NUMBERS.get(tens, 0) * 10 + CHINESE_NUMBERS.get(ones, 0)


def update_profile(profile: TravelProfile, text: str) -> TravelProfile:
    data = profile.model_dump()
    destination_patterns = [
        r"(?:去|到|目的地(?:是|为)?|想去)\s*([\u4e00-\u9fa5A-Za-z·]+?)(?=旅游|旅行|玩|，|,|。|\s|$)",
        r"([\u4e00-\u9fa5A-Za-z·]{2,12})\s*(?:[旅游玩]|自由行)",
    ]
    for pattern in destination_patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            if candidate not in {"我想", "计划", "准备"}:
                data["destination"] = candidate
                break

    match = re.search(r"(\d{1,2})\s*(?:天|日)", text)
    if match:
        data["days"] = min(int(match.group(1)), 30)

    match = re.search(
        r"(?:预算|总预算|总共|控制在)\s*(?:为|是|约|大约|大概)?\s*(\d+(?:\.\d+)?)\s*(万|千|元|块)?",
        text,
    )
    if not match:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(万|千|元|块)", text)
    if match:
        amount = float(match.group(1))
        unit = match.group(2) or "元"
        data["budget"] = amount * {"万": 10000, "千": 1000, "元": 1, "块": 1}[unit]

    match = re.search(r"(\d{1,2}|[一二两三四五六七八九十]{1,3})\s*(?:个人|人|位)", text)
    if match:
        data["travelers"] = min(_parse_small_number(match.group(1)), 20)

    found = set(data.get("preferences", []))
    for label, words in PREFERENCE_WORDS.items():
        if any(word in text for word in words):
            found.add(label)
    data["preferences"] = sorted(found)

    match = re.search(r"(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})", text)
    if match:
        try:
            data["start_date"] = date(*map(int, match.groups()))
        except ValueError:
            pass
    return TravelProfile.model_validate(data)


def clarification(profile: TravelProfile) -> str:
    questions = {
        "目的地": "想去哪个城市或地区？",
        "旅行天数": "计划玩几天？",
        "总预算": "总预算大约多少元（包含几位出行者）？",
        "兴趣偏好": "更偏好自然风光、人文历史、艺术、美食、亲子还是购物？",
    }
    missing = profile.missing
    known = []
    if profile.destination:
        known.append(f"目的地 {profile.destination}")
    if profile.days:
        known.append(f"{profile.days} 天")
    prefix = f"已记录：{'、'.join(known)}。" if known else ""
    return prefix + "为避免行程失真，还需要确认：" + " ".join(questions[item] for item in missing)


def _weather_summary(context: dict) -> str:
    daily = context.get("weather", {})
    highs, lows, rain = daily.get("temperature_2m_max", []), daily.get("temperature_2m_min", []), daily.get("precipitation_probability_max", [])
    if not highs or not lows:
        return "出发前 3 天再次查看天气预报。"
    rain_max = max(rain) if rain else 0
    return f"近期预报约 {min(lows):.0f}–{max(highs):.0f}℃，最高降雨概率 {rain_max}%；按天气准备雨具和分层衣物。"


def local_plan(profile: TravelProfile, context: dict) -> str:
    days = profile.days or 1
    people = profile.travelers
    total = profile.budget or 0
    per_day = total / days
    accommodation = round(total * 0.35)
    food = round(total * 0.25)
    transport = round(total * 0.20)
    tickets = round(total * 0.15)
    reserve = round(total - accommodation - food - transport - tickets)
    themes = profile.preferences or ["城市漫游"]
    blocks = []
    for index in range(days):
        theme = themes[index % len(themes)]
        blocks.append(
            f"### 第 {index + 1} 天｜{theme}主题·同一区域慢游\n"
            f"- 08:00–09:00：酒店附近早餐（约 ¥{max(20, round(per_day * .05))}）\n"
            "- 09:30–12:00：区域核心景点 A；公共交通 20–40 分钟，预留完整参观时间\n"
            f"- 12:00–13:30：当地特色午餐（约 ¥{max(40, round(per_day * .10))}）\n"
            "- 14:00–17:00：相邻景点 B + 街区漫步；步行或地铁 10–25 分钟\n"
            f"- 17:30–19:00：晚餐与休息（约 ¥{max(50, round(per_day * .12))}）\n"
            "- 19:00–20:30：可选夜景/夜市；体力不足可直接返回酒店\n"
            "- 住宿：优先选择地铁换乘站 800 米内、评分较稳定的酒店，减少次日折返"
        )
    warning = "" if per_day >= 350 * people else "\n> 预算偏紧：建议选择青旅/经济型酒店、减少付费景点，市内以公交地铁为主。"
    return f"""## {profile.destination} {days} 日旅行方案

> 这是离线规则引擎生成的可执行骨架。具体景点名称、营业状态和票价需联网或配置模型后核验。{warning}

**行程原则**：每天 2 个核心景点 + 1 个可选夜间活动；按相邻区域聚类，午后保留休息弹性。

{chr(10).join(blocks)}

## 预算预估（{people} 人合计）

| 类别 | 金额 |
|---|---:|
| 住宿 | ¥{accommodation} |
| 餐饮 | ¥{food} |
| 市内/往返交通预留 | ¥{transport} |
| 门票与体验 | ¥{tickets} |
| 机动金 | ¥{reserve} |
| **总计** | **¥{round(total)}** |

## 出行贴士与避坑指南

1. {_weather_summary(context)}
2. 热门景点只通过官方公众号、官网或正规票务平台预约；拒绝无资质的“快速通道”。
3. 打车使用正规平台并核对车牌；餐厅点餐前确认时价、计价单位和服务费。
4. 行程涉及宗教场所或传统街区时，遵守着装、摄影和安静参观要求。
5. 每天留出约 10% 预算与 1 小时时间缓冲，避免因排队或天气被迫赶路。
"""


SYSTEM_PROMPT = """你是严谨的旅行规划 Agent。请基于用户画像和实时工具上下文输出中文 Markdown 行程。
要求：每天最多3-4个景点，按地理相邻区域安排；列出具体时间、景点、交通方式与耗时、餐饮、住宿；
严格遵守总预算并用表格分项汇总；明确实时信息的查询日期与待核验项；最后给风俗、天气穿搭、预约和防坑提示。
不得虚构工具上下文中没有的实时票价或营业状态。"""


async def llm_plan(profile: TravelProfile, context: dict):
    if not settings.llm_api_key:
        return None
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"profile": profile.model_dump(mode="json"), "tool_context": context}, ensure_ascii=False)},
        ],
        "temperature": 0.3,
        "max_tokens": 6000,
        "stream": True,
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    try:
        timeout = httpx.Timeout(settings.llm_timeout)
        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        event = json.loads(data)
                        delta = event["choices"][0].get("delta", {})
                        if delta.get("content"):
                            chunks.append(delta["content"])
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        logger.debug("Ignored malformed LLM stream event")
        content = "".join(chunks).strip()
        if not content:
            logger.warning("LLM returned an empty response")
            return None
        return content
    except httpx.HTTPStatusError as exc:
        logger.error("LLM API returned HTTP %s: %s", exc.response.status_code, exc.response.text[:500])
        return None
    except httpx.TimeoutException:
        logger.error("LLM request timed out after %.0f seconds", settings.llm_timeout)
        return None
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.error("LLM request failed: %s", exc)
        return None


@dataclass
class PlannerAgent:
    profiles: dict[str, TravelProfile] = field(default_factory=dict)

    async def respond(self, session_id: str, message: str) -> tuple[str, str, TravelProfile, list[str]]:
        profile = update_profile(self.profiles.get(session_id, TravelProfile()), message)
        self.profiles[session_id] = profile
        if profile.missing:
            return clarification(profile), "collecting", profile, []
        context, sources = await enrich_destination(profile.destination or "")
        plan = await llm_plan(profile, context) or local_plan(profile, context)
        return plan, "complete", profile, sources
