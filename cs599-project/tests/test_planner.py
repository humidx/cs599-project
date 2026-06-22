from src.models import TravelProfile
from src.planner import clarification, local_plan, update_profile


def test_extracts_core_constraints():
    profile = update_profile(TravelProfile(), "两个人去杭州玩3天，预算5000元，喜欢自然和人文")
    assert profile.destination == "杭州"
    assert profile.days == 3
    assert profile.budget == 5000
    assert profile.travelers == 2
    assert set(profile.preferences) == {"自然", "人文"}
    assert profile.missing == []


def test_requests_missing_information():
    profile = update_profile(TravelProfile(), "想去成都旅游")
    message = clarification(profile)
    assert "旅行天数" not in message
    assert "计划玩几天" in message
    assert "总预算" in message


def test_budget_is_preserved():
    profile = TravelProfile(destination="杭州", days=3, budget=5000, travelers=2, preferences=["自然"])
    plan = local_plan(profile, {})
    assert "**¥5000**" in plan
    assert plan.count("### 第") == 3


def test_extracts_chinese_traveler_count():
    profile = update_profile(TravelProfile(), "十二人去北京玩五天")
    assert profile.travelers == 12


def test_accepts_budget_without_currency_unit_across_turns():
    profile = update_profile(
        TravelProfile(),
        "我一个人下周去广州及其附近旅游10天，自然风光和人文都需要考虑",
    )
    profile = update_profile(profile, "一个人 预算20000")
    assert profile.destination == "广州及其附近"
    assert profile.days == 10
    assert profile.travelers == 1
    assert profile.budget == 20000
    assert profile.missing == []
