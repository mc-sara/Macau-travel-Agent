from agent.parser import parse_goal, parse_structured_goal


def test_parse_family_goal():
    goal = parse_goal('今天下午想和老婆孩子出去玩几个小时，别离家太远。')
    assert goal['scenario'] == 'family'
    assert goal['duration_hours'] == 5
    assert goal['people']['adults'] == 2
    assert goal['people']['children'] == 1
    assert goal['people']['child_age'] == 5
    assert 'kid_friendly' in goal['preferences']
    assert 'low_fatigue' in goal['preferences']
    assert goal['structured_goal']['relationship_type'] == 'family_with_children'


def test_parse_friends_goal():
    goal = parse_goal('今天下午和朋友4个人出去玩，2男2女，安排一下。')
    assert goal['scenario'] == 'friends'
    assert goal['people']['total'] == 4
    assert 'social' in goal['preferences']
    assert 'photo_friendly' in goal['preferences']


def test_parse_gender_count_without_friend_keyword():
    goal = parse_goal('今天下午2男3女出去玩，安排一下。')
    assert goal['scenario'] == 'friends'
    assert goal['people']['total'] == 5
    assert goal['people']['male'] == 2
    assert goal['people']['female'] == 3
    assert 'social' in goal['preferences']
    assert goal['structured_goal']['planning_strategy']['restaurant_table_size_required'] == 5


def test_parse_chinese_gender_count():
    goal = parse_goal('下午两男三女想在澳门轻松玩一下')
    assert goal['scenario'] == 'friends'
    assert goal['people']['total'] == 5
    assert goal['people']['male'] == 2
    assert goal['people']['female'] == 3


def test_parse_couple_goal():
    goal = parse_goal('今天下午想和对象约会，浪漫一点但别太累。')
    assert goal['scenario'] == 'couple'
    assert goal['people']['total'] == 2
    assert 'romantic' in goal['preferences']
    assert 'low_fatigue' in goal['preferences']
    assert goal['structured_goal']['relationship_type'] == 'couple'


def test_parse_structured_goal_seniors():
    structured = parse_structured_goal('我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。')
    assert structured['relationship_type'] == 'family_with_seniors'
    assert 'avoid_stairs' in structured['hard_constraints']
    assert structured['planning_strategy']['pace'] == 'slow'


def test_vague_input_marks_clarification_needed():
    structured = parse_structured_goal('下午出去玩一下。')
    assert structured['clarification_needed'] is True
    assert structured['clarification_questions']
