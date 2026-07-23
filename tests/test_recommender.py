from agent.parser import parse_goal
from agent.tools import search_attractions
from agent.recommender import _beam_search, _canonical_poi_key, _rank_candidate_pois, _resolve_origin, recommend_itineraries


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
    assert plan['map_view']['provider'] == 'leaflet_osm'
    assert len(plan['map_view']['points']) == len(plan['poi_details']) + 1
    assert len(plan['map_view']['polyline']) == len(plan['map_view']['points'])
    assert plan['map_view']['points'][0]['type'] == 'origin'


def test_beam_search_dedupes_same_place_aliases():
    goal = parse_goal('我想带爸妈下午轻松逛逛，不想爬楼梯，最好有地方坐，晚上吃点清淡的。')
    first_route = _beam_search(goal, _rank_candidate_pois(goal, limit=None))[0][0]
    keys = [_canonical_poi_key(poi) for poi in first_route]
    assert len(keys) == len(set(keys))
    names = [poi['name'] for poi in first_route]
    assert not ({'澳门仁慈堂大楼', '澳門仁慈堂大樓'} <= set(names))


def test_confirmed_duplicate_pois_removed_from_excel_candidates():
    goal = parse_goal('我想带爸妈下午轻松逛逛，不想爬楼梯，最好有地方坐。')
    all_names = {poi['name'] for poi in search_attractions(goal, limit=None)}
    removed = {
        '澳門仁慈堂大樓', '莲溪庙', '白鸽巢前地', '大炮台陈列室', '哪咤庙（大三巴）', '耶稣会纪念广场', '崗頂前地',
        '東望洋炮台、聖母雪地殿教堂及燈塔', '媽祖閣（媽閣廟）', '玫瑰聖母堂（板樟堂）', '聖奧斯定堂',
        '三街會館（關帝廟）', '马礼逊教堂', '仁慈堂博物馆', '妈阁庙前地壁画', '圣若瑟修院藏珍馆',
    }
    assert all_names.isdisjoint(removed)
    kept = {
        '澳门仁慈堂大楼', '莲峰庙', '白鸽巢公园', '大炮台', '大三巴', '岗顶前地',
        '东望洋炮台、圣母雪地殿教堂及灯塔', '妈祖阁（妈阁庙）', '玫瑰圣母堂（板樟堂）',
        '圣奥斯定教堂', '三街会馆（关帝庙）', '基督教坟场', '圣若瑟修院大楼、圣若瑟修院教堂、前地及石阶',
    }
    assert kept <= all_names
