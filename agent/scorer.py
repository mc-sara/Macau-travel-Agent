from typing import Any, Dict, List


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, round(value)))


def _route_quality(routes: List[Dict[str, Any]]) -> int:
    if not routes:
        return 70
    score = 100
    for route in routes:
        duration = route.get("duration_min", 0) or 0
        walking = route.get("walking_distance_m", 0) or 0
        if duration > 20:
            score -= 15
        elif duration > 15:
            score -= 6
        if walking > 500:
            score -= 25
        elif walking > 300:
            score -= 12
    return _clamp(score, 45, 100)


def _availability_quality(availability: List[Dict[str, Any]]) -> int:
    if not availability:
        return 75
    available_count = sum(1 for item in availability if item.get("available"))
    return round(100 * available_count / len(availability))


def _weighted_score(breakdown: Dict[str, int], weights: Dict[str, float]) -> int:
    return _clamp(sum(breakdown[key] * weights[key] for key in weights))


def _truthy_feature(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip() not in {"", "无", "官方未说明", "未知", "False", "false", "0"}


def score_poi(poi: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    tags = set(poi.get("tags", []))
    preferences = set(goal.get("preferences", []))
    features = dict(poi.get("score_features") or {})
    accessibility = poi.get("accessibility") or {}

    senior_friendly = features.get("senior_friendly", 90 if "senior_friendly" in tags else 65)
    low_fatigue = features.get("low_fatigue", 88 if "low_fatigue" in tags else 65)
    rest_area = features.get("rest_area", 90 if "rest_area" in tags else 55)
    toilet_access = features.get("toilet_access", 85 if _truthy_feature(accessibility.get("accessible_toilet")) else 60)
    avoid_stairs = features.get("avoid_stairs", 45 if accessibility.get("stairs_count", 0) else 85)
    poi_text = " ".join(str(poi.get(key, "")) for key in ["name", "category", "reason"])
    if any(word in poi_text for word in ["石阶", "台阶", "楼梯"]):
        avoid_stairs = min(avoid_stairs, 40)
        low_fatigue = min(low_fatigue, 65)
    indoor = features.get("indoor", 90 if "indoor" in tags else 55)

    preference_match = 70
    if preferences:
        preference_match += min(25, sum(1 for item in preferences if item in tags) * 8)
    if "historic" in tags or "photo_friendly" in tags:
        preference_match += 5

    weights = {
        "senior_friendly": 0.30,
        "low_fatigue": 0.20,
        "rest_toilet": 0.20,
        "avoid_stairs": 0.15,
        "preference_match": 0.10,
        "indoor": 0.05,
    }
    rest_toilet = (rest_area + toilet_access) / 2
    score = _weighted_score(
        {
            "senior_friendly": senior_friendly,
            "low_fatigue": low_fatigue,
            "rest_toilet": rest_toilet,
            "avoid_stairs": avoid_stairs,
            "preference_match": preference_match,
            "indoor": indoor,
        },
        weights,
    )

    reasons: List[str] = []
    if senior_friendly >= 85:
        reasons.append("适合长者慢慢参观")
    if low_fatigue >= 85:
        reasons.append("整体疲劳度较低")
    if rest_area >= 85 or toilet_access >= 80:
        reasons.append("有休息或洗手间支持")
    if indoor >= 85:
        reasons.append("室内或半室内体验较稳定")
    if not reasons:
        reasons.append(poi.get("reason") or "来自真实景点数据")

    risk_flags: List[str] = []
    if avoid_stairs < 70:
        risk_flags.append("可能有台阶或坡道，需现场留意")
    if rest_area < 65:
        risk_flags.append("休息点信息不足")
    if toilet_access < 65:
        risk_flags.append("洗手间信息不足")

    return {
        "score": score,
        "reasons": reasons[:3],
        "risk_flags": risk_flags,
        "breakdown": {
            "senior_friendly": _clamp(senior_friendly),
            "low_fatigue": _clamp(low_fatigue),
            "rest_toilet": _clamp(rest_toilet),
            "avoid_stairs": _clamp(avoid_stairs),
            "preference_match": _clamp(preference_match),
            "indoor": _clamp(indoor),
        },
    }


def _poi_quality(plan: Dict[str, Any]) -> int:
    poi_scores = [item.get("poi_score", {}).get("score") for item in plan.get("poi_details", [])]
    poi_scores = [score for score in poi_scores if isinstance(score, (int, float))]
    if poi_scores:
        return _clamp(sum(poi_scores) / len(poi_scores))
    tags = set(plan.get("tags", []))
    return 92 if "senior_friendly" in tags else 80


def _fatigue_quality(plan: Dict[str, Any]) -> int:
    tags = set(plan.get("tags", []))
    routes = plan.get("routes", [])
    base = 94 if "low_fatigue" in tags else _route_quality(routes)
    if len(plan.get("timeline", [])) > 3 and plan.get("scenario") == "senior":
        base -= 12
    for route in routes:
        if route.get("walking_distance_m", 0) > 500:
            base -= 15
    return _clamp(base, 45, 100)


def _rest_toilet_quality(plan: Dict[str, Any]) -> int:
    details = plan.get("poi_details", [])
    if details:
        scores = []
        for item in details:
            breakdown = item.get("poi_score", {}).get("breakdown", {})
            scores.append(breakdown.get("rest_toilet", 70))
        return _clamp(sum(scores) / len(scores))
    tags = set(plan.get("tags", []))
    return 92 if {"rest_area", "toilet_access"} & tags else 78


def score_plan(plan: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    tags = set(plan.get("tags", [])) | set(goal.get("preferences", []))
    routes = plan.get("routes", [])
    availability = plan.get("availability", [])
    route_score = _route_quality(routes)
    executable_score = _availability_quality(availability)

    if plan.get("poi_details"):
        breakdown = {
            "poi_quality": _poi_quality(plan),
            "transport_simplicity": route_score,
            "low_fatigue": _fatigue_quality(plan),
            "rest_toilet_support": _rest_toilet_quality(plan),
            "executable": executable_score,
        }
        weights = {
            "poi_quality": 0.35,
            "transport_simplicity": 0.25,
            "low_fatigue": 0.20,
            "rest_toilet_support": 0.10,
            "executable": 0.10,
        }
    else:
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
    for detail in plan.get("poi_details", [])[:2]:
        poi_reasons = detail.get("poi_score", {}).get("reasons", [])
        if poi_reasons:
            reasons.append(f"{detail.get('name')}：{poi_reasons[0]}。")

    risks = [
        "热门区域可能人流较多，建议现场优先选择有座椅的位置短暂停留。",
        "如长者当天体力不足，应切换到备选轻量路线或减少一个停留点。",
    ]
    for route in routes:
        if route.get("duration_min", 0) > 20:
            risks.append("存在单段转场超过 20 分钟的情况，建议预留缓冲时间。")
            break
    for detail in plan.get("poi_details", []):
        risks.extend(detail.get("poi_score", {}).get("risk_flags", [])[:1])

    return {"score": _weighted_score(breakdown, weights), "score_breakdown": breakdown, "reasons": reasons, "risks": list(dict.fromkeys(risks))[:5]}
