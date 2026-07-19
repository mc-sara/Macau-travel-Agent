from agent.parser import parse_goal
from agent.tools import check_availability, get_accessibility, mock_map_route_api, search_attractions, search_local_merchants


def test_search_attractions_returns_senior_candidates():
    goal = parse_goal('我想带爸妈下午轻松逛逛，不想爬楼梯。')
    attractions = search_attractions(goal)
    names = [item['name'] for item in attractions]
    assert '澳门文化中心' in names
    assert any(item['id'] == 'attraction_502' for item in attractions)
    assert all('real_excel' in item.get('tags', []) for item in attractions[:3])


def test_get_accessibility_returns_real_excel_record():
    accessibility = get_accessibility('attraction_502')
    assert 'senior_tips_zh' in accessibility
    assert accessibility['rest_areas']
    assert accessibility['steep_slopes'] is False


def test_mock_map_route_api_returns_navigation_fields():
    route = mock_map_route_api('家', '二龙喉公园缆车')
    assert route['route_distance_km'] > 0
    assert route['duration_min'] > 0
    assert route['walking_distance_m'] >= 0
    assert 'route_summary' in route


def test_search_local_merchants_returns_senior_safe_merchants():
    goal = parse_goal('今天下午带爸妈出去轻松逛逛，晚上吃清淡一点。')
    merchants = search_local_merchants(goal)
    assert merchants['senior_activities']
    assert all('score_features' in item for item in merchants['senior_activities'][:3])
    assert merchants['restaurants'] == []
    assert merchants['drink_shops'] == []


def test_check_availability_finds_merchant_slot():
    availability = check_availability('res_001', '17:30', 3)
    assert availability['available'] is True
    assert availability['queue_minutes'] == 0
    assert availability['item_id'] == 'res_001'
