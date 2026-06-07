import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from agent.goal_enricher import enrich_goal
from agent.goal_schema import default_goal
from agent.goal_validator import validate_and_normalize_goal


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


def _mentions_mixed_gender_without_counts(text: str) -> bool:
    if _parse_gender_counts(text) is not None:
        return False
    return _contains_any(text, "有男有女", "男女都有", "男生女生都有", "有男生有女生")


SYSTEM_MESSAGE = (
    "你是澳门本地生活 Agent 的需求解析器。"
    "你的任务不是生成游玩路线，而是把用户自然语言转成结构化 JSON。"
    "必须只输出 JSON。"
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_env_file(env_file: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not env_file.exists():
        return values
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def load_llm_config(env_file: Optional[Path] = None) -> Dict[str, str]:
    configured_env_file = os.environ.get("MACAU_AGENT_ENV_FILE")
    path = env_file or (Path(configured_env_file) if configured_env_file else _project_root() / ".env")
    file_values = _parse_env_file(path)
    return {
        "api_key": os.environ.get("OPENAI_API_KEY") or file_values.get("OPENAI_API_KEY", ""),
        "base_url": (os.environ.get("OPENAI_BASE_URL") or file_values.get("OPENAI_BASE_URL", "")).rstrip("/"),
        "model": os.environ.get("OPENAI_MODEL") or file_values.get("OPENAI_MODEL", "gpt-5.5"),
    }


def redact_config(config: Dict[str, str]) -> Dict[str, str]:
    redacted = dict(config)
    if redacted.get("api_key"):
        redacted["api_key"] = "[REDACTED]"
    return redacted


class OpenAICompatibleClient:
    def chat_completion(self, *, base_url: str, api_key: str, model: str, messages: list, temperature: float = 0) -> Dict[str, Any]:
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


def _extract_json_object(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    return json.loads(stripped)


def normalize_llm_goal_payload(raw_goal: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    """Normalize provider-specific JSON into our structured_goal schema.

    Some OpenAI-compatible models return useful fields under parsed_request instead
    of the top-level schema. This adapter lifts those fields before validation.
    """
    parsed = raw_goal.get("parsed_request", {}) if isinstance(raw_goal.get("parsed_request", {}), dict) else {}
    group = raw_goal.get("group", {}) if isinstance(raw_goal.get("group", {}), dict) else {}
    normalization_steps = []
    raw_llm_shape = sorted(raw_goal.keys())
    goal = default_goal(user_text)

    # Start with any top-level model fields, then override with parsed_request when
    # it contains more specific values.
    for key, value in raw_goal.items():
        if key != "parsed_request":
            if isinstance(value, dict) and isinstance(goal.get(key), dict):
                goal[key].update(value)
            else:
                goal[key] = value

    relationship = parsed.get("relationship_type") or goal.get("relationship_type")
    outing_intent = parsed.get("outing_intent") or goal.get("outing_intent")
    party_size = (
        parsed.get("party_size")
        or parsed.get("people_count")
        or parsed.get("total_people")
        or group.get("total_people")
        or group.get("party_size")
    )
    composition = parsed.get("group_composition", {}) if isinstance(parsed.get("group_composition", {}), dict) else {}
    group_composition = group.get("gender_count", {}) if isinstance(group.get("gender_count", {}), dict) else {}
    if not composition and group_composition:
        composition = group_composition

    male = composition.get("male", goal.get("people", {}).get("male", 0))
    female = composition.get("female", goal.get("people", {}).get("female", 0))
    children = composition.get("children", goal.get("people", {}).get("children", 0))
    seniors = composition.get("seniors", goal.get("people", {}).get("seniors", 0))

    if party_size is not None:
        goal["people"]["total"] = party_size
        if parsed.get("party_size") is not None:
            normalization_steps.append("parsed_request.party_size -> people.total")
        elif parsed.get("people_count") is not None:
            normalization_steps.append("parsed_request.people_count -> people.total")
        elif parsed.get("total_people") is not None:
            normalization_steps.append("parsed_request.total_people -> people.total")
        elif group.get("total_people") is not None:
            normalization_steps.append("group.total_people -> people.total")
        elif group.get("party_size") is not None:
            normalization_steps.append("group.party_size -> people.total")
    goal["people"]["male"] = male or 0
    goal["people"]["female"] = female or 0
    goal["people"]["children"] = children or 0
    goal["people"]["seniors"] = seniors or 0
    if composition.get("male") is not None:
        normalization_steps.append(("group.gender_count" if group_composition else "parsed_request.group_composition") + ".male -> people.male")
    if composition.get("female") is not None:
        normalization_steps.append(("group.gender_count" if group_composition else "parsed_request.group_composition") + ".female -> people.female")

    # For this demo, a mixed non-family social group maps to friends so the
    # existing planner picks the group route instead of falling back to general.
    if relationship == "mixed_group" and goal["people"].get("total", 0) >= 3:
        relationship = "friends"
        normalization_steps.append("mixed_group + total>=3 -> friends")
    goal["relationship_type"] = relationship or "general"

    if outing_intent in (None, "general_outing") and goal["relationship_type"] == "friends":
        outing_intent = "half_day_outing"
        normalization_steps.append("general_outing + friends -> half_day_outing")
    goal["outing_intent"] = outing_intent or "general_outing"

    if parsed.get("date"):
        goal["time"]["date"] = parsed["date"]
    if parsed.get("time_period"):
        goal["time"]["start_period"] = parsed["time_period"]
    if parsed.get("duration_hours"):
        goal["time"]["duration_hours"] = parsed["duration_hours"]
    if isinstance(raw_goal.get("time"), dict):
        raw_time = raw_goal["time"]
        if raw_time.get("date"):
            goal["time"]["date"] = raw_time["date"]
        if raw_time.get("period"):
            goal["time"]["start_period"] = raw_time["period"]
            normalization_steps.append("time.period -> time.start_period")

    constraints = parsed.get("constraints") or parsed.get("hard_constraints") or raw_goal.get("hard_constraints") or []
    preferences = parsed.get("preferences") or parsed.get("soft_preferences") or raw_goal.get("soft_preferences") or []
    goal["hard_constraints"] = list(constraints) if isinstance(constraints, list) else []
    goal["soft_preferences"] = list(preferences) if isinstance(preferences, list) else []

    if goal["relationship_type"] == "friends":
        for pref in ["social", "photo_friendly", "dinner_together"]:
            if pref not in goal["soft_preferences"]:
                goal["soft_preferences"].append(pref)

    text_gender_counts = _parse_gender_counts(user_text)
    if text_gender_counts and (goal["people"].get("male", 0) == 0 and goal["people"].get("female", 0) == 0):
        goal["people"].update(text_gender_counts)
        goal["relationship_type"] = "friends"
        if goal.get("outing_intent") in (None, "general_outing"):
            goal["outing_intent"] = "half_day_outing"
        for pref in ["social", "photo_friendly", "dinner_together"]:
            if pref not in goal["soft_preferences"]:
                goal["soft_preferences"].append(pref)
        normalization_steps.append("user_text gender_count -> people.male/female")

    if _contains_any(user_text, "孩子", "小孩", "亲子") and goal["people"].get("children", 0) == 0:
        goal["relationship_type"] = "family_with_children"
        goal["people"]["children"] = 1
        goal["people"]["total"] = max(goal["people"].get("total", 0), 3)
        if "kid_friendly" not in goal["hard_constraints"]:
            goal["hard_constraints"].append("kid_friendly")
        if "low_fatigue" not in goal["hard_constraints"]:
            goal["hard_constraints"].append("low_fatigue")
        normalization_steps.append("user_text child_mention -> people.children")

    if _contains_any(user_text, "爸妈", "父母", "爸爸妈妈") and goal["people"].get("seniors", 0) == 0:
        goal["relationship_type"] = "family_with_seniors"
        goal["people"]["seniors"] = 2
        goal["people"]["total"] = max(goal["people"].get("total", 0), 3)
        for constraint in ["senior_friendly", "low_fatigue"]:
            if constraint not in goal["hard_constraints"]:
                goal["hard_constraints"].append(constraint)
        normalization_steps.append("user_text parent_mention -> people.seniors")

    if _contains_any(user_text, "不要爬楼梯", "不爬楼梯", "避免楼梯", "别爬楼梯") and "avoid_stairs" not in goal["hard_constraints"]:
        goal["hard_constraints"].append("avoid_stairs")
        normalization_steps.append("user_text avoid_stairs -> hard_constraints")

    if _contains_any(user_text, "低卡", "减肥", "少油", "健康餐") and "low_calorie_food" not in goal["soft_preferences"]:
        goal["soft_preferences"].append("low_calorie_food")
        normalization_steps.append("user_text low_calorie -> soft_preferences")

    if _contains_any(user_text, "密室", "剧本杀", "escape room"):
        if "escape_room" not in goal["soft_preferences"]:
            goal["soft_preferences"].append("escape_room")
        if "indoor_activity" not in goal["soft_preferences"]:
            goal["soft_preferences"].append("indoor_activity")
        if goal["relationship_type"] == "general":
            goal["relationship_type"] = "friends"
            goal["outing_intent"] = "indoor_plan"
            for pref in ["social", "chat_friendly"]:
                if pref not in goal["soft_preferences"]:
                    goal["soft_preferences"].append(pref)
        goal["clarification_needed"] = False
        goal["clarification_questions"] = []
        normalization_steps.append("user_text escape_room -> friends indoor preference")

    if _mentions_mixed_gender_without_counts(user_text):
        goal["clarification_needed"] = True
        if "gender_breakdown" not in goal["missing_info"]:
            goal["missing_info"].append("gender_breakdown")
        question = "请补充男女各有几个人？"
        if question not in goal["clarification_questions"]:
            goal["clarification_questions"].append(question)
        normalization_steps.append("user_text mixed_gender_without_counts -> clarification_needed")

    if _is_vague_short_input(user_text):
        goal["relationship_type"] = "general"
        goal["clarification_needed"] = True
        if not goal.get("missing_info"):
            goal["missing_info"] = ["relationship_type", "people_count", "budget", "activity_preference"]
        if not goal.get("clarification_questions"):
            goal["clarification_questions"] = [
                "是一个人、情侣、朋友还是家庭出行？",
                "大概几个人？",
                "希望轻松一点还是可以多走路？",
            ]
        normalization_steps.append("user_text vague_input -> clarification_needed")

    missing_info = parsed.get("missing_info") or raw_goal.get("missing_info")
    if isinstance(missing_info, list) and missing_info:
        goal["missing_info"] = missing_info

    assumptions = parsed.get("assumptions") or raw_goal.get("assumptions")
    if isinstance(assumptions, list) and assumptions:
        goal["assumptions"] = assumptions

    goal["raw_text"] = raw_goal.get("raw_text") or raw_goal.get("original_input") or user_text
    goal["confidence"] = raw_goal.get("confidence", parsed.get("confidence", 0.8 if parsed else 0.6))
    normalized = enrich_goal(validate_and_normalize_goal(goal))
    return _with_debug(
        normalized,
        raw_llm_shape=raw_llm_shape,
        normalization_steps=normalization_steps,
        normalized_from_provider_payload=bool(parsed or group),
    )


def _parse_goal_with_real_llm(user_text: str, client: Optional[Any] = None) -> Dict[str, Any]:
    config = load_llm_config()
    if not config.get("api_key") or not config.get("base_url"):
        return parse_goal_with_mock_llm(user_text)
    provider = client or OpenAICompatibleClient()
    response = provider.chat_completion(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": build_llm_prompt(user_text)},
        ],
        temperature=0,
    )
    content = response["choices"][0]["message"]["content"]
    raw_goal = _extract_json_object(content)
    return _with_debug(
        normalize_llm_goal_payload(raw_goal, user_text),
        llm_mode="real",
        llm_fallback_used=False,
        llm_provider="real",
    )


def _is_vague_short_input(text: str) -> bool:
    stripped = text.strip().strip("。！？!?")
    has_group_signal = _contains_any(stripped, "男", "女", "朋友", "对象", "情侣", "孩子", "小孩", "爸妈", "父母", "长辈", "老人", "同学", "同事")
    has_specific_preference = _contains_any(stripped, "低卡", "浪漫", "拍照", "不要爬楼梯", "不爬楼梯", "室内", "预算", "餐厅", "咖啡")
    return len(stripped) <= 10 and _contains_any(stripped, "出去玩", "玩一下", "逛逛") and not has_group_signal and not has_specific_preference


PROMPT_TEMPLATE = """
你是澳门本地生活 Agent 的需求解析器。
你的任务是把用户自然语言转成结构化 JSON。

要求：
1. 只输出 JSON，不要输出解释文本。
2. 不要生成路线，不要推荐景点，不要生成行程。
3. 不要编造用户没有说的信息；缺失内容写入 missing_info。
4. 如果必须做默认假设，写入 assumptions。
5. 必须区分 hard_constraints 和 soft_preferences。
6. relationship_type 必须从枚举中选择。
7. outing_intent 必须从枚举中选择。

relationship_type 枚举：
family_with_children, family_with_seniors, couple, friends, solo, business, classmates, mixed_group, general

outing_intent 枚举：
half_day_outing, dinner_plan, date_plan, photo_citywalk, kid_friendly_play, low_fatigue_relax, celebration, local_experience, rainy_day_plan, indoor_plan, general_outing

用户输入：{user_text}
""".strip()


def build_llm_prompt(user_text: str) -> str:
    return PROMPT_TEMPLATE.format(user_text=user_text)


def _contains_any(text: str, *keywords: str) -> bool:
    return any(keyword in text for keyword in keywords)


def _base(raw_text: str) -> Dict[str, Any]:
    goal = default_goal(raw_text)
    goal["missing_info"] = ["start_location", "budget", "exact_start_time"]
    goal["assumptions"] = ["未提供起点，默认从澳门半岛出发", "未提供预算，默认中等预算", "未提供具体开始时间，默认下午2点开始"]
    return goal


def _with_debug(goal: Dict[str, Any], **debug: Any) -> Dict[str, Any]:
    existing = goal.get("_debug", {}) if isinstance(goal.get("_debug", {}), dict) else {}
    goal["_debug"] = {**existing, **debug}
    return goal


def parse_goal_with_mock_llm(user_text: str, llm_mode: str = "mock", fallback_used: bool = False) -> Dict[str, Any]:
    text = user_text.strip()
    goal = _base(user_text)
    gender_counts = _parse_gender_counts(text)
    total_people = _parse_total_people(text)

    if gender_counts is not None:
        goal.update({
            "relationship_type": "friends",
            "outing_intent": "half_day_outing",
            "confidence": 0.9,
            "people": {**goal["people"], **gender_counts, "children": 0, "seniors": 0, "relationship_note": "按多人朋友聚会处理"},
            "soft_preferences": ["social", "photo_friendly", "dinner_together", "chat_friendly"] + (["escape_room", "indoor_activity"] if "密室" in text else []),
        })
    elif _contains_any(text, "爸妈", "父母", "长辈", "老人", "妈妈", "爸爸"):
        goal.update({
            "relationship_type": "family_with_seniors",
            "outing_intent": "low_fatigue_relax",
            "confidence": 0.9,
            "people": {**goal["people"], "total": total_people or 3, "seniors": 2, "relationship_note": "带父母或长辈轻松游玩"},
            "hard_constraints": ["senior_friendly", "avoid_stairs", "low_fatigue", "short_walking_distance"],
            "soft_preferences": ["local_specialty"],
        })
    elif _contains_any(text, "孩子", "小孩", "亲子", "老婆"):
        child_age_match = re.search(r"([0-9一二两三四五六七八九十]+)\s*岁", text)
        goal.update({
            "relationship_type": "family_with_children",
            "outing_intent": "kid_friendly_play",
            "confidence": 0.9,
            "people": {**goal["people"], "total": 3, "male": 1, "female": 1, "children": 1, "seniors": 0, "relationship_note": "亲子家庭出行"},
            "hard_constraints": ["kid_friendly", "low_fatigue", "short_walking_distance"],
            "soft_preferences": ["low_calorie_food"] if "低卡" in text or "减肥" in text else [],
        })
        if child_age_match:
            goal["people"]["child_age_note"] = child_age_match.group(0)
    elif _contains_any(text, "对象", "约会", "情侣", "浪漫", "女朋友", "男朋友"):
        goal.update({
            "relationship_type": "couple",
            "outing_intent": "date_plan",
            "confidence": 0.88,
            "people": {**goal["people"], "total": 2, "relationship_note": "情侣约会"},
            "hard_constraints": ["low_fatigue"] if "别太累" in text or "不要太累" in text else [],
            "soft_preferences": ["romantic", "photo_friendly", "surprise_action"],
        })
    elif _contains_any(text, "朋友", "聚会") or (total_people is not None and total_people >= 3) or _contains_any(text, "密室", "剧本杀", "escape room"):
        escape_activity_preferences = ["escape_room", "indoor_activity"] if _contains_any(text, "密室", "剧本杀", "escape room") else []
        needs_gender_breakdown = _mentions_mixed_gender_without_counts(text)
        clarification_questions = ["请补充男女各有几个人？"] if needs_gender_breakdown else []
        goal.update({
            "relationship_type": "friends",
            "outing_intent": "indoor_plan" if escape_activity_preferences else "half_day_outing",
            "confidence": 0.86 if escape_activity_preferences else 0.78,
            "people": {**goal["people"], "total": total_people or 4, "relationship_note": "密室/剧本杀按朋友组队活动处理" if escape_activity_preferences else "朋友聚会"},
            "soft_preferences": ["social", "photo_friendly", "dinner_together"] + escape_activity_preferences,
            "missing_info": goal["missing_info"] + (["gender_breakdown"] if needs_gender_breakdown else []),
            "clarification_needed": needs_gender_breakdown,
            "clarification_questions": clarification_questions,
        })
    else:
        goal.update({
            "relationship_type": "general",
            "outing_intent": "general_outing",
            "confidence": 0.35,
            "clarification_needed": True,
            "clarification_questions": [
                "是一个人、情侣、朋友还是家庭出行？",
                "大概几个人？",
                "希望轻松一点还是可以多走路？",
            ],
        })

    return _with_debug(
        enrich_goal(validate_and_normalize_goal(goal)),
        llm_mode=llm_mode,
        llm_fallback_used=fallback_used,
        llm_provider="mock",
    )


def parse_goal_with_llm(
    user_text: str,
    use_mock: bool = True,
    client: Optional[Any] = None,
    llm_mode: Optional[str] = None,
) -> Dict[str, Any]:
    mode = llm_mode or ("mock" if use_mock else "real")
    if mode == "mock":
        return parse_goal_with_mock_llm(user_text, llm_mode="mock")
    if mode == "real":
        return _parse_goal_with_real_llm(user_text, client=client)
    if mode == "auto":
        try:
            goal = _parse_goal_with_real_llm(user_text, client=client)
            return _with_debug(goal, llm_mode="auto", llm_fallback_used=False)
        except (KeyError, json.JSONDecodeError, urllib.error.URLError, TimeoutError, ValueError):
            return parse_goal_with_mock_llm(user_text, llm_mode="auto", fallback_used=True)
    raise ValueError(f"Unsupported llm_mode: {mode}")
