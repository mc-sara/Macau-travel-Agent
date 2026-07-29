# 主 Agent 接入 Restaurant 数据库

本文面向主团队后端开发，说明如何把冻结 SQLite 接入现有主 Agent。以下示例均为只读
接口，不要求修改 `macau_senior_agent_submission.html`，也不自动改变现有规划器、
评分器或 HTTP API。

## 1. 接入文件和版本

数据库：

```text
restaurant/data/restaurant_recommendation_v1.0.0.db
```

发布版本：

```text
restaurant-static-v1.0.0
```

主 Agent 景点表：

```text
data/excel/macau_attractions_master.xlsx
```

在应用启动时先检查：

```sql
SELECT COUNT(*) FROM restaurants;                 -- 489
SELECT COUNT(*) FROM attraction_restaurants;      -- 6798
SELECT COUNT(DISTINCT attraction_id)
FROM attraction_restaurants;                      -- 89（ID 305 为成功 0 结果）
SELECT COUNT(*) FROM restaurant_static_features;  -- 3074
SELECT COUNT(*) FROM restaurant_review_flags;     -- 115
```

还应读取 `restaurant/data/manifest.json` 校验文件 SHA-256 和版本。数量或哈希不匹配时
拒绝加载，不要静默使用未知版本。

## 2. 连接键

```text
主 Agent 景点表.id
  └─ attraction_restaurants.attraction_id
       └─ restaurants.restaurant_id
            ├─ restaurant_contacts.restaurant_id
            ├─ restaurant_static_features.restaurant_id
            ├─ restaurant_feature_evidence.restaurant_id
            ├─ restaurant_review_flags.restaurant_id
            └─ 其他保留扩展表.restaurant_id
```

- 主 Agent 的 `id` 与数据库的 `attraction_id` 都按文本比较。
- `restaurant_id` 只保证在当前数据库版本内部稳定。
- 跨版本识别餐厅使用唯一 `amap_poi_id`。
- 不按 `restaurant_name` 自动合并。

## 3. Python 只读连接

```python
from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = (
    PROJECT_ROOT
    / "restaurant"
    / "data"
    / "restaurant_recommendation_v1.0.0.db"
)

def open_restaurant_db() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Restaurant DB not found: {DB_PATH}")
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        conn.close()
        raise RuntimeError("Restaurant DB integrity check failed")
    return conn
```

生产请求只读冻结数据库。更新时生成新的版本文件，完成验收后再切换配置；不要在原
文件上边读边写。

## 4. 按景点读取候选餐厅

基础 SQL：

```sql
SELECT
    ar.attraction_id,
    r.restaurant_id,
    r.amap_poi_id,
    r.restaurant_name,
    r.longitude,
    r.latitude,
    r.coordinate_system,
    r.address,
    r.telephone,
    r.type_raw,
    r.type_code,
    r.category_level_1,
    r.category_level_2,
    ar.straight_distance_m,
    ar.search_radius_m,
    ar.search_keyword,
    ar.collected_at
FROM attraction_restaurants AS ar
JOIN restaurants AS r
  ON r.restaurant_id = ar.restaurant_id
WHERE ar.attraction_id = :attraction_id
ORDER BY
    ar.straight_distance_m IS NULL,
    ar.straight_distance_m,
    r.restaurant_id
LIMIT :limit;
```

Python：

```python
def list_restaurants_near_attraction(
    conn: sqlite3.Connection,
    attraction_id: str,
    limit: int = 30,
) -> list[dict]:
    if not attraction_id:
        raise ValueError("attraction_id is required")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = conn.execute(SQL_NEARBY, {
        "attraction_id": str(attraction_id),
        "limit": limit,
    }).fetchall()
    return [dict(row) for row in rows]
```

`straight_distance_m` 只能显示为静态直线距离。不得据此声称“步行 X 分钟”或“路线
无障碍”。

景点 ID `305` 在既定 `餐厅/1500米` 条件内成功返回 0 条，函数应返回空数组并保留
“本条件无结果”的语义；不得报数据库错误，也不得借用其他景点候选补齐。

## 5. 批量读取标签

不要对每个候选逐条发 SQL。先得到候选 `restaurant_id`，再一次批量读取：

```sql
SELECT
    restaurant_id,
    feature_name,
    feature_label,
    confidence,
    feature_version,
    calculated_at
FROM restaurant_static_features
WHERE restaurant_id IN (
    SELECT ar.restaurant_id
    FROM attraction_restaurants AS ar
    WHERE ar.attraction_id = :attraction_id
)
ORDER BY restaurant_id, feature_name;
```

规则：

- 使用 `feature_label`；当前 `feature_value` 必须为 `NULL`。
- `confidence` 是证据可信度，不是推荐评分。
- 某维度缺失表示证据不足，不等于否定。
- 标签只是候选解释信息；当前第三阶段真实排序暂停。

## 6. 查证隔离

先读取未解决标记：

```sql
SELECT
    restaurant_id,
    review_scope,
    review_status,
    reason,
    source,
    affects_recommendation
FROM restaurant_review_flags
WHERE resolved_at IS NULL
  AND restaurant_id IN (
      SELECT ar.restaurant_id
      FROM attraction_restaurants AS ar
      WHERE ar.attraction_id = :attraction_id
  );
```

数据库约束保证 `affects_recommendation=0`。应用层仍应执行：

1. 保留餐厅基础 POI 作为候选；
2. 对命中的 `review_scope` 不使用相应标签匹配；
3. 可以向前端显示“该标签需要查证”，但不能显示为已确认结论；
4. 不因缺少标签而自动填入默认偏好。

当前 115 家查证餐厅不能因 JOIN 写法错误而恢复标签权重。

## 7. 标签证据

需要解释标签时查询：

```sql
SELECT
    evidence_id,
    restaurant_id,
    feature_name,
    evidence_type,
    evidence_value,
    source,
    source_url,
    confidence,
    collected_at
FROM restaurant_feature_evidence
WHERE restaurant_id = :restaurant_id
  AND feature_name = :feature_name
ORDER BY evidence_id;
```

来源解释：

- `amap_type_raw`：高德原始类别证据；
- `category_prior`：已审核类别先验；
- `menu_inferred`：已审核菜单/名称线索推断；
- `manual_verified`：人工逐店确认；
- `official_description`、`review_inferred`：保留接口，使用时必须有明确来源。

`category_prior` 不能被前端改写成“这家店一定低盐/适合老人”等单店事实。

## 8. 联系方式

```sql
SELECT
    contact_type,
    contact_value,
    display_label,
    is_primary,
    is_verified,
    verification_source,
    source_url,
    last_verified_at,
    status,
    notes
FROM restaurant_contacts
WHERE restaurant_id = :restaurant_id
ORDER BY is_primary DESC, contact_id;
```

当前联系方式来自静态源且总体状态为待核验。`is_verified=0` 时前端应显示“请致电
确认”或同等提示，不能表示为已验证预订渠道。

## 9. 类别映射

餐厅表已保存当次规范类别；需要审计映射规则时：

```sql
SELECT
    category_level_1,
    category_level_2,
    mapping_version,
    mapping_status,
    evidence
FROM category_mapping
WHERE source = 'amap'
  AND type_raw = :type_raw
  AND (type_code = :type_code OR (type_code IS NULL AND :type_code IS NULL))
ORDER BY mapping_id DESC
LIMIT 1;
```

如果新数据出现未映射组合，应阻止发布并进入人工审核，不能在主 Agent 请求期间临时
猜类别。

## 10. 建议的后端 DTO

```json
{
  "attraction_id": "101",
  "static_version": "restaurant-static-v1.0.0",
  "restaurants": [
    {
      "restaurant_id": 1,
      "amap_poi_id": "B0...",
      "name": "餐厅名称",
      "coordinate": {
        "longitude": 113.0,
        "latitude": 22.0,
        "system": "GCJ-02"
      },
      "category": {
        "level_1": "中餐",
        "level_2": "粤菜",
        "type_raw": "高德原始分类"
      },
      "static_distance_m": 350,
      "features": {},
      "review_flags": [],
      "dynamic": {
        "route": {"status": "not_requested"},
        "crowd": {"status": "unavailable"},
        "queue": {"status": "unavailable"},
        "live_open_status": {"status": "unavailable"}
      }
    }
  ]
}
```

不要在默认候选查询中自动请求路线。`dynamic.route.status=not_requested` 与
`unavailable` 不同：前者是尚未显式调用，后者是调用能力/数据源不存在或失败。

## 11. 动态路线接入

只有用户明确选择某餐厅并请求路线时才调用：

```text
主 Agent 用户动作
  → Dynamic Agent
  → Provider Registry
  → AmapWalkingRouteProvider
  → TTL Cache
  → 统一 Route DTO
```

当前没有用户实时坐标。`route-test` 只使用指定景点坐标作为测试代理，响应必须携带：

```json
{
  "origin_source": "attraction_coordinate_test_proxy",
  "origin_is_proxy": true
}
```

该结果不能称为真实用户路线，不能回写
`attraction_restaurants.straight_distance_m`，也不能当作永久静态数据。

人流、排队和实时营业状态当前必须返回：

```json
{
  "status": "unavailable",
  "provider": "unavailable",
  "data": null,
  "error_type": "provider_not_configured"
}
```

具体字段以 `restaurant_pipeline/providers/contracts.py` 为准。空数据不能解释成
“不拥挤”“不用排队”或“已关门”。

## 12. 兼容桥

`integration/restaurant_data.py` 可作为现有 `agent/restaurant_data.py` 的独立兼容
参考。接入时建议只替换数据库路径并在主 Agent 服务启动测试中调用，不要把 Restaurant
Agent 与主 Agent 本体混称。

当前交付桥已经提供：

- `restaurant_database_path()`：返回版本化 SQLite，支持
  `RESTAURANT_DATABASE_PATH` 环境变量覆盖；
- `load_nearby_restaurants(attraction_ids, limit_per_attraction=5,
  include_features=True, include_review_flags=True)`：按景点读取候选，并返回
  `static_features`、`feature_labels`、`review_flags`、
  `features_available` 和 `requires_review`；
- `load_restaurant_features(restaurant_ids)`：按餐厅 ID 批量返回
  `feature_name → label/confidence/version/calculated_at`；
- `load_restaurant_feature_evidence(restaurant_id, feature_name=None)`：
  返回标签证据；
- `load_restaurant_review_flags(restaurant_ids)`：批量返回未解决查证状态。

桥以只读 URI 打开数据库。动态路线不混入该静态桥，仍通过 Dynamic Agent 显式调用。

## 13. 启动期验收

生产加载新版本前运行：

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

并验证：

- `restaurants.amap_poi_id` 无重复；
- 关系表没有孤立景点或餐厅；
- 所有关系景点 ID 都存在于主 Agent 工作簿；
- `restaurant_static_features.feature_value IS NULL`；
- `confidence` 不超出 0–1；
- `restaurant_review_flags.affects_recommendation=0`；
- `dynamic_provider_cache` 不作为静态事实读取；
- 版本、计数和 manifest 哈希匹配。

只有最终交付报告中的只读数据追溯、Excel/SQLite 对账、标签接口调用，以及
Restaurant Pipeline 原有离线测试全部通过，才能切换主 Agent 配置。
