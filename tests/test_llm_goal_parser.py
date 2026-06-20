from agent.llm_goal_parser import build_llm_prompt, parse_goal_with_llm


def test_mock_llm_parser_handles_generic_group_as_senior_safe():
    goal = parse_goal_with_llm('今天下午2男3女出去玩，安排一下。', use_mock=True)
    assert goal['relationship_type'] == 'general'
    assert goal['outing_intent'] == 'general_outing'
    assert goal['people']['total'] == 5
    assert goal['people']['male'] == 2
    assert goal['people']['female'] == 3
    assert 'senior_friendly' in goal['hard_constraints']
    assert goal['confidence'] >= 0.5


def test_mock_llm_parser_handles_seniors():
    goal = parse_goal_with_llm('我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。', use_mock=True)
    assert goal['relationship_type'] == 'family_with_seniors'
    assert goal['people']['seniors'] == 2
    assert 'avoid_stairs' in goal['hard_constraints']
    assert 'low_fatigue' in goal['hard_constraints']


def test_mock_llm_parser_handles_vague_input_with_senior_clarification():
    goal = parse_goal_with_llm('下午出去玩一下。', use_mock=True)
    assert goal['clarification_needed'] is True
    assert goal['confidence'] < 0.45
    assert any('长者' in q or '楼梯' in q for q in goal['clarification_questions'])


def test_build_llm_prompt_requires_json_only_and_no_route_generation():
    prompt = build_llm_prompt('我想带爸妈轻松逛逛。')
    assert '只输出 JSON' in prompt
    assert '不要生成路线' in prompt
    assert 'relationship_type' in prompt
    assert 'hard_constraints' in prompt
    assert 'family_with_seniors' in prompt
