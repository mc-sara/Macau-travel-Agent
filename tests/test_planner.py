from agent.planner import generate_candidate_plans, plan_day


def test_plan_day_family_returns_best_plan_with_tool_steps():
    result = plan_day('今天下午想和老婆孩子出去玩几个小时，别离家太远。')
    assert result['goal']['scenario'] == 'family'
    assert result['best_plan']['title'] == '亲子低疲劳半日路线'
    assert result['best_plan']['score']['score'] >= 80
    assert result['tool_steps']
    assert result['best_plan']['timeline']


def test_plan_day_three_scenarios():
    cases = [
        ('今天下午想和老婆孩子出去玩几个小时，别离家太远。', 'family'),
        ('今天下午和朋友4个人出去玩，2男2女，安排一下。', 'friends'),
        ('今天下午想和对象约会，浪漫一点但别太累。', 'couple'),
    ]
    for text, scenario in cases:
        result = plan_day(text)
        assert result['goal']['scenario'] == scenario
        assert result['best_plan']['timeline']
        assert result['alternatives']
        assert 'score' in result['best_plan']


def test_generate_candidate_plans_returns_main_and_alternative():
    plans = generate_candidate_plans({'scenario': 'couple', 'people': {'total': 2}, 'origin': '家'})
    assert len(plans) >= 2
    assert any('鲜花' in step['name'] or '小岛花房' in step['name'] for step in plans[0]['timeline'])
