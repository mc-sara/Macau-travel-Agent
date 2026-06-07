from typing import Any, Dict, List


def _find_step(plan: Dict[str, Any], keywords: List[str]) -> Dict[str, Any]:
    for step in plan.get("timeline", []):
        name = step.get("name", "")
        if any(keyword in name for keyword in keywords):
            return step
    return plan.get("timeline", [{}])[0]


def reserve_activity(plan: Dict[str, Any]) -> Dict[str, Any]:
    step = _find_step(plan, ["乐园", "展览", "旅游塔", "体验馆", "桌游"])
    return {
        "type": "activity",
        "status": "success",
        "order_id": f"ACT-MO-{abs(hash(plan.get('id', 'plan'))) % 10000:04d}",
        "message": f"{step.get('name', '活动')}预约成功",
    }


def reserve_restaurant(plan: Dict[str, Any]) -> Dict[str, Any]:
    step = _find_step(plan, ["餐厅", "小馆"])
    return {
        "type": "restaurant",
        "status": "success",
        "order_id": f"RES-MO-{abs(hash(plan.get('title', 'restaurant'))) % 10000:04d}",
        "message": f"{step.get('name', '餐厅')}订位成功",
    }


def order_drink_or_extra(plan: Dict[str, Any]) -> Dict[str, Any]:
    gift_step = _find_step(plan, ["花房", "蛋糕"])
    if gift_step.get("name") and any(keyword in gift_step["name"] for keyword in ["花房", "蛋糕"]):
        return {
            "type": "gift",
            "status": "success",
            "order_id": f"GFT-MO-{abs(hash(gift_step['name'])) % 10000:04d}",
            "message": f"{gift_step['name']}已安排配送",
        }
    drink_step = _find_step(plan, ["奶茶", "咖啡"])
    return {
        "type": "drink",
        "status": "success",
        "order_id": f"DRK-MO-{abs(hash(drink_step.get('name', 'drink'))) % 10000:04d}",
        "message": f"{drink_step.get('name', '饮品')}已提前点单",
    }


def send_plan_message(plan: Dict[str, Any], goal: Dict[str, Any]) -> str:
    names = " → ".join(step.get("name", "") for step in plan.get("timeline", []))
    scenario = goal.get("scenario")
    if scenario == "family":
        return f"搞定啦，今天下午带老婆孩子走轻松路线：{names}。每段路都比较短，餐厅也有低卡套餐和儿童椅。"
    if scenario == "friends":
        return f"今天下午朋友局安排好了：{names}。有拍照、有奶茶休息，晚餐4人桌也订好了。"
    if scenario == "couple":
        return f"今天下午约会安排好了：{names}。路线不累，晚餐靠窗位和鲜花惊喜也安排上了。"
    return f"今天下午路线安排好了：{names}。"


def execute_plan(plan: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    bookings = [
        reserve_activity(plan),
        reserve_restaurant(plan),
        order_drink_or_extra(plan),
    ]
    return {
        "status": "success",
        "bookings": bookings,
        "final_message": send_plan_message(plan, goal),
    }
