from agent.parser import parse_structured_goal


class FakeRealParserClient:
    def __init__(self):
        self.called = False

    def chat_completion(self, *, base_url, api_key, model, messages, temperature=0):
        self.called = True
        return {'choices': [{'message': {'content': '{"relationship_type":"general","outing_intent":"general_outing","confidence":0.8,"people":{"total":5,"male":2,"female":3,"children":0,"seniors":0},"hard_constraints":["senior_friendly"],"soft_preferences":[]}'}}]}


def test_parse_structured_goal_can_use_real_llm_client(tmp_path, monkeypatch):
    env_file = tmp_path / '.env'
    env_file.write_text(
        'OPENAI_API_KEY=dummy-key\n'
        'OPENAI_BASE_URL=https://example.test/v1\n'
        'OPENAI_MODEL=gpt-test\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('MACAU_AGENT_ENV_FILE', str(env_file))
    client = FakeRealParserClient()
    goal = parse_structured_goal('今天下午2男3女出去玩，安排一下。', use_llm=True, client=client)
    assert client.called is True
    assert goal['relationship_type'] == 'general'
    assert goal['people']['total'] == 5
