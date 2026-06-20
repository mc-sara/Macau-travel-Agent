from agent.parser import parse_goal
from agent.tools import check_availability, get_accessibility, mock_map_route_api, search_attractions, search_local_merchants


def test_search_attractions_returns_senior_candidates():
    goal = parse_goal('我想带爸妈下午轻松逛逛，不想爬楼梯。')
    attractions = search_attractions(goal)
    names = [item['name'] for item in attractions]
    assert '二龙喉公园缆车' in names
    assert any(item['id'] == 'attraction_guia_cable_car' for item in attractions)


def test_get_accessibility_returns_risk_for_ruins_of_st_paul():
    accessibility = get_accessibility('attraction_ruins_st_paul')
    assert accessibility['stairs_count'] == 68
    assert accessibility['steep_slopes'] is True
    assert '68级石阶' in accessibility['senior_tips_zh']


def test_mock_map_route_api_returns_navigation_fields():
    route = mock_map_route_api('家', '二龙喉公园缆车')
    assert route['route_distance_km'] > 0
    assert route['duration_min'] > 0
    assert route['walking_distance_m'] >= 0
    assert 'route_summary' in route


def test_search_local_merchants_returns_senior_safe_merchants():
    goal = parse_goal('今天下午带爸妈出去轻松逛逛，晚上吃清淡一点。')
    merchants = search_local_merchants(goal)
    assert merchants['restaurants'][0]['name'] == '轻悦生活餐厅'
    assert merchants['friend_activities'] == []
    assert merchants['couple_activities'] == []
    assert merchants['drink_shops']


def test_check_availability_finds_merchant_slot():
    availability = check_availability('res_001', '17:30', 3)
    assert availability['available'] is True
    assert availability['queue_minutes'] == 0
    assert availability['item_id'] == 'res_001'
