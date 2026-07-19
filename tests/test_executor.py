from agent.executor import build_oral_guide, build_route_card, execute_plan, order_drink_or_extra, reserve_activity, reserve_restaurant, send_plan_message
from agent.planner import plan_day


def test_execute_senior_plan_returns_bookings_route_card_and_message():
    result = plan_day('我想带爸妈下午轻松逛逛，不想爬楼梯，最好有地方坐。')
    execution = execute_plan(result['best_plan'], result['goal'])
    assert execution['bookings']
    assert all(item['status'] == 'success' for item in execution['bookings'])
    assert execution['route_card']['large_text_ready'] is True
    assert execution['route_card']['boarding_instruction']
    assert execution['route_card']['dropoff_instruction']
    assert execution['route_card']['walking_instruction']
    assert execution['oral_guide']['mandarin']
    assert execution['oral_guide']['cantonese']
    assert execution['qwenpaw_actions'][0]['channel'] == 'booking'
    assert '长者路线卡' in execution['final_message']


def test_reserve_activity_creates_order_id():
    result = plan_day('我想带爸妈下午轻松逛逛。')
    booking = reserve_activity(result['best_plan'])
    assert booking['status'] == 'success'
    assert booking['order_id'].startswith('ACT-MO-')


def test_reserve_restaurant_creates_order_id_and_light_food_note():
    result = plan_day('我想带爸妈晚上吃点清淡的。')
    booking = reserve_restaurant(result['best_plan'])
    assert booking['status'] == 'success'
    assert booking['order_id'].startswith('RES-MO-')
    assert '少油少盐' in booking['message']


def test_order_drink_or_extra_uses_less_sugar_note():
    result = plan_day('带妈妈轻松逛逛，想喝点东西但不要太甜。')
    order = order_drink_or_extra(result['best_plan'])
    assert order['status'] == 'success'
    assert order['order_id'].startswith('DRK-MO-')
    assert '少糖少冰' in order['message']


def test_send_plan_message_is_senior_specific():
    result = plan_day('下午带爷爷奶奶在澳门走走，路不要太长。')
    message = send_plan_message(result['best_plan'], result['goal'])
    assert 'QwenPaw' in message
    assert '少步行' in message
    assert '避楼梯' in message


def test_build_route_card_has_three_instruction_fields():
    result = plan_day('外婆走路慢，最好全程有电梯或无障碍通道。')
    card = build_route_card(result['best_plan'])
    assert card['boarding_instruction']
    assert card['dropoff_instruction']
    assert card['walking_instruction']
    assert card['language'] == 'zh-CN / zh-HK'
    assert len(card['sentences']) == 3
    assert '电梯' in card['sentences'][2] or '平路' in card['sentences'][2]


def test_build_oral_guide_returns_mandarin_and_cantonese_copy():
    result = plan_day('下午带爷爷奶奶在澳门走走，路不要太长，中途最好有厕所和座椅。')
    guide = build_oral_guide(result['best_plan'], result['goal'])
    assert '我们现在先去' in guide['mandarin']
    assert '我哋而家先去' in guide['cantonese']
    assert guide['tts_config']['rate'] == '-15%'
