from agent.goal_enricher import enrich_goal
from agent.goal_schema import default_goal
from agent.goal_validator import validate_and_normalize_goal


def test_enrich_senior_group_requires_correct_table_size_and_rest():
    goal = default_goal('下午带爸妈轻松逛逛，三个人，晚上吃清淡一点。')
    goal.update({
        'relationship_type': 'family_with_seniors',
        'outing_intent': 'low_fatigue_relax',
        'people': {'total': 3, 'male': 0, 'female': 0, 'children': 0, 'seniors': 2},
        'soft_preferences': ['low_calorie_food'],
    })
    enriched = enrich_goal(validate_and_normalize_goal(goal))
    strategy = enriched['planning_strategy']
    assert strategy['restaurant_table_size_required'] == 3
    assert strategy['must_include_meal'] is True
    assert strategy['must_include_rest'] is True
    assert 'senior_friendly_restaurant' in strategy['preferred']
    assert 'light_food' in strategy['preferred']


def test_enrich_general_input_is_senior_safe_by_default():
    goal = validate_and_normalize_goal({
        'raw_text': '下午出去玩几个小时，别太累。',
        'relationship_type': 'general',
        'people': {'total': 2, 'male': 0, 'female': 0, 'children': 0, 'seniors': 0},
    })
    enriched = enrich_goal(goal)
    strategy = enriched['planning_strategy']
    assert strategy['pace'] == 'slow'
    assert strategy['max_walking_per_segment_m'] <= 300
    assert strategy['max_route_duration_per_segment_min'] <= 18
    assert 'rest_area' in strategy['preferred']
    assert 'stairs' in strategy['avoid']


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


def test_enrich_wheelchair_or_elevator_prefers_accessible_route():
    goal = validate_and_normalize_goal({
        'raw_text': '外婆走路慢，最好全程有电梯或无障碍通道。',
        'relationship_type': 'family_with_seniors',
        'people': {'total': 2, 'male': 0, 'female': 0, 'children': 0, 'seniors': 1},
        'hard_constraints': ['wheelchair_friendly', 'elevator_required'],
    })
    enriched = enrich_goal(goal)
    strategy = enriched['planning_strategy']
    assert 'wheelchair_friendly' in strategy['preferred']
    assert 'elevator_access' in strategy['preferred']
    assert 'narrow_walkway' in strategy['avoid']
