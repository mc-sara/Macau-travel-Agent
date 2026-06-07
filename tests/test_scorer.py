from agent.scorer import score_plan


def test_score_family_plan_returns_explanations_and_risks():
    goal = {'scenario': 'family'}
    plan = {
        'scenario': 'family',
        'timeline': [{'name': '二龙喉公园缆车'}, {'name': '澳门小熊亲子乐园'}, {'name': '轻悦生活餐厅'}],
        'routes': [{'duration_min': 12, 'walking_distance_m': 120}, {'duration_min': 9, 'walking_distance_m': 90}],
        'availability': [{'available': True}, {'available': True}],
        'tags': ['kid_friendly', 'low_fatigue', 'low_calorie'],
    }
    score = score_plan(plan, goal)
    assert score['score'] >= 80
    assert score['score_breakdown']
    assert any('儿童' in reason or '亲子' in reason for reason in score['reasons'])
    assert any('大三巴' in risk or '台阶' in risk for risk in score['risks'])


def test_score_friends_plan_prioritizes_social_and_route():
    goal = {'scenario': 'friends'}
    plan = {
        'scenario': 'friends',
        'timeline': [{'name': '议事亭前地'}, {'name': '玫瑰圣母堂'}, {'name': '氹仔葡式小馆'}],
        'routes': [{'duration_min': 5, 'walking_distance_m': 260}, {'duration_min': 18, 'walking_distance_m': 140}],
        'availability': [{'available': True}],
        'tags': ['social', 'photo_friendly', 'chat_friendly'],
    }
    score = score_plan(plan, goal)
    assert score['score'] >= 75
    assert any('拍照' in reason or '聊天' in reason for reason in score['reasons'])


def test_score_couple_plan_includes_surprise_reason():
    goal = {'scenario': 'couple'}
    plan = {
        'scenario': 'couple',
        'timeline': [{'name': '澳门旅游塔'}, {'name': '塔景氛围餐厅'}, {'name': '小岛花房'}],
        'routes': [{'duration_min': 15, 'walking_distance_m': 100}, {'duration_min': 9, 'walking_distance_m': 110}],
        'availability': [{'available': True}, {'available': True}],
        'tags': ['romantic', 'low_fatigue', 'photo_friendly', 'surprise'],
    }
    score = score_plan(plan, goal)
    assert score['score'] >= 80
    assert any('鲜花' in reason or '惊喜' in reason for reason in score['reasons'])
