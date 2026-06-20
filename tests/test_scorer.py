from agent.scorer import score_plan


def _senior_plan():
    return {
        'scenario': 'senior',
        'timeline': [{'name': '议事亭前地'}, {'name': '澳门城市展览空间'}, {'name': '轻悦生活餐厅'}],
        'routes': [{'duration_min': 8, 'walking_distance_m': 120}, {'duration_min': 12, 'walking_distance_m': 150}],
        'availability': [{'available': True}, {'available': True}],
        'tags': ['senior_friendly', 'low_fatigue', 'rest_area', 'toilet_access'],
    }


def test_score_senior_plan_returns_explanations_and_risks():
    score = score_plan(_senior_plan(), {'scenario': 'senior'})
    assert score['score'] >= 80
    assert score['score_breakdown']
    assert set(score['score_breakdown']) == {'senior_friendly', 'transport_simplicity', 'low_fatigue', 'rest_toilet_support', 'executable'}
    assert any('长者' in reason or '低疲劳' in reason for reason in score['reasons'])
    assert any('人流' in risk or '体力' in risk for risk in score['risks'])


def test_score_senior_plan_prioritizes_short_walking_and_execution():
    score = score_plan(_senior_plan(), {'scenario': 'senior'})
    assert score['score_breakdown']['transport_simplicity'] >= 80
    assert score['score_breakdown']['executable'] == 100
    assert any('QwenPaw' in reason for reason in score['reasons'])


def test_score_penalizes_long_walking_segments():
    plan = _senior_plan()
    plan['routes'] = [{'duration_min': 25, 'walking_distance_m': 520}, {'duration_min': 20, 'walking_distance_m': 410}]
    score = score_plan(plan, {'scenario': 'senior'})
    assert score['score_breakdown']['transport_simplicity'] < 80
    assert score['score'] < 90
