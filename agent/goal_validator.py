from copy import deepcopy
from typing import Any, Dict, List

from agent.goal_schema import HARD_SOFT_PREFERENCE_ENUM, OUTING_INTENT_ENUM, RELATIONSHIP_TYPE_ENUM, default_goal


SENIOR_KEYWORDS = ("爸妈", "父母", "妈妈", "爸爸", "爷爷", "奶奶", "外公", "外婆", "长者", "老人", "长辈", "银龄")


def _unique(items: List[str]) -> List[str]:
    result: List[str] = []
    for item in items:
        if item in HARD_SOFT_PREFERENCE_ENUM and item not in result:
            result.append(item)
    return result


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_people(people: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "total": _safe_int(people.get("total"), 0),
        "male": _safe_int(people.get("male"), 0),
        "female": _safe_int(people.get("female"), 0),
        "children": _safe_int(people.get("children"), 0),
        "seniors": _safe_int(people.get("seniors"), 0),
        "relationship_note": people.get("relationship_note", ""),
    }
    counted_total = normalized["male"] + normalized["female"] + normalized["children"] + normalized["seniors"]
    if counted_total > normalized["total"]:
        normalized["total"] = counted_total
    if normalized["total"] <= 0:
        normalized["total"] = 2
    return normalized


def validate_and_normalize_goal(goal: Dict[str, Any]) -> Dict[str, Any]:
    normalized = default_goal(goal.get("raw_text", ""))
    merged = deepcopy(normalized)

    for key, value in goal.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value

    if merged.get("relationship_type") not in RELATIONSHIP_TYPE_ENUM:
        merged["relationship_type"] = "general"
    if merged.get("outing_intent") not in OUTING_INTENT_ENUM:
        merged["outing_intent"] = "general_outing"

    if "confidence" in goal:
        merged["confidence"] = max(0.0, min(1.0, _safe_float(merged.get("confidence"), 0.6)))
    else:
        merged["confidence"] = 0.6

    merged["people"] = _normalize_people(merged.get("people", {}))
    merged["hard_constraints"] = _unique(list(merged.get("hard_constraints", [])))
    merged["soft_preferences"] = _unique(list(merged.get("soft_preferences", [])))

    raw_text = merged.get("raw_text", "")
    people = merged["people"]
    if people["seniors"] > 0 or any(keyword in raw_text for keyword in SENIOR_KEYWORDS):
        if people["seniors"] <= 0:
            people["seniors"] = 2 if any(keyword in raw_text for keyword in ("爸妈", "父母", "爷爷奶奶")) else 1
            people["total"] = max(people["total"], people["seniors"] + 1)
        merged["relationship_type"] = "family_with_seniors"
        merged["outing_intent"] = "low_fatigue_relax"
    elif merged["relationship_type"] == "general":
        # The product is senior-first; vague requests stay general but inherit senior-safe constraints.
        merged["outing_intent"] = merged.get("outing_intent") or "general_outing"

    merged["hard_constraints"] = _unique(
        merged["hard_constraints"] + ["senior_friendly", "low_fatigue", "short_walking_distance"]
    )
    if "不要爬楼梯" in raw_text or "不爬楼梯" in raw_text or "楼梯" in raw_text:
        merged["hard_constraints"] = _unique(merged["hard_constraints"] + ["avoid_stairs"])
    if "轮椅" in raw_text or "无障碍" in raw_text:
        merged["hard_constraints"] = _unique(merged["hard_constraints"] + ["wheelchair_friendly"])
    if "电梯" in raw_text:
        merged["hard_constraints"] = _unique(merged["hard_constraints"] + ["elevator_required"])
    if "厕所" in raw_text or "洗手间" in raw_text:
        merged["soft_preferences"] = _unique(merged["soft_preferences"] + ["toilet_access"])
    if "坐" in raw_text or "休息" in raw_text:
        merged["soft_preferences"] = _unique(merged["soft_preferences"] + ["rest_area"])
    if "清淡" in raw_text or "少油" in raw_text or "低卡" in raw_text:
        merged["soft_preferences"] = _unique(merged["soft_preferences"] + ["low_calorie_food"])

    return merged
