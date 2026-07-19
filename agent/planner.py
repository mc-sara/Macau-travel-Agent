from typing import Any, Dict, List

from agent.parser import parse_goal
from agent.recommender import recommend_itineraries
from agent.scorer import score_plan
from agent.tools import check_availability, get_accessibility, mock_map_route_api, search_attractions, search_local_merchants


def _timeline(names: List[str]) -> List[Dict[str, Any]]:
    return [{"time": time, "name": name} for time, name in zip(["14:00", "15:00", "16:20", "17:40", "18:30"], names)]


def _routes_for_timeline(timeline: List[Dict[str, Any]], origin: str) -> List[Dict[str, Any]]:
    points = [origin] + [step["name"] for step in timeline]
    return [mock_map_route_api(points[index], points[index + 1]) for index in range(len(points) - 1)]


def build_timeline(scenario: str, goal: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    goal = goal or {}
    if scenario == "senior":
        return _timeline(["澳门仁慈堂大楼", "澳门中央图书馆", "澳门文化中心"])
    if scenario == "family":
        return _timeline(["二龙喉公园", "白鸽巢公园", "澳门中央图书馆"])
    if scenario == "friends" and "escape_room" in goal.get("preferences", []):
        return _timeline(["澳门仁慈堂大楼", "玫瑰圣母堂（板樟堂）", "澳门文化中心"])
    if scenario == "friends":
        return _timeline(["澳门仁慈堂大楼", "玫瑰圣母堂（板樟堂）", "澳门文化中心", "澳门渔人码头"])
    if scenario == "couple":
        return _timeline(["澳门文化中心", "澳门渔人码头", "观音莲花苑"])
    return _timeline(["澳门仁慈堂大楼", "澳门中央图书馆", "澳门文化中心"])


def _availability_for_scenario(scenario: str, people_count: int, goal: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    goal = goal or {}
    if scenario == "senior":
        return [check_availability("attraction_501", "14:00", people_count), check_availability("attraction_505", "15:00", people_count), check_availability("attraction_502", "16:20", people_count)]
    if scenario == "family":
        return [check_availability("attraction_628", "14:00", people_count), check_availability("attraction_510", "15:00", people_count), check_availability("attraction_505", "16:20", people_count)]
    if scenario == "friends":
        return [check_availability("attraction_501", "14:00", people_count), check_availability("attraction_575", "15:00", people_count), check_availability("attraction_502", "16:20", people_count)]
    if scenario == "couple":
        return [check_availability("attraction_502", "14:00", people_count), check_availability("attraction_504", "15:00", people_count), check_availability("attraction_535", "16:20", people_count)]
    return []


def _main_plan(goal: Dict[str, Any]) -> Dict[str, Any]:
    scenario = goal.get("scenario", "general")
    timeline = build_timeline(scenario, goal)
    people_count = goal.get("people", {}).get("total", 2)
    titles = {
        "senior": "长者低疲劳半日路线",
        "family": "亲子低疲劳半日路线",
        "friends": "朋友拍照聊天半日路线",
        "couple": "情侣浪漫低疲劳约会路线",
        "general": "澳门轻松半日路线",
    }
    tags = {
        "senior": ["senior_friendly", "low_fatigue", "short_walking_distance", "avoid_stairs", "rest_area", "toilet_access"],
        "family": ["kid_friendly", "low_fatigue", "low_calorie"],
        "friends": ["social", "photo_friendly", "chat_friendly"] + (["escape_room", "indoor_activity"] if "escape_room" in goal.get("preferences", []) else []),
        "couple": ["romantic", "low_fatigue", "photo_friendly", "surprise"],
        "general": ["low_fatigue"],
    }
    plan = {
        "id": f"{scenario}_main",
        "scenario": scenario,
        "title": titles.get(scenario, titles["general"]),
        "timeline": timeline,
        "routes": _routes_for_timeline(timeline, goal.get("origin", "家")),
        "availability": _availability_for_scenario(scenario, people_count, goal),
        "tags": tags.get(scenario, tags["general"]),
        "budget": {"currency": "MOP", "estimated_total": {"senior": 520, "family": 650, "friends": 920, "couple": 1180}.get(scenario, 600)},
    }
    plan["score"] = score_plan(plan, goal)
    return plan


def _alternative_plan(goal: Dict[str, Any]) -> Dict[str, Any]:
    scenario = goal.get("scenario", "general")
    alternatives = {
        "senior": ["澳门仁慈堂大楼", "澳门中央图书馆"],
        "family": ["二龙喉公园", "白鸽巢公园", "澳门中央图书馆"],
        "friends": ["澳门仁慈堂大楼", "玫瑰圣母堂（板樟堂）", "澳门渔人码头"],
        "couple": ["澳门文化中心", "澳门渔人码头", "观音莲花苑"],
        "general": ["澳门仁慈堂大楼", "澳门中央图书馆"],
    }
    timeline = _timeline(alternatives.get(scenario, alternatives["general"]))
    plan = {
        "id": f"{scenario}_alternative",
        "scenario": scenario,
        "title": "备选轻量路线",
        "timeline": timeline,
        "routes": _routes_for_timeline(timeline, goal.get("origin", "家")),
        "availability": [],
        "tags": goal.get("preferences", []),
        "budget": {"currency": "MOP", "estimated_total": 520},
    }
    plan["score"] = score_plan(plan, goal)
    return plan


def _fallback_candidate_plans(goal: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [_main_plan(goal), _alternative_plan(goal)]


def generate_candidate_plans(goal: Dict[str, Any]) -> List[Dict[str, Any]]:
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
        {"tool": "llm_goal_parser", "status": "success", "summary": f"LLM/Mock LLM 将自然语言拆解为 {goal.get('structured_goal', {}).get('relationship_type', goal['scenario'])}"},
        {"tool": "goal_validator", "status": "success", "summary": "校验人数、关系类型、置信度和枚举字段"},
        {"tool": "goal_enricher", "status": "success", "summary": "补全低疲劳、餐桌人数、休息点和避让策略"},
        {"tool": "parse_goal", "status": "success", "summary": f"兼容旧 Planner，识别为 {goal['scenario']} 场景"},
        {"tool": "search_attractions", "status": "success", "summary": f"找到 {len(attractions)} 个候选景点"},
        {"tool": "get_accessibility", "status": "success", "summary": f"检查 {len(accessibility)} 条疲劳/台阶风险"},
        {"tool": "mock_map_route_api", "status": "success", "summary": f"计算 {len(best_plan['routes'])} 段导航路线"},
        {"tool": "search_local_merchants", "status": "success", "summary": f"查询 {sum(len(v) for v in merchants.values())} 个本地商户/活动"},
        {"tool": "check_availability", "status": "success", "summary": f"确认 {len(best_plan['availability'])} 个可执行动作"},
        {"tool": "score_plan", "status": "success", "summary": f"最佳方案评分 {best_plan['score']['score']} 分"},
    ]


def plan_day(user_text: str, use_llm: bool = False, llm_mode: str = "mock") -> Dict[str, Any]:
    goal = parse_goal(user_text, use_llm=use_llm, llm_mode=llm_mode)
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
