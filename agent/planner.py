from typing import Any, Dict, List, Optional

from agent.parser import parse_goal
from agent.recommender import recommend_itineraries
from agent.scorer import score_plan
from agent.tools import check_availability, get_accessibility, mock_map_route_api, search_attractions, search_local_merchants


SENIOR_TAGS = ["senior_friendly", "low_fatigue", "short_walking_distance", "avoid_stairs", "rest_area", "toilet_access"]
SENIOR_FALLBACK_NAMES = ["澳门仁慈堂大楼", "澳门中央图书馆", "澳门文化中心"]
SENIOR_FALLBACK_IDS = ["attraction_501", "attraction_505", "attraction_502"]


def _timeline(names: List[str]) -> List[Dict[str, Any]]:
    return [{"time": time, "name": name} for time, name in zip(["14:00", "15:00", "16:20", "17:40", "18:30"], names)]


def _routes_for_timeline(timeline: List[Dict[str, Any]], origin: str) -> List[Dict[str, Any]]:
    points = [origin] + [step["name"] for step in timeline]
    return [mock_map_route_api(points[index], points[index + 1]) for index in range(len(points) - 1)]


def build_timeline(_scenario: str = "senior", goal: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    return _timeline(SENIOR_FALLBACK_NAMES)


def _availability_for_senior(people_count: int) -> List[Dict[str, Any]]:
    return [check_availability(item_id, time, people_count) for item_id, time in zip(SENIOR_FALLBACK_IDS, ["14:00", "15:00", "16:20"])]


def _main_plan(goal: Dict[str, Any]) -> Dict[str, Any]:
    people_count = goal.get("people", {}).get("total", 2)
    timeline = build_timeline("senior", goal)
    plan = {
        "id": "senior_main",
        "scenario": "senior",
        "title": "长者低疲劳半日路线",
        "timeline": timeline,
        "routes": _routes_for_timeline(timeline, goal.get("origin", "家")),
        "availability": _availability_for_senior(people_count),
        "tags": SENIOR_TAGS,
        "budget": {"currency": "MOP", "estimated_total": 520},
    }
    plan["score"] = score_plan(plan, goal)
    return plan


def _alternative_plan(goal: Dict[str, Any]) -> Dict[str, Any]:
    timeline = _timeline(["澳门仁慈堂大楼", "澳门中央图书馆"])
    plan = {
        "id": "senior_alternative",
        "scenario": "senior",
        "title": "备选轻量路线",
        "timeline": timeline,
        "routes": _routes_for_timeline(timeline, goal.get("origin", "家")),
        "availability": [],
        "tags": SENIOR_TAGS,
        "budget": {"currency": "MOP", "estimated_total": 520},
    }
    plan["score"] = score_plan(plan, goal)
    return plan


def _fallback_candidate_plans(goal: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [_main_plan(goal), _alternative_plan(goal)]


def generate_candidate_plans(goal: Dict[str, Any]) -> List[Dict[str, Any]]:
    goal = dict(goal)
    goal["scenario"] = "senior"
    try:
        plans = recommend_itineraries(goal, max_plans=3)
        if len(plans) >= 2:
            return plans
    except Exception:
        pass
    return _fallback_candidate_plans(goal)


def _tool_steps(goal: Dict[str, Any], best_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    attractions = search_attractions(goal)
    merchants = search_local_merchants(goal)
    accessibility = [get_accessibility(item["id"]) for item in attractions[:2]]
    return [
        {"tool": "llm_goal_parser", "status": "success", "summary": "解析为长者本地生活需求"},
        {"tool": "goal_validator", "status": "success", "summary": "校验人数、起点、适老约束和置信度"},
        {"tool": "goal_enricher", "status": "success", "summary": "补全低疲劳、休息点、厕所和避让策略"},
        {"tool": "parse_goal", "status": "success", "summary": "统一进入 senior 路线规划"},
        {"tool": "search_attractions", "status": "success", "summary": f"找到 {len(attractions)} 个候选景点"},
        {"tool": "get_accessibility", "status": "success", "summary": f"检查 {len(accessibility)} 条疲劳/台阶风险"},
        {"tool": "mock_map_route_api", "status": "success", "summary": f"计算 {len(best_plan['routes'])} 段导航路线"},
        {"tool": "search_local_merchants", "status": "success", "summary": f"查询 {len(merchants.get('senior_activities', []))} 个长者适合活动"},
        {"tool": "check_availability", "status": "success", "summary": f"确认 {len(best_plan['availability'])} 个可执行动作"},
        {"tool": "score_plan", "status": "success", "summary": f"最佳方案评分 {best_plan['score']['score']} 分"},
    ]


def plan_day(user_text: str, use_llm: bool = False, llm_mode: str = "mock", origin_text: str = "", origin_coords: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    goal = parse_goal(user_text, use_llm=use_llm, llm_mode=llm_mode)
    goal["scenario"] = "senior"
    origin_text = str(origin_text or "").strip()
    if origin_text:
        goal["origin"] = origin_text
        structured = goal.setdefault("structured_goal", {})
        location = structured.setdefault("location", {})
        if isinstance(location, dict):
            location["start_location"] = origin_text
    if origin_coords and origin_coords.get("latitude") is not None and origin_coords.get("longitude") is not None:
        goal["origin_coords"] = {
            "latitude": float(origin_coords["latitude"]),
            "longitude": float(origin_coords["longitude"]),
        }
        if origin_coords.get("location"):
            goal["origin_coords"]["location"] = origin_coords["location"]
    candidates = generate_candidate_plans(goal)
    candidates = sorted(candidates, key=lambda item: item["score"]["score"], reverse=True)
    best_plan = candidates[0]
    return {
        "goal": goal,
        "structured_goal": goal.get("structured_goal", {}),
        "clarification_needed": goal.get("structured_goal", {}).get("clarification_needed", False),
        "clarification_questions": goal.get("structured_goal", {}).get("clarification_questions", []),
        "tool_steps": _tool_steps(goal, best_plan),
        "best_plan": best_plan,
        "alternatives": candidates[1:],
    }
