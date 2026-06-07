from copy import deepcopy
from typing import Any, Dict, List


def _append_unique(items: List[str], additions: List[str]) -> List[str]:
    result = list(items)
    for item in additions:
        if item not in result:
            result.append(item)
    return result


def _set_max(strategy: Dict[str, Any], key: str, value: int) -> None:
    current = strategy.get(key)
    if current is None or int(current) > value:
        strategy[key] = value


def enrich_goal(goal: Dict[str, Any]) -> Dict[str, Any]:
    enriched = deepcopy(goal)
    relationship = enriched.get("relationship_type", "general")
    people = enriched.get("people", {})
    strategy = enriched.setdefault("planning_strategy", {})
    strategy.setdefault("pace", "medium")
    strategy.setdefault("max_walking_per_segment_m", 600)
    strategy.setdefault("max_route_duration_per_segment_min", 25)
    strategy.setdefault("must_include_meal", True)
    strategy.setdefault("must_include_rest", False)
    strategy.setdefault("restaurant_table_size_required", people.get("total", 2))
    strategy.setdefault("avoid", [])
    strategy.setdefault("preferred", [])

    hard_constraints = set(enriched.get("hard_constraints", []))
    soft_preferences = set(enriched.get("soft_preferences", []))

    if relationship == "friends":
        strategy["pace"] = "medium"
        strategy["restaurant_table_size_required"] = people.get("total", 4)
        strategy["must_include_meal"] = True
        strategy["must_include_rest"] = True
        strategy["preferred"] = _append_unique(strategy["preferred"], ["photo_spot", "drink_break", "group_activity", "group_restaurant"])
        strategy["avoid"] = _append_unique(strategy["avoid"], ["couple_only_restaurant", "too_quiet"])
        if "escape_room" in soft_preferences:
            strategy["preferred"] = _append_unique(strategy["preferred"], ["escape_room", "indoor_activity", "team_activity"])
            strategy["must_include_group_activity"] = True

    if relationship == "family_with_children":
        strategy["pace"] = "slow"
        strategy["must_include_rest"] = True
        strategy["restaurant_table_size_required"] = people.get("total", 3)
        _set_max(strategy, "max_walking_per_segment_m", 300)
        _set_max(strategy, "max_route_duration_per_segment_min", 20)
        strategy["preferred"] = _append_unique(strategy["preferred"], ["kid_friendly_place", "indoor", "rest_area", "low_calorie_restaurant"])
        strategy["avoid"] = _append_unique(strategy["avoid"], ["long_queue", "too_tiring", "stairs", "crowded_hotspots"])

    if relationship == "family_with_seniors":
        strategy["pace"] = "slow"
        strategy["must_include_rest"] = True
        strategy["restaurant_table_size_required"] = people.get("total", 3)
        _set_max(strategy, "max_walking_per_segment_m", 300)
        _set_max(strategy, "max_route_duration_per_segment_min", 18)
        strategy["preferred"] = _append_unique(strategy["preferred"], ["rest_area", "senior_friendly_restaurant", "flat_route"])
        strategy["avoid"] = _append_unique(strategy["avoid"], ["stairs", "long_queue", "steep_slopes", "too_tiring"])

    if relationship == "couple":
        strategy["pace"] = "medium_slow"
        strategy["restaurant_table_size_required"] = 2
        _set_max(strategy, "max_route_duration_per_segment_min", 20)
        strategy["preferred"] = _append_unique(strategy["preferred"], ["view", "cafe", "romantic_dinner", "surprise_action"])
        strategy["avoid"] = _append_unique(strategy["avoid"], ["too_crowded", "too_tiring", "family_noise"])

    if "low_fatigue" in hard_constraints or "low_fatigue" in soft_preferences:
        strategy["must_include_rest"] = True
        _set_max(strategy, "max_route_duration_per_segment_min", 20)
        _set_max(strategy, "max_walking_per_segment_m", 400)
        strategy["avoid"] = _append_unique(strategy["avoid"], ["too_tiring", "long_walk"])

    if "avoid_long_queue" in hard_constraints or "avoid_long_queue" in soft_preferences:
        strategy["avoid"] = _append_unique(strategy["avoid"], ["long_queue"])

    enriched["planning_strategy"] = strategy
    return enriched
