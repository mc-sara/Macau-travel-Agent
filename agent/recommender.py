from typing import Any, Dict, List, Tuple

from agent.scorer import score_plan, score_poi
from agent.tools import check_availability, mock_map_route_api, search_attractions


TIMES = ["14:00", "15:00", "16:20", "17:40"]


def _timeline(names: List[str]) -> List[Dict[str, Any]]:
    return [{"time": time, "name": name} for time, name in zip(TIMES, names)]


def _scenario_title(scenario: str, index: int) -> str:
    if scenario == "senior":
        return ["长者低疲劳精选路线", "长者文化慢游路线", "长者轻量备选路线"][min(index, 2)]
    if scenario == "family":
        return ["亲子轻松半日路线", "亲子公园文化路线", "亲子轻量备选路线"][min(index, 2)]
    if scenario == "friends":
        return ["朋友拍照聊天路线", "朋友文化散步路线", "朋友轻量备选路线"][min(index, 2)]
    if scenario == "couple":
        return ["情侣低疲劳约会路线", "情侣拍照慢游路线", "情侣轻量备选路线"][min(index, 2)]
    return ["澳门轻松半日路线", "澳门文化慢游路线", "澳门轻量备选路线"][min(index, 2)]


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


def _rank_candidate_pois(goal: Dict[str, Any], limit: int = 15) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    seen = set()
    for poi in search_attractions(goal):
        name = poi.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        item = dict(poi)
        item["poi_score"] = score_poi(item, goal)
        candidates.append(item)
    return sorted(candidates, key=lambda item: item["poi_score"]["score"], reverse=True)[:limit]


def _routes_for_names(origin: str, names: List[str]) -> List[Dict[str, Any]]:
    points = [origin] + names
    return [mock_map_route_api(points[index], points[index + 1]) for index in range(len(points) - 1)]


def _beam_search(goal: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]]:
    scenario = goal.get("scenario", "general")
    max_points = 3 if scenario == "senior" else 4
    min_points = 2
    beam_width = 5
    beams: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]] = [([], [], 0)]
    complete: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]] = []

    # 搜索阶段不调用地图 API，避免 Beam Search 产生几十次高德请求。
    # 先用 POI 质量、类别多样性和适老风险排序；只对最终 Top 路线计算真实路线。
    for _ in range(max_points):
        expanded: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]] = []
        for route_pois, route_segments, _score in beams:
            used = {item["name"] for item in route_pois}
            for poi in candidates:
                if poi["name"] in used:
                    continue
                new_pois = route_pois + [poi]
                poi_score = sum(item["poi_score"]["score"] for item in new_pois)
                route_diversity = len({item.get("category", "") for item in new_pois}) * 4
                risk_penalty = sum(len(item.get("poi_score", {}).get("risk_flags", [])) for item in new_pois) * 4
                density_penalty = max(0, len(new_pois) - 3) * 8
                total_score = poi_score + route_diversity - risk_penalty - density_penalty
                expanded.append((new_pois, route_segments, total_score))
        expanded.sort(key=lambda item: item[2], reverse=True)
        beams = expanded[:beam_width]
        complete.extend(item for item in beams if len(item[0]) >= min_points)

    unique: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]] = []
    seen_keys = set()
    for item in sorted(complete, key=lambda value: value[2], reverse=True):
        key = tuple(poi["name"] for poi in item[0])
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(item)
    return unique


def _plan_from_route(goal: Dict[str, Any], route_item: Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int], index: int) -> Dict[str, Any]:
    scenario = goal.get("scenario", "general")
    pois, routes, _raw_score = route_item
    people_count = goal.get("people", {}).get("total", 2)
    timeline = _timeline([item["name"] for item in pois])
    routes = _routes_for_names(goal.get("origin", "家"), [item["name"] for item in pois])
    tags = sorted(set(goal.get("preferences", [])) | {tag for poi in pois for tag in poi.get("tags", [])} | {"dynamic_recommendation"})
    plan = {
        "id": f"{scenario}_dynamic_{index + 1}",
        "scenario": scenario,
        "title": _scenario_title(scenario, index),
        "timeline": timeline,
        "routes": routes,
        "availability": [check_availability(poi["id"], timeline[pos]["time"], people_count) for pos, poi in enumerate(pois)],
        "tags": tags,
        "budget": {"currency": "MOP", "estimated_total": {"senior": 520, "family": 650, "friends": 920, "couple": 1180}.get(scenario, 600)},
        "poi_details": pois,
        "recommendation_reasons": [reason for poi in pois for reason in poi.get("poi_score", {}).get("reasons", [])][:5],
        "risk_flags": list(dict.fromkeys(flag for poi in pois for flag in poi.get("poi_score", {}).get("risk_flags", [])))[:5],
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
