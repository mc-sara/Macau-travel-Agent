from agent.goal_enricher import enrich_goal
from agent.goal_schema import default_goal
from agent.goal_validator import validate_and_normalize_goal


def test_enrich_friends_group_requires_correct_table_size_and_rest():
    goal = default_goal('今天下午2男3女出去玩，安排一下。')
    goal.update({
        'relationship_type': 'friends',
        'outing_intent': 'half_day_outing',
        'people': {'total': 5, 'male': 2, 'female': 3, 'children': 0, 'seniors': 0},
    })
    enriched = enrich_goal(validate_and_normalize_goal(goal))
    strategy = enriched['planning_strategy']
    assert strategy['restaurant_table_size_required'] == 5
    assert strategy['must_include_meal'] is True
    assert strategy['must_include_rest'] is True
    assert 'group_restaurant' in strategy['preferred']


def test_enrich_family_with_children_is_low_fatigue():
    goal = validate_and_normalize_goal({
        'raw_text': '带5岁孩子玩几个小时，老婆想吃低卡一点。',
        'relationship_type': 'family_with_children',
        'people': {'total': 3, 'male': 1, 'female': 1, 'children': 1, 'seniors': 0},
        'soft_preferences': ['low_calorie_food'],
    })
    enriched = enrich_goal(goal)
    strategy = enriched['planning_strategy']
    assert strategy['max_walking_per_segment_m'] <= 300
    assert strategy['max_route_duration_per_segment_min'] <= 20
    assert 'kid_friendly_place' in strategy['preferred']
    assert 'long_queue' in strategy['avoid']


def test_enrich_family_with_seniors_avoids_stairs():
    goal = validate_and_normalize_goal({
        'raw_text': '我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。',
        'relationship_type': 'family_with_seniors',
        'people': {'total': 3, 'male': 1, 'female': 1, 'children': 0, 'seniors': 2},
    })
    enriched = enrich_goal(goal)
    strategy = enriched['planning_strategy']
    assert strategy['max_walking_per_segment_m'] <= 300
    assert 'stairs' in strategy['avoid']
    assert 'rest_area' in strategy['preferred']


def test_enrich_couple_prefers_romantic_surprise():
    goal = validate_and_normalize_goal({
        'raw_text': '今天下午想和对象约会，浪漫一点但别太累。',
        'relationship_type': 'couple',
        'outing_intent': 'date_plan',
        'people': {'total': 2, 'male': 1, 'female': 1, 'children': 0, 'seniors': 0},
    })
    enriched = enrich_goal(goal)
    strategy = enriched['planning_strategy']
    assert strategy['pace'] == 'medium_slow'
    assert 'romantic_dinner' in strategy['preferred']
    assert 'surprise_action' in strategy['preferred']
    assert 'too_crowded' in strategy['avoid']
