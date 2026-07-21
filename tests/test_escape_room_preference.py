from agent.parser import parse_goal
from agent.planner import plan_day
from agent.tools import search_local_merchants


def test_old_entertainment_text_routes_to_senior_safe_plan():
    goal = parse_goal("今天下午2男3女出去玩，想去室内活动，安排一下。")
    assert goal["scenario"] == "senior"
    assert "senior_friendly" in goal["preferences"]
    assert "short_walking_distance" in goal["preferences"]


def test_search_local_merchants_returns_senior_excel_activities_for_senior_plan():
    goal = parse_goal("我想带爸妈下午轻松逛逛，晚上吃点清淡的。")
    merchants = search_local_merchants(goal)
    assert merchants["senior_activities"]
    first = merchants["senior_activities"][0]
    assert first["name"]
    assert "score_features" in first
    assert "accessibility_raw" in first
    assert "transport_raw" in first
    assert "category_info" in first
    assert "accessibility_score" in first["score_features"]
    assert merchants["restaurants"] == []
    assert "friend_activities" not in merchants
    assert "couple_activities" not in merchants
    assert "family_activities" not in merchants


def test_plan_day_excludes_old_entertainment_activity():
    result = plan_day("我想带爸妈下午轻松逛逛，不想爬楼梯。")
    names = [step["name"] for step in result["best_plan"]["timeline"]]
    assert result["goal"]["scenario"] == "senior"
    assert result["best_plan"]["id"].startswith("senior_dynamic_")
    assert "澳门悬疑密室体验馆" not in names
    assert "长者" in result["best_plan"]["title"]
