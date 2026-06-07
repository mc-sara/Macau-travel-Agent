from agent.llm_goal_parser import normalize_llm_goal_payload


def test_text_fallback_restores_gender_counts_when_provider_only_returns_total():
    raw = {
        "relationship_type": "general",
        "outing_intent": "half_day_outing",
        "group": {"total_people": 5},
        "time": {"period": "afternoon"},
    }

    goal = normalize_llm_goal_payload(raw, "今天下午2男3女出去玩，安排一下。")

    assert goal["relationship_type"] == "friends"
    assert goal["people"]["total"] == 5
    assert goal["people"]["male"] == 2
    assert goal["people"]["female"] == 3
    assert goal["planning_strategy"]["restaurant_table_size_required"] == 5
    assert "user_text gender_count -> people.male/female" in goal["_debug"]["normalization_steps"]


def test_text_fallback_restores_child_and_low_calorie_constraints():
    raw = {
        "relationship_type": "family_with_children",
        "outing_intent": "kid_friendly_play",
        "people": {"total": 2, "children": 0},
        "hard_constraints": [],
        "soft_preferences": [],
    }

    goal = normalize_llm_goal_payload(raw, "带5岁孩子玩几个小时，老婆想吃低卡一点。")

    assert goal["relationship_type"] == "family_with_children"
    assert goal["people"]["total"] == 3
    assert goal["people"]["children"] == 1
    assert "kid_friendly" in goal["hard_constraints"]
    assert "low_calorie_food" in goal["soft_preferences"]
    assert "user_text child_mention -> people.children" in goal["_debug"]["normalization_steps"]


def test_text_fallback_restores_seniors_and_avoid_stairs():
    raw = {
        "relationship_type": "family_with_seniors",
        "outing_intent": "low_fatigue_relax",
        "people": {"total": 2, "seniors": 0},
        "hard_constraints": [],
    }

    goal = normalize_llm_goal_payload(raw, "我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。")

    assert goal["relationship_type"] == "family_with_seniors"
    assert goal["people"]["total"] == 3
    assert goal["people"]["seniors"] == 2
    assert "avoid_stairs" in goal["hard_constraints"]
    assert "senior_friendly" in goal["hard_constraints"]
    assert "user_text parent_mention -> people.seniors" in goal["_debug"]["normalization_steps"]


def test_text_fallback_forces_clarification_for_vague_short_input():
    raw = {
        "relationship_type": "general",
        "outing_intent": "half_day_outing",
        "missing_info": [],
        "clarification_needed": False,
    }

    goal = normalize_llm_goal_payload(raw, "下午出去玩一下。")

    assert goal["relationship_type"] == "general"
    assert goal["clarification_needed"] is True
    assert goal["missing_info"]
    assert goal["clarification_questions"]
    assert "user_text vague_input -> clarification_needed" in goal["_debug"]["normalization_steps"]


def test_text_fallback_asks_gender_breakdown_when_mixed_gender_group_lacks_counts():
    raw = {
        "relationship_type": "friends",
        "outing_intent": "indoor_plan",
        "people": {"total": 5, "male": 0, "female": 0},
        "soft_preferences": ["escape_room", "indoor_activity"],
        "missing_info": [],
        "clarification_needed": False,
    }

    goal = normalize_llm_goal_payload(raw, "我们几个朋友出去玩，5个人，有男有女，想去密室。")

    assert goal["relationship_type"] == "friends"
    assert goal["people"]["total"] == 5
    assert goal["people"]["male"] == 0
    assert goal["people"]["female"] == 0
    assert "escape_room" in goal["soft_preferences"]
    assert goal["clarification_needed"] is True
    assert "gender_breakdown" in goal["missing_info"]
    assert "请补充男女各有几个人？" in goal["clarification_questions"]
    assert "user_text mixed_gender_without_counts -> clarification_needed" in goal["_debug"]["normalization_steps"]
