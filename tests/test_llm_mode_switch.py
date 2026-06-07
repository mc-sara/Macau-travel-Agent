from agent.parser import parse_structured_goal
from agent.planner import plan_day


class FakeRealClient:
    def __init__(self):
        self.called = False

    def chat_completion(self, *, base_url, api_key, model, messages, temperature=0):
        self.called = True
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"relationship_type":"mixed_group","outing_intent":"half_day_outing","group":{"total_people":5,"gender_count":{"male":2,"female":3}},"time":{"date":"today","period":"afternoon"}}'
                    }
                }
            ]
        }


class FailingRealClient:
    def chat_completion(self, **kwargs):
        raise TimeoutError("simulated provider timeout")


def _write_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=test-secret-key\n"
        "OPENAI_BASE_URL=https://example.test/v1\n"
        "OPENAI_MODEL=gpt-test\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MACAU_AGENT_ENV_FILE", str(env_file))


def test_parse_structured_goal_real_mode_uses_provider_client(tmp_path, monkeypatch):
    _write_env(tmp_path, monkeypatch)
    client = FakeRealClient()

    goal = parse_structured_goal("今天下午2男3女出去玩，安排一下。", llm_mode="real", client=client)

    assert client.called is True
    assert goal["relationship_type"] == "friends"
    assert goal["people"]["total"] == 5
    assert goal["people"]["male"] == 2
    assert goal["people"]["female"] == 3
    assert goal["_debug"]["llm_mode"] == "real"


def test_parse_structured_goal_mock_mode_does_not_use_provider_client(tmp_path, monkeypatch):
    _write_env(tmp_path, monkeypatch)
    client = FakeRealClient()

    goal = parse_structured_goal("今天下午2男3女出去玩，安排一下。", llm_mode="mock", client=client)

    assert client.called is False
    assert goal["relationship_type"] == "friends"
    assert goal["people"]["total"] == 5
    assert goal["_debug"]["llm_mode"] == "mock"


def test_parse_structured_goal_auto_mode_falls_back_to_mock(tmp_path, monkeypatch):
    _write_env(tmp_path, monkeypatch)

    goal = parse_structured_goal("今天下午2男3女出去玩，安排一下。", llm_mode="auto", client=FailingRealClient())

    assert goal["relationship_type"] == "friends"
    assert goal["people"]["total"] == 5
    assert goal["_debug"]["llm_mode"] == "auto"
    assert goal["_debug"]["llm_fallback_used"] is True


def test_plan_day_accepts_llm_mode_and_exposes_it(tmp_path, monkeypatch):
    _write_env(tmp_path, monkeypatch)

    result = plan_day("今天下午2男3女出去玩，安排一下。", llm_mode="mock")

    assert result["structured_goal"]["_debug"]["llm_mode"] == "mock"
    assert result["goal"]["people"]["total"] == 5
