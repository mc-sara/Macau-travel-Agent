from agent.executor import execute_plan, order_drink_or_extra, reserve_activity, reserve_restaurant, send_plan_message
from agent.planner import plan_day


def test_execute_family_plan_returns_bookings_and_message():
    result = plan_day('今天下午想和老婆孩子出去玩几个小时，别离家太远。')
    execution = execute_plan(result['best_plan'], result['goal'])
    assert execution['bookings']
    assert all(item['status'] == 'success' for item in execution['bookings'])
    assert '老婆' in execution['final_message'] or '孩子' in execution['final_message']
    assert execution['final_message']


def test_reserve_activity_creates_order_id():
    result = plan_day('今天下午想和对象约会，浪漫一点但别太累。')
    booking = reserve_activity(result['best_plan'])
    assert booking['status'] == 'success'
    assert booking['order_id'].startswith('ACT-MO-')


def test_reserve_restaurant_creates_order_id():
    result = plan_day('今天下午和朋友4个人出去玩，2男2女，安排一下。')
    booking = reserve_restaurant(result['best_plan'])
    assert booking['status'] == 'success'
    assert booking['order_id'].startswith('RES-MO-')


def test_order_drink_or_extra_handles_couple_gift():
    result = plan_day('今天下午想和对象约会，浪漫一点但别太累。')
    order = order_drink_or_extra(result['best_plan'])
    assert order['status'] == 'success'
    assert order['order_id'].startswith(('DRK-MO-', 'GFT-MO-'))


def test_send_plan_message_is_scenario_specific():
    result = plan_day('今天下午想和对象约会，浪漫一点但别太累。')
    message = send_plan_message(result['best_plan'], result['goal'])
    assert '约会' in message or '鲜花' in message or '旅游塔' in message
