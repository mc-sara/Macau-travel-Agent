from typing import Any, Dict, List


def _route_quality(routes: List[Dict[str, Any]]) -> int:
    if not routes:
        return 60
    long_segments = sum(1 for route in routes if route.get("duration_min", 0) > 18)
    high_walk = sum(1 for route in routes if route.get("walking_distance_m", 0) > 400)
    score = 100 - long_segments * 15 - high_walk * 15
    return max(50, min(100, score))


def _availability_quality(availability: List[Dict[str, Any]]) -> int:
    if not availability:
        return 70
    available_count = sum(1 for item in availability if item.get("available"))
    return round(100 * available_count / len(availability))


def _weighted_score(breakdown: Dict[str, int], weights: Dict[str, float]) -> int:
    return round(sum(breakdown[key] * weights[key] for key in weights))


def score_plan(plan: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    scenario = goal.get("scenario") or plan.get("scenario")
    tags = set(plan.get("tags", []))
    routes = plan.get("routes", [])
    availability = plan.get("availability", [])
    route_score = _route_quality(routes)
    executable_score = _availability_quality(availability)
    reasons: List[str] = []
    risks: List[str] = []

    if scenario == "family":
        breakdown = {
            "kid_friendly": 95 if "kid_friendly" in tags else 75,
            "low_fatigue": 95 if "low_fatigue" in tags else route_score,
            "route_smoothness": route_score,
            "low_calorie_food": 92 if "low_calorie" in tags else 70,
            "executable": executable_score,
        }
        weights = {
            "kid_friendly": 0.25,
            "low_fatigue": 0.25,
            "route_smoothness": 0.20,
            "low_calorie_food": 0.20,
            "executable": 0.10,
        }
        reasons.extend([
            "亲子乐园和缆车组合适合5岁儿童，下午节奏轻松。",
            "每段交通时间短、步行少，符合低疲劳要求。",
            "餐厅提供低卡套餐和儿童椅，兼顾家长减脂和孩子用餐。",
            "活动票和餐厅座位可用，方案可执行。",
        ])
        risks.append("不推荐走大三巴正门：有68级台阶，孩子和家长容易累。")
    elif scenario == "friends":
        breakdown = {
            "social_value": 94 if "social" in tags else 75,
            "photo_value": 90 if "photo_friendly" in tags else 70,
            "route_smoothness": route_score,
            "restaurant_match": 90 if "chat_friendly" in tags else 75,
            "executable": executable_score,
        }
        weights = {
            "social_value": 0.25,
            "photo_value": 0.15,
            "route_smoothness": 0.20,
            "restaurant_match": 0.20,
            "executable": 0.20,
        }
        reasons.extend([
            "议事亭前地和玫瑰圣母堂拍照价值高，适合朋友 citywalk。",
            "中途安排奶茶休息，适合聊天和等人。",
            "晚餐选择4人桌和分享菜，适合朋友聚餐。",
            "路线从半岛核心区到晚餐点，不明显折返。",
        ])
        if "escape_room" in tags:
            reasons.insert(0, "已识别用户明确想去密室，方案加入澳门悬疑密室体验馆并检查可预约余位。")
    elif scenario == "couple":
        breakdown = {
            "romance": 96 if "romantic" in tags else 75,
            "low_fatigue": 92 if "low_fatigue" in tags else route_score,
            "photo_value": 88 if "photo_friendly" in tags else 70,
            "dining_experience": 92,
            "surprise_execution": 95 if "surprise" in tags else 65,
        }
        weights = {
            "romance": 0.30,
            "low_fatigue": 0.20,
            "photo_value": 0.15,
            "dining_experience": 0.20,
            "surprise_execution": 0.15,
        }
        reasons.extend([
            "旅游塔观景、咖啡和氛围餐厅连续形成约会氛围。",
            "室内点位和短途打车为主，不需要长时间步行。",
            "鲜花可配送到餐厅，能形成明确的惊喜执行动作。",
            "餐厅可订靠窗位，适合拍照和约会。",
        ])
    else:
        breakdown = {"route_smoothness": route_score, "executable": executable_score}
        weights = {"route_smoothness": 0.6, "executable": 0.4}
        reasons.append("路线和可执行性满足基础本地生活安排。")

    return {
        "score": _weighted_score(breakdown, weights),
        "score_breakdown": breakdown,
        "reasons": reasons,
        "risks": risks,
    }
