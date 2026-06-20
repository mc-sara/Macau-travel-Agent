from agent.parser import parse_goal, parse_structured_goal


def test_parse_senior_parent_goal():
    goal = parse_goal('今天下午想带爸妈出去玩几个小时，别太累，不要爬楼梯。')
    assert goal['scenario'] == 'senior'
    assert goal['duration_hours'] == 5
    assert goal['people']['seniors'] == 2
    assert 'senior_friendly' in goal['preferences']
    assert 'avoid_stairs' in goal['preferences']
    assert 'low_fatigue' in goal['preferences']
    assert goal['structured_goal']['relationship_type'] == 'family_with_seniors'


def test_parse_vague_goal_defaults_to_senior_safe():
    goal = parse_goal('今天下午两个人出去玩，安排一下。')
    assert goal['scenario'] == 'senior'
    assert goal['people']['total'] == 2
    assert 'senior_friendly' in goal['preferences']
    assert 'short_walking_distance' in goal['preferences']


def test_parse_old_friend_text_no_longer_routes_to_friends():
    goal = parse_goal('今天下午和朋友4个人出去玩，2男2女，安排一下。')
    assert goal['scenario'] == 'senior'
    assert 'social' not in goal['preferences']
    assert 'photo_friendly' not in goal['preferences']


def test_parse_old_couple_text_no_longer_routes_to_couple():
    goal = parse_goal('今天下午想和对象约会，浪漫一点但别太累。')
    assert goal['scenario'] == 'senior'
    assert 'romantic' not in goal['preferences']
    assert 'senior_friendly' in goal['preferences']


def test_parse_structured_goal_seniors():
    structured = parse_structured_goal('我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。')
    assert structured['relationship_type'] == 'family_with_seniors'
    assert 'avoid_stairs' in structured['hard_constraints']
    assert structured['planning_strategy']['pace'] == 'slow'


def test_vague_input_marks_clarification_needed():
    structured = parse_structured_goal('下午出去玩一下。')
    assert structured['clarification_needed'] is True
    assert structured['clarification_questions']
