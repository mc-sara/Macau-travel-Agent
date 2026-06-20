from agent.goal_validator import validate_and_normalize_goal


def test_validator_repairs_people_total_but_keeps_general_senior_safe():
    goal = {
        'raw_text': '今天下午2男3女出去玩，安排一下。',
        'relationship_type': 'friends',
        'outing_intent': 'half_day_outing',
        'people': {'total': 2, 'male': 2, 'female': 3, 'children': 0, 'seniors': 0},
    }
    normalized = validate_and_normalize_goal(goal)
    assert normalized['people']['total'] == 5
    assert normalized['relationship_type'] == 'general'
    assert 'senior_friendly' in normalized['hard_constraints']


def test_validator_non_senior_child_text_no_longer_creates_child_scenario():
    goal = {
        'raw_text': '带孩子出去玩',
        'relationship_type': 'couple',
        'people': {'total': 3, 'male': 1, 'female': 1, 'children': 1, 'seniors': 0},
    }
    normalized = validate_and_normalize_goal(goal)
    assert normalized['relationship_type'] == 'general'
    assert 'kid_friendly' not in normalized['hard_constraints']
    assert 'senior_friendly' in normalized['hard_constraints']


def test_validator_seniors_add_senior_constraints():
    goal = {
        'raw_text': '我爸妈来澳门，不要爬楼梯',
        'relationship_type': 'general',
        'people': {'total': 3, 'male': 1, 'female': 1, 'children': 0, 'seniors': 2},
    }
    normalized = validate_and_normalize_goal(goal)
    assert normalized['relationship_type'] == 'family_with_seniors'
    assert 'senior_friendly' in normalized['hard_constraints']
    assert 'avoid_stairs' in normalized['hard_constraints']


def test_validator_invalid_relationship_becomes_general():
    goal = {'raw_text': '下午出去玩', 'relationship_type': 'unknown_type'}
    normalized = validate_and_normalize_goal(goal)
    assert normalized['relationship_type'] == 'general'
    assert normalized['confidence'] == 0.6


def test_validator_large_old_group_stays_general_senior_safe():
    goal = {
        'raw_text': '5个人出去玩一下',
        'relationship_type': 'couple',
        'people': {'total': 5, 'male': 2, 'female': 3, 'children': 0, 'seniors': 0},
    }
    normalized = validate_and_normalize_goal(goal)
    assert normalized['relationship_type'] == 'general'
    assert normalized['people']['total'] == 5
    assert 'short_walking_distance' in normalized['hard_constraints']
