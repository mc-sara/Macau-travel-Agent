import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen

from agent.mock_data import load_merchants


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "是", "有", "友好"}


def _to_float(value: Any) -> Optional[float]:
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _excel_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "excel" / filename


def _col(row: Dict[str, Any], prefix: str, default: Any = "") -> Any:
    for key, value in row.items():
        if str(key).startswith(prefix):
            return value if value == value else default
    return default


def _load_excel_attractions() -> List[Dict[str, Any]]:
    import pandas as pd

    attractions_df = pd.read_excel(_excel_path("macau_attractions_master.xlsx")).fillna("")
    coord_by_id: Dict[int, Dict[str, Any]] = {}
    coord_by_name: Dict[str, Dict[str, Any]] = {}
    reasons_file = _excel_path("澳门经典ID对应表格_适老化理由修订.xlsx")
    accessibility_file = _excel_path("attraction_accessibility_filled.xlsx")
    reasons_df = pd.read_excel(reasons_file).fillna("") if reasons_file.exists() else pd.DataFrame()
    accessibility_df = pd.read_excel(accessibility_file).fillna("") if accessibility_file.exists() else pd.DataFrame()

    reasons: Dict[int, Dict[str, Any]] = {}
    for row in reasons_df.to_dict(orient="records"):
        item_id = int(_col(row, "id", 0) or 0)
        reasons[item_id] = row

    accessibility: Dict[int, Dict[str, Any]] = {}
    for row in accessibility_df.to_dict(orient="records"):
        item_id = int(_col(row, "attraction_id", 0) or 0)
        accessibility[item_id] = row

    records: List[Dict[str, Any]] = []
    seen_names = set()
    for row in attractions_df.to_dict(orient="records"):
        item_id = int(_col(row, "id", 0) or 0)
        name = str(_col(row, "name_zh", "")).strip()
        if not item_id or not name or name in seen_names:
            continue
        seen_names.add(name)
        reason_row = reasons.get(item_id, {})
        access_row = accessibility.get(item_id, {})
        category = str(_col(reason_row, "scenic_category_zh", "其他景点"))
        senior_reason = str(_col(reason_row, "适老化推荐理由", "")).strip()
        senior_tip = str(_col(access_row, "senior_tips_zh", senior_reason or "官方景点数据，建议现场核实无障碍入口、厕所和休息座椅。"))
        region = str(_col(row, "region", "澳门")) or str(_col(reason_row, "region", "澳门"))
        latitude = _to_float(_col(row, "latitude", ""))
        longitude = _to_float(_col(row, "longitude", ""))
        location = f"{longitude},{latitude}" if latitude is not None and longitude is not None else ""
        is_indoor = any(word in category + senior_reason + senior_tip for word in ["博物馆", "展览", "图书馆", "文化中心", "室内", "半室内"])
        is_rest_area = any(word in name + category for word in ["公园", "花园", "前地", "图书馆", "文化中心"])
        is_senior_friendly = _to_bool(_col(access_row, "wheelchair_friendly", False)) or is_indoor or is_rest_area
        tags = ["real_excel", "official_source"]
        if is_senior_friendly:
            tags.extend(["senior_friendly", "low_fatigue"])
        if is_indoor:
            tags.append("indoor")
        if is_rest_area:
            tags.append("rest_area")
        if any(word in category + name for word in ["世界遗产", "教堂", "历史", "庙", "大楼"]):
            tags.append("historic")
        if any(word in name + senior_reason for word in ["拍照", "前地", "渔人码头", "艺术", "文化"]):
            tags.append("photo_friendly")
        accessibility_features = {
            "senior_friendly": 90 if is_senior_friendly else 60,
            "low_fatigue": 88 if is_senior_friendly else 65,
            "rest_area": 90 if is_rest_area else 55,
            "toilet_access": 80 if "厕所" in senior_tip or "洗手间" in senior_tip or "卫生间" in senior_tip else 60,
            "indoor": 90 if is_indoor else 55,
            "avoid_stairs": 90 if "台阶" not in senior_tip and "楼梯" not in senior_tip else 55,
        }
        records.append({
            "id": f"attraction_{item_id}",
            "source_id": item_id,
            "name": name,
            "region": region,
            "latitude": latitude,
            "longitude": longitude,
            "location": location,
            "address": str(_col(row, "address", "")),
            "opening_hours": str(_col(row, "opening_hours", "")),
            "ticket_info": str(_col(row, "ticket_info", "")),
            "category": category,
            "tags": sorted(set(tags)),
            "duration_min": 45,
            "features": [category, "真实Excel景点", senior_reason or senior_tip],
            "score_features": accessibility_features,
            "reason": senior_reason or senior_tip,
        })
    return records


def _load_excel_accessibility() -> Dict[str, Dict[str, Any]]:
    import pandas as pd

    accessibility_file = _excel_path("attraction_accessibility_filled.xlsx")
    if not accessibility_file.exists():
        return {}
    df = pd.read_excel(accessibility_file).fillna("")
    result: Dict[str, Dict[str, Any]] = {}
    for row in df.to_dict(orient="records"):
        item_id = int(_col(row, "attraction_id", 0) or 0)
        if not item_id:
            continue
        stairs_raw = _col(row, "stairs_count", 0)
        try:
            stairs_count = max(0, int(float(stairs_raw)))
        except (TypeError, ValueError):
            stairs_count = 0
        steep_text = str(_col(row, "steep_slopes", "low")).strip().lower()
        steep = steep_text not in {"", "低", "无", "官方未说明", "unknown", "no", "none", "low"}
        wheelchair_text = str(_col(row, "wheelchair_friendly", "")).strip().lower()
        wheelchair_friendly = wheelchair_text in {"true", "1", "yes", "是", "有", "友好"}
        result[f"attraction_{item_id}"] = {
            "stairs_count": stairs_count,
            "steep_slopes": steep,
            "rest_areas": str(_col(row, "rest_areas", "unknown")),
            "senior_tips_zh": str(_col(row, "senior_tips_zh", "官方景点数据，建议现场核实无障碍入口、厕所和休息座椅。")),
            "accessible_toilet": str(_col(row, "accessible_toilet", "unknown")),
            "wheelchair_friendly": wheelchair_friendly,
        }
    return result


try:
    ATTRACTIONS: List[Dict[str, Any]] = _load_excel_attractions()
    ACCESSIBILITY: Dict[str, Dict[str, Any]] = _load_excel_accessibility()
except Exception:
    # 仅当 Excel/依赖不可用时保留极小兜底；正式路线不再依赖虚构地点。
    ATTRACTIONS = [
        {"id": "attraction_501", "source_id": 501, "name": "澳门仁慈堂大楼", "region": "澳门半岛", "tags": ["real_excel", "senior_friendly", "historic"], "duration_min": 45, "features": ["澳门世界遗产", "真实景点"]},
        {"id": "attraction_505", "source_id": 505, "name": "澳门中央图书馆", "region": "澳门半岛", "tags": ["real_excel", "senior_friendly", "indoor"], "duration_min": 45, "features": ["图书馆", "真实景点"]},
    ]
    ACCESSIBILITY = {}


ROUTES: Dict[tuple, Dict[str, Any]] = {}
AMAP_GEOCODE_CACHE: Dict[str, Dict[str, Any]] = {}
AMAP_ROUTE_CACHE: Dict[tuple, Dict[str, Any]] = {}
AMAP_LAST_REQUEST_AT = 0.0
ATTRACTION_LOCATION_INDEX: Dict[str, Dict[str, Any]] = {
    str(item.get("name", "")).strip(): {
        "name": item.get("name"),
        "location": item.get("location"),
        "formatted_address": item.get("address") or item.get("name"),
        "source": "excel_coordinates",
    }
    for item in ATTRACTIONS
    if item.get("location") and item.get("name")
}


def search_attractions(goal: Dict[str, Any]) -> List[Dict[str, Any]]:
    scenario = goal.get("scenario")
    if scenario == "senior":
        preferred = ["senior_friendly", "low_fatigue", "indoor", "rest_area"]
    elif scenario == "family":
        preferred = ["low_fatigue", "rest_area", "indoor"]
    elif scenario == "friends":
        preferred = ["photo_friendly", "historic", "indoor"]
    elif scenario == "couple":
        preferred = ["photo_friendly", "indoor", "rest_area"]
    else:
        preferred = ["low_fatigue", "photo_friendly"]

    def score(item: Dict[str, Any]) -> int:
        tags = set(item.get("tags", []))
        return sum(1 for tag in preferred if tag in tags)

    ranked = sorted(ATTRACTIONS, key=score, reverse=True)
    selected = [item for item in ranked if score(item) > 0][:15] or ATTRACTIONS[:15]
    return [enrich_poi_for_recommendation(item) for item in selected]


def get_accessibility(attraction_id: str) -> Dict[str, Any]:
    return ACCESSIBILITY.get(attraction_id, {"stairs_count": 0, "steep_slopes": False, "rest_areas": "未知", "senior_tips_zh": "暂无特殊风险。", "accessible_toilet": "官方未说明", "wheelchair_friendly": False})


def enrich_poi_for_recommendation(item: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(item)
    accessibility = get_accessibility(str(item.get("id", "")))
    features = dict(enriched.get("score_features") or {})
    if accessibility.get("wheelchair_friendly"):
        features["senior_friendly"] = max(features.get("senior_friendly", 0), 95)
        features["low_fatigue"] = max(features.get("low_fatigue", 0), 90)
    stairs_count = int(accessibility.get("stairs_count") or 0)
    if stairs_count > 0 or accessibility.get("steep_slopes"):
        features["avoid_stairs"] = min(features.get("avoid_stairs", 70), 45)
        features["low_fatigue"] = min(features.get("low_fatigue", 80), 65)
    if str(accessibility.get("rest_areas", "")) not in {"", "无", "官方未说明"}:
        features["rest_area"] = max(features.get("rest_area", 0), 90)
    if str(accessibility.get("accessible_toilet", "")) not in {"", "无", "官方未说明"}:
        features["toilet_access"] = max(features.get("toilet_access", 0), 85)
    enriched["score_features"] = features
    enriched["accessibility"] = accessibility
    enriched["reason"] = enriched.get("reason") or accessibility.get("senior_tips_zh", "")
    return enriched


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_env_file(path: Optional[Path] = None) -> Dict[str, str]:
    env_path = path or _project_root() / ".env"
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


def load_amap_config() -> Dict[str, str]:
    file_values = _parse_env_file()
    return {
        "key": os.environ.get("AMAP_WEBSERVICE_KEY") or file_values.get("AMAP_WEBSERVICE_KEY", ""),
        "city": os.environ.get("AMAP_CITY") or file_values.get("AMAP_CITY", "澳门"),
        "route_provider": os.environ.get("AMAP_ROUTE_PROVIDER") or file_values.get("AMAP_ROUTE_PROVIDER", "api"),
    }


def _amap_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    global AMAP_LAST_REQUEST_AT
    config = load_amap_config()
    if not config["key"]:
        raise RuntimeError("AMAP_WEBSERVICE_KEY is missing")
    min_interval = float(os.environ.get("AMAP_MIN_INTERVAL_SECONDS", "1.0"))
    elapsed = time.monotonic() - AMAP_LAST_REQUEST_AT
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    query = urlencode({**params, "key": config["key"], "output": "JSON"})
    with urlopen(f"https://restapi.amap.com{path}?{query}", timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))
    AMAP_LAST_REQUEST_AT = time.monotonic()
    return data


def _geocode_from_excel(place: str) -> Optional[Dict[str, Any]]:
    key = str(place).strip()
    if key in ATTRACTION_LOCATION_INDEX:
        return dict(ATTRACTION_LOCATION_INDEX[key])
    return None


def amap_geocode(place: str) -> Dict[str, Any]:
    cache_key = str(place).strip()
    if cache_key in AMAP_GEOCODE_CACHE:
        return dict(AMAP_GEOCODE_CACHE[cache_key])
    excel_geo = _geocode_from_excel(place)
    if excel_geo:
        AMAP_GEOCODE_CACHE[cache_key] = dict(excel_geo)
        return excel_geo
    config = load_amap_config()
    query = place if "澳门" in place else f"澳门{place}"
    data = _amap_get("/v3/geocode/geo", {"address": query, "city": config["city"]})
    if data.get("status") != "1" or not data.get("geocodes"):
        raise RuntimeError(f"高德地理编码失败: {data.get('info') or data.get('infocode')}")
    first = data["geocodes"][0]
    location = first.get("location", "")
    try:
        lng, lat = [float(item) for item in location.split(",", 1)]
    except ValueError as exc:
        raise RuntimeError("高德地理编码失败: invalid location") from exc
    # 项目里有部分演示商户名是虚构/泛化名称。高德可能会匹配到内地同名 POI，
    # 这里限制澳门大致经纬度范围，避免把澳门路线错误算成跨城长距离。
    if not (113.3 <= lng <= 113.8 and 22.0 <= lat <= 22.4):
        raise RuntimeError(f"高德地理编码失败: location outside Macau ({location})")
    result = {
        "name": place,
        "location": location,
        "formatted_address": first.get("formatted_address", query),
    }
    AMAP_GEOCODE_CACHE[cache_key] = dict(result)
    return result


def _amap_direction_path(mode: str) -> str:
    if mode in {"walking", "walk"}:
        return "/v3/direction/walking"
    if mode in {"bus", "transit", "transfer"}:
        return "/v3/direction/transit/integrated"
    return "/v3/direction/driving"


def _normalize_amap_route(origin: str, destination: str, mode: str, path: Dict[str, Any], provider: str = "real_amap_api") -> Dict[str, Any]:
    distance_m = float(path.get("distance") or 0)
    duration_s = float(path.get("duration") or 0)
    duration_min = max(1, round(duration_s / 60)) if duration_s else 0
    route_distance_km = round(distance_m / 1000, 1) if distance_m else 0.0
    walking_distance_m = int(distance_m) if mode in {"walking", "walk"} else min(180, max(80, int(distance_m * 0.04))) if distance_m else 120
    display_mode = "walking" if mode in {"walking", "walk"} else "taxi"
    return {
        "origin": origin,
        "destination": destination,
        "mode": display_mode,
        "route_distance_km": route_distance_km,
        "duration_min": duration_min,
        "walking_distance_m": walking_distance_m,
        "transfer_count": 0,
        "traffic_level": provider,
        "route_summary": f"高德真实路线：约{duration_min}分钟，{route_distance_km}公里",
        "map_provider": provider,
    }


def call_amap_route(origin: str, destination: str, mode: str = "taxi") -> Dict[str, Any]:
    cache_key = (str(origin).strip(), str(destination).strip(), mode)
    if cache_key in AMAP_ROUTE_CACHE:
        return dict(AMAP_ROUTE_CACHE[cache_key])
    origin_geo = amap_geocode(origin)
    destination_geo = amap_geocode(destination)
    path = _amap_direction_path(mode)
    params = {"origin": origin_geo["location"], "destination": destination_geo["location"]}
    if "transit" in path:
        params["city"] = load_amap_config()["city"]
    data = _amap_get(path, params)
    if data.get("status") != "1":
        raise RuntimeError(f"高德路线规划失败: {data.get('info') or data.get('infocode')}")
    route = data.get("route") or {}
    paths = route.get("paths") or []
    if not paths:
        raise RuntimeError("高德路线规划失败: no route path")
    result = _normalize_amap_route(origin, destination, mode, paths[0])
    AMAP_ROUTE_CACHE[cache_key] = dict(result)
    return result


def _fallback_route(origin: str, destination: str, mode: str = "taxi", reason: str = "") -> Dict[str, Any]:
    cache_key = (str(origin).strip(), str(destination).strip(), mode)
    if cache_key in AMAP_ROUTE_CACHE:
        return dict(AMAP_ROUTE_CACHE[cache_key])
    # Mock 仅作为真实高德/Skill 失败时的兜底，后续接 QwenPaw Skill 后可删除。
    route = ROUTES.get((origin, destination))
    if route is None:
        route = {"route_distance_km": 2.5, "duration_min": 12, "walking_distance_m": 180, "transfer_count": 0, "traffic_level": "mock_fallback", "route_summary": f"{mode} 兜底路线：距离和时间适中"}
    result = {"origin": origin, "destination": destination, "mode": mode, **route, "map_provider": "mock_fallback"}
    if reason:
        result["fallback_reason"] = reason
    AMAP_ROUTE_CACHE[cache_key] = dict(result)
    return result


def mock_map_route_api(origin: str, destination: str, mode: str = "taxi") -> Dict[str, Any]:
    cache_key = (str(origin).strip(), str(destination).strip(), mode)
    if cache_key in AMAP_ROUTE_CACHE:
        return dict(AMAP_ROUTE_CACHE[cache_key])
    provider = load_amap_config().get("route_provider", "api")
    if provider in {"api", "amap", "real"}:
        try:
            return call_amap_route(origin, destination, mode)
        except Exception as exc:
            return _fallback_route(origin, destination, mode, reason=str(exc))
    # TODO: provider == "skill" 时在这里调用 QwenPaw/OpenClaw 高德 Skill，再复用 _normalize_amap_route。
    return _fallback_route(origin, destination, mode, reason=f"unsupported provider: {provider}")


def search_local_merchants(goal: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    # 本阶段不再把虚构餐厅/奶茶店作为主要数据源；先用 Excel 真实景点作为可执行停留点。
    # 后续如接入真实餐饮/POI API，可在这里补 restaurants / drink_shops。
    scenario = goal.get("scenario")
    attractions = search_attractions(goal)
    if scenario == "senior":
        return {
            "senior_activities": attractions[:5],
            "family_activities": [],
            "friend_activities": [],
            "couple_activities": [],
            "restaurants": [],
            "drink_shops": [],
            "gift_shops": [],
        }
    return {
        "senior_activities": attractions[:5] if scenario == "senior" else [],
        "family_activities": attractions[:5] if scenario == "family" else [],
        "friend_activities": attractions[:5] if scenario == "friends" else [],
        "couple_activities": attractions[:5] if scenario == "couple" else [],
        "restaurants": [],
        "drink_shops": [],
        "gift_shops": [],
    }


def _excel_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for item in ATTRACTIONS:
        items.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "available_slots": ["14:00", "15:00", "16:20", "17:40"],
            "tickets_left": 999,
            "queue_minutes": 0,
            "features": item.get("features", []),
            "source": "excel_attractions",
        })
    return items


def _all_items() -> List[Dict[str, Any]]:
    merchants = load_merchants()
    items: List[Dict[str, Any]] = _excel_items()
    for category_items in merchants.values():
        items.extend(category_items)
    return items


def check_availability(item_id: str, time: str, people_count: int) -> Dict[str, Any]:
    for item in _all_items():
        if item.get("id") == item_id:
            available = time in item.get("available_slots", []) and item.get("tickets_left", people_count) >= people_count
            return {
                "item_id": item_id,
                "name": item.get("name"),
                "available": available,
                "time": time,
                "people_count": people_count,
                "queue_minutes": item.get("queue_minutes", 0),
                "tickets_left": item.get("tickets_left"),
                "message": "可预约/有位" if available else "当前时间不可用",
            }
    return {"item_id": item_id, "available": False, "time": time, "people_count": people_count, "queue_minutes": None, "message": "未找到该项目"}
