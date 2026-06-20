from copy import deepcopy
from typing import Any, Dict, List


SENIOR_RELATIONSHIPS = {"family_with_seniors", "caregiver_with_seniors", "senior_couple", "solo_senior", "general"}


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
    """Add senior-friendly planning defaults to a structured goal.

    The project is now positioned as a senior Macau local-life Agent. Non-senior or
    vague inputs are treated as general senior-friendly requests instead of being
    expanded into friends/couple/children scenarios.
    """
    enriched = deepcopy(goal)
    relationship = enriched.get("relationship_type", "general")
    people = enriched.get("people", {})
    strategy = enriched.setdefault("planning_strategy", {})
    strategy.setdefault("pace", "slow")
    strategy.setdefault("max_walking_per_segment_m", 300)
    strategy.setdefault("max_route_duration_per_segment_min", 18)
    strategy.setdefault("must_include_meal", True)
    strategy.setdefault("must_include_rest", True)
    strategy.setdefault("restaurant_table_size_required", people.get("total", 2))
    strategy.setdefault("avoid", [])
    strategy.setdefault("preferred", [])

    hard_constraints = set(enriched.get("hard_constraints", []))
    soft_preferences = set(enriched.get("soft_preferences", []))

    if relationship not in SENIOR_RELATIONSHIPS:
        enriched["relationship_type"] = "general"
        relationship = "general"

    strategy["pace"] = "slow" if relationship != "solo_senior" else "very_slow"
    strategy["must_include_meal"] = True
    strategy["must_include_rest"] = True
    strategy["restaurant_table_size_required"] = people.get("total", 2)
    _set_max(strategy, "max_walking_per_segment_m", 300)
    _set_max(strategy, "max_route_duration_per_segment_min", 18)
    strategy["preferred"] = _append_unique(
        strategy["preferred"],
        [
            "rest_area",
            "toilet_access",
            "senior_friendly_restaurant",
            "flat_route",
            "simple_transport",
        ],
    )
    strategy["avoid"] = _append_unique(
        strategy["avoid"],
        ["stairs", "long_queue", "steep_slopes", "too_tiring", "long_walk", "crowded_hotspots"],
    )

    if "low_fatigue" in hard_constraints or "low_fatigue" in soft_preferences:
        _set_max(strategy, "max_route_duration_per_segment_min", 16)
        _set_max(strategy, "max_walking_per_segment_m", 250)
        strategy["avoid"] = _append_unique(strategy["avoid"], ["too_tiring", "long_walk"])

    if "wheelchair_friendly" in hard_constraints or "elevator_required" in hard_constraints:
        strategy["preferred"] = _append_unique(strategy["preferred"], ["wheelchair_friendly", "elevator_access"])
        strategy["avoid"] = _append_unique(strategy["avoid"], ["stairs", "narrow_walkway"])

    if "avoid_long_queue" in hard_constraints or "avoid_long_queue" in soft_preferences:
        strategy["avoid"] = _append_unique(strategy["avoid"], ["long_queue"])

    if "low_calorie_food" in hard_constraints or "low_calorie_food" in soft_preferences:
        strategy["preferred"] = _append_unique(strategy["preferred"], ["light_food", "less_oil_less_salt"])

    enriched["planning_strategy"] = strategy
    return enriched
