from agent.planner import plan_day


def test_planner_uses_structured_goal_for_group_size():
    result = plan_day('今天下午2男3女出去玩，安排一下。')
    goal = result['goal']
    assert goal['scenario'] == 'friends'
    assert goal['structured_goal']['people']['total'] == 5
    assert goal['structured_goal']['planning_strategy']['restaurant_table_size_required'] == 5
    assert any(item['people_count'] == 5 for item in result['best_plan']['availability'])


def test_tool_steps_include_llm_goal_parser():
    result = plan_day('今天下午2男3女出去玩，安排一下。')
    tools = [step['tool'] for step in result['tool_steps']]
    assert 'llm_goal_parser' in tools
    assert 'goal_validator' in tools
    assert 'goal_enricher' in tools


def test_vague_input_returns_clarification_payload():
    result = plan_day('下午出去玩一下。')
    assert result['goal']['structured_goal']['clarification_needed'] is True
    assert result['clarification_needed'] is True
    assert result['clarification_questions']
