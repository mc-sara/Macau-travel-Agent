from typing import Any, Dict, List

from agent.mock_data import load_merchants


ATTRACTIONS: List[Dict[str, Any]] = [
    {
        "id": "attraction_guia_cable_car",
        "name": "二龙喉公园缆车",
        "region": "澳门半岛",
        "tags": ["family", "low_fatigue", "kid_friendly", "cable_car"],
        "duration_min": 60,
        "features": ["缆车", "公园", "入口区域轻松", "适合儿童"],
    },
    {
        "id": "attraction_ruins_st_paul",
        "name": "大三巴牌坊",
        "region": "澳门半岛",
        "tags": ["photo_friendly", "historic", "stairs_risk"],
        "duration_min": 45,
        "features": ["地标", "拍照", "正门台阶多"],
    },
    {
        "id": "attraction_senado_square",
        "name": "议事亭前地",
        "region": "澳门半岛",
        "tags": ["friends", "photo_friendly", "citywalk"],
        "duration_min": 45,
        "features": ["拍照", "citywalk", "交通便利"],
    },
    {
        "id": "attraction_st_dominic",
        "name": "玫瑰圣母堂",
        "region": "澳门半岛",
        "tags": ["friends", "photo_friendly", "historic"],
        "duration_min": 35,
        "features": ["建筑", "拍照", "靠近议事亭前地"],
    },
    {
        "id": "attraction_macau_tower",
        "name": "澳门旅游塔",
        "region": "澳门半岛",
        "tags": ["couple", "romantic", "photo_friendly", "indoor"],
        "duration_min": 60,
        "features": ["观景", "室内", "约会氛围"],
    },
]

ACCESSIBILITY: Dict[str, Dict[str, Any]] = {
    "attraction_guia_cable_car": {
        "stairs_count": 8,
        "steep_slopes": False,
        "rest_areas": "较多",
        "senior_tips_zh": "建议乘坐缆车并停留在入口和平台区域，步行压力低。",
    },
    "attraction_ruins_st_paul": {
        "stairs_count": 68,
        "steep_slopes": True,
        "rest_areas": "少",
        "senior_tips_zh": "正面有68级石阶，亲子或长者路线建议避开正门台阶。",
    },
    "attraction_senado_square": {
        "stairs_count": 0,
        "steep_slopes": False,
        "rest_areas": "中等",
        "senior_tips_zh": "广场区域较平坦，但人流较多，建议控制停留时间。",
    },
    "attraction_st_dominic": {
        "stairs_count": 5,
        "steep_slopes": False,
        "rest_areas": "中等",
        "senior_tips_zh": "靠近议事亭前地，步行距离短，适合轻量 citywalk。",
    },
    "attraction_macau_tower": {
        "stairs_count": 0,
        "steep_slopes": False,
        "rest_areas": "较多",
        "senior_tips_zh": "室内电梯和座位充足，适合低疲劳约会。",
    },
}

ROUTES: Dict[tuple, Dict[str, Any]] = {
    ("家", "二龙喉公园缆车"): {"route_distance_km": 2.8, "duration_min": 12, "walking_distance_m": 120, "transfer_count": 0, "traffic_level": "smooth", "route_summary": "打车约12分钟，门口上下车，步行少"},
    ("二龙喉公园缆车", "澳门小熊亲子乐园"): {"route_distance_km": 1.9, "duration_min": 9, "walking_distance_m": 90, "transfer_count": 0, "traffic_level": "smooth", "route_summary": "短途打车，适合带孩子衔接"},
    ("澳门小熊亲子乐园", "轻悦生活餐厅"): {"route_distance_km": 2.1, "duration_min": 10, "walking_distance_m": 100, "transfer_count": 0, "traffic_level": "smooth", "route_summary": "活动后直接去餐厅，孩子不容易累"},
    ("轻悦生活餐厅", "茶语澳门低糖奶茶"): {"route_distance_km": 0.6, "duration_min": 6, "walking_distance_m": 180, "transfer_count": 0, "traffic_level": "smooth", "route_summary": "餐后附近取低糖饮品，适合收尾"},
    ("家", "议事亭前地"): {"route_distance_km": 3.0, "duration_min": 14, "walking_distance_m": 160, "transfer_count": 0, "traffic_level": "normal", "route_summary": "打车到核心步行区，开场方便"},
    ("议事亭前地", "玫瑰圣母堂"): {"route_distance_km": 0.3, "duration_min": 5, "walking_distance_m": 260, "transfer_count": 0, "traffic_level": "walk", "route_summary": "步行拍照路线，不折返"},
    ("玫瑰圣母堂", "茶语澳门低糖奶茶"): {"route_distance_km": 0.5, "duration_min": 6, "walking_distance_m": 350, "transfer_count": 0, "traffic_level": "walk", "route_summary": "中途奶茶休息，方便聊天"},
    ("茶语澳门低糖奶茶", "澳门城市展览空间"): {"route_distance_km": 1.2, "duration_min": 8, "walking_distance_m": 120, "transfer_count": 0, "traffic_level": "smooth", "route_summary": "从休息点转到室内展览，节奏舒适"},
    ("澳门城市展览空间", "氹仔葡式小馆"): {"route_distance_km": 5.1, "duration_min": 18, "walking_distance_m": 140, "transfer_count": 0, "traffic_level": "normal", "route_summary": "晚餐转场到氹仔，适合4人聚餐"},
    ("家", "澳门旅游塔"): {"route_distance_km": 4.2, "duration_min": 15, "walking_distance_m": 100, "transfer_count": 0, "traffic_level": "smooth", "route_summary": "短途打车到旅游塔，室内观景不累"},
    ("澳门旅游塔", "海风咖啡"): {"route_distance_km": 1.1, "duration_min": 7, "walking_distance_m": 80, "transfer_count": 0, "traffic_level": "smooth", "route_summary": "观景后去咖啡甜品，氛围连续"},
    ("海风咖啡", "塔景氛围餐厅"): {"route_distance_km": 1.6, "duration_min": 9, "walking_distance_m": 110, "transfer_count": 0, "traffic_level": "smooth", "route_summary": "晚餐短途转场，可订靠窗位"},
    ("塔景氛围餐厅", "小岛花房"): {"route_distance_km": 0.0, "duration_min": 0, "walking_distance_m": 0, "transfer_count": 0, "traffic_level": "delivery", "route_summary": "鲜花配送到餐厅，无需用户额外移动"},
}


def search_attractions(goal: Dict[str, Any]) -> List[Dict[str, Any]]:
    scenario = goal.get("scenario")
    if scenario == "senior":
        return [item for item in ATTRACTIONS if item["id"] in {"attraction_senado_square", "attraction_guia_cable_car", "attraction_macau_tower", "attraction_ruins_st_paul"}]
    if scenario == "family":
        return [item for item in ATTRACTIONS if "family" in item["tags"] or item["id"] == "attraction_ruins_st_paul"]
    if scenario == "friends":
        return [item for item in ATTRACTIONS if "friends" in item["tags"]]
    if scenario == "couple":
        return [item for item in ATTRACTIONS if "couple" in item["tags"]]
    return ATTRACTIONS[:]


def get_accessibility(attraction_id: str) -> Dict[str, Any]:
    return ACCESSIBILITY.get(attraction_id, {"stairs_count": 0, "steep_slopes": False, "rest_areas": "未知", "senior_tips_zh": "暂无特殊风险。"})


def mock_map_route_api(origin: str, destination: str, mode: str = "taxi") -> Dict[str, Any]:
    route = ROUTES.get((origin, destination))
    if route is None:
        route = {"route_distance_km": 2.5, "duration_min": 12, "walking_distance_m": 180, "transfer_count": 0, "traffic_level": "normal", "route_summary": f"{mode} 模拟路线：距离和时间适中"}
    return {"origin": origin, "destination": destination, "mode": mode, **route}


def search_local_merchants(goal: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    merchants = load_merchants()
    scenario = goal.get("scenario")
    if scenario == "senior":
        restaurants = [item for item in merchants["restaurants"] if "family" in item.get("scenario_tags", []) or item.get("id") == "res_001"]
        return {
            "senior_activities": [],
            "family_activities": [],
            "friend_activities": [],
            "couple_activities": [],
            "restaurants": restaurants,
            "drink_shops": merchants["drink_shops"],
            "gift_shops": [],
        }
    restaurants = [item for item in merchants["restaurants"] if scenario in item.get("scenario_tags", [])]
    return {
        "family_activities": merchants["family_activities"] if scenario == "family" else [],
        "friend_activities": merchants["friend_activities"] if scenario == "friends" else [],
        "couple_activities": merchants["couple_activities"] if scenario == "couple" else [],
        "restaurants": restaurants,
        "drink_shops": merchants["drink_shops"],
        "gift_shops": merchants["gift_shops"] if scenario == "couple" else [],
    }


def _all_items() -> List[Dict[str, Any]]:
    merchants = load_merchants()
    items: List[Dict[str, Any]] = []
    for category_items in merchants.values():
        items.extend(category_items)
    return items


def check_availability(item_id: str, time: str, people_count: int) -> Dict[str, Any]:
    for item in _all_items():
        if item.get("id") == item_id:
            available = time in item.get("available_slots", []) and item.get("tickets_left", people_count) >= people_count
            return {
                "item_id": item_id,
                "name": item.get("name"),
                "available": available,
                "time": time,
                "people_count": people_count,
                "queue_minutes": item.get("queue_minutes", 0),
                "tickets_left": item.get("tickets_left"),
                "message": "可预约/有位" if available else "当前时间不可用",
            }
    return {"item_id": item_id, "available": False, "time": time, "people_count": people_count, "queue_minutes": None, "message": "未找到该项目"}
