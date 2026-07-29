# Restaurant SQLite 数据字典

数据库文件：`restaurant_recommendation_v1.0.0.db`  
静态版本：`restaurant-static-v1.0.0`  
数据库：SQLite  
坐标系：GCJ-02

本文按实际冻结库定义，不按设想猜字段。`NOT NULL`、主键、唯一键和外键均来自实际
SQLite schema。

## 1. 总表

| 表 | 行数 | 用途 | 主 Agent 默认读取 |
|---|---:|---|---|
| `attractions` | 90 | 当次景点输入快照 | 否，主 Agent 已有景点主表 |
| `restaurants` | 489 | 去重餐厅实体 | 是 |
| `attraction_restaurants` | 6,798 | 景点—餐厅多对多关系 | 是 |
| `category_mapping` | 31 | 类别映射规则 | 按需 |
| `restaurant_contacts` | 361 | 联系方式 | 按需 |
| `restaurant_static_features` | 3,074 | 离散静态标签 | 是 |
| `restaurant_feature_evidence` | 9,942 | 标签及原始特征证据 | 解释时 |
| `restaurant_review_flags` | 115 | 需要查证和隔离 | 是 |
| `restaurant_change_log` | 370 | 字段变更审计 | 否 |
| `collection_runs` | 1 | 采集运行审计 | 否 |
| `collection_log` | 393 | 分页任务审计 | 否 |
| `dynamic_provider_cache` | 10 | 动态 Provider TTL 缓存 | 否 |
| `restaurant_business_hours` | 0 | 核验后的营业时段预留 | 否 |
| `restaurant_media` | 0 | 媒体及授权预留 | 否 |
| `restaurant_menu_items` | 0 | 菜单预留 | 否 |
| `restaurant_reservation_channels` | 0 | 预约渠道预留 | 否 |
| `restaurant_service_options` | 0 | 服务能力预留 | 否 |
| `schema_migrations` | 2 | 数据库迁移版本 | 否 |

## 2. `attractions`

当前采集所用景点快照。Excel 不重复导出；主 Agent 应以自己已有景点工作簿为主。

主键：`attraction_id`

| 字段 | 类型/约束 | 来源与含义 | 空值规则 |
|---|---|---|---|
| `attraction_id` | TEXT PK | 主 Agent 景点 `id` | 不可空 |
| `attraction_name` | TEXT NOT NULL | 主 Agent `name_zh` | 不可空 |
| `longitude` | REAL NOT NULL | 景点经度 | 不可空 |
| `latitude` | REAL NOT NULL | 景点纬度 | 不可空 |
| `coordinate_system` | TEXT NOT NULL | 当前为 `GCJ-02` | 不可空 |
| `source_version` | TEXT NOT NULL | 逐景点输入指纹/版本 | 不可空 |
| `collection_status` | TEXT | 该景点采集状态 | 未记录可空 |
| `last_collected_at` | TEXT | 最近成功采集时间，ISO 时间 | 未采集可空 |

## 3. `restaurants`

餐厅实体表。一个高德 POI 只保存一次。

主键：`restaurant_id`  
唯一键：`amap_poi_id`  
索引：`type_code/type_raw` 类别查询索引

| 字段 | 类型/约束 | 来源与含义 | 空值规则 |
|---|---|---|---|
| `restaurant_id` | INTEGER PK AUTOINCREMENT | 当前库内部餐厅 ID | 自动生成 |
| `amap_poi_id` | TEXT NOT NULL UNIQUE | 高德 POI ID；主去重键 | 不可空 |
| `restaurant_name` | TEXT NOT NULL | 高德餐厅名称 | 不可空 |
| `brand_name` | TEXT | 规范品牌名 | 未识别可空 |
| `branch_name` | TEXT | 分店名 | 未识别可空 |
| `longitude` | REAL | POI 经度 | 源未提供可空 |
| `latitude` | REAL | POI 纬度 | 源未提供可空 |
| `coordinate_system` | TEXT | POI 坐标系，当前为 GCJ-02 | 未确认不得猜 |
| `address` | TEXT | 高德地址 | 未提供可空 |
| `telephone` | TEXT | 高德原始电话展示值 | 未提供可空 |
| `type_raw` | TEXT | 高德原始分类路径，原样保留 | 未提供可空 |
| `type_code` | TEXT | 高德类别编码 | 未提供可空 |
| `category_level_1` | TEXT | 项目一级规范类别 | 未映射可空 |
| `category_level_2` | TEXT | 项目二级规范类别 | 未映射可空 |
| `average_price` | REAL | 可核验平均价格预留 | 当前多数/全部未知可空；不得猜 |
| `city` | TEXT | 城市 | 未提供可空 |
| `district` | TEXT | 区域 | 未提供可空 |
| `business_area` | TEXT | 商圈 | 未提供可空 |
| `source` | TEXT NOT NULL | 当前为 `amap` | 不可空 |
| `source_url` | TEXT | 源记录 URL | 无稳定 URL 可空 |
| `source_license` | TEXT | 来源许可说明 | 未记录可空 |
| `data_quality_status` | TEXT NOT NULL DEFAULT `unreviewed` | 实体级数据质量状态 | 不可空 |
| `first_collected_at` | TEXT | 首次采集时间 | 可空 |
| `last_updated_at` | TEXT | 最近实体更新 | 可空 |
| `last_verified_at` | TEXT | 最近人工/来源核验 | 未核验可空 |
| `data_version` | TEXT | 单记录数据指纹/版本 | 可空但发布应保留 |

`telephone` 是 POI 原始字段；规范化的多联系方式应读取 `restaurant_contacts`。

## 4. `attraction_restaurants`

景点—餐厅多对多关系。相同餐厅可关联多个景点。

复合主键：`attraction_id + restaurant_id`  
外键：`attraction_id → attractions.attraction_id`  
外键：`restaurant_id → restaurants.restaurant_id`  
索引：景点、餐厅、直线距离

| 字段 | 类型/约束 | 来源与含义 | 空值规则 |
|---|---|---|---|
| `attraction_id` | TEXT PK/FK NOT NULL | 主 Agent 景点 ID | 不可空 |
| `restaurant_id` | INTEGER PK/FK NOT NULL | 当前库餐厅 ID | 不可空 |
| `straight_distance_m` | REAL | 景点到餐厅的静态直线距离（米） | 无有效坐标可空 |
| `search_radius_m` | INTEGER | 本次搜索半径，当前 1500 | 旧记录可空 |
| `search_keyword` | TEXT | 本次关键词，当前 `餐厅` | 旧记录可空 |
| `search_page` | INTEGER | POI 出现页码 | 可空 |
| `search_rank` | INTEGER | POI 在该页/结果中的顺序 | 可空 |
| `attraction_source_version` | TEXT NOT NULL | 对应景点输入指纹 | 不可空 |
| `raw_file` | TEXT NOT NULL | 原始响应审计路径 | 库内不可空；Excel 为可移植性不导出 |
| `collected_at` | TEXT | 关系首次/本次采集时间 | 可空 |

`straight_distance_m` 不是步行距离或路线时间。

当前关系只覆盖 89 个景点。`attractions` 中的 ID `305` 有成功的 0 结果采集日志，
所以没有关系记录；这是已记录的采集结果，不是孤立外键或丢数。

## 5. `category_mapping`

高德原始分类到项目两级分类的版本化映射。

主键：`mapping_id`  
唯一键：`source + type_raw + type_code + mapping_version`

| 字段 | 类型/约束 | 含义 | 空值规则 |
|---|---|---|---|
| `mapping_id` | INTEGER PK AUTOINCREMENT | 映射记录 ID | 自动生成 |
| `source` | TEXT NOT NULL | 原始来源，当前 `amap` | 不可空 |
| `type_raw` | TEXT NOT NULL | 高德原始分类路径 | 不可空 |
| `type_code` | TEXT | 高德分类编码 | 源无编码可空 |
| `category_level_1` | TEXT | 项目一级类别 | 待审核可空 |
| `category_level_2` | TEXT | 项目二级类别 | 待审核可空 |
| `mapping_version` | TEXT NOT NULL | 映射规则版本 | 不可空 |
| `mapping_status` | TEXT NOT NULL DEFAULT `pending_review` | 审核状态 | 不可空 |
| `evidence` | TEXT | 映射依据 | 无说明可空，但发布映射应有依据 |

## 6. `restaurant_contacts`

规范化联系方式。

主键：`contact_id`  
唯一键：`restaurant_id + contact_type + contact_value`  
外键：`restaurant_id → restaurants.restaurant_id`

| 字段 | 类型/约束 | 含义 | 空值规则 |
|---|---|---|---|
| `contact_id` | INTEGER PK AUTOINCREMENT | 联系方式 ID | 自动生成 |
| `restaurant_id` | INTEGER FK NOT NULL | 所属餐厅 | 不可空 |
| `contact_type` | TEXT NOT NULL | 如 phone、website 等 | 不可空 |
| `contact_value` | TEXT NOT NULL | 电话号码或联系值 | 不可空 |
| `display_label` | TEXT | 展示说明 | 可空 |
| `is_primary` | INTEGER NOT NULL DEFAULT 0 | 是否主要联系方式，0/1 | 不可空 |
| `is_verified` | INTEGER NOT NULL DEFAULT 0 | 是否已独立核验，0/1 | 不可空 |
| `verification_source` | TEXT | 核验来源 | 未核验可空 |
| `source_url` | TEXT | 来源 URL | 可空 |
| `valid_from` | TEXT | 有效期开始 | 未知可空 |
| `valid_to` | TEXT | 有效期结束 | 未知可空 |
| `last_verified_at` | TEXT | 最近核验时间 | 未核验可空 |
| `status` | TEXT NOT NULL DEFAULT `unverified` | 联系方式状态 | 不可空 |
| `notes` | TEXT | 备注 | 可空 |

`is_verified=0` 不等于号码错误，只表示没有完成本项目独立核验。

## 7. `restaurant_static_features`

当前发布的离散静态标签。

复合主键：`restaurant_id + feature_name + feature_version`  
外键：`restaurant_id → restaurants.restaurant_id`

| 字段 | 类型/约束 | 含义 | 空值规则 |
|---|---|---|---|
| `restaurant_id` | INTEGER PK/FK NOT NULL | 所属餐厅 | 不可空 |
| `feature_name` | TEXT PK NOT NULL | 九个标签维度之一 | 不可空 |
| `feature_value` | REAL | 连续值预留 | 当前版本必须为 NULL |
| `feature_label` | TEXT | 离散标签文本 | 当前发布记录应非空 |
| `confidence` | REAL | 证据可信度 0–1 | 无可量化置信度可空 |
| `feature_version` | TEXT PK NOT NULL | 当前 `discrete-taste-v1.0` | 不可空 |
| `calculated_at` | TEXT NOT NULL | 标签生成时间 | 不可空 |

当前九个 `feature_name`：

`cuisine_primary`、`cuisine_secondary`、`taste_tags`、
`serving_temperature`、`meal_type_tags`、`flavor_intensity`、
`elderly_positive_tags`、`elderly_caution_tags`、`nutrition_structure`。

## 8. `restaurant_feature_evidence`

标签和原始特征的证据表。

主键：`evidence_id`  
外键：`restaurant_id → restaurants.restaurant_id`

| 字段 | 类型/约束 | 含义 | 空值规则 |
|---|---|---|---|
| `evidence_id` | INTEGER PK AUTOINCREMENT | 证据 ID | 自动生成 |
| `restaurant_id` | INTEGER FK NOT NULL | 所属餐厅 | 不可空 |
| `feature_name` | TEXT NOT NULL | 证据支持的维度；也可为 `source_category` | 不可空 |
| `evidence_type` | TEXT NOT NULL | `amap_type_raw/category_prior/menu_inferred/manual_verified/...` | 不可空 |
| `evidence_value` | TEXT | 原始类别、审核结论或推断依据 | 无文本可空 |
| `source` | TEXT NOT NULL | `amap` 或审核来源名 | 不可空 |
| `source_url` | TEXT | 可访问来源 URL | 无 URL 可空 |
| `raw_file` | TEXT | 原始 JSON/审核文件引用 | SQLite 审计保留；Excel 不导出本地路径 |
| `confidence` | REAL | 该证据可信度 0–1 | 原始事实未赋值可空 |
| `collected_at` | TEXT | 获取/生成证据时间 | 可空 |

当前 9,942 条包括：

- 6,868 条高德原始类别证据 `amap_type_raw`；
- 396 条已审核 `category_prior`；
- 446 条已审核 `menu_inferred`；
- 2,232 条 `manual_verified`。

后三项合计 3,074，与发布标签数一致。

## 9. `restaurant_review_flags`

证据不足或类别异常时的安全隔离。

主键：`review_flag_id`  
唯一键：`restaurant_id + review_scope + source`  
外键：`restaurant_id → restaurants.restaurant_id`  
检查约束：`affects_recommendation = 0`

| 字段 | 类型/约束 | 含义 | 空值规则 |
|---|---|---|---|
| `review_flag_id` | INTEGER PK AUTOINCREMENT | 查证记录 ID | 自动生成 |
| `restaurant_id` | INTEGER FK NOT NULL | 所属餐厅 | 不可空 |
| `review_scope` | TEXT NOT NULL | 受影响的标签/审核范围 | 不可空 |
| `review_status` | TEXT NOT NULL | 当前为 `需要查证` | 不可空 |
| `reason` | TEXT | 查证原因 | 可空但应填写 |
| `source` | TEXT NOT NULL | 标记来源 | 不可空 |
| `source_reference` | TEXT | 审核文件/记录引用 | SQLite 审计保留；Excel 不导出本地路径 |
| `affects_recommendation` | INTEGER NOT NULL DEFAULT 0 CHECK=0 | 必须为 0，禁止参与推荐 | 不可空 |
| `created_at` | TEXT NOT NULL | 建立时间 | 不可空 |
| `resolved_at` | TEXT | 解决时间 | 未解决为 NULL |

## 10. `restaurant_change_log`

餐厅字段规范化或审核变更记录。

主键：`change_id`  
外键：`restaurant_id → restaurants.restaurant_id`  
外键：`run_id → collection_runs.run_id`

| 字段 | 类型/约束 | 含义 | 空值规则 |
|---|---|---|---|
| `change_id` | INTEGER PK AUTOINCREMENT | 变更 ID | 自动生成 |
| `restaurant_id` | INTEGER FK | 当前库餐厅 ID | 删除/历史特殊情况可空 |
| `amap_poi_id` | TEXT NOT NULL | 跨版本餐厅识别键 | 不可空 |
| `field_name` | TEXT NOT NULL | 发生变化的字段 | 不可空 |
| `previous_value` | TEXT | 旧值 | 首次赋值可空 |
| `current_value` | TEXT | 新值 | 清空字段可空 |
| `source_raw_file` | TEXT | 变更原始证据路径 | SQLite 审计保留；Excel 不导出 |
| `detected_at` | TEXT NOT NULL | 检测时间 | 不可空 |
| `run_id` | TEXT FK | 关联采集运行 | 人工审核变更可空 |

## 11. `collection_runs`

一次流水线运行的审计摘要，不是业务查询表。

主键：`run_id`

| 字段 | 类型/约束 | 含义 |
|---|---|---|
| `run_id` | TEXT PK | 运行唯一 ID |
| `run_mode` | TEXT NOT NULL | single/sample/full 等 |
| `input_file` | TEXT NOT NULL | 输入工作簿审计引用 |
| `input_file_sha256` | TEXT | 工作簿 SHA-256 |
| `configuration_sha256` | TEXT | 采集配置 SHA-256 |
| `started_at` | TEXT NOT NULL | 开始时间 |
| `finished_at` | TEXT | 完成时间 |
| `status` | TEXT NOT NULL | 运行状态 |
| `statistics_json` | TEXT | 统计 JSON |
| `error_message` | TEXT | 失败信息 |

## 12. `collection_log`

单景点、关键词和页码级任务日志，用于分页、重试和断点续跑。

主键：`task_key`

| 字段 | 类型/约束 | 含义 |
|---|---|---|
| `task_key` | TEXT PK | 规范化请求任务键 |
| `attraction_id` | TEXT | 景点 ID |
| `keyword` | TEXT | 关键词 |
| `page` | INTEGER | 页码 |
| `request_status` | TEXT | 请求状态 |
| `result_count` | INTEGER | 返回 POI 数 |
| `error_code` | TEXT | 高德/网络错误码 |
| `error_message` | TEXT | 错误信息 |
| `retry_count` | INTEGER | 已重试次数 |
| `started_at` | TEXT | 开始时间 |
| `finished_at` | TEXT | 完成时间 |
| `raw_file` | TEXT | 对应原始 JSON |

相同参数成功任务且 `raw_file` 存在时应复用，不重复请求。

## 13. `dynamic_provider_cache`

统一动态 Provider 的 TTL 缓存。它不是静态业务事实，发布 Excel 不导出，主 Agent 不
应把旧记录当作当前人流/排队/营业状态。

主键：`cache_key`  
索引：`expires_at`

| 字段 | 类型/约束 | 含义 |
|---|---|---|
| `cache_key` | TEXT PK | Provider + 规范请求的缓存键 |
| `provider_type` | TEXT NOT NULL | route/crowd/queue/live_open_status |
| `provider_name` | TEXT NOT NULL | amap/unavailable/mock 等 |
| `request_json` | TEXT NOT NULL | 规范请求 DTO |
| `response_json` | TEXT | 响应 DTO |
| `status` | TEXT NOT NULL | success/unavailable/error 等 |
| `fetched_at` | TEXT NOT NULL | 获取时间 |
| `expires_at` | TEXT NOT NULL | 过期时间 |
| `error_type` | TEXT | 结构化错误类型 |
| `error_message` | TEXT | 安全错误信息 |

## 14. `restaurant_business_hours`（0 行，预留）

只有来源明确且完成核验的营业时段才能写入。

| 字段 | 类型/约束 | 含义 |
|---|---|---|
| `business_hour_id` | INTEGER PK AUTOINCREMENT | 时段 ID |
| `restaurant_id` | INTEGER FK NOT NULL | 所属餐厅 |
| `day_of_week` | INTEGER | 星期编码 |
| `open_time` | TEXT | 开门时间 |
| `close_time` | TEXT | 关门时间 |
| `raw_text` | TEXT | 来源原文 |
| `effective_from` | TEXT | 生效日期 |
| `effective_to` | TEXT | 失效日期 |
| `status` | TEXT NOT NULL DEFAULT `unverified` | 核验状态 |
| `source_url` | TEXT | 来源 URL |
| `last_verified_at` | TEXT | 最近核验时间 |

这张表是静态核验时段，不等于“现在营业中”。实时状态必须走动态 Provider。

## 15. `restaurant_media`（0 行，预留）

主键：`media_id`；唯一键：`restaurant_id + media_url`。

| 字段 | 类型/约束 | 含义 |
|---|---|---|
| `media_id` | INTEGER PK AUTOINCREMENT | 媒体 ID |
| `restaurant_id` | INTEGER FK NOT NULL | 所属餐厅 |
| `media_type` | TEXT NOT NULL | image/video 等 |
| `media_url` | TEXT NOT NULL | 媒体 URL |
| `caption` | TEXT | 说明 |
| `source_url` | TEXT | 来源页面 |
| `license_or_usage` | TEXT | 许可/使用范围 |
| `last_verified_at` | TEXT | 最近核验 |

没有明确许可不得写入或向 GitHub 分发媒体。

## 16. `restaurant_menu_items`（0 行，预留）

| 字段 | 类型/约束 | 含义 |
|---|---|---|
| `menu_item_id` | INTEGER PK AUTOINCREMENT | 菜品 ID |
| `restaurant_id` | INTEGER FK NOT NULL | 所属餐厅 |
| `item_name` | TEXT NOT NULL | 菜名 |
| `item_category` | TEXT | 菜品类别 |
| `price` | REAL | 价格 |
| `currency` | TEXT | 币种 |
| `description` | TEXT | 描述 |
| `source_url` | TEXT | 来源 URL |
| `last_verified_at` | TEXT | 最近核验 |

标签中的“菜单推断”不是这张表的已核验菜单数据。

## 17. `restaurant_reservation_channels`（0 行，预留）

外键：`restaurant_id → restaurants`；
`booking_phone_contact_id → restaurant_contacts`。

| 字段 | 类型/约束 | 含义 |
|---|---|---|
| `reservation_channel_id` | INTEGER PK AUTOINCREMENT | 预约渠道 ID |
| `restaurant_id` | INTEGER FK NOT NULL | 所属餐厅 |
| `channel_type` | TEXT NOT NULL | phone/web/app 等 |
| `channel_name` | TEXT | 渠道名 |
| `booking_url` | TEXT | 预订 URL |
| `booking_phone_contact_id` | INTEGER FK | 电话联系方式 |
| `app_or_mini_program_name` | TEXT | App/小程序名 |
| `supports_online_booking` | INTEGER | 是否在线预订，0/1/NULL |
| `supports_same_day_booking` | INTEGER | 是否当日预订，0/1/NULL |
| `status` | TEXT NOT NULL DEFAULT `unverified` | 核验状态 |
| `source_url` | TEXT | 证据 URL |
| `last_verified_at` | TEXT | 最近核验 |
| `notes` | TEXT | 备注 |

0 行不表示餐厅不支持预约。

## 18. `restaurant_service_options`（0 行，预留）

唯一键：`restaurant_id + option_type + option_value`。

| 字段 | 类型/约束 | 含义 |
|---|---|---|
| `service_option_id` | INTEGER PK AUTOINCREMENT | 服务能力 ID |
| `restaurant_id` | INTEGER FK NOT NULL | 所属餐厅 |
| `option_type` | TEXT NOT NULL | 服务类型 |
| `option_value` | TEXT | 具体值 |
| `confidence` | REAL | 证据可信度 |
| `evidence_id` | INTEGER | 证据引用预留 |
| `source_url` | TEXT | 来源 URL |
| `last_verified_at` | TEXT | 最近核验 |

无数据时不能推断无障碍、外卖、素食或其他服务是否存在。

## 19. `schema_migrations`

主键：`version`。

| 字段 | 类型/约束 | 含义 |
|---|---|---|
| `version` | TEXT PK | schema 迁移版本 |
| `applied_at` | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | 应用时间 |

## 20. 完整性规则

发布验收必须满足：

```sql
PRAGMA integrity_check;      -- 必须返回 ok
PRAGMA foreign_key_check;    -- 必须 0 行
```

并检查：

- `restaurants.amap_poi_id` 唯一且非空；
- 关系复合主键无重复；
- 关系景点均存在于主 Agent 景点工作簿；
- 关系餐厅均存在于 `restaurants`；
- `restaurant_static_features.feature_value` 全为空；
- 非空 `confidence` 在 0–1；
- `restaurant_review_flags.affects_recommendation` 全为 0；
- Excel 业务 Sheet 与 SQLite 对应表行数一致；
- Excel 不包含本地绝对路径、API Key、动态缓存和重复景点主表。
