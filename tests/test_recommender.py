from agent.parser import parse_goal
from agent.recommender import recommend_itineraries


def test_recommend_itineraries_returns_dynamic_real_routes():
    goal = parse_goal('我想带爸妈下午轻松逛逛，不想爬楼梯。')
    plans = recommend_itineraries(goal)
    assert len(plans) >= 2
    assert all(plan['id'].startswith('senior_dynamic_') for plan in plans)
    assert all('dynamic_recommendation' in plan['tags'] for plan in plans)
    assert all(2 <= len(plan['timeline']) <= 3 for plan in plans)
    assert all(plan['score']['score'] >= 70 for plan in plans)
    assert all(plan.get('poi_details') for plan in plans)


def test_recommend_itineraries_avoids_duplicate_pois():
    goal = parse_goal('下午带爷爷奶奶在澳门走走，路不要太长，中途最好有厕所和座椅。')
    for plan in recommend_itineraries(goal):
        names = [step['name'] for step in plan['timeline']]
        assert len(names) == len(set(names))


def test_recommend_itineraries_contains_reasons_and_risks():
    goal = parse_goal('外婆走路慢，最好全程有电梯或无障碍通道。')
    plan = recommend_itineraries(goal)[0]
    assert plan['recommendation_reasons']
    assert 'score_breakdown' in plan['score']
