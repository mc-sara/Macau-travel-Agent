from agent.parser import parse_goal
from agent.recommender import _beam_search, _rank_candidate_pois, _resolve_origin, recommend_itineraries


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


def test_wheelchair_input_filters_non_wheelchair_pois():
    goal = parse_goal('外婆坐轮椅，需要无障碍通道和电梯。')
    candidates = _rank_candidate_pois(goal, limit=30)
    assert candidates
    assert all(str((poi.get('accessibility_raw') or {}).get('wheelchair_friendly', '')).lower() != 'no' for poi in candidates)


def test_no_stairs_input_filters_high_stairs_and_steep_slopes():
    goal = parse_goal('我想带爸妈轻松逛逛，不要爬楼梯，不能走台阶。')
    candidates = _rank_candidate_pois(goal, limit=30)
    assert candidates
    for poi in candidates:
        raw = poi.get('accessibility_raw') or {}
        assert float(raw.get('stairs_count') or 0) <= 20
        assert str(raw.get('steep_slopes', '')).lower() not in {'high', 'medium_high'}


def test_plain_senior_input_does_not_hard_filter_by_default():
    goal = parse_goal('今天下午带爸妈在澳门轻松逛逛。')
    candidates = [
        {'name': '高风险点', 'accessibility_raw': {'stairs_count': 35, 'steep_slopes': 'high', 'trip_hazards': 'high'}},
        {'name': '普通点', 'accessibility_raw': {'stairs_count': 0, 'steep_slopes': 'low', 'trip_hazards': 'low'}},
    ]
    from agent.recommender import _filter_candidates_by_hard_constraints
    assert _filter_candidates_by_hard_constraints(candidates, goal) == candidates


def test_origin_aware_beam_search_uses_um_origin():
    goal = parse_goal('从澳门大学出发，带爸妈轻松逛逛。')
    origin = _resolve_origin(goal)
    assert origin['name'] == '澳门大学'
    assert 22.12 <= origin['latitude'] <= 22.14
    routes = _beam_search(goal, _rank_candidate_pois(goal, limit=None))
    assert routes
    first_route = routes[0][0]
    assert first_route[0]['region'] in {'氹仔', '路氹', '路环'}
    assert all('route_step_metrics' in poi for poi in first_route)
    assert first_route[0]['route_step_metrics']['from_previous_distance_km'] < 4


def test_origin_aware_beam_search_keeps_cluster_continuity():
    goal = parse_goal('从议事亭前地出发，带爸妈轻松逛逛。')
    first_route = _beam_search(goal, _rank_candidate_pois(goal, limit=None))[0][0]
    clusters = [poi.get('route_cluster') for poi in first_route]
    assert len(set(clusters)) == 1


def test_final_plan_contains_verified_routes_and_explanations():
    goal = parse_goal('从澳门大学出发，带爸妈轻松逛逛。')
    plan = recommend_itineraries(goal)[0]
    assert plan['route_verification']['segment_count'] == len(plan['routes'])
    assert plan['total_duration_min'] == plan['route_verification']['total_duration_min']
    assert plan['total_walking_distance_m'] == plan['route_verification']['total_walking_distance_m']
    assert plan['route_summary'].startswith('澳门大学 ->')
    assert len(plan['station_explanations']) == len(plan['poi_details'])
    assert all(item['reasons'] for item in plan['station_explanations'])
    assert all(route.get('from_name') and route.get('to_name') for route in plan['routes'])
    assert plan['recommendation_reasons']
    assert 'origin_aware_beam_search' in plan['tags']
