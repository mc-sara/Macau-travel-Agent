from agent.tools import search_origin_candidates


def test_search_origin_candidates_returns_macau_candidates():
    candidates = search_origin_candidates('澳门大学')
    assert candidates
    first = candidates[0]
    assert first['name'] in {'澳门大学', '澳門大學'}
    assert 22.03 <= first['latitude'] <= 22.25
    assert 113.42 <= first['longitude'] <= 113.68
    assert first['provider'] in {'local_alias', 'excel_coordinates', 'amap_geocode'}
