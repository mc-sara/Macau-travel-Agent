from typing import Any, Dict, List, Optional, Tuple
import re

from agent.scorer import score_plan, score_poi
from agent.tools import amap_geocode, check_availability, mock_map_route_api, search_attractions


TIMES = ["14:00", "15:00", "16:20", "17:40"]


def _timeline(names: List[str]) -> List[Dict[str, Any]]:
    return [{"time": time, "name": name} for time, name in zip(TIMES, names)]


def _scenario_title(_scenario: str, index: int) -> str:
    return ["长者低疲劳精选路线", "长者文化慢游路线", "长者轻量备选路线"][min(index, 2)]


def _route_cost(routes: List[Dict[str, Any]]) -> int:
    cost = 0
    for route in routes:
        cost += int(route.get("duration_min", 0) or 0)
        cost += int((route.get("walking_distance_m", 0) or 0) / 50)
    return cost


def _route_penalty(routes: List[Dict[str, Any]], scenario: str) -> int:
    penalty = 0
    for route in routes:
        duration = route.get("duration_min", 0) or 0
        walking = route.get("walking_distance_m", 0) or 0
        if duration > 20:
            penalty += 18
        elif duration > 15:
            penalty += 7
        if walking > 500:
            penalty += 25
        elif walking > 300:
            penalty += 10
    if scenario == "senior":
        penalty += max(0, len(routes) - 2) * 5
    return penalty


def _goal_text(goal: Dict[str, Any]) -> str:
    structured = goal.get("structured_goal") or {}
    return " ".join(
        str(value or "")
        for value in [goal.get("raw_text", ""), structured.get("raw_text", "")]
    )


def _goal_preferences(goal: Dict[str, Any]) -> set:
    structured = goal.get("structured_goal") or {}
    values: List[Any] = []
    # For hard filtering, use only constraints that are likely explicit. The flat
    # legacy `preferences` list is senior-safe by default and contains items such
    # as avoid_stairs/low_fatigue even when the user did not ask for them.
    if structured:
        values.extend(structured.get("hard_constraints", []) or [])
        values.extend(structured.get("soft_preferences", []) or [])
    else:
        values.extend(goal.get("preferences", []) or [])
    return {str(item) for item in values if item}


def _explicit_filter_modes(goal: Dict[str, Any]) -> set:
    prefs = _goal_preferences(goal)
    structured = goal.get("structured_goal") or {}
    text = _goal_text(goal)
    modes = set()
    if {"wheelchair_friendly", "elevator_required"} & prefs or any(word in text for word in ["轮椅", "无障碍", "电梯", "升降机"]):
        modes.add("wheelchair")
    if {"avoid_stairs", "flat_route", "elevator_required"} & prefs or any(word in text for word in ["不能爬楼梯", "不要爬楼梯", "不爬楼梯", "避开楼梯", "不要台阶", "不能走台阶", "无台阶"]):
        modes.add("stairs")
    # low_fatigue / short_walking_distance are senior defaults in the parser, so
    # only treat them as hard filters when there is no structured parser payload
    # or when the raw text explicitly mentions walking difficulty.
    explicit_short_walk_text = any(word in text for word in ["少走路", "走路少", "路不要太长", "走不远", "腿脚不好", "走路慢", "低疲劳"])
    if explicit_short_walk_text or (not structured and {"short_walking_distance"} & prefs):
        modes.add("short_walking")
    return modes


def _float_raw(raw: Dict[str, Any], key: str, default: float = 0) -> float:
    try:
        return float(raw.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _is_high(value: Any) -> bool:
    return str(value).strip().lower() in {"high", "medium_high", "高", "较高"}


def _hard_filter_reason(poi: Dict[str, Any], modes: set) -> Optional[str]:
    raw = poi.get("accessibility_raw") or poi.get("accessibility") or {}
    wheelchair = str(raw.get("wheelchair_friendly", "")).strip().lower()
    stairs_count = _float_raw(raw, "stairs_count", 0)
    steep_slopes = raw.get("steep_slopes")
    walking_distance = _float_raw(raw, "estimated_walking_distance_m", 0)
    trip_hazards = raw.get("trip_hazards")

    if "wheelchair" in modes and wheelchair in {"no", "false", "0", "否", "无"}:
        return "wheelchair_friendly=no"
    if "stairs" in modes and stairs_count > 20:
        return "stairs_count>20"
    if "stairs" in modes and _is_high(steep_slopes):
        return "steep_slopes=high"
    if "short_walking" in modes and walking_distance > 650:
        return "estimated_walking_distance_m>650"
    if ({"stairs", "short_walking", "wheelchair"} & modes) and _is_high(trip_hazards):
        return "trip_hazards=high"
    return None


def _filter_candidates_by_hard_constraints(candidates: List[Dict[str, Any]], goal: Dict[str, Any]) -> List[Dict[str, Any]]:
    modes = _explicit_filter_modes(goal)
    if not modes:
        return candidates
    kept: List[Dict[str, Any]] = []
    for poi in candidates:
        reason = _hard_filter_reason(poi, modes)
        if not reason:
            kept.append(poi)
    return kept


def _rank_candidate_pois(goal: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    seen = set()
    for poi in search_attractions(goal, limit=None):
        name = poi.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        item = dict(poi)
        item["poi_score"] = score_poi(item, goal)
        candidates.append(item)
    ranked = sorted(candidates, key=lambda item: item["poi_score"]["score"], reverse=True)
    filtered = _filter_candidates_by_hard_constraints(ranked, goal)
    return filtered[:limit] if limit is not None else filtered


def _parse_location(location: str) -> Optional[Tuple[float, float]]:
    if not location or "," not in str(location):
        return None
    try:
        lng, lat = [float(part) for part in str(location).split(",", 1)]
        return lat, lng
    except (TypeError, ValueError):
        return None


def _poi_coords(poi: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    lat = poi.get("latitude")
    lng = poi.get("longitude")
    if lat is not None and lng is not None:
        try:
            return float(lat), float(lng)
        except (TypeError, ValueError):
            pass
    return _parse_location(str(poi.get("location", "")))


def _origin_text(goal: Dict[str, Any]) -> str:
    structured = goal.get("structured_goal") or {}
    location = structured.get("location", {}) if isinstance(structured.get("location", {}), dict) else {}
    origin = goal.get("origin") or location.get("start_location")
    if origin and str(origin).strip() not in {"家", "None", "null"}:
        return str(origin).strip()
    text = _goal_text(goal)
    match = re.search(r"(?:从|由)([^，,。；;]+?)(?:出发|开始|起步|去|$)", text)
    if match:
        extracted = match.group(1).strip()
        if extracted:
            return extracted
    return "议事亭前地"


LOCAL_ORIGIN_ALIASES: Dict[str, Dict[str, Any]] = {
    "澳门大学": {"latitude": 22.1291, "longitude": 113.5456, "location": "113.5456,22.1291", "formatted_address": "澳门大学"},
    "澳門大學": {"latitude": 22.1291, "longitude": 113.5456, "location": "113.5456,22.1291", "formatted_address": "澳門大學"},
    "澳大": {"latitude": 22.1291, "longitude": 113.5456, "location": "113.5456,22.1291", "formatted_address": "澳门大学"},
}


def _resolve_origin(goal: Dict[str, Any]) -> Dict[str, Any]:
    origin = goal.get("origin_coords")
    if isinstance(origin, dict) and origin.get("latitude") is not None and origin.get("longitude") is not None:
        return {"name": goal.get("origin") or "用户起点", "latitude": float(origin["latitude"]), "longitude": float(origin["longitude"]), "location": f"{origin['longitude']},{origin['latitude']}"}
    text = _origin_text(goal)
    if text in LOCAL_ORIGIN_ALIASES:
        alias = dict(LOCAL_ORIGIN_ALIASES[text])
        return {"name": text, **alias}
    try:
        geo = amap_geocode(text)
        coords = _parse_location(geo.get("location", ""))
        if coords:
            lat, lng = coords
            return {"name": text, "latitude": lat, "longitude": lng, "location": geo.get("location"), "formatted_address": geo.get("formatted_address", text)}
    except Exception:
        pass
    # Fallback to Senado Square center when start location is missing or geocode fails.
    return {"name": text or "议事亭前地", "latitude": 22.1936, "longitude": 113.5390, "location": "113.5390,22.1936", "fallback": True}


def _haversine_km(a: Optional[Tuple[float, float]], b: Optional[Tuple[float, float]]) -> float:
    if not a or not b:
        return 3.0
    import math
    lat1, lon1 = a
    lat2, lon2 = b
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def _distance_score(distance_km: float) -> float:
    if distance_km <= 0.8:
        return 100
    if distance_km <= 1.5:
        return 90
    if distance_km <= 3.0:
        return 75
    if distance_km <= 5.0:
        return 55
    if distance_km <= 8.0:
        return 35
    return 15


def _continuity_score(route_pois: List[Dict[str, Any]], poi: Dict[str, Any]) -> float:
    if not route_pois:
        return 70
    prev = route_pois[-1]
    if poi.get("route_cluster") and poi.get("route_cluster") == prev.get("route_cluster"):
        return 100
    if poi.get("region") and poi.get("region") == prev.get("region"):
        return 82
    return 35


def _risk_penalty(poi: Dict[str, Any], route_pois: List[Dict[str, Any]]) -> float:
    penalty = len((poi.get("poi_score") or {}).get("risk_flags", [])) * 4
    features = poi.get("score_features") or {}
    if features.get("walking_comfort", 100) < 60:
        penalty += 8
    if features.get("standing_comfort", 100) < 60:
        penalty += 6
    if route_pois and route_pois[-1].get("score_features", {}).get("walking_comfort", 100) < 65 and features.get("walking_comfort", 100) < 65:
        penalty += 8
    return penalty


def _coverage_bonus(route_pois: List[Dict[str, Any]]) -> float:
    if not route_pois:
        return 0
    features = [poi.get("score_features") or {} for poi in route_pois]
    has_rest = any(item.get("rest_support", 0) >= 75 for item in features)
    has_toilet = any(item.get("toilet_support", 0) >= 75 for item in features)
    return (5 if has_rest else -5) + (5 if has_toilet else -5)


def _step_score(route_pois: List[Dict[str, Any]], poi: Dict[str, Any], current_coords: Optional[Tuple[float, float]]) -> float:
    poi_coords = _poi_coords(poi)
    distance_km = _haversine_km(current_coords, poi_coords)
    senior_score = (poi.get("poi_score") or {}).get("score", 60)
    score = (
        senior_score * 0.55
        + _distance_score(distance_km) * 0.25
        + _continuity_score(route_pois, poi) * 0.15
        + min(100, len({p.get("category", "") for p in route_pois + [poi]}) * 35) * 0.05
        - _risk_penalty(poi, route_pois)
    )
    poi["route_step_metrics"] = {
        "from_previous_distance_km": round(distance_km, 2),
        "distance_score": round(_distance_score(distance_km), 1),
        "continuity_score": round(_continuity_score(route_pois, poi), 1),
        "risk_penalty": round(_risk_penalty(poi, route_pois), 1),
        "step_score": round(score, 1),
    }
    return score


def _route_total_score(route_pois: List[Dict[str, Any]], raw_score: float) -> float:
    distance_penalty = sum(max(0, (poi.get("route_step_metrics") or {}).get("from_previous_distance_km", 0) - 4) * 4 for poi in route_pois)
    cross_region_penalty = sum(8 for idx in range(1, len(route_pois)) if route_pois[idx].get("region") != route_pois[idx - 1].get("region"))
    route_fatigue_penalty = sum(5 for poi in route_pois if (poi.get("score_features") or {}).get("walking_comfort", 100) < 65)
    return raw_score / max(1, len(route_pois)) + _coverage_bonus(route_pois) - distance_penalty - cross_region_penalty - route_fatigue_penalty


def _routes_for_names(origin: str, names: List[str]) -> List[Dict[str, Any]]:
    points = [origin] + names
    return [mock_map_route_api(points[index], points[index + 1]) for index in range(len(points) - 1)]


def _beam_search(goal: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]]:
    max_points = 3
    min_points = 2
    beam_width = 5
    origin = _resolve_origin(goal)
    origin_coords = (origin["latitude"], origin["longitude"])
    beams: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float, Optional[Tuple[float, float]]]] = [([], [], 0.0, origin_coords)]
    complete: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]] = []

    # Origin-aware Beam Search: expand routes from the user's start point while
    # keeping top-k partial routes. Search uses straight-line distance for speed;
    # final plans still call AMap/fallback route verification.
    for _ in range(max_points):
        expanded: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float, Optional[Tuple[float, float]]]] = []
        for route_pois, route_segments, raw_score, current_coords in beams:
            used = {item["name"] for item in route_pois}
            for candidate in candidates:
                if candidate["name"] in used:
                    continue
                poi = dict(candidate)
                step_score = _step_score(route_pois, poi, current_coords)
                new_pois = route_pois + [poi]
                new_raw_score = raw_score + step_score
                expanded.append((new_pois, route_segments, new_raw_score, _poi_coords(poi)))
        expanded.sort(key=lambda item: _route_total_score(item[0], item[2]), reverse=True)
        beams = expanded[:beam_width]
        for route_pois, route_segments, raw_score, _coords in beams:
            if len(route_pois) >= min_points:
                complete.append((route_pois, route_segments, _route_total_score(route_pois, raw_score)))

    unique: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]] = []
    seen_keys = set()
    for item in sorted(complete, key=lambda value: value[2], reverse=True):
        key = tuple(poi["name"] for poi in item[0])
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(item)
    return unique



def _verified_routes(origin: str, pois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    points = [origin] + [poi["name"] for poi in pois]
    routes: List[Dict[str, Any]] = []
    for index in range(len(points) - 1):
        route = mock_map_route_api(points[index], points[index + 1])
        route["segment_index"] = index + 1
        route["from_name"] = points[index]
        route["to_name"] = points[index + 1]
        routes.append(route)
    return routes


def _route_verification(routes: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_duration = sum(int(route.get("duration_min", 0) or 0) for route in routes)
    total_walking = sum(int(route.get("walking_distance_m", 0) or 0) for route in routes)
    total_distance = round(sum(float(route.get("route_distance_km", 0) or 0) for route in routes), 1)
    providers = sorted({str(route.get("map_provider") or route.get("traffic_level") or "unknown") for route in routes})
    long_segments = [route for route in routes if int(route.get("walking_distance_m", 0) or 0) > 300 or int(route.get("duration_min", 0) or 0) > 20]
    return {
        "provider": "+".join(providers),
        "segment_count": len(routes),
        "total_duration_min": total_duration,
        "total_walking_distance_m": total_walking,
        "total_route_distance_km": total_distance,
        "has_long_segment": bool(long_segments),
        "long_segment_count": len(long_segments),
    }


def _station_explanation(poi: Dict[str, Any], index: int) -> Dict[str, Any]:
    features = poi.get("score_features") or {}
    metrics = poi.get("route_step_metrics") or {}
    raw = poi.get("accessibility_raw") or {}
    reasons: List[str] = []
    if metrics.get("from_previous_distance_km") is not None:
        prefix = "距离起点" if index == 0 else "距离上一站"
        reasons.append(f"{prefix}约 {metrics['from_previous_distance_km']} 公里")
    if metrics.get("continuity_score", 0) >= 95:
        reasons.append("和上一站在同一 route_cluster，路线连续")
    elif metrics.get("continuity_score", 0) >= 80:
        reasons.append("和上一站同区域，减少跨区折返")
    if features.get("walking_comfort", 0) >= 80:
        reasons.append("内部步行压力较低")
    if features.get("stairs_comfort", 0) >= 80:
        reasons.append("台阶/坡度压力较低")
    if features.get("rest_support", 0) >= 75:
        reasons.append("有较好的休息点支持")
    if features.get("toilet_support", 0) >= 75:
        reasons.append("厕所支持较好")
    if not reasons:
        reasons.extend((poi.get("poi_score") or {}).get("reasons", [])[:2])
    warnings: List[str] = []
    if poi.get("avoid_route_zh"):
        warnings.append(f"避让：{poi['avoid_route_zh']}")
    if str(raw.get("crowd_level", "")).lower() in {"high", "medium_high"}:
        warnings.append("人流可能偏多，建议避开高峰")
    warnings.extend((poi.get("poi_score") or {}).get("risk_flags", [])[:2])
    return {
        "name": poi.get("name"),
        "region": poi.get("region"),
        "route_cluster": poi.get("route_cluster"),
        "reasons": list(dict.fromkeys(reasons))[:5],
        "warnings": list(dict.fromkeys(warnings))[:4],
        "best_access_route_zh": poi.get("best_access_route_zh", ""),
        "senior_tips_zh": poi.get("senior_tips_zh", ""),
    }


def _route_warnings(routes: List[Dict[str, Any]], pois: List[Dict[str, Any]]) -> List[str]:
    warnings: List[str] = []
    for route in routes:
        walking = int(route.get("walking_distance_m", 0) or 0)
        duration = int(route.get("duration_min", 0) or 0)
        if walking > 300:
            warnings.append(f"{route.get('from_name')} 到 {route.get('to_name')} 步行约 {walking} 米，建议打车/短途接驳")
        if duration > 20:
            warnings.append(f"{route.get('from_name')} 到 {route.get('to_name')} 约 {duration} 分钟，注意中途休息")
    for poi in pois:
        if poi.get("avoid_route_zh"):
            warnings.append(f"{poi.get('name')} 避让路线：{poi.get('avoid_route_zh')}")
    return list(dict.fromkeys(warnings))[:6]


def _route_summary_text(origin: str, pois: List[Dict[str, Any]], verification: Dict[str, Any]) -> str:
    names = " -> ".join([origin] + [poi["name"] for poi in pois])
    return f"{names}；预计约 {verification['total_duration_min']} 分钟，步行约 {verification['total_walking_distance_m']} 米。"


def _plan_from_route(goal: Dict[str, Any], route_item: Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float], index: int) -> Dict[str, Any]:
    scenario = "senior"
    pois, _routes, _raw_score = route_item
    people_count = goal.get("people", {}).get("total", 2)
    origin = _origin_text(goal)
    timeline = _timeline([item["name"] for item in pois])
    routes = _verified_routes(origin, pois)
    verification = _route_verification(routes)
    station_explanations = [_station_explanation(poi, pos) for pos, poi in enumerate(pois)]
    route_warnings = _route_warnings(routes, pois)
    tags = sorted(set(goal.get("preferences", [])) | {tag for poi in pois for tag in poi.get("tags", [])} | {"dynamic_recommendation", "origin_aware_beam_search"})
    recommendation_reasons = list(dict.fromkeys(
        [reason for item in station_explanations for reason in item.get("reasons", [])]
        + [reason for poi in pois for reason in poi.get("poi_score", {}).get("reasons", [])]
    ))[:8]
    risk_flags = list(dict.fromkeys(
        route_warnings
        + [warning for item in station_explanations for warning in item.get("warnings", [])]
        + [flag for poi in pois for flag in poi.get("poi_score", {}).get("risk_flags", [])]
    ))[:8]
    plan = {
        "id": f"{scenario}_dynamic_{index + 1}",
        "scenario": scenario,
        "title": _scenario_title(scenario, index),
        "timeline": timeline,
        "routes": routes,
        "route_verification": verification,
        "total_duration_min": verification["total_duration_min"],
        "total_walking_distance_m": verification["total_walking_distance_m"],
        "route_summary": _route_summary_text(origin, pois, verification),
        "station_explanations": station_explanations,
        "availability": [check_availability(poi["id"], timeline[pos]["time"], people_count) for pos, poi in enumerate(pois)],
        "tags": tags,
        "budget": {"currency": "MOP", "estimated_total": 520},
        "poi_details": pois,
        "recommendation_reasons": recommendation_reasons,
        "risk_flags": risk_flags,
    }
    plan["score"] = score_plan(plan, goal)
    return plan


def recommend_itineraries(goal: Dict[str, Any], max_plans: int = 3) -> List[Dict[str, Any]]:
    candidates = _rank_candidate_pois(goal)
    if len(candidates) < 2:
        return []
    route_items = _beam_search(goal, candidates)
    plans = [_plan_from_route(goal, item, index) for index, item in enumerate(route_items[:max_plans])]
    return sorted(plans, key=lambda item: item["score"]["score"], reverse=True)
