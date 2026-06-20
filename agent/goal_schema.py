from copy import deepcopy
from typing import Any, Dict, List


RELATIONSHIP_TYPE_ENUM: List[str] = [
    "family_with_seniors",
    "caregiver_with_seniors",
    "senior_couple",
    "solo_senior",
    "general",
]

OUTING_INTENT_ENUM: List[str] = [
    "low_fatigue_relax",
    "half_day_outing",
    "dinner_plan",
    "local_experience",
    "rainy_day_plan",
    "general_outing",
]

HARD_SOFT_PREFERENCE_ENUM: List[str] = [
    "low_fatigue",
    "short_walking_distance",
    "senior_friendly",
    "avoid_stairs",
    "indoor_required",
    "low_calorie_food",
    "budget_control",
    "avoid_long_queue",
    "local_specialty",
    "rest_area",
    "toilet_access",
    "flat_route",
    "wheelchair_friendly",
    "elevator_required",
    "shaded_or_indoor",
    "simple_transport",
    "family_notification",
    "route_card_needed",
    "oral_guide_needed",
]

DEFAULT_PLANNING_STRATEGY: Dict[str, Any] = {
    "pace": "slow",
    "max_walking_per_segment_m": 300,
    "max_route_duration_per_segment_min": 18,
    "must_include_meal": True,
    "must_include_rest": True,
    "restaurant_table_size_required": 2,
    "avoid": ["stairs", "long_queue", "steep_slopes", "too_tiring"],
    "preferred": ["rest_area", "senior_friendly_restaurant", "flat_route"],
}


def default_goal(raw_text: str) -> Dict[str, Any]:
    return {
        "raw_text": raw_text,
        "relationship_type": "general",
        "outing_intent": "general_outing",
        "confidence": 0.5,
        "people": {
            "total": 2,
            "male": 0,
            "female": 0,
            "children": 0,
            "seniors": 0,
            "relationship_note": "",
        },
        "time": {
            "date": "today",
            "start_period": "afternoon",
            "start_time": None,
            "duration_hours": 5,
            "end_before": None,
        },
        "location": {
            "city": "Macau",
            "start_location": None,
            "preferred_area": None,
            "avoid_area": [],
        },
        "hard_constraints": [],
        "soft_preferences": [],
        "budget": {
            "level": "medium",
            "per_person_max": None,
        },
        "planning_strategy": deepcopy(DEFAULT_PLANNING_STRATEGY),
        "missing_info": [],
        "clarification_needed": False,
        "clarification_questions": [],
        "assumptions": [],
    }
