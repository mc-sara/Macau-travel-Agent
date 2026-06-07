from copy import deepcopy
from typing import Any, Dict, List

from agent.goal_schema import HARD_SOFT_PREFERENCE_ENUM, OUTING_INTENT_ENUM, RELATIONSHIP_TYPE_ENUM, default_goal


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

    people = merged["people"]
    if people["children"] > 0:
        merged["relationship_type"] = "family_with_children"
        merged["outing_intent"] = "kid_friendly_play"
        merged["hard_constraints"] = _unique(merged["hard_constraints"] + ["kid_friendly", "low_fatigue", "short_walking_distance"])
    elif people["seniors"] > 0:
        merged["relationship_type"] = "family_with_seniors"
        merged["outing_intent"] = "low_fatigue_relax"
        merged["hard_constraints"] = _unique(merged["hard_constraints"] + ["senior_friendly", "avoid_stairs", "low_fatigue"])
    elif merged["relationship_type"] == "couple" and people["total"] > 2:
        merged["relationship_type"] = "friends"
        merged["outing_intent"] = "half_day_outing"
        merged["soft_preferences"] = _unique(merged["soft_preferences"] + ["social", "chat_friendly"])

    if merged["relationship_type"] == "friends" and "social" not in merged["soft_preferences"]:
        merged["soft_preferences"] = _unique(merged["soft_preferences"] + ["social", "photo_friendly", "dinner_together"])
    if merged["relationship_type"] == "couple":
        merged["soft_preferences"] = _unique(merged["soft_preferences"] + ["romantic", "surprise_action"])

    return merged
