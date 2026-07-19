import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TTS_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"


def _parse_env_file(path: Optional[Path] = None) -> Dict[str, str]:
    env_path = path or ROOT / ".env"
    values: Dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_tts_config() -> Dict[str, Any]:
    env = _parse_env_file()
    workspace_id = os.environ.get("ALIYUN_TTS_WORKSPACE_ID") or env.get("ALIYUN_TTS_WORKSPACE_ID", "")
    endpoint = os.environ.get("ALIYUN_TTS_ENDPOINT") or env.get("ALIYUN_TTS_ENDPOINT", "")
    if not endpoint and workspace_id:
        endpoint = f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
    if not endpoint:
        endpoint = DEFAULT_TTS_ENDPOINT
    return {
        "api_key": os.environ.get("ALIYUN_TTS_API_KEY") or env.get("ALIYUN_TTS_API_KEY", ""),
        "workspace_id": workspace_id,
        "endpoint": endpoint,
        "model": os.environ.get("ALIYUN_TTS_MODEL") or env.get("ALIYUN_TTS_MODEL", "cosyvoice-v3-flash"),
        "mandarin_voice": os.environ.get("ALIYUN_TTS_MANDARIN_VOICE") or env.get("ALIYUN_TTS_MANDARIN_VOICE", "longanyang"),
        "cantonese_voice": os.environ.get("ALIYUN_TTS_CANTONESE_VOICE") or env.get("ALIYUN_TTS_CANTONESE_VOICE", "longanyang"),
        "format": os.environ.get("ALIYUN_TTS_FORMAT") or env.get("ALIYUN_TTS_FORMAT", "wav"),
        "sample_rate": int(os.environ.get("ALIYUN_TTS_SAMPLE_RATE") or env.get("ALIYUN_TTS_SAMPLE_RATE", "24000")),
        "rate": float(os.environ.get("ALIYUN_TTS_RATE") or env.get("ALIYUN_TTS_RATE", "1.0")),
        "output_dir": os.environ.get("TTS_OUTPUT_DIR") or env.get("TTS_OUTPUT_DIR", "static/audio"),
    }


def _safe_language(language: str) -> str:
    language = (language or "mandarin").strip().lower()
    if language in {"yue", "cantonese", "粤语", "廣東話", "广东话"}:
        return "cantonese"
    return "mandarin"


def _download_file(url: str, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=60) as response:
        output_path.write_bytes(response.read())
    return output_path.stat().st_size


def synthesize_speech(text: str, language: str = "mandarin", filename_prefix: str = "tts") -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("text is required")

    config = load_tts_config()
    if not config["api_key"]:
        raise RuntimeError("ALIYUN_TTS_API_KEY is missing")

    lang = _safe_language(language)
    voice = config["cantonese_voice"] if lang == "cantonese" else config["mandarin_voice"]
    payload = {
        "model": config["model"],
        "input": {
            "text": text,
            "voice": voice,
            "format": config["format"],
            "sample_rate": config["sample_rate"],
        },
    }
    if lang == "cantonese" and voice == "longanhuan_v3":
        payload["input"]["instruction"] = "请用广东话表达。"
    # 当前可用性测试显示最小参数最稳定；非必须参数暂不发送，避免引擎 418/428。

    request = Request(
        config["endpoint"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Aliyun TTS HTTP {exc.code}: {body[:300]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Aliyun TTS request failed: {exc}") from exc

    audio = ((data.get("output") or {}).get("audio") or {})
    audio_url = audio.get("url")
    if not audio_url:
        raise RuntimeError(f"Aliyun TTS returned no audio url: {data}")

    ext = config["format"].lower()
    filename = f"{filename_prefix}_{lang}_{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}"
    relative_path = Path(config["output_dir"]) / filename
    output_path = ROOT / relative_path
    size = _download_file(audio_url, output_path)

    return {
        "provider": "aliyun_cosyvoice",
        "model": config["model"],
        "voice": voice,
        "language": lang,
        "audio_url": "/" + str(relative_path).replace(os.sep, "/"),
        "file_path": str(output_path),
        "bytes": size,
        "request_id": data.get("request_id", ""),
        "expires_at": audio.get("expires_at"),
        "usage": data.get("usage", {}),
    }
