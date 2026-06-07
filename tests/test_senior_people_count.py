from agent.llm_goal_parser import parse_goal_with_llm
from agent.goal_validator import validate_and_normalize_goal


def test_validator_keeps_total_when_unclassified_adult_exists():
    goal = {
        'raw_text': '我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。',
        'relationship_type': 'family_with_seniors',
        'people': {'total': 3, 'male': 0, 'female': 0, 'children': 0, 'seniors': 2},
    }
    normalized = validate_and_normalize_goal(goal)
    assert normalized['people']['total'] == 3


def test_mock_llm_parser_counts_user_plus_parents():
    goal = parse_goal_with_llm('我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。', use_mock=True)
    assert goal['people']['total'] == 3
    assert goal['people']['seniors'] == 2
