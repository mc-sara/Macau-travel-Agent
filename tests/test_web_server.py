import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from web_server import MacauAgentHandler


def _start_test_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), MacauAgentHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def _post_json(url, payload):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_api_plan_returns_clarification_and_escape_room_plan():
    server, base_url = _start_test_server()
    try:
        status, payload = _post_json(base_url + "/api/plan", {"user_text": "我们几个朋友出去玩，5个人，有男有女，想去密室。"})
    finally:
        server.shutdown()
        server.server_close()

    assert status == 200
    result = payload["result"]
    assert result["clarification_needed"] is True
    assert "请补充男女各有几个人？" in result["clarification_questions"]
    assert "澳门悬疑密室体验馆" in [step["name"] for step in result["best_plan"]["timeline"]]


def test_api_execute_can_run_selected_alternative_plan():
    server, base_url = _start_test_server()
    try:
        _, plan_payload = _post_json(base_url + "/api/plan", {"user_text": "今天下午2男3女想玩密室，顺便吃饭。"})
        result = plan_payload["result"]
        alternative_id = result["alternatives"][0]["id"]
        status, payload = _post_json(
            base_url + "/api/execute",
            {"user_text": "今天下午2男3女想玩密室，顺便吃饭。", "plan_id": alternative_id, "plan_result": result},
        )
    finally:
        server.shutdown()
        server.server_close()

    assert status == 200
    assert payload["selected_plan_id"] == alternative_id
    assert payload["execution"]["status"] == "success"
    assert payload["execution"]["bookings"]
    assert payload["execution"]["final_message"]
