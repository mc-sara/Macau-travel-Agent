# 澳游半日管家 Agent Demo 设计文档

## 1. 产品定位

澳游半日管家 Agent 面向澳门本地生活场景，目标是把用户的一句话需求转化为可执行的半日吃喝玩安排。

它不是普通推荐系统。普通推荐系统通常给用户一组景点或餐厅候选项，仍然需要用户自己查路线、比距离、看是否有位、安排时间。本 Demo 的核心是展示 Agent 帮用户把事情做完：规划路线、解释原因、检查可用性，并在用户确认后模拟预约、订座、点单和发送消息。

## 2. Agent 工作流

整体链路如下：

```text
用户自然语言输入
→ llm_goal_parser 将人话拆解为 structured_goal
→ goal_validator 校验和修正关系类型、人数、枚举字段
→ goal_enricher 补全 planning_strategy：低疲劳、餐桌人数、休息点、避让策略
→ parse_goal 兼容旧 Planner 输入
→ search_attractions 查询澳门景点候选
→ get_accessibility 查询疲劳和台阶风险
→ mock_map_route_api 计算导航距离、时间、步行量
→ search_local_merchants 查询本地商户和活动
→ check_availability 检查活动/餐厅/饮品/礼物可用性
→ generate_candidate_plans 生成主方案和备选方案
→ score_plan 可解释评分
→ Streamlit UI 展示需求拆解、路线、理由、风险、预算
→ execute_plan 模拟执行预约、订位、点单、消息生成
```

## 3. 场景解析策略

当前版本采用“LLM/Mock LLM 需求拆解 + Schema 校验 + 规则补全”的混合策略。

LLM/Mock LLM 不直接生成路线，而是只负责把人类语言转成结构化需求 `structured_goal`：

- relationship_type：family_with_children / family_with_seniors / couple / friends / general 等
- outing_intent：half_day_outing / date_plan / kid_friendly_play / low_fatigue_relax 等
- people：总人数、男女数量、儿童数量、长辈数量
- hard_constraints：必须满足的硬约束，例如 low_fatigue、kid_friendly、avoid_stairs
- soft_preferences：软偏好，例如 photo_friendly、romantic、dinner_together
- planning_strategy：步行上限、路线时长上限、是否必须安排休息、餐桌人数等
- missing_info / assumptions：缺失信息和默认假设

然后系统再做两层稳定化：

1. `goal_validator.py`：修正明显矛盾，例如 2男3女但 total=2 时改为 total=5；children>0 时改为亲子家庭；seniors>0 时加入避开楼梯。
2. `goal_enricher.py`：根据关系和偏好补全规划策略，例如 friends+5人需要5人桌，亲子家庭需要低疲劳和休息点，长辈家庭要避开台阶。

这样可以兼顾自然语言理解的灵活性和 Demo 规划链路的稳定性。

## 4. Tool Layer 设计

Tool Layer 位于 `agent/tools.py`，模拟 Agent 可以调用的外部工具。

### search_attractions

返回澳门候选景点，例如二龙喉公园缆车、议事亭前地、玫瑰圣母堂、澳门旅游塔等。

### get_accessibility

返回景点疲劳风险，例如大三巴正门有 68 级台阶，亲子路线应避开正门台阶。

### mock_map_route_api

这是 Demo 的重点。它模拟地图 API，返回：

- route_distance_km
- duration_min
- walking_distance_m
- transfer_count
- traffic_level
- route_summary

这样可以体现本地生活 Agent 不是只看直线距离，而是看真实导航成本、步行量、换乘和疲劳程度。

### search_local_merchants

从 `data/mock_merchants.json` 查询餐厅、奶茶、活动、礼物等。

### check_availability

模拟查询餐厅是否有位、活动是否有票、奶茶是否需要排队、花店是否可配送。

## 5. Planner 设计

Planner 位于 `agent/planner.py`。

首版为了 Demo 稳定，采用“固定高质量主路线 + 一个备选路线”的方案：

### 亲子家庭

```text
二龙喉公园缆车 → 澳门小熊亲子乐园 → 轻悦生活餐厅 → 茶语澳门低糖奶茶
```

重点体现：低疲劳、儿童友好、低卡餐饮、避开大三巴台阶。

### 朋友聚会

```text
议事亭前地 → 玫瑰圣母堂 → 茶语澳门低糖奶茶 → 澳门城市展览空间 → 氹仔葡式小馆
```

重点体现：拍照、聊天、社交、按实际人数检查餐厅桌位、路线不折返。比如用户输入“2男3女”时，系统会把 `restaurant_table_size_required` 设为 5，并用 5 人检查晚餐可用性。

### 情侣约会

```text
澳门旅游塔 → 海风咖啡 → 塔景氛围餐厅 → 小岛花房
```

重点体现：观景氛围、室内低疲劳、靠窗晚餐、鲜花惊喜。

## 6. Scoring 设计

Scorer 位于 `agent/scorer.py`，输出不仅包括总分，还包括评分拆解、推荐理由和风险提示。

### 亲子家庭权重

- 儿童友好度：25%
- 低疲劳程度：25%
- 路线顺畅度：20%
- 低卡餐饮匹配：20%
- 可执行性：10%

### 朋友聚会权重

- 社交价值：25%
- 拍照价值：15%
- 路线顺畅度：20%
- 餐厅匹配度：20%
- 可执行性：20%

### 情侣约会权重

- 氛围感：30%
- 低疲劳程度：20%
- 拍照价值：15%
- 餐饮体验：20%
- 惊喜执行：15%

## 7. Executor 设计

Executor 位于 `agent/executor.py`，在用户点击“确认并安排”后执行：

1. reserve_activity：模拟预约活动
2. reserve_restaurant：模拟订餐厅
3. order_drink_or_extra：模拟点奶茶、订花或蛋糕
4. send_plan_message：生成可发给老婆、朋友或对象的消息

输出包括订单号、状态和最终通知消息。

## 8. 为什么这是 Agent 而不是推荐系统

本 Demo 的关键不是“推荐几个地方”，而是完成本地生活任务链路：

- 理解用户真实约束：亲子、朋友、情侣、低疲劳、低卡、浪漫
- 调用工具补充信息：路线、台阶、商户、可用性
- 进行多目标决策：路线、疲劳、餐饮、执行性
- 输出可解释结论：为什么这样安排
- 最后执行动作：预约、订位、点单、生成消息

这符合比赛中“不是搜索推，而是帮用户把事情做完”的方向。
