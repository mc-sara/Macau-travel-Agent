from agent.planner import generate_candidate_plans, plan_day


def test_plan_day_senior_returns_best_plan_with_tool_steps():
    result = plan_day('我想带爸妈下午轻松逛逛，不想爬楼梯。')
    assert result['goal']['scenario'] == 'senior'
    assert result['best_plan']['id'].startswith('senior_dynamic_')
    assert result['best_plan']['score']['score'] >= 80
    assert len(result['tool_steps']) >= 5


def test_plan_day_senior_cases():
    cases = [
        '我想带爸妈下午轻松逛逛，不想爬楼梯。',
        '下午带爷爷奶奶在澳门走走，路不要太长，中途最好有厕所和座椅。',
        '外婆走路慢，最好全程有电梯或无障碍通道。',
    ]
    for text in cases:
        result = plan_day(text)
        assert result['goal']['scenario'] == 'senior'
        assert result['best_plan']['scenario'] == 'senior'
        assert 'senior_friendly' in result['best_plan']['tags']


def test_generate_candidate_plans_returns_dynamic_or_fallback_plans():
    plans = generate_candidate_plans({'scenario': 'senior', 'people': {'total': 3}, 'origin': '家', 'preferences': ['senior_friendly']})
    assert len(plans) >= 2
    assert plans[0]['scenario'] == 'senior'
    assert plans[0]['score']['score'] >= 70
