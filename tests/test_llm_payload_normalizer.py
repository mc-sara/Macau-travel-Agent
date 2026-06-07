from agent.llm_goal_parser import normalize_llm_goal_payload


def test_normalize_real_api_parsed_request_payload_to_structured_goal():
    raw = {
        'original_input': '今天下午2男3女出去玩，安排一下。',
        'relationship_type': 'general',
        'outing_intent': 'general_outing',
        'people': {'total': 2, 'male': 0, 'female': 0, 'children': 0, 'seniors': 0},
        'parsed_request': {
            'date': 'today',
            'time_period': 'afternoon',
            'party_size': 5,
            'group_composition': {'male': 2, 'female': 3},
            'relationship_type': 'mixed_group',
            'outing_intent': 'general_outing',
        },
    }

    normalized = normalize_llm_goal_payload(raw, '今天下午2男3女出去玩，安排一下。')

    assert normalized['relationship_type'] == 'friends'
    assert normalized['outing_intent'] == 'half_day_outing'
    assert normalized['people']['total'] == 5
    assert normalized['people']['male'] == 2
    assert normalized['people']['female'] == 3
    assert normalized['planning_strategy']['restaurant_table_size_required'] == 5
    assert 'social' in normalized['soft_preferences']


def test_normalize_real_api_uses_nested_constraints_and_missing_info():
    raw = {
        'parsed_request': {
            'party_size': 3,
            'relationship_type': 'family_with_seniors',
            'outing_intent': 'low_fatigue_relax',
            'constraints': ['avoid_stairs', 'low_fatigue'],
            'preferences': ['local_specialty'],
            'missing_info': ['budget'],
        }
    }

    normalized = normalize_llm_goal_payload(raw, '我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。')

    assert normalized['relationship_type'] == 'family_with_seniors'
    assert normalized['people']['total'] == 3
    assert 'avoid_stairs' in normalized['hard_constraints']
    assert 'local_specialty' in normalized['soft_preferences']
    assert 'budget' in normalized['missing_info']
    assert 'stairs' in normalized['planning_strategy']['avoid']
