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


def _feature_value(features: Dict[str, Any], key: str, default: int = 60) -> int:
    value = features.get(key, default)
    try:
        return _clamp(float(value))
    except (TypeError, ValueError):
        return default


def _raw_text(value: Any) -> str:
    return str(value).strip().lower()


def _collect_poi_risks(poi: Dict[str, Any], feature_breakdown: Dict[str, int]) -> List[str]:
    raw = poi.get("accessibility_raw") or poi.get("accessibility") or {}
    risks: List[str] = []
    stairs_count = raw.get("stairs_count", 0) or 0
    try:
        stairs_count = int(float(stairs_count))
    except (TypeError, ValueError):
        stairs_count = 0
    steep = raw.get("steep_slopes")
    steep_text = _raw_text(steep)

    if feature_breakdown["stairs_comfort"] < 60 or stairs_count > 20 or steep_text in {"high", "medium_high"} or steep is True:
        risks.append("台阶或坡度风险较高，建议避开困难入口")
    elif feature_breakdown["stairs_comfort"] < 75 or stairs_count > 8:
        risks.append("有少量台阶或坡道，需放慢速度")

    if feature_breakdown["walking_comfort"] < 60:
        risks.append("内部步行距离偏长")
    if feature_breakdown["rest_support"] < 60:
        risks.append("休息座椅支持不足")
    if feature_breakdown["toilet_support"] < 60:
        risks.append("厕所或无障碍厕所信息不足")
    if feature_breakdown["weather_comfort"] < 60:
        risks.append("日晒或雨天暴露风险较高")
    if feature_breakdown["crowd_comfort"] < 60:
        risks.append("人流压力偏高")
    if feature_breakdown["ground_safety"] < 60:
        risks.append("地面或绊倒风险需要留意")
    if feature_breakdown["standing_comfort"] < 60:
        risks.append("久站风险偏高")

    avoid_route = str(raw.get("avoid_route_zh", "")).strip()
    if avoid_route:
        risks.append(f"避让建议：{avoid_route}")
    return list(dict.fromkeys(risks))[:5]


def _collect_poi_reasons(poi: Dict[str, Any], feature_breakdown: Dict[str, int]) -> List[str]:
    raw = poi.get("accessibility_raw") or poi.get("accessibility") or {}
    reasons: List[str] = []
    if feature_breakdown["walking_comfort"] >= 85:
        reasons.append("内部步行距离短")
    elif feature_breakdown["walking_comfort"] >= 75:
        reasons.append("步行距离可控")

    if feature_breakdown["stairs_comfort"] >= 85:
        reasons.append("台阶和坡度压力低")
    elif feature_breakdown["stairs_comfort"] >= 75:
        reasons.append("台阶风险相对可控")

    if feature_breakdown["accessibility_score"] >= 85:
        reasons.append("无障碍入口、电梯或坡道支持较好")
    elif feature_breakdown["accessibility_score"] >= 72:
        reasons.append("基础无障碍条件尚可")

    if feature_breakdown["rest_support"] >= 80 and feature_breakdown["toilet_support"] >= 80:
        reasons.append("休息点和厕所支持较完整")
    elif feature_breakdown["rest_support"] >= 80:
        reasons.append("有较好的休息点")
    elif feature_breakdown["toilet_support"] >= 80:
        reasons.append("厕所支持较好")

    if feature_breakdown["weather_comfort"] >= 82:
        reasons.append("遮阴、室内或空调休息条件较好")
    if feature_breakdown["crowd_comfort"] >= 82:
        reasons.append("人流压力相对低")
    if feature_breakdown["ground_safety"] >= 82:
        reasons.append("地面安全性较好")
    if feature_breakdown["standing_comfort"] >= 82:
        reasons.append("不需要长时间站立")
    if feature_breakdown["senior_interest_match"] >= 78:
        reasons.append("内容适合长者慢慢参观")

    best_access_route = str(raw.get("best_access_route_zh", "")).strip()
    if best_access_route:
        reasons.append(f"推荐入口：{best_access_route}")
    if not reasons:
        reasons.append(poi.get("reason") or "来自真实景点数据，适合短暂停留")
    return list(dict.fromkeys(reasons))[:5]


def score_poi(poi: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    features = dict(poi.get("score_features") or {})
    feature_breakdown = {
        "walking_comfort": _feature_value(features, "walking_comfort", _feature_value(features, "low_fatigue", 65)),
        "stairs_comfort": _feature_value(features, "stairs_comfort", _feature_value(features, "avoid_stairs", 65)),
        "accessibility_score": _feature_value(features, "accessibility_score", _feature_value(features, "senior_friendly", 65)),
        "rest_support": _feature_value(features, "rest_support", _feature_value(features, "rest_area", 60)),
        "toilet_support": _feature_value(features, "toilet_support", _feature_value(features, "toilet_access", 60)),
        "weather_comfort": _feature_value(features, "weather_comfort", _feature_value(features, "indoor", 60)),
        "crowd_comfort": _feature_value(features, "crowd_comfort", 60),
        "ground_safety": _feature_value(features, "ground_safety", 60),
        "standing_comfort": _feature_value(features, "standing_comfort", 60),
        "senior_interest_match": _feature_value(features, "senior_interest_match", 65),
    }

    weights = {
        "walking_comfort": 0.20,
        "stairs_comfort": 0.15,
        "accessibility_score": 0.15,
        "rest_support": 0.12,
        "toilet_support": 0.12,
        "weather_comfort": 0.08,
        "crowd_comfort": 0.08,
        "ground_safety": 0.05,
        "senior_interest_match": 0.05,
    }
    score = _weighted_score(feature_breakdown, weights)
    risk_flags = _collect_poi_risks(poi, feature_breakdown)
    reasons = _collect_poi_reasons(poi, feature_breakdown)

    return {
        "score": score,
        "reasons": reasons,
        "risk_flags": risk_flags,
        "feature_breakdown": feature_breakdown,
        # Backward-compatible shape used by current plan-level scorer.
        "breakdown": {
            **feature_breakdown,
            "senior_friendly": feature_breakdown["accessibility_score"],
            "low_fatigue": _clamp((feature_breakdown["walking_comfort"] + feature_breakdown["stairs_comfort"] + feature_breakdown["standing_comfort"]) / 3) if "standing_comfort" in feature_breakdown else _clamp((feature_breakdown["walking_comfort"] + feature_breakdown["stairs_comfort"]) / 2),
            "rest_toilet": _clamp((feature_breakdown["rest_support"] + feature_breakdown["toilet_support"]) / 2),
            "avoid_stairs": feature_breakdown["stairs_comfort"],
            "preference_match": feature_breakdown["senior_interest_match"],
            "indoor": feature_breakdown["weather_comfort"],
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
