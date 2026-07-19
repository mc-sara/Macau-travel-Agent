from typing import Any, Dict, List


def _find_step(plan: Dict[str, Any], keywords: List[str]) -> Dict[str, Any]:
    for step in plan.get("timeline", []):
        name = step.get("name", "")
        if any(keyword in name for keyword in keywords):
            return step
    return plan.get("timeline", [{}])[0]


def _first_step(plan: Dict[str, Any]) -> Dict[str, Any]:
    return plan.get("timeline", [{}])[0]


def _first_route(plan: Dict[str, Any]) -> Dict[str, Any]:
    return plan.get("routes", [{}])[0]


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
    first = _first_step(plan).get("name", "第一站")
    route = _first_route(plan)
    destination = route.get("destination", first)
    duration = route.get("duration_min", 10)
    walking = route.get("walking_distance_m", 180)
    boarding = "在家门口或最近的无障碍上车点上车；如果不熟路，建议直接打车或让家属叫车。"
    dropoff = f"坐到 {destination} 附近下车，预计车程约 {duration} 分钟。"
    walking_instruction = f"下车后走平路或电梯通道，步行约 {walking} 米；累了先找座椅休息 10 分钟，不要勉强爬楼梯。"
    return {
        "boarding_instruction": boarding,
        "dropoff_instruction": dropoff,
        "walking_instruction": walking_instruction,
        "sentences": [boarding, dropoff, walking_instruction],
        "risk_note": "如果人多、下雨或长者觉得累，优先改为室内休息点或直接前往餐厅。",
        "language": "zh-CN / zh-HK",
        "large_text_ready": True,
    }


def build_oral_guide(plan: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    first = _first_step(plan).get("name", "第一站")
    route = _first_route(plan)
    destination = route.get("destination", first)
    walking = route.get("walking_distance_m", 180)
    mandarin = f"我们现在先去{first}。等一下在{destination}附近下车，下车后慢慢走，大概步行{walking}米，尽量走平路和电梯。路上如果累了，就先坐下来休息，不用赶时间。"
    cantonese = f"我哋而家先去{first}。等阵喺{destination}附近落车，落车之后慢慢行，大概行{walking}米，尽量行平路同搭电梯。中途攰嘅话，就坐低休息阵，唔使赶。"
    return {
        "mandarin": mandarin,
        "cantonese": cantonese,
        "tts_config": {
            "provider": "mock-edge-tts",
            "voice_zh_cn": "zh-CN-XiaoxiaoNeural",
            "voice_zh_hk": "zh-HK-HiuMaanNeural",
            "rate": "-15%",
            "pitch": "-2Hz",
            "status": "mock_ready",
        },
    }


def build_qwenpaw_actions(plan: Dict[str, Any], goal: Dict[str, Any], bookings: List[Dict[str, Any]], route_card: Dict[str, Any], oral_guide: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"channel": "booking", "status": "success", "summary": f"已处理 {len(bookings)} 个订位/点单动作", "details": bookings},
        {"channel": "wechat_route_card", "status": "success", "summary": "已模拟发送三句话路线卡给家属", "preview": " / ".join(route_card["sentences"])},
        {"channel": "voice_guide", "status": "success", "summary": "已生成普通话和粤语语音导游词，等待 TTS 播放或发送", "preview": oral_guide["mandarin"]},
        {"channel": "family_notice", "status": "success", "summary": "已模拟通知家属：路线低疲劳、少步行、可休息"},
    ]


def send_plan_message(plan: Dict[str, Any], goal: Dict[str, Any]) -> str:
    names = " → ".join(step.get("name", "") for step in plan.get("timeline", []))
    return f"QwenPaw 已生成长者路线卡：{names}。全程按少步行、避楼梯和可休息原则安排，餐厅已备注清淡少油少盐，并已准备普通话/粤语语音导游词。"


def execute_plan(plan: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    bookings = [reserve_activity(plan), reserve_restaurant(plan), order_drink_or_extra(plan)]
    route_card = build_route_card(plan)
    oral_guide = build_oral_guide(plan, goal)
    qwenpaw_actions = build_qwenpaw_actions(plan, goal, bookings, route_card, oral_guide)
    return {
        "status": "success",
        "bookings": bookings,
        "route_card": route_card,
        "oral_guide": oral_guide,
        "qwenpaw_actions": qwenpaw_actions,
        "final_message": send_plan_message(plan, goal),
    }
