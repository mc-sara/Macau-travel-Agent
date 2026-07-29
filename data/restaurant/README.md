# data：可上传的 Restaurant 数据交付

本目录是 Restaurant Agent 可上传 GitHub 的干净数据区。主 Agent 根目录原有 `data/`
不属于本次整理范围，没有复制或覆盖。

## 1. 文件

| 文件 | 权威用途 | 是否给主团队直接读取 |
|---|---|---|
| `澳门餐厅数据_v1.0.0.xlsx` | 人工审核、GitHub 共享、业务查阅 | 是，主要交付 |
| `restaurant_recommendation_v1.0.0.db` | 规范化机器接口、主 Agent 查询 | 是，运行接口 |
| `DATA_DICTIONARY.md` | 每张表、字段、键、来源和空值语义 | 是 |
| `manifest.json` | 版本、计数、文件哈希、边界和连接键 | 是 |

Excel 和 SQLite 来自同一冻结版本。不得手工分别修改。更新必须由流水线生成两者并
对账。

## 2. Excel Sheet

| Sheet | 对应 SQLite | 行数 | 说明 |
|---|---|---:|---|
| `交付说明` | manifest/说明 | 1 页 | 版本、计数、连接键、边界 |
| `餐厅` | `restaurants` | 489 | 按高德 POI ID 去重的实体 |
| `景点餐厅关系` | `attraction_restaurants` | 6,798 | 已去除本地 `raw_file` 路径 |
| `联系方式` | `restaurant_contacts` | 361 | 电话等静态联系方式 |
| `类别映射` | `category_mapping` | 31 | 原始类别到两级类别 |
| `标签字典` | 标签字段说明 | 9 类 | 九类标签的含义、示例和推断边界 |
| `餐厅标签分列` | `restaurants` + `restaurant_static_features` + `restaurant_review_flags` | 489 | 每家餐厅一行，九类标签严格分列；人工审核主视图 |
| `标签明细（机器）` | `restaurant_static_features` | 3,074 | 纵向机器映射；不作为人工混合标签视图 |
| `特征证据` | `restaurant_feature_evidence` | 9,942 | 已去除本地 `raw_file` 路径 |
| `需要查证` | `restaurant_review_flags` | 115 | 已去除本地 `source_reference` 路径 |
| `变更日志` | `restaurant_change_log` | 370 | 已去除本地 `source_raw_file` 路径 |

Excel 没有重复保存 SQLite 的：

- `attractions`：因为 90 条景点主数据已经位于主 Agent
  `data/excel/macau_attractions_master.xlsx`；
- `collection_log`、`collection_runs`：运行审计，不是 GitHub 业务共享视图；
- `dynamic_provider_cache`：过期动态缓存，不是静态事实；
- 6 张 0 行保留扩展表：结构已在 SQLite 和数据字典中保留，无业务数据可展示；
- `schema_migrations`：数据库内部迁移记录。

## 3. SQLite 表分组

### 主 Agent 日常读取

- `restaurants`
- `attraction_restaurants`
- `category_mapping`
- `restaurant_contacts`
- `restaurant_static_features`
- `restaurant_feature_evidence`
- `restaurant_review_flags`

### 审计/更新读取

- `attractions`
- `restaurant_change_log`
- `collection_runs`
- `collection_log`
- `schema_migrations`

### 不作为静态事实读取

- `dynamic_provider_cache`

### 预留且当前为空

- `restaurant_business_hours`
- `restaurant_media`
- `restaurant_menu_items`
- `restaurant_reservation_channels`
- `restaurant_service_options`

空表表示接口已预留但尚无独立核验数据，绝不能解释为“没有营业时间”“不支持预约”
或“不提供某项服务”。

## 4. 主连接

```sql
SELECT
    ar.attraction_id,
    r.restaurant_id,
    r.amap_poi_id,
    r.restaurant_name,
    r.category_level_1,
    r.category_level_2,
    ar.straight_distance_m
FROM attraction_restaurants ar
JOIN restaurants r ON r.restaurant_id = ar.restaurant_id
WHERE ar.attraction_id = :main_agent_attraction_id
ORDER BY ar.straight_distance_m;
```

`main_agent_attraction_id` 来自主 Agent 景点工作簿的 `id`。景点 ID 使用文本连接；
餐厅跨版本识别使用 `amap_poi_id`。

当前 90 个景点中有 89 个存在关系。ID `305`（九澳七苦圣母小堂）在既定
`餐厅/1500米` 条件内请求成功但返回 0 条，因此查询返回空列表是正确结果，不得用邻近
其他景点的餐厅补齐。

## 5. 标签读取

```sql
SELECT feature_name, feature_label, confidence, feature_version
FROM restaurant_static_features
WHERE restaurant_id = :restaurant_id
ORDER BY feature_name;
```

- `feature_label` 是当前离散标签。
- `feature_value` 必须为 `NULL`。
- `confidence` 是证据可信度，不是推荐分。
- 使用前查询 `restaurant_review_flags`；未解决查证范围不得参与匹配。

## 6. 空值和布尔值

- 未知、未提供、未核验统一保留 `NULL`/Excel 空白。
- 不得用 0、空字符串或 `false` 伪装为确定事实。
- SQLite 布尔接口使用 `0/1`，但只有字段语义明确时才可解释。
- 预留表 0 行表示没有可发布数据，不表示业务否定。

## 7. 数据来源和许可字段

- POI 实体与原始类别来源：高德 `amap`。
- `source_url`、`source_license` 允许为空；为空时不得补造链接或许可结论。
- 标签来源写入 `restaurant_feature_evidence`。
- 运行原始 JSON 在原流水线审计区保留，不复制到本 GitHub 包。

## 8. 数据版本

| 项目 | 值 |
|---|---|
| 静态版本 | `restaurant-static-v1.0.0` |
| 数据采集日期 | 2026-07-29 |
| 冻结日期 | 2026-07-30 |
| 坐标系 | GCJ-02 |
| 餐厅去重键 | `amap_poi_id` |
| 景点连接键 | `attraction_id` → 主 Agent `id` |

完整字段说明见 `DATA_DICTIONARY.md`。实际接入见
`../主要脚本/MAIN_AGENT_INTEGRATION.md`。
