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


def _clean_raw_row(row: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in row.items():
        if value != value:
            cleaned[str(key)] = ""
        else:
            cleaned[str(key)] = value
    return cleaned


def _score_yes_partial(value: Any, unknown: int = 55) -> int:
    text = str(value).strip().lower()
    if text in {"yes", "true", "1", "是", "有", "good", "友好"}:
        return 95
    if text in {"partial", "partly", "部分", "一般", "medium", "low_medium"}:
        return 70
    if text in {"limited", "少量", "有限", "medium_high"}:
        return 55
    if text in {"no", "false", "0", "无", "否", "high"}:
        return 35
    return unknown


def _score_good_level(value: Any, unknown: int = 55) -> int:
    text = str(value).strip().lower()
    mapping = {
        "excellent": 98,
        "very_good": 95,
        "good": 90,
        "yes": 90,
        "inside_or_nearby": 90,
        "low": 90,
        "low_medium": 82,
        "partial": 72,
        "medium": 68,
        "medium_high": 50,
        "limited": 50,
        "high": 35,
        "no": 35,
        "none": 35,
        "无": 35,
        "官方未说明": unknown,
        "unknown": unknown,
        "": unknown,
    }
    return mapping.get(text, unknown)


def _score_inverse_risk(value: Any, unknown: int = 60) -> int:
    text = str(value).strip().lower()
    mapping = {
        "none": 96,
        "no": 96,
        "无": 96,
        "low": 92,
        "low_medium": 82,
        "medium": 68,
        "partial": 65,
        "medium_high": 50,
        "high": 32,
        "yes": 40,
        "slope_or_stone_steps": 35,
        "uneven_stone": 45,
        "flat": 92,
        "smooth": 92,
        "official_unknown": unknown,
        "官方未说明": unknown,
        "unknown": unknown,
        "": unknown,
    }
    return mapping.get(text, unknown)


def _score_walking_distance(value: Any) -> int:
    distance = _to_float(value)
    if distance is None:
        return 60
    if distance <= 180:
        return 96
    if distance <= 300:
        return 88
    if distance <= 450:
        return 76
    if distance <= 650:
        return 58
    if distance <= 900:
        return 42
    return 28


def _score_visit_duration(value: Any) -> int:
    duration = _to_float(value)
    if duration is None:
        return 65
    if duration <= 30:
        return 92
    if duration <= 50:
        return 84
    if duration <= 75:
        return 68
    if duration <= 100:
        return 52
    return 38


def _score_stairs(access_row: Dict[str, Any]) -> int:
    stairs = _to_float(_col(access_row, "stairs_count", 0)) or 0
    steep_score = _score_inverse_risk(_col(access_row, "steep_slopes", ""), 65)
    stair_score = max(20, 100 - stairs * 2.2)
    if stairs <= 2:
        stair_score = 95
    elif stairs <= 8:
        stair_score = 82
    elif stairs <= 20:
        stair_score = 62
    return _clamp((stair_score * 0.65) + (steep_score * 0.35))


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, round(value)))


def _score_transport_simplicity(transport_row: Dict[str, Any]) -> int:
    if not transport_row:
        return 60
    text = " ".join(str(transport_row.get(key, "")) for key in [
        "transport_type", "line_name", "low_floor_wheelchair_seat_available", "boarding_point", "dropoff_point", "walking_route"
    ])
    score = 70
    if "轻轨" in text or "的士" in text:
        score += 8
    if "升降机" in text or "低地板" in text or "轮椅" in text:
        score += 8
    if len(str(transport_row.get("line_name", ""))) > 80:
        score -= 5
    if any(word in text for word in ["陡", "斜路", "石级", "石阶", "楼梯", "小巷"]):
        score -= 18
    if any(word in text for word in ["避免", "行动不便者建议改乘的士"]):
        score -= 5
    return _clamp(score, 30, 95)


def _build_score_features(row: Dict[str, Any], access_row: Dict[str, Any], transport_row: Dict[str, Any], reason_row: Dict[str, Any]) -> Dict[str, int]:
    category = str(_col(reason_row, "scenic_category_zh", ""))
    name = str(_col(row, "name_zh", ""))
    senior_reason = str(_col(reason_row, "senior_reason_zh", ""))
    senior_tip = str(_col(access_row, "senior_tips_zh", ""))
    combined_text = name + category + senior_reason + senior_tip

    wheelchair = _score_yes_partial(_col(access_row, "wheelchair_friendly", ""), 58)
    elevator = _score_yes_partial(_col(access_row, "has_elevator", ""), 55)
    entrance = _score_yes_partial(_col(access_row, "accessible_entrance", ""), 58)
    ramp = _score_yes_partial(_col(access_row, "ramp_available", ""), 55)
    handrails = _score_yes_partial(_col(access_row, "handrails_available", ""), 55)
    accessibility_score = _clamp(wheelchair * 0.30 + elevator * 0.18 + entrance * 0.20 + ramp * 0.17 + handrails * 0.15)

    walking_comfort = _score_walking_distance(_col(access_row, "estimated_walking_distance_m", ""))
    visit_comfort = _score_visit_duration(_col(access_row, "estimated_visit_duration_min", ""))
    stairs_comfort = _score_stairs(access_row)
    rest_support = _clamp(_score_good_level(_col(access_row, "rest_areas", ""), 55) * 0.70 + _score_good_level(_col(access_row, "shaded_rest_areas", ""), 55) * 0.30)
    toilet_support = _clamp(_score_yes_partial(_col(access_row, "accessible_toilet", ""), 55) * 0.60 + _score_good_level(_col(access_row, "toilet_distance_level", ""), 55) * 0.40)
    weather_comfort = _clamp(_score_inverse_risk(_col(access_row, "sun_or_rain_exposure", ""), 60) * 0.45 + _score_good_level(_col(access_row, "air_conditioned_or_indoor_rest", ""), 55) * 0.35 + _score_good_level(_col(access_row, "shaded_rest_areas", ""), 55) * 0.20)
    crowd_comfort = _score_inverse_risk(_col(access_row, "crowd_level", ""), 60)
    ground_safety = _clamp(_score_inverse_risk(_col(access_row, "ground_surface", ""), 60) * 0.55 + _score_inverse_risk(_col(access_row, "trip_hazards", ""), 60) * 0.35 + handrails * 0.10)
    standing_comfort = _score_inverse_risk(_col(access_row, "standing_time_risk", ""), 60)
    transport_simplicity = _score_transport_simplicity(transport_row)

    senior_interest_match = 62
    if any(word in category for word in ["博物馆", "展览", "文化", "历史", "世界遗产", "教堂", "庙", "图书馆"]):
        senior_interest_match += 15
    if any(word in category + name for word in ["公园", "花园", "前地", "休憩"]):
        senior_interest_match += 12
    if any(word in senior_reason + senior_tip for word in ["慢慢", "短暂停留", "节奏可控", "休息", "长者"]):
        senior_interest_match += 8
    senior_interest_match = _clamp(senior_interest_match, 45, 95)

    low_fatigue = _clamp(walking_comfort * 0.35 + stairs_comfort * 0.25 + standing_comfort * 0.20 + visit_comfort * 0.20)
    is_indoor = any(word in combined_text for word in ["博物馆", "展览", "图书馆", "文化中心", "室内", "半室内", "空调"])

    return {
        "accessibility_score": accessibility_score,
        "walking_comfort": walking_comfort,
        "stairs_comfort": stairs_comfort,
        "rest_support": rest_support,
        "toilet_support": toilet_support,
        "weather_comfort": weather_comfort,
        "crowd_comfort": crowd_comfort,
        "ground_safety": ground_safety,
        "standing_comfort": standing_comfort,
        "transport_simplicity": transport_simplicity,
        "senior_interest_match": senior_interest_match,
        # Backward-compatible aliases for current scorer/planner. Later scorer.py can consume the new names directly.
        "senior_friendly": _clamp(accessibility_score * 0.45 + low_fatigue * 0.30 + senior_interest_match * 0.25),
        "low_fatigue": low_fatigue,
        "rest_area": rest_support,
        "toilet_access": toilet_support,
        "avoid_stairs": stairs_comfort,
        "indoor": 90 if is_indoor else _clamp(weather_comfort * 0.75),
    }


def _load_excel_attractions() -> List[Dict[str, Any]]:
    import pandas as pd

    attractions_df = pd.read_excel(_excel_path("macau_attractions_master.xlsx")).fillna("")
    reasons_file = _excel_path("澳门经典ID对应表格_适老化理由修订.xlsx")
    accessibility_file = _excel_path("attraction_accessibility_filled.xlsx")
    transport_file = _excel_path("attraction_transport_updated.xlsx")
    reasons_df = pd.read_excel(reasons_file).fillna("") if reasons_file.exists() else pd.DataFrame()
    accessibility_df = pd.read_excel(accessibility_file).fillna("") if accessibility_file.exists() else pd.DataFrame()
    transport_df = pd.read_excel(transport_file).fillna("") if transport_file.exists() else pd.DataFrame()

    reasons: Dict[int, Dict[str, Any]] = {}
    for raw_row in reasons_df.to_dict(orient="records"):
        row = _clean_raw_row(raw_row)
        item_id = int(_col(row, "id", 0) or 0)
        reasons[item_id] = row

    accessibility: Dict[int, Dict[str, Any]] = {}
    for raw_row in accessibility_df.to_dict(orient="records"):
        row = _clean_raw_row(raw_row)
        item_id = int(_col(row, "attraction_id", 0) or 0)
        accessibility[item_id] = row

    transport: Dict[int, Dict[str, Any]] = {}
    for raw_row in transport_df.to_dict(orient="records"):
        row = _clean_raw_row(raw_row)
        item_id = int(_col(row, "attraction_id", 0) or 0)
        transport[item_id] = row

    records: List[Dict[str, Any]] = []
    seen_names = set()
    for raw_row in attractions_df.to_dict(orient="records"):
        row = _clean_raw_row(raw_row)
        item_id = int(_col(row, "id", 0) or 0)
        name = str(_col(row, "name_zh", "")).strip()
        if not item_id or not name or name in seen_names:
            continue
        seen_names.add(name)
        reason_row = reasons.get(item_id, {})
        access_row = accessibility.get(item_id, {})
        transport_row = transport.get(item_id, {})
        category = str(_col(reason_row, "scenic_category_zh", "其他景点"))
        senior_reason = str(_col(reason_row, "senior_reason_zh", "")).strip()
        senior_tip = str(_col(access_row, "senior_tips_zh", senior_reason or "官方景点数据，建议现场核实无障碍入口、厕所和休息座椅。"))
        region = str(_col(row, "region", "澳门")) or str(_col(reason_row, "region", "澳门"))
        route_cluster = str(_col(row, "route_cluster", "")).strip()
        latitude = _to_float(_col(row, "latitude", ""))
        longitude = _to_float(_col(row, "longitude", ""))
        location = f"{longitude},{latitude}" if latitude is not None and longitude is not None else ""
        score_features = _build_score_features(row, access_row, transport_row, reason_row)

        tags = ["real_excel", "official_source", "senior_friendly", "low_fatigue"]
        if score_features.get("indoor", 0) >= 80:
            tags.append("indoor")
        if score_features.get("rest_support", 0) >= 75:
            tags.append("rest_area")
        if any(word in category + name for word in ["世界遗产", "教堂", "历史", "庙", "大楼", "博物馆"]):
            tags.append("historic")
        if any(word in name + senior_reason for word in ["拍照", "前地", "渔人码头", "艺术", "文化"]):
            tags.append("photo_friendly")

        accessibility_raw = _clean_raw_row(access_row)
        transport_raw = _clean_raw_row(transport_row)
        category_info = {
            "scenic_category_zh": category,
            "senior_reason_zh": senior_reason,
            "reason_region": str(_col(reason_row, "region", "")),
        }
        records.append({
            "id": f"attraction_{item_id}",
            "source_id": item_id,
            "name": name,
            "name_en": str(_col(row, "name_en", "")),
            "region": region,
            "route_cluster": route_cluster,
            "latitude": latitude,
            "longitude": longitude,
            "location": location,
            "address": str(_col(row, "address", "")),
            "opening_hours": str(_col(row, "opening_hours", "")),
            "ticket_info": str(_col(row, "ticket_info", "")),
            "category": category,
            "tags": sorted(set(tags)),
            "duration_min": int(_to_float(_col(access_row, "estimated_visit_duration_min", "")) or 45),
            "features": [category, "真实Excel景点", senior_reason or senior_tip],
            "score_features": score_features,
            "accessibility_raw": accessibility_raw,
            "transport_raw": transport_raw,
            "category_info": category_info,
            "accessibility": accessibility_raw,
            "reason": senior_reason or senior_tip,
            "senior_tips_zh": senior_tip,
            "best_access_route_zh": str(_col(access_row, "best_access_route_zh", "")),
            "avoid_route_zh": str(_col(access_row, "avoid_route_zh", "")),
        })
    return records


def _load_excel_accessibility() -> Dict[str, Dict[str, Any]]:
    import pandas as pd

    accessibility_file = _excel_path("attraction_accessibility_filled.xlsx")
    if not accessibility_file.exists():
        return {}
    df = pd.read_excel(accessibility_file).fillna("")
    result: Dict[str, Dict[str, Any]] = {}
    for raw_row in df.to_dict(orient="records"):
        row = _clean_raw_row(raw_row)
        item_id = int(_col(row, "attraction_id", 0) or 0)
        if not item_id:
            continue
        normalized = dict(row)
        stairs_raw = _col(row, "stairs_count", 0)
        try:
            normalized["stairs_count"] = max(0, int(float(stairs_raw)))
        except (TypeError, ValueError):
            normalized["stairs_count"] = 0
        steep_text = str(_col(row, "steep_slopes", "low")).strip().lower()
        normalized["steep_slopes"] = steep_text not in {"", "低", "无", "官方未说明", "unknown", "no", "none", "low"}
        wheelchair_text = str(_col(row, "wheelchair_friendly", "")).strip().lower()
        normalized["wheelchair_friendly"] = wheelchair_text in {"true", "1", "yes", "是", "有", "友好"}
        result[f"attraction_{item_id}"] = normalized
    return result


try:
    ATTRACTIONS: List[Dict[str, Any]] = _load_excel_attractions()
    ACCESSIBILITY: Dict[str, Dict[str, Any]] = _load_excel_accessibility()
except Exception:
    # 仅当 Excel/依赖不可用时保留极小兜底；正式路线不再依赖虚构地点。
    ATTRACTIONS = [
        {"id": "attraction_501", "source_id": 501, "name": "澳门仁慈堂大楼", "region": "澳门半岛", "tags": ["real_excel", "senior_friendly", "historic"], "duration_min": 45, "features": ["澳门世界遗产", "真实景点"], "score_features": {}},
        {"id": "attraction_505", "source_id": 505, "name": "澳门中央图书馆", "region": "澳门半岛", "tags": ["real_excel", "senior_friendly", "indoor"], "duration_min": 45, "features": ["图书馆", "真实景点"], "score_features": {}},
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


def search_attractions(goal: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    preferred = ["senior_friendly", "low_fatigue", "indoor", "rest_area"]

    def score(item: Dict[str, Any]) -> int:
        tags = set(item.get("tags", []))
        features = item.get("score_features") or {}
        tag_score = sum(1 for tag in preferred if tag in tags) * 8
        feature_score = (
            features.get("senior_friendly", 60) * 0.30
            + features.get("walking_comfort", 60) * 0.20
            + features.get("stairs_comfort", 60) * 0.15
            + features.get("rest_support", 60) * 0.12
            + features.get("toilet_support", 60) * 0.10
            + features.get("transport_simplicity", 60) * 0.08
            + features.get("senior_interest_match", 60) * 0.05
        )
        return round(feature_score + tag_score)

    ranked = sorted(ATTRACTIONS, key=score, reverse=True)
    selected = [item for item in ranked if score(item) > 0] or ATTRACTIONS
    if limit is not None:
        selected = selected[:limit]
    return [enrich_poi_for_recommendation(item) for item in selected]


def get_accessibility(attraction_id: str) -> Dict[str, Any]:
    return ACCESSIBILITY.get(attraction_id, {"stairs_count": 0, "steep_slopes": False, "rest_areas": "未知", "senior_tips_zh": "暂无特殊风险。", "accessible_toilet": "官方未说明", "wheelchair_friendly": False})


def enrich_poi_for_recommendation(item: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(item)
    accessibility = get_accessibility(str(item.get("id", "")))
    features = dict(enriched.get("score_features") or {})
    enriched.setdefault("accessibility_raw", dict(accessibility))
    enriched.setdefault("transport_raw", {})
    enriched.setdefault("category_info", {"scenic_category_zh": enriched.get("category", ""), "senior_reason_zh": enriched.get("reason", "")})
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
    attractions = search_attractions(goal)
    return {
        "senior_activities": attractions[:5],
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
