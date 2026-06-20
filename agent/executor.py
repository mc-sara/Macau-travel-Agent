from typing import Any, Dict, List


def _find_step(plan: Dict[str, Any], keywords: List[str]) -> Dict[str, Any]:
    for step in plan.get("timeline", []):
        name = step.get("name", "")
        if any(keyword in name for keyword in keywords):
            return step
    return plan.get("timeline", [{}])[0]


def reserve_activity(plan: Dict[str, Any]) -> Dict[str, Any]:
    step = _find_step(plan, ["前地", "公园", "展览", "塔", "空间"])
    return {"type": "activity", "status": "success", "order_id": f"ACT-MO-{abs(hash(plan.get('id', 'plan'))) % 10000:04d}", "message": f"{step.get('name', '适老停留点')}已加入路线卡"}


def reserve_restaurant(plan: Dict[str, Any]) -> Dict[str, Any]:
    step = _find_step(plan, ["餐厅", "小馆"])
    return {"type": "restaurant", "status": "success", "order_id": f"RES-MO-{abs(hash(plan.get('title', 'restaurant'))) % 10000:04d}", "message": f"{step.get('name', '清淡餐厅')}订位成功，已备注少油少盐"}


def order_drink_or_extra(plan: Dict[str, Any]) -> Dict[str, Any]:
    drink_step = _find_step(plan, ["奶茶", "咖啡", "饮品"])
    return {"type": "drink", "status": "success", "order_id": f"DRK-MO-{abs(hash(drink_step.get('name', 'drink'))) % 10000:04d}", "message": f"{drink_step.get('name', '饮品')}已提前点单，备注少糖少冰"}


def build_route_card(plan: Dict[str, Any]) -> Dict[str, Any]:
    first = plan.get("timeline", [{}])[0].get("name", "第一站")
    return {
        "boarding_instruction": "从出发点打车或乘坐最近的无障碍接驳点上车",
        "dropoff_instruction": f"到 {first} 附近下车",
        "walking_instruction": "下车后优先走平路和电梯通道，单段步行控制在 5 到 8 分钟内",
        "risk_note": "如果人多或感觉累，先找座椅休息 10 分钟再继续",
        "large_text_ready": True,
    }


def send_plan_message(plan: Dict[str, Any], goal: Dict[str, Any]) -> str:
    names = " → ".join(step.get("name", "") for step in plan.get("timeline", []))
    return f"QwenPaw 已生成长者路线卡：{names}。全程按少步行、避楼梯和可休息原则安排，餐厅已备注清淡少油少盐。"


def execute_plan(plan: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    bookings = [reserve_activity(plan), reserve_restaurant(plan), order_drink_or_extra(plan)]
    return {"status": "success", "bookings": bookings, "route_card": build_route_card(plan), "final_message": send_plan_message(plan, goal)}
