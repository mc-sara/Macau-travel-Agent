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


def test_plan_day_accepts_explicit_origin_text():
    result = plan_day('带爸妈轻松逛逛，不想爬楼梯。', origin_text='澳门大学')
    assert result['goal']['origin'] == '澳门大学'
    assert result['best_plan']['route_summary'].startswith('澳门大学 ->')
    assert result['best_plan']['map_view']['points'][0]['name'] == '澳门大学'


def test_plan_day_accepts_explicit_origin_coordinates():
    result = plan_day(
        '带爸妈轻松逛逛，不想爬楼梯。',
        origin_text='测试起点',
        origin_coords={'latitude': 22.1291, 'longitude': 113.5456},
    )
    assert result['goal']['origin'] == '测试起点'
    assert result['goal']['origin_coords']['latitude'] == 22.1291
    assert result['best_plan']['map_view']['points'][0]['name'] == '测试起点'
    assert result['best_plan']['map_view']['points'][0]['latitude'] == 22.1291
