import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.llm_goal_parser import (
    OpenAICompatibleClient,
    _extract_json_object,
    build_llm_prompt,
    load_llm_config,
    redact_config,
)


def main() -> None:
    cfg = load_llm_config()
    print("config", redact_config(cfg))

    client = OpenAICompatibleClient()
    text = "今天下午2男3女出去玩，安排一下。"

    resp = client.chat_completion(
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
        model=cfg["model"],
        messages=[
            {
                "role": "system",
                "content": "你是澳门本地生活 Agent 的需求解析器。必须只输出 JSON，不要输出解释文本。",
            },
            {
                "role": "user",
                "content": build_llm_prompt(text),
            },
        ],
        temperature=0,
    )

    content = resp["choices"][0]["message"]["content"]
    raw = _extract_json_object(content)

    print("raw_json_begin")
    print(json.dumps(raw, ensure_ascii=False, indent=2))
    print("raw_json_end")


if __name__ == "__main__":
    main()
