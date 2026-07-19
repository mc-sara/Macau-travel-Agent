# Data Dictionary

当前 Excel 表头只保留英文列名，中文解释集中放在这里。

## macau_attractions_master.xlsx

| column | 中文含义 |
|---|---|
| id | 主键 |
| name_zh | 中文名 |
| name_en | 葡/英文名 |
| region | 区域 |
| latitude | 纬度 |
| longitude | 经度 |
| address | 地址 |
| opening_hours | 开放时间 |
| ticket_info | 门票 |
| route_cluster | 路线片区 |

## 澳门经典ID对应表格_适老化理由修订.xlsx

| column | 中文含义 |
|---|---|
| id | 主键 |
| name_zh | 中文名 |
| scenic_category_zh | 景点类别 |
| region | 区域 |
| senior_reason_zh | 适老化推荐理由 |

## attraction_accessibility_filled.xlsx

| column | 中文含义 |
|---|---|
| attraction_id | 对应景点 ID |
| wheelchair_friendly | 轮椅友善 |
| has_elevator | 有无电梯/升降机/扶梯 |
| steep_slopes | 有无陡坡 |
| stairs_count | 台阶级数 |
| rest_areas | 休息点/长椅情况 |
| accessible_toilet | 无障碍厕所 |
| senior_tips_zh | 长者专属提示语 |
| accessible_entrance | 无障碍入口 |
| ramp_available | 是否有坡道 |
| handrails_available | 是否有扶手 |
| ground_surface | 路面状况 |
| trip_hazards | 绊倒风险 |
| shaded_rest_areas | 遮阴休息点 |
| estimated_walking_distance_m | 核心游览步行距离 |
| estimated_visit_duration_min | 建议停留时长 |
| standing_time_risk | 久站风险 |
| toilet_distance_level | 厕所便利度 |
| crowd_level | 人流压力 |
| sun_or_rain_exposure | 暴晒或淋雨风险 |
| air_conditioned_or_indoor_rest | 室内/冷气休息点 |
| best_access_route_zh | 推荐长者入口/路线 |
| avoid_route_zh | 建议避开的路线 |

## attraction_transport_updated.xlsx

| column | 中文含义 |
|---|---|
| id | 主键 |
| attraction_id | 对应景点 ID |
| transport_type | 交通类型 |
| line_name | 路线 |
| low_floor_wheelchair_seat_available | 低地板和轮椅座椅可用 |
| boarding_point | 长辈上车点 |
| dropoff_point | 下车站点 |
| walking_route | 下车后步行指引 |

## Notes

- `attraction_accessibility_filled.xlsx` 中的适老字段是 demo-oriented synthetic data：根据景点类型、route_cluster、交通步行描述和长者出行常识生成，用于推荐算法 demo，不代表官方核验事实。
- `macau_attractions_master.xlsx` 已删除非实体项 `宣傳片`，并补齐空地址。