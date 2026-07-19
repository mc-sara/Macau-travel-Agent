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

SENIOR_KEYWORDS = ("爸妈", "父母", "爸爸", "妈妈", "爷爷", "奶奶", "外公", "外婆", "长者", "老人", "长辈", "银龄")


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


def _contains_any(text: str, *keywords: str) -> bool:
    return any(keyword in text for keyword in keywords)


SYSTEM_MESSAGE = (
    "你是银龄澳门本地生活 Agent 的需求解析器。"
    "只把用户自然语言转成适老 structured_goal JSON，不生成路线。"
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
    default_base_url = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    default_model = "qwen3.7-max"
    return {
        "api_key": (
            os.environ.get("OPENAI_API_KEY")
            or os.environ.get("DASHSCOPE_API_KEY")
            or file_values.get("OPENAI_API_KEY", "")
            or file_values.get("DASHSCOPE_API_KEY", "")
        ),
        "base_url": (
            os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("DASHSCOPE_BASE_URL")
            or file_values.get("OPENAI_BASE_URL", "")
            or file_values.get("DASHSCOPE_BASE_URL", "")
            or default_base_url
        ).rstrip("/"),
        "model": (
            os.environ.get("OPENAI_MODEL")
            or os.environ.get("DASHSCOPE_MODEL")
            or file_values.get("OPENAI_MODEL", "")
            or file_values.get("DASHSCOPE_MODEL", "")
            or default_model
        ),
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
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
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


def _with_debug(goal: Dict[str, Any], **debug: Any) -> Dict[str, Any]:
    existing = goal.get("_debug", {}) if isinstance(goal.get("_debug", {}), dict) else {}
    goal["_debug"] = {**existing, **debug}
    return goal


def _base(raw_text: str) -> Dict[str, Any]:
    goal = default_goal(raw_text)
    goal["missing_info"] = ["start_location", "exact_start_time", "mobility_limit"]
    goal["assumptions"] = ["未提供起点，默认从澳门半岛出发", "未提供具体开始时间，默认下午2点开始", "默认按低疲劳适老路线规划"]
    return goal


def _apply_text_fallbacks(goal: Dict[str, Any], user_text: str, normalization_steps: list) -> None:
    gender_counts = _parse_gender_counts(user_text)
    total_people = _parse_total_people(user_text)
    if total_people is not None:
        goal["people"]["total"] = total_people
        normalization_steps.append("user_text total_people -> people.total")
    if gender_counts:
        goal["people"].update(gender_counts)
        normalization_steps.append("user_text gender_count -> people.male/female")

    if _contains_any(user_text, *SENIOR_KEYWORDS):
        goal["relationship_type"] = "family_with_seniors"
        goal["outing_intent"] = "low_fatigue_relax"
        if goal["people"].get("seniors", 0) <= 0:
            goal["people"]["seniors"] = 2 if _contains_any(user_text, "爸妈", "父母", "爷爷奶奶") else 1
        goal["people"]["total"] = max(goal["people"].get("total", 0), goal["people"].get("seniors", 0) + 1)
        goal["people"]["relationship_note"] = "长者/家属陪同出行"
        normalization_steps.append("user_text senior_mention -> people.seniors")
    elif goal.get("relationship_type") not in {"family_with_seniors", "caregiver_with_seniors", "senior_couple", "solo_senior"}:
        goal["relationship_type"] = "general"
        goal["outing_intent"] = goal.get("outing_intent") if goal.get("outing_intent") in {"low_fatigue_relax", "half_day_outing", "dinner_plan", "local_experience", "rainy_day_plan", "general_outing"} else "general_outing"
        normalization_steps.append("non_senior_relationship -> general senior-safe")

    hard = goal.setdefault("hard_constraints", [])
    soft = goal.setdefault("soft_preferences", [])
    for item in ["senior_friendly", "low_fatigue", "short_walking_distance"]:
        if item not in hard:
            hard.append(item)
    if _contains_any(user_text, "不要爬楼梯", "不爬楼梯", "避免楼梯", "别爬楼梯", "楼梯") and "avoid_stairs" not in hard:
        hard.append("avoid_stairs")
        normalization_steps.append("user_text avoid_stairs -> hard_constraints")
    if _contains_any(user_text, "轮椅", "无障碍") and "wheelchair_friendly" not in hard:
        hard.append("wheelchair_friendly")
        normalization_steps.append("user_text wheelchair -> hard_constraints")
    if "电梯" in user_text and "elevator_required" not in hard:
        hard.append("elevator_required")
        normalization_steps.append("user_text elevator -> hard_constraints")
    if _contains_any(user_text, "厕所", "洗手间") and "toilet_access" not in soft:
        soft.append("toilet_access")
        normalization_steps.append("user_text toilet -> soft_preferences")
    if _contains_any(user_text, "坐", "休息") and "rest_area" not in soft:
        soft.append("rest_area")
        normalization_steps.append("user_text rest_area -> soft_preferences")
    if _contains_any(user_text, "清淡", "少油", "少盐", "低卡", "健康餐") and "low_calorie_food" not in soft:
        soft.append("low_calorie_food")
        normalization_steps.append("user_text light_food -> soft_preferences")

    if _is_vague_short_input(user_text):
        goal["relationship_type"] = "general"
        goal["clarification_needed"] = True
        goal["missing_info"] = ["start_location", "senior_count", "mobility_limit", "meal_preference"]
        goal["clarification_questions"] = [
            "请问从澳门哪里出发？",
            "同行长者大概几位？是否能走楼梯？",
            "晚餐有没有清淡、少油少盐或忌口要求？",
        ]
        normalization_steps.append("user_text vague_input -> senior_clarification_needed")


def normalize_llm_goal_payload(raw_goal: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    parsed = raw_goal.get("parsed_request", {}) if isinstance(raw_goal.get("parsed_request", {}), dict) else {}
    group = raw_goal.get("group", {}) if isinstance(raw_goal.get("group", {}), dict) else {}
    normalization_steps = []
    raw_llm_shape = sorted(raw_goal.keys())
    goal = default_goal(user_text)

    for key, value in raw_goal.items():
        if key != "parsed_request":
            if isinstance(value, dict) and isinstance(goal.get(key), dict):
                goal[key].update(value)
            else:
                goal[key] = value

    relationship = parsed.get("relationship_type") or goal.get("relationship_type")
    outing_intent = parsed.get("outing_intent") or goal.get("outing_intent")
    party_size = parsed.get("party_size") or parsed.get("people_count") or parsed.get("total_people") or group.get("total_people") or group.get("party_size")
    composition = parsed.get("group_composition", {}) if isinstance(parsed.get("group_composition", {}), dict) else {}
    group_composition = group.get("gender_count", {}) if isinstance(group.get("gender_count", {}), dict) else {}
    if not composition and group_composition:
        composition = group_composition

    if party_size is not None:
        goal["people"]["total"] = party_size
        normalization_steps.append("provider party_size -> people.total")
    for key in ["male", "female", "children", "seniors"]:
        if composition.get(key) is not None:
            goal["people"][key] = composition.get(key) or 0
            normalization_steps.append(f"provider composition.{key} -> people.{key}")

    goal["relationship_type"] = relationship or "general"
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

    missing_info = parsed.get("missing_info") or raw_goal.get("missing_info")
    if isinstance(missing_info, list) and missing_info:
        goal["missing_info"] = missing_info
    assumptions = parsed.get("assumptions") or raw_goal.get("assumptions")
    if isinstance(assumptions, list) and assumptions:
        goal["assumptions"] = assumptions

    _apply_text_fallbacks(goal, user_text, normalization_steps)
    goal["raw_text"] = raw_goal.get("raw_text") or raw_goal.get("original_input") or user_text
    goal["confidence"] = raw_goal.get("confidence", parsed.get("confidence", 0.8 if parsed else 0.6))
    normalized = enrich_goal(validate_and_normalize_goal(goal))
    return _with_debug(normalized, raw_llm_shape=raw_llm_shape, normalization_steps=normalization_steps, normalized_from_provider_payload=bool(parsed or group))


def _parse_goal_with_real_llm(user_text: str, client: Optional[Any] = None) -> Dict[str, Any]:
    config = load_llm_config()
    if not config.get("api_key") or not config.get("base_url"):
        return parse_goal_with_mock_llm(user_text)
    provider = client or OpenAICompatibleClient()
    response = provider.chat_completion(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        messages=[{"role": "system", "content": SYSTEM_MESSAGE}, {"role": "user", "content": build_llm_prompt(user_text)}],
        temperature=0,
    )
    content = response["choices"][0]["message"]["content"]
    raw_goal = _extract_json_object(content)
    return _with_debug(normalize_llm_goal_payload(raw_goal, user_text), llm_mode="real", llm_fallback_used=False, llm_provider="real")


def _is_vague_short_input(text: str) -> bool:
    stripped = text.strip().strip("。！？!?")
    has_senior_signal = _contains_any(stripped, *SENIOR_KEYWORDS)
    has_specific_preference = _contains_any(stripped, "清淡", "少油", "不要爬楼梯", "不爬楼梯", "室内", "厕所", "休息", "轮椅", "电梯", "无障碍")
    return len(stripped) <= 10 and _contains_any(stripped, "出去玩", "玩一下", "逛逛") and not has_senior_signal and not has_specific_preference


PROMPT_TEMPLATE = """
你是银龄澳门本地生活 Agent 的需求解析器。
你的任务是把用户自然语言转成结构化 JSON，供适老路线 Planner 使用。

要求：
1. 只输出 JSON，不要输出解释文本。
2. 不要生成路线，不要推荐景点，不要生成行程。
3. 不要编造用户没有说的信息；缺失内容写入 missing_info。
4. 如果必须做默认假设，写入 assumptions。
5. 必须区分 hard_constraints 和 soft_preferences。
6. relationship_type 必须从枚举中选择。
7. outing_intent 必须从枚举中选择。
8. 追问优先围绕出发地点、长者人数、是否能走楼梯、是否需要轮椅/电梯、步行接受程度和清淡饮食。

relationship_type 枚举：
family_with_seniors, caregiver_with_seniors, senior_couple, solo_senior, general

outing_intent 枚举：
low_fatigue_relax, half_day_outing, dinner_plan, local_experience, rainy_day_plan, general_outing

hard_constraints / soft_preferences 可选值：
low_fatigue, short_walking_distance, senior_friendly, avoid_stairs, indoor_required, low_calorie_food, budget_control, avoid_long_queue, local_specialty, rest_area, toilet_access, flat_route, wheelchair_friendly, elevator_required, shaded_or_indoor, simple_transport, family_notification, route_card_needed, oral_guide_needed

用户输入：{user_text}
""".strip()


def build_llm_prompt(user_text: str) -> str:
    return PROMPT_TEMPLATE.format(user_text=user_text)


def parse_goal_with_mock_llm(user_text: str, llm_mode: str = "mock", fallback_used: bool = False) -> Dict[str, Any]:
    goal = _base(user_text)
    steps = []
    _apply_text_fallbacks(goal, user_text.strip(), steps)
    if not _is_vague_short_input(user_text) and goal.get("relationship_type") == "general":
        goal["confidence"] = 0.55
    elif _is_vague_short_input(user_text):
        goal["confidence"] = 0.35
    else:
        goal["confidence"] = 0.9
    return _with_debug(enrich_goal(validate_and_normalize_goal(goal)), llm_mode=llm_mode, llm_fallback_used=fallback_used, llm_provider="mock", normalization_steps=steps)


def parse_goal_with_llm(user_text: str, use_mock: bool = True, client: Optional[Any] = None, llm_mode: Optional[str] = None) -> Dict[str, Any]:
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
