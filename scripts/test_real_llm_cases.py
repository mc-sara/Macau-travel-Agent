import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.parser import parse_structured_goal
from agent.llm_goal_parser import load_llm_config, redact_config


CASES: List[Dict[str, Any]] = [
    {
        "id": "friends_group",
        "text": "今天下午2男3女出去玩，安排一下。",
        "expect": {
            "relationship_type": "friends",
            "people.total": 5,
            "people.male": 2,
            "people.female": 3,
            "planning_strategy.restaurant_table_size_required": 5,
        },
    },
    {
        "id": "couple_date",
        "text": "今天下午想和对象约会，浪漫一点但别太累。",
        "expect": {
            "relationship_type": "couple",
            "outing_intent": "date_plan",
            "people.total": 2,
            "soft_preferences contains": "romantic",
        },
    },
    {
        "id": "family_child",
        "text": "带5岁孩子玩几个小时，老婆想吃低卡一点。",
        "expect": {
            "relationship_type": "family_with_children",
            "people.children": 1,
            "hard_constraints contains": "kid_friendly",
            "soft_preferences contains": "low_calorie_food",
        },
    },
    {
        "id": "family_seniors",
        "text": "我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。",
        "expect": {
            "relationship_type": "family_with_seniors",
            "people.seniors": 2,
            "hard_constraints contains": "avoid_stairs",
        },
    },
    {
        "id": "vague_input",
        "text": "下午出去玩一下。",
        "expect": {
            "relationship_type": "general",
            "clarification_needed": True,
            "missing_info nonempty": True,
        },
    },
]


def get_nested(data: Dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def evaluate_goal(goal: Dict[str, Any], expectations: Dict[str, Any]) -> Tuple[bool, List[str]]:
    failures: List[str] = []
    for key, expected in expectations.items():
        if key.endswith(" contains"):
            path = key[: -len(" contains")]
            actual = get_nested(goal, path)
            if not isinstance(actual, list) or expected not in actual:
                failures.append(f"{path} expected to contain {expected} got {actual}")
        elif key.endswith(" nonempty"):
            path = key[: -len(" nonempty")]
            actual = get_nested(goal, path)
            if expected and not actual:
                failures.append(f"{path} expected nonempty got {actual}")
            elif not expected and actual:
                failures.append(f"{path} expected empty got {actual}")
        else:
            actual = get_nested(goal, key)
            if actual != expected:
                failures.append(f"{key} expected {expected} got {actual}")
    return len(failures) == 0, failures


def run_cases(client: Optional[Any] = None, llm_mode: str = "real") -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for case in CASES:
        goal = parse_structured_goal(case["text"], llm_mode=llm_mode, client=client)
        passed, failures = evaluate_goal(goal, case["expect"])
        results.append({
            "id": case["id"],
            "text": case["text"],
            "passed": passed,
            "failures": failures,
            "goal": goal,
        })
    return results


def main() -> int:
    print("config", redact_config(load_llm_config()))
    results = run_cases(llm_mode="real")
    failed = 0
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] {result['id']}")
        goal = result["goal"]
        print(
            "  normalized:",
            f"relationship_type={goal.get('relationship_type')}",
            f"outing_intent={goal.get('outing_intent')}",
            f"people={goal.get('people')}",
        )
        debug = goal.get("_debug", {})
        if debug:
            print("  debug:", {k: debug.get(k) for k in ["llm_mode", "llm_provider", "llm_fallback_used", "normalization_steps"]})
        for failure in result["failures"]:
            print("  -", failure)
        if not result["passed"]:
            failed += 1
    print(f"summary: {len(results) - failed}/{len(results)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
