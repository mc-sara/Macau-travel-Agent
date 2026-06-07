from agent.parser import parse_goal
from agent.planner import plan_day
from agent.tools import search_local_merchants


def test_parser_keeps_escape_room_preference_from_user_text():
    goal = parse_goal("今天下午2男3女出去玩，想去密室，安排一下。")

    structured = goal["structured_goal"]
    assert "escape_room" in structured["soft_preferences"]
    assert "escape_room" in goal["preferences"]


def test_search_local_merchants_returns_escape_room_for_preference():
    goal = parse_goal("今天下午2男3女出去玩，想去密室，安排一下。")

    merchants = search_local_merchants(goal)

    names = [item["name"] for item in merchants["friend_activities"]]
    assert "澳门悬疑密室体验馆" in names


def test_plan_day_includes_escape_room_when_requested():
    result = plan_day("今天下午2男3女出去玩，想去密室，安排一下。")

    names = [step["name"] for step in result["best_plan"]["timeline"]]

    assert "澳门悬疑密室体验馆" in names
    assert "密室" in "、".join(result["best_plan"]["score"]["reasons"])


def test_plan_day_defaults_to_escape_room_activity_for_explicit_escape_room_goal_without_group():
    result = plan_day("今天下午想玩密室逃脱，安排一下。")

    names = [step["name"] for step in result["best_plan"]["timeline"]]

    assert result["goal"]["scenario"] == "friends"
    assert "escape_room" in result["goal"]["preferences"]
    assert "澳门悬疑密室体验馆" in names
    assert "密室" in "、".join(result["best_plan"]["score"]["reasons"])


def test_plan_day_treats_script_murder_as_escape_room_related_activity():
    result = plan_day("今天下午想玩剧本杀，安排一下。")

    names = [step["name"] for step in result["best_plan"]["timeline"]]

    assert result["goal"]["scenario"] == "friends"
    assert "escape_room" in result["goal"]["preferences"]
    assert "澳门悬疑密室体验馆" in names
