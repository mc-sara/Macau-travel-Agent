from agent.parser import parse_goal
from agent.scorer import score_plan, score_poi
from agent.tools import search_attractions


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
    assert any('长者' in reason or '慢慢走' in reason for reason in score['reasons'])
    assert any('人多' in risk or '累了' in risk for risk in score['risks'])


def test_score_senior_plan_prioritizes_short_walking_and_execution():
    score = score_plan(_senior_plan(), {'scenario': 'senior'})
    assert score['score_breakdown']['transport_simplicity'] >= 80
    assert score['score_breakdown']['executable'] == 100
    assert all('QwenPaw' not in reason for reason in score['reasons'])
    assert any('第一站节奏轻' in reason for reason in score['reasons'])


def test_score_penalizes_long_walking_segments():
    plan = _senior_plan()
    plan['routes'] = [{'duration_min': 25, 'walking_distance_m': 520}, {'duration_min': 20, 'walking_distance_m': 410}]
    score = score_plan(plan, {'scenario': 'senior'})
    assert score['score_breakdown']['transport_simplicity'] < 80
    assert score['score'] < 90


def test_score_poi_uses_new_senior_feature_breakdown():
    goal = parse_goal('我从澳门大学出发，带爸妈轻松逛，不要爬楼梯。')
    poi = search_attractions(goal)[0]
    score = score_poi(poi, goal)
    required = {
        'walking_comfort',
        'stairs_comfort',
        'accessibility_score',
        'rest_support',
        'toilet_support',
        'weather_comfort',
        'crowd_comfort',
        'ground_safety',
        'standing_comfort',
        'senior_interest_match',
    }
    assert score['score'] > 0
    assert score['reasons']
    assert 'feature_breakdown' in score
    assert required <= set(score['feature_breakdown'])
    assert score['breakdown']['rest_toilet'] >= 0


def test_score_poi_explains_penalties_for_weak_features():
    poi = {
        'name': '测试高风险景点',
        'score_features': {
            'walking_comfort': 35,
            'stairs_comfort': 30,
            'accessibility_score': 45,
            'rest_support': 40,
            'toilet_support': 45,
            'weather_comfort': 35,
            'crowd_comfort': 40,
            'ground_safety': 35,
            'standing_comfort': 40,
            'senior_interest_match': 60,
        },
        'accessibility_raw': {
            'stairs_count': 35,
            'steep_slopes': 'high',
            'avoid_route_zh': '避免正门台阶和陡坡。',
        },
    }
    score = score_poi(poi, {'scenario': 'senior', 'preferences': ['avoid_stairs']})
    assert score['score'] < 50
    assert score['risk_flags']
    assert any('台阶' in risk or '步行' in risk for risk in score['risk_flags'])
