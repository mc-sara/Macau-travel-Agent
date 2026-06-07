from agent.llm_goal_parser import normalize_llm_goal_payload


def test_normalizer_records_debug_steps_for_group_payload():
    raw = {
        "relationship_type": "mixed_group",
        "outing_intent": "half_day_outing",
        "group": {
            "total_people": 5,
            "gender_count": {"male": 2, "female": 3},
        },
        "time": {"date": "today", "period": "afternoon"},
        "hard_constraints": ["人数为5人"],
    }

    goal = normalize_llm_goal_payload(raw, "今天下午2男3女出去玩，安排一下。")

    debug = goal["_debug"]
    assert debug["raw_llm_shape"] == [
        "group",
        "hard_constraints",
        "outing_intent",
        "relationship_type",
        "time",
    ]
    assert "group.total_people -> people.total" in debug["normalization_steps"]
    assert "group.gender_count.male -> people.male" in debug["normalization_steps"]
    assert "group.gender_count.female -> people.female" in debug["normalization_steps"]
    assert "mixed_group + total>=3 -> friends" in debug["normalization_steps"]
    assert "time.period -> time.start_period" in debug["normalization_steps"]
    assert debug["normalized_from_provider_payload"] is True


def test_normalizer_records_debug_steps_for_parsed_request_payload():
    raw = {
        "parsed_request": {
            "party_size": 5,
            "group_composition": {"male": 2, "female": 3},
            "relationship_type": "mixed_group",
            "outing_intent": "general_outing",
        }
    }

    goal = normalize_llm_goal_payload(raw, "今天下午2男3女出去玩，安排一下。")

    steps = goal["_debug"]["normalization_steps"]
    assert "parsed_request.party_size -> people.total" in steps
    assert "parsed_request.group_composition.male -> people.male" in steps
    assert "parsed_request.group_composition.female -> people.female" in steps
    assert "general_outing + friends -> half_day_outing" in steps
