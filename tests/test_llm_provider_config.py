import json
from agent.llm_goal_parser import load_llm_config, parse_goal_with_llm, redact_config


class FakeOpenAICompatibleClient:
    def chat_completion(self, *, base_url, api_key, model, messages, temperature=0):
        assert base_url == 'https://example.test/v1'
        assert api_key == 'dummy-key'
        assert model == 'gpt-test'
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        content = {
            'relationship_type': 'general',
            'outing_intent': 'general_outing',
            'confidence': 0.7,
            'people': {'total': 5, 'male': 2, 'female': 3, 'children': 0, 'seniors': 0},
            'hard_constraints': ['senior_friendly'],
            'soft_preferences': [],
        }
        return {'choices': [{'message': {'content': json.dumps(content, ensure_ascii=False)}}]}


def test_load_llm_config_from_env_file_without_hardcoding_secret(tmp_path, monkeypatch):
    env_file = tmp_path / '.env'
    env_file.write_text(
        'OPENAI_API_KEY=dummy-key\n'
        'OPENAI_BASE_URL=https://example.test/v1\n'
        'OPENAI_MODEL=gpt-test\n',
        encoding='utf-8',
    )
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_BASE_URL', raising=False)
    monkeypatch.delenv('OPENAI_MODEL', raising=False)
    config = load_llm_config(env_file)
    assert config['api_key'] == 'dummy-key'
    assert config['base_url'] == 'https://example.test/v1'
    assert config['model'] == 'gpt-test'
    assert redact_config(config)['api_key'] == '[REDACTED]'


def test_real_llm_path_uses_configured_openai_compatible_client(tmp_path, monkeypatch):
    env_file = tmp_path / '.env'
    env_file.write_text(
        'OPENAI_API_KEY=dummy-key\n'
        'OPENAI_BASE_URL=https://example.test/v1\n'
        'OPENAI_MODEL=gpt-test\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('MACAU_AGENT_ENV_FILE', str(env_file))
    goal = parse_goal_with_llm('今天下午2男3女出去玩，安排一下。', use_mock=False, client=FakeOpenAICompatibleClient())
    assert goal['relationship_type'] == 'general'
    assert goal['people']['total'] == 5
    assert goal['planning_strategy']['restaurant_table_size_required'] == 5
    assert 'senior_friendly' in goal['hard_constraints']
