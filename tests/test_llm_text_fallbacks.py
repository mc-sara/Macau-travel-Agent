from agent.llm_goal_parser import normalize_llm_goal_payload


def test_text_fallback_restores_gender_counts_but_keeps_senior_safe_general():
    raw = {"relationship_type": "general", "outing_intent": "half_day_outing", "group": {"total_people": 5}, "time": {"period": "afternoon"}}
    goal = normalize_llm_goal_payload(raw, "今天下午2男3女出去玩，安排一下。")
    assert goal["relationship_type"] == "general"
    assert goal["people"]["total"] == 5
    assert goal["people"]["male"] == 2
    assert goal["people"]["female"] == 3
    assert goal["planning_strategy"]["restaurant_table_size_required"] == 5
    assert "user_text gender_count -> people.male/female" in goal["_debug"]["normalization_steps"]


def test_text_fallback_child_text_no_longer_restores_child_scenario():
    raw = {"relationship_type": "family_with_children", "outing_intent": "kid_friendly_play", "people": {"total": 2, "children": 0}, "hard_constraints": [], "soft_preferences": []}
    goal = normalize_llm_goal_payload(raw, "带5岁孩子玩几个小时，想吃低卡一点。")
    assert goal["relationship_type"] == "general"
    assert "kid_friendly" not in goal["hard_constraints"]
    assert "senior_friendly" in goal["hard_constraints"]
    assert "low_calorie_food" in goal["soft_preferences"]


def test_text_fallback_restores_seniors_and_avoid_stairs():
    raw = {"relationship_type": "family_with_seniors", "outing_intent": "low_fatigue_relax", "people": {"total": 2, "seniors": 0}, "hard_constraints": []}
    goal = normalize_llm_goal_payload(raw, "我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。")
    assert goal["relationship_type"] == "family_with_seniors"
    assert goal["people"]["total"] == 3
    assert goal["people"]["seniors"] == 2
    assert "avoid_stairs" in goal["hard_constraints"]
    assert "senior_friendly" in goal["hard_constraints"]
    assert "user_text senior_mention -> people.seniors" in goal["_debug"]["normalization_steps"]


def test_text_fallback_forces_senior_clarification_for_vague_short_input():
    raw = {"relationship_type": "general", "outing_intent": "half_day_outing", "missing_info": [], "clarification_needed": False}
    goal = normalize_llm_goal_payload(raw, "下午出去玩一下。")
    assert goal["relationship_type"] == "general"
    assert goal["clarification_needed"] is True
    assert "senior_count" in goal["missing_info"]
    assert any("长者" in q or "楼梯" in q for q in goal["clarification_questions"])


def test_old_mixed_gender_entertainment_no_longer_asks_gender_breakdown():
    raw = {"relationship_type": "friends", "outing_intent": "indoor_plan", "people": {"total": 5, "male": 0, "female": 0}, "soft_preferences": [], "missing_info": [], "clarification_needed": False}
    goal = normalize_llm_goal_payload(raw, "我们几个朋友出去玩，5个人，有男有女，想找室内地方。")
    assert goal["relationship_type"] == "general"
    assert goal["people"]["total"] == 5
    assert "senior_friendly" in goal["hard_constraints"]
    assert "gender_breakdown" not in goal["missing_info"]
