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


def test_api_plan_returns_senior_plan():
    server, base_url = _start_test_server()
    try:
        status, payload = _post_json(base_url + "/api/plan", {"user_text": "我想带爸妈下午轻松逛逛，不想爬楼梯，最好有地方坐，晚上吃点清淡的。"})
    finally:
        server.shutdown()
        server.server_close()

    assert status == 200
    result = payload["result"]
    assert result["goal"]["scenario"] == "senior"
    assert result["best_plan"]["id"] == "senior_main"
    assert "长者" in result["best_plan"]["title"] or "银龄" in result["best_plan"]["title"]
    assert "senior_friendly" in result["best_plan"]["tags"]
    assert "澳门悬疑密室体验馆" not in [step["name"] for step in result["best_plan"]["timeline"]]


def test_api_execute_can_run_selected_senior_alternative_plan():
    server, base_url = _start_test_server()
    try:
        _, plan_payload = _post_json(base_url + "/api/plan", {"user_text": "下午带爷爷奶奶在澳门走走，路不要太长，中途最好有厕所和座椅。"})
        result = plan_payload["result"]
        alternative_id = result["alternatives"][0]["id"]
        status, payload = _post_json(
            base_url + "/api/execute",
            {"user_text": "下午带爷爷奶奶在澳门走走，路不要太长，中途最好有厕所和座椅。", "plan_id": alternative_id, "plan_result": result},
        )
    finally:
        server.shutdown()
        server.server_close()

    assert status == 200
    assert payload["selected_plan_id"] == alternative_id
    assert payload["execution"]["status"] == "success"
    assert payload["execution"]["bookings"]
    assert payload["execution"]["final_message"]
