from agent.goal_schema import (
    HARD_SOFT_PREFERENCE_ENUM,
    OUTING_INTENT_ENUM,
    RELATIONSHIP_TYPE_ENUM,
    default_goal,
)


def test_default_goal_has_required_top_level_fields():
    goal = default_goal('下午出去玩一下')
    for key in [
        'raw_text',
        'relationship_type',
        'outing_intent',
        'confidence',
        'people',
        'time',
        'location',
        'hard_constraints',
        'soft_preferences',
        'budget',
        'planning_strategy',
        'missing_info',
        'clarification_needed',
        'clarification_questions',
        'assumptions',
    ]:
        assert key in goal


def test_default_goal_uses_allowed_enums_and_safe_defaults():
    goal = default_goal('下午出去玩一下')
    assert goal['relationship_type'] in RELATIONSHIP_TYPE_ENUM
    assert goal['outing_intent'] in OUTING_INTENT_ENUM
    assert goal['confidence'] == 0.5
    assert goal['people']['total'] == 2
    assert goal['time']['duration_hours'] == 5
    assert goal['location']['city'] == 'Macau'
    assert goal['budget']['level'] == 'medium'


def test_preference_enum_contains_demo_constraints():
    assert 'low_fatigue' in HARD_SOFT_PREFERENCE_ENUM
    assert 'photo_friendly' in HARD_SOFT_PREFERENCE_ENUM
    assert 'avoid_stairs' in HARD_SOFT_PREFERENCE_ENUM
    assert 'dinner_together' in HARD_SOFT_PREFERENCE_ENUM
