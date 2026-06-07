from scripts.test_real_llm_cases import CASES, evaluate_goal, run_cases


class FakeMultiCaseClient:
    def chat_completion(self, *, base_url, api_key, model, messages, temperature=0):
        prompt = messages[-1]["content"]
        if "2男3女" in prompt:
            content = '{"relationship_type":"mixed_group","outing_intent":"half_day_outing","group":{"total_people":5,"gender_count":{"male":2,"female":3}},"time":{"date":"today","period":"afternoon"}}'
        elif "对象" in prompt:
            content = '{"relationship_type":"couple","outing_intent":"date_plan","people":{"total":2},"hard_constraints":["low_fatigue"],"soft_preferences":["romantic"]}'
        elif "5岁孩子" in prompt:
            content = '{"relationship_type":"family_with_children","outing_intent":"kid_friendly_play","people":{"total":3,"children":1},"hard_constraints":["kid_friendly"],"soft_preferences":["low_calorie_food"]}'
        elif "爸妈" in prompt:
            content = '{"relationship_type":"family_with_seniors","outing_intent":"low_fatigue_relax","people":{"total":3,"seniors":2},"hard_constraints":["avoid_stairs","senior_friendly"]}'
        else:
            content = '{"relationship_type":"general","outing_intent":"general_outing","confidence":0.3,"clarification_needed":true,"missing_info":["people","budget"]}'
        return {"choices": [{"message": {"content": content}}]}


def _write_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=test-secret-key\n"
        "OPENAI_BASE_URL=https://example.test/v1\n"
        "OPENAI_MODEL=gpt-test\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MACAU_AGENT_ENV_FILE", str(env_file))


def test_cases_define_five_required_demo_scenarios():
    case_ids = [case["id"] for case in CASES]
    assert case_ids == ["friends_group", "couple_date", "family_child", "family_seniors", "vague_input"]


def test_evaluate_goal_returns_pass_for_matching_expectations():
    goal = {
        "relationship_type": "friends",
        "people": {"total": 5, "male": 2, "female": 3},
        "planning_strategy": {"restaurant_table_size_required": 5},
    }
    passed, failures = evaluate_goal(goal, {"relationship_type": "friends", "people.total": 5, "people.male": 2})
    assert passed is True
    assert failures == []


def test_evaluate_goal_reports_failed_expectations():
    goal = {"relationship_type": "general", "people": {"total": 2}}
    passed, failures = evaluate_goal(goal, {"relationship_type": "friends", "people.total": 5})
    assert passed is False
    assert "relationship_type expected friends got general" in failures
    assert "people.total expected 5 got 2" in failures


def test_run_cases_with_fake_real_client_passes_all_cases(tmp_path, monkeypatch):
    _write_env(tmp_path, monkeypatch)
    results = run_cases(client=FakeMultiCaseClient(), llm_mode="real")
    assert all(result["passed"] for result in results)
    assert len(results) == 5
