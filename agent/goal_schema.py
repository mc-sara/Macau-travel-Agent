from copy import deepcopy
from typing import Any, Dict, List


RELATIONSHIP_TYPE_ENUM: List[str] = [
    "family_with_children",
    "family_with_seniors",
    "couple",
    "friends",
    "solo",
    "business",
    "classmates",
    "mixed_group",
    "general",
]

OUTING_INTENT_ENUM: List[str] = [
    "half_day_outing",
    "dinner_plan",
    "date_plan",
    "photo_citywalk",
    "kid_friendly_play",
    "low_fatigue_relax",
    "celebration",
    "local_experience",
    "rainy_day_plan",
    "indoor_plan",
    "general_outing",
]

HARD_SOFT_PREFERENCE_ENUM: List[str] = [
    "low_fatigue",
    "short_walking_distance",
    "kid_friendly",
    "senior_friendly",
    "avoid_stairs",
    "indoor_required",
    "photo_friendly",
    "romantic",
    "social",
    "chat_friendly",
    "dinner_together",
    "low_calorie_food",
    "budget_control",
    "avoid_long_queue",
    "surprise_action",
    "local_specialty",
    "escape_room",
    "indoor_activity",
]

DEFAULT_PLANNING_STRATEGY: Dict[str, Any] = {
    "pace": "medium",
    "max_walking_per_segment_m": 600,
    "max_route_duration_per_segment_min": 25,
    "must_include_meal": True,
    "must_include_rest": False,
    "restaurant_table_size_required": 2,
    "avoid": [],
    "preferred": [],
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
