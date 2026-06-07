from typing import Any, Dict, List, Optional
import re

from agent.llm_goal_parser import parse_goal_with_llm


CHINESE_NUMBERS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

RELATIONSHIP_TO_SCENARIO = {
    "family_with_children": "family",
    "family_with_seniors": "family",
    "couple": "couple",
    "friends": "friends",
    "classmates": "friends",
    "mixed_group": "friends",
    "business": "friends",
    "solo": "general",
    "general": "general",
}


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _parse_count_token(token: str) -> int:
    if token.isdigit():
        return int(token)
    if token in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[token]
    if len(token) == 2 and token.startswith("十") and token[1] in CHINESE_NUMBERS:
        return 10 + CHINESE_NUMBERS[token[1]]
    if len(token) == 2 and token.endswith("十") and token[0] in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[token[0]] * 10
    if len(token) == 3 and token[1] == "十" and token[0] in CHINESE_NUMBERS and token[2] in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[token[0]] * 10 + CHINESE_NUMBERS[token[2]]
    return 0


def _parse_gender_counts(text: str) -> Optional[Dict[str, int]]:
    pattern = r"([0-9一二两三四五六七八九十]+)\s*男\s*([0-9一二两三四五六七八九十]+)\s*女"
    match = re.search(pattern, text)
    if not match:
        return None
    male = _parse_count_token(match.group(1))
    female = _parse_count_token(match.group(2))
    if male <= 0 and female <= 0:
        return None
    return {"total": male + female, "male": male, "female": female}


def _parse_total_people(text: str) -> Optional[int]:
    pattern = r"([0-9一二两三四五六七八九十]+)\s*(?:个)?\s*人"
    match = re.search(pattern, text)
    if not match:
        return None
    total = _parse_count_token(match.group(1))
    return total if total > 0 else None


def parse_structured_goal(
    user_text: str,
    use_llm: bool = False,
    client: Optional[Any] = None,
    llm_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse user text into the new structured goal format."""
    mode = llm_mode or ("real" if use_llm else "mock")
    return parse_goal_with_llm(user_text, use_mock=(mode == "mock"), client=client, llm_mode=mode)


def adapt_structured_goal_to_legacy_goal(structured_goal: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt structured goal to the existing planner-compatible goal format."""
    relationship = structured_goal.get("relationship_type", "general")
    scenario = RELATIONSHIP_TO_SCENARIO.get(relationship, "general")
    people = dict(structured_goal.get("people", {}))
    duration_hours = structured_goal.get("time", {}).get("duration_hours", 5)
    preferences = list(structured_goal.get("hard_constraints", [])) + list(structured_goal.get("soft_preferences", []))

    if scenario == "family" and relationship == "family_with_children":
        people.setdefault("adults", max(1, people.get("total", 3) - people.get("children", 1)))
        people.setdefault("child_age", 5)
        if "kid_friendly" not in preferences:
            preferences.append("kid_friendly")
        if "low_calorie_food" in preferences and "low_calorie" not in preferences:
            preferences.append("low_calorie")
    elif scenario == "family" and relationship == "family_with_seniors":
        people.setdefault("adults", max(1, people.get("total", 3) - people.get("seniors", 2)))
        if "senior_friendly" not in preferences:
            preferences.append("senior_friendly")
    elif scenario == "couple":
        people["total"] = 2
        if "romantic" not in preferences:
            preferences.append("romantic")
        if "low_fatigue" not in preferences:
            preferences.append("low_fatigue")
    elif scenario == "friends":
        people.setdefault("total", 4)
        if "social" not in preferences:
            preferences.append("social")
        if "photo_friendly" not in preferences:
            preferences.append("photo_friendly")

    return {
        "raw_text": structured_goal.get("raw_text", ""),
        "scenario": scenario,
        "duration_hours": duration_hours,
        "people": people,
        "preferences": preferences,
        "origin": structured_goal.get("location", {}).get("start_location") or "家",
        "structured_goal": structured_goal,
    }


def parse_goal(user_text: str, use_llm: bool = False, llm_mode: Optional[str] = None) -> Dict[str, Any]:
    """Parse a Chinese natural-language local-life request into planner-compatible goal."""
    structured_goal = parse_structured_goal(user_text, use_llm=use_llm, llm_mode=llm_mode)
    return adapt_structured_goal_to_legacy_goal(structured_goal)
