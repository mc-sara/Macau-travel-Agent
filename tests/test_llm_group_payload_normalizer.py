from agent.llm_goal_parser import normalize_llm_goal_payload


def test_normalize_real_api_group_payload_to_senior_safe_goal():
    raw = {
        "relationship_type": "mixed_group",
        "outing_intent": "half_day_outing",
        "group": {"total_people": 5, "gender_count": {"male": 2, "female": 3}},
        "time": {"date": "today", "period": "afternoon"},
        "hard_constraints": ["今天下午出行", "人数为5人", "2男3女"],
        "soft_preferences": [],
        "missing_info": ["具体出发时间", "出发地点", "活动时长"],
        "assumptions": ["用户希望安排澳门本地下午半日活动", "5人为普通混合小组，具体关系未知"],
    }
    normalized = normalize_llm_goal_payload(raw, "今天下午2男3女出去玩，安排一下。")
    assert normalized["relationship_type"] == "general"
    assert normalized["outing_intent"] == "half_day_outing"
    assert normalized["people"]["total"] == 5
    assert normalized["people"]["male"] == 2
    assert normalized["people"]["female"] == 3
    assert normalized["time"]["date"] == "today"
    assert normalized["time"]["start_period"] == "afternoon"
    assert normalized["planning_strategy"]["restaurant_table_size_required"] == 5
    assert "senior_friendly" in normalized["hard_constraints"]
    assert "具体出发时间" in normalized["missing_info"]
