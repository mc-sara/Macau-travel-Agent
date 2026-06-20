from typing import Any, Dict, List


def _route_quality(routes: List[Dict[str, Any]]) -> int:
    if not routes:
        return 70
    long_segments = sum(1 for route in routes if route.get("duration_min", 0) > 18)
    high_walk = sum(1 for route in routes if route.get("walking_distance_m", 0) > 300)
    score = 100 - long_segments * 15 - high_walk * 20
    return max(50, min(100, score))


def _availability_quality(availability: List[Dict[str, Any]]) -> int:
    if not availability:
        return 70
    available_count = sum(1 for item in availability if item.get("available"))
    return round(100 * available_count / len(availability))


def _weighted_score(breakdown: Dict[str, int], weights: Dict[str, float]) -> int:
    return round(sum(breakdown[key] * weights[key] for key in weights))


def score_plan(plan: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    tags = set(plan.get("tags", [])) | set(goal.get("preferences", []))
    routes = plan.get("routes", [])
    availability = plan.get("availability", [])
    route_score = _route_quality(routes)
    executable_score = _availability_quality(availability)

    breakdown = {
        "senior_friendly": 96 if "senior_friendly" in tags else 82,
        "transport_simplicity": route_score,
        "low_fatigue": 96 if "low_fatigue" in tags else route_score,
        "rest_toilet_support": 94 if {"rest_area", "toilet_access"} & tags else 78,
        "executable": executable_score,
    }
    weights = {
        "senior_friendly": 0.35,
        "transport_simplicity": 0.25,
        "low_fatigue": 0.20,
        "rest_toilet_support": 0.10,
        "executable": 0.10,
    }
    reasons = [
        "方案优先控制步行距离和转场时间，适合长者低疲劳出行。",
        "路线避开明显台阶和长队风险，并保留休息节奏。",
        "餐饮安排偏清淡，可备注少油少盐或少糖少冰。",
        "订位、点单和路线卡可由 QwenPaw 模拟执行，便于家属确认。",
    ]
    risks = [
        "热门区域可能人流较多，建议现场优先选择有座椅的位置短暂停留。",
        "如长者当天体力不足，应切换到备选轻量路线或减少一个停留点。",
    ]
    return {"score": _weighted_score(breakdown, weights), "score_breakdown": breakdown, "reasons": reasons, "risks": risks}
