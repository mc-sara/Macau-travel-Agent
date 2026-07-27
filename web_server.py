import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from agent.executor import execute_plan
from agent.parser import parse_goal
from agent.planner import plan_day
from agent.tools import search_origin_candidates
from agent.tts import synthesize_speech


ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8899


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> Tuple[Dict[str, Any], str]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}, "missing request body"
    raw = handler.rfile.read(length).decode("utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {}, f"invalid json: {exc}"
    if not isinstance(data, dict):
        return {}, "request body must be a JSON object"
    return data, ""



def _origin_coords_from_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        lat = data.get("origin_lat")
        lng = data.get("origin_lng")
        if lat is None or lng is None or str(lat).strip() == "" or str(lng).strip() == "":
            return {}
        latitude = float(lat)
        longitude = float(lng)
    except (TypeError, ValueError):
        return {}
    if not (113.42 <= longitude <= 113.68 and 22.03 <= latitude <= 22.25):
        return {}
    return {"latitude": latitude, "longitude": longitude, "location": f"{longitude},{latitude}"}

def _all_plans(result: Dict[str, Any]) -> list:
    return [result["best_plan"]] + result.get("alternatives", [])


def _find_plan(result: Dict[str, Any], plan_id: str) -> Dict[str, Any]:
    for plan in _all_plans(result):
        if plan.get("id") == plan_id:
            return plan
    return result["best_plan"]


class MacauAgentHandler(BaseHTTPRequestHandler):
    server_version = "MacauAgentDemo/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/geocode":
            query = (parse_qs(parsed.query).get("q") or [""])[0].strip()
            if not query:
                _json_response(self, 400, {"error": "q is required"})
                return
            try:
                candidates = search_origin_candidates(query)
            except Exception as exc:
                _json_response(self, 500, {"error": str(exc)})
                return
            _json_response(self, 200, {"status": "success", "query": query, "candidates": candidates})
            return
        if path == "/":
            path = "/user_compact.html"
        if path == "/health":
            _json_response(self, 200, {"status": "ok"})
            return
        if path.startswith("/api/"):
            _json_response(self, 404, {"error": "unknown api endpoint"})
            return

        file_path = (ROOT / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(ROOT)) or not file_path.exists() or not file_path.is_file():
            _json_response(self, 404, {"error": "file not found"})
            return

        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/plan":
            data, error = _read_json(self)
            if error:
                _json_response(self, 400, {"error": error})
                return
            user_text = str(data.get("user_text", "")).strip()
            origin_text = str(data.get("origin_text", "")).strip()
            origin_coords = _origin_coords_from_payload(data)
            if not user_text:
                _json_response(self, 400, {"error": "user_text is required"})
                return
            try:
                result = plan_day(user_text, origin_text=origin_text, origin_coords=origin_coords)
            except Exception as exc:  # keep UI from hanging during demo
                _json_response(self, 500, {"error": str(exc)})
                return
            _json_response(self, 200, {"status": "success", "result": result})
            return

        if path == "/api/analyze":
            data, error = _read_json(self)
            if error:
                _json_response(self, 400, {"error": error})
                return
            user_text = str(data.get("user_text", "")).strip()
            origin_text = str(data.get("origin_text", "")).strip()
            if not user_text:
                _json_response(self, 400, {"error": "user_text is required"})
                return
            try:
                llm_mode = str(data.get("llm_mode", "auto")).strip() or "auto"
                goal = parse_goal(user_text, use_llm=(llm_mode != "mock"), llm_mode=llm_mode)
                goal["scenario"] = "senior"
                if origin_text:
                    goal["origin"] = origin_text
                    structured = goal.setdefault("structured_goal", {})
                    location = structured.setdefault("location", {})
                    if isinstance(location, dict):
                        location["start_location"] = origin_text
            except Exception as exc:
                _json_response(self, 500, {"error": str(exc)})
                return
            _json_response(
                self,
                200,
                {
                    "status": "success",
                    "goal": goal,
                    "structured_goal": goal.get("structured_goal", {}),
                    "clarification_needed": goal.get("structured_goal", {}).get("clarification_needed", False),
                    "clarification_questions": goal.get("structured_goal", {}).get("clarification_questions", []),
                },
            )
            return

        if path == "/api/execute":
            data, error = _read_json(self)
            if error:
                _json_response(self, 400, {"error": error})
                return
            user_text = str(data.get("user_text", "")).strip()
            origin_text = str(data.get("origin_text", "")).strip()
            origin_coords = _origin_coords_from_payload(data)
            plan_id = str(data.get("plan_id", "")).strip()
            if not user_text:
                _json_response(self, 400, {"error": "user_text is required"})
                return
            try:
                plan_result = data.get("plan_result") if isinstance(data.get("plan_result"), dict) else None
                result = plan_result or plan_day(user_text, origin_text=origin_text, origin_coords=origin_coords)
                plan = _find_plan(result, plan_id)
                execution = execute_plan(plan, result["goal"])
            except Exception as exc:
                _json_response(self, 500, {"error": str(exc)})
                return
            _json_response(
                self,
                200,
                {
                    "status": "success",
                    "selected_plan_id": plan.get("id"),
                    "selected_plan": plan,
                    "execution": execution,
                },
            )
            return

        if path == "/api/tts":
            data, error = _read_json(self)
            if error:
                _json_response(self, 400, {"error": error})
                return
            text = str(data.get("text", "")).strip()
            language = str(data.get("language", "mandarin")).strip()
            if not text:
                _json_response(self, 400, {"error": "text is required"})
                return
            try:
                audio = synthesize_speech(text, language=language, filename_prefix="route_guide")
            except Exception as exc:
                _json_response(self, 500, {"error": str(exc)})
                return
            _json_response(self, 200, {"status": "success", "audio": audio})
            return

        _json_response(self, 404, {"error": "unknown api endpoint"})


def run(host: str = HOST, port: int = PORT) -> None:
    server = ThreadingHTTPServer((host, port), MacauAgentHandler)
    print(f"Macau local agent user UI: http://{host}:{port}/")
    server.serve_forever()


if __name__ == "__main__":
    run()
