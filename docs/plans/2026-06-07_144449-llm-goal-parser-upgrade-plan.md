# LLM 需求拆解升级 Implementation Plan

> **For Hermes:** 先按阶段开发；每完成一个功能，必须运行对应测试和 smoke test，确认成功后再继续。当前计划先不写代码，只确定开发路线和验收标准。

**Goal:** 将当前规则版 `parse_goal` 升级为“LLM 需求理解 + Schema 校验 + 规则补全 + Planner/Scorer 消费结构化目标”的混合架构，让 Agent 能更灵活理解人类语言，并稳定归类到家庭、情侣、朋友、长辈家庭、独自休闲等场景。

**Architecture:** 保留现有 parser/tools/planner/scorer/executor 主链路，在 parser 前后新增 `llm_goal_parser`、`goal_schema`、`goal_validator`、`goal_enricher`。LLM 只负责把自然语言转成结构化 JSON；系统负责校验、纠错、补全规划策略；Planner 和 Scorer 只消费校验后的 structured_goal。

**Tech Stack:** Python 3, pytest, optional LLM provider/API, JSON schema style validation, Streamlit UI.

---

## 一、总体开发路线

推荐按 6 个阶段做：

1. 设计结构化需求 Schema
2. 开发纯本地校验与规则补全，不先接 LLM
3. 接入 LLM parser，并做 mock fallback
4. 改造 Planner/Scorer，让它们读取 structured_goal
5. 改造 Streamlit UI，展示“LLM 需求拆解结果”
6. 做端到端测试和 Demo 话术优化

为什么不第一步直接接 LLM：

- 先定义 Schema，才能约束 LLM 输出。
- 先有 validator/enricher，才能避免 LLM 输出不稳定。
- 即使 LLM 暂时不可用，也能用 mock parser 跑通 Demo。
- 比赛 Demo 最重要的是稳定展示，而不是完全依赖实时模型。

---

## 二、目标架构

当前链路：

```text
parse_goal 规则解析
→ planner
→ scorer
→ executor
```

升级后链路：

```text
用户自然语言
→ llm_goal_parser
→ goal_validator
→ goal_enricher
→ planner
→ scorer
→ executor
```

各层职责：

### 1. llm_goal_parser

负责理解人类语言，输出原始 structured_goal。

它不生成路线，只输出：

- 人群关系
- 出行意图
- 人数
- 时间
- 地点
- 硬约束
- 软偏好
- 缺失信息
- 是否需要追问
- 规划策略初稿

### 2. goal_validator

负责检查 LLM 输出是否合理。

例如：

- `relationship_type` 是否在枚举里
- `people.total` 是否等于 male + female + children + seniors
- `duration_hours` 是否是合理数字
- total > 2 但 relationship_type = couple 时是否需要修正
- children > 0 时是否应归入 family_with_children

### 3. goal_enricher

负责根据规则补充规划策略。

例如：

- 2男3女 → 朋友聚会，餐厅需要 5 人桌
- 带孩子 → kid_friendly、low_fatigue、short_walking
- 带长辈 → avoid_stairs、rest_area_required
- 情侣约会 → romantic、surprise_action、quiet_restaurant
- 不想累 → max_walking_per_segment_m 降低

### 4. planner

不再只看 `scenario`，而是读取：

- relationship_type
- outing_intent
- hard_constraints
- soft_preferences
- planning_strategy

### 5. scorer

评分逻辑升级为：

- 硬约束不满足：强扣分或过滤
- 软偏好不满足：轻扣分
- planning_strategy 满足越多，分越高

### 6. executor

仍然负责预约、订座、点单、消息生成，但消息内容可以基于 structured_goal 更个性化。

---

## 三、建议 Schema

创建文件：

```text
agent/goal_schema.py
```

核心结构：

```python
{
    "relationship_type": "friends",
    "outing_intent": "half_day_outing",
    "confidence": 0.92,
    "people": {
        "total": 5,
        "male": 2,
        "female": 3,
        "children": 0,
        "seniors": 0,
        "relationship_note": "2男3女朋友聚会"
    },
    "time": {
        "date": "today",
        "start_period": "afternoon",
        "start_time": None,
        "duration_hours": 5,
        "end_before": None
    },
    "location": {
        "city": "Macau",
        "start_location": None,
        "preferred_area": None,
        "avoid_area": []
    },
    "hard_constraints": ["low_fatigue"],
    "soft_preferences": ["photo_friendly", "social", "dinner_together"],
    "budget": {
        "level": "medium",
        "per_person_max": None
    },
    "planning_strategy": {
        "pace": "medium_slow",
        "max_walking_per_segment_m": 500,
        "max_route_duration_per_segment_min": 20,
        "must_include_meal": True,
        "must_include_rest": True,
        "restaurant_table_size_required": 5,
        "avoid": ["long_queue", "too_tiring"],
        "preferred": ["photo_spot", "drink_break", "group_restaurant"]
    },
    "missing_info": ["start_location", "budget", "exact_start_time"],
    "clarification_needed": False,
    "clarification_questions": [],
    "assumptions": [
        "未提供起点，默认从澳门半岛出发",
        "未提供预算，默认中等预算"
    ]
}
```

### 枚举建议

relationship_type：

```text
family_with_children
family_with_seniors
couple
friends
solo
business
classmates
mixed_group
general
```

outing_intent：

```text
half_day_outing
dinner_plan
date_plan
photo_citywalk
kid_friendly_play
low_fatigue_relax
celebration
local_experience
rainy_day_plan
indoor_plan
general_outing
```

hard_constraints / soft_preferences：

```text
low_fatigue
short_walking_distance
kid_friendly
senior_friendly
avoid_stairs
indoor_required
photo_friendly
romantic
social
chat_friendly
dinner_together
low_calorie_food
budget_control
avoid_long_queue
surprise_action
local_specialty
```

---

## 四、详细开发步骤

## Phase 1：Schema 和本地验证层

### Task 1.1 创建 goal_schema.py

**Objective:** 定义 structured_goal 的默认结构、允许枚举和基础构造函数。

**Files:**

- Create: `/Users/sara/Document/项目/UM比赛/macau-local-agent-demo/agent/goal_schema.py`
- Create: `/Users/sara/Document/项目/UM比赛/macau-local-agent-demo/tests/test_goal_schema.py`

**核心函数：**

```python
def default_goal(raw_text: str) -> dict
```

**验收：**

```bash
cd /Users/sara/Document/项目/UM比赛/macau-local-agent-demo
python3 -m pytest tests/test_goal_schema.py -v
```

预期：测试通过。

---

### Task 1.2 创建 goal_validator.py

**Objective:** 校验和修正 LLM 输出，避免 total/person/scenario 不一致。

**Files:**

- Create: `agent/goal_validator.py`
- Create: `tests/test_goal_validator.py`

**核心函数：**

```python
def validate_and_normalize_goal(goal: dict) -> dict
```

**必须覆盖的测试：**

1. 2男3女但 total=2 → 修正 total=5。
2. children > 0 但 relationship_type=couple → 修正为 family_with_children。
3. seniors > 0 → 自动加入 senior_friendly / avoid_stairs。
4. relationship_type 不在枚举 → 修正为 general。
5. confidence 缺失 → 默认 0.6。

**验收：**

```bash
python3 -m pytest tests/test_goal_validator.py -v
```

---

### Task 1.3 创建 goal_enricher.py

**Objective:** 根据 validated goal 补全 planning_strategy。

**Files:**

- Create: `agent/goal_enricher.py`
- Create: `tests/test_goal_enricher.py`

**核心函数：**

```python
def enrich_goal(goal: dict) -> dict
```

**规则示例：**

- friends + total=5 → restaurant_table_size_required=5
- family_with_children → max_walking_per_segment_m <= 300
- family_with_seniors → avoid 包含 stairs / long_queue
- couple → preferred 包含 romantic_dinner / surprise_action
- low_fatigue → max_route_duration_per_segment_min <= 20

**验收：**

```bash
python3 -m pytest tests/test_goal_enricher.py -v
```

---

## Phase 2：LLM 解析层

### Task 2.1 创建 llm_goal_parser.py 的 mock 版本

**Objective:** 先不依赖真实 LLM，先用 mock/stub 模拟 LLM 输出，确保链路稳定。

**Files:**

- Create: `agent/llm_goal_parser.py`
- Create: `tests/test_llm_goal_parser.py`

**核心函数：**

```python
def parse_goal_with_llm(user_text: str, use_mock: bool = True) -> dict
```

**mock 行为：**

输入：

```text
今天下午2男3女出去玩，安排一下。
```

输出：

```python
{
    "relationship_type": "friends",
    "outing_intent": "half_day_outing",
    "confidence": 0.9,
    "people": {"total": 5, "male": 2, "female": 3, "children": 0, "seniors": 0},
    ...
}
```

**验收：**

```bash
python3 -m pytest tests/test_llm_goal_parser.py -v
```

---

### Task 2.2 增加真实 LLM Prompt 模板

**Objective:** 加入可复用 prompt，但真实 API 可后接。

**Files:**

- Modify: `agent/llm_goal_parser.py`
- Create: `docs/llm_goal_parser_prompt.md`

**Prompt 原则：**

- 只输出 JSON
- 不生成路线
- 不编造用户没有说的信息
- 缺失信息写入 missing_info
- 不确定时设置 clarification_needed
- 区分 hard_constraints 与 soft_preferences
- relationship_type 和 outing_intent 必须来自枚举

**验收：**

```bash
python3 -m pytest tests/test_llm_goal_parser.py -v
```

---

### Task 2.3 接入真实 LLM 调用，保留 mock fallback

**Objective:** 如果环境配置了 LLM API，就调用真实 LLM；否则回退 mock。

**Files:**

- Modify: `agent/llm_goal_parser.py`
- Modify: `requirements.txt`，按实际 provider 加依赖

**建议接口：**

```python
def parse_goal_with_llm(user_text: str, use_mock: bool = False) -> dict:
    if use_mock or no_api_key:
        return parse_goal_with_mock_llm(user_text)
    return call_real_llm(user_text)
```

**注意：**

真实 LLM 接入时不要直接污染 Planner。必须经过：

```text
parse_goal_with_llm → validate_and_normalize_goal → enrich_goal
```

**验收：**

```bash
python3 -m pytest tests/test_llm_goal_parser.py tests/test_goal_validator.py tests/test_goal_enricher.py -v
```

---

## Phase 3：兼容旧 parser，形成统一入口

### Task 3.1 改造 parser.py 为统一入口

**Objective:** `parse_goal` 继续存在，但内部改为优先走 LLM 结构化解析，再转成旧 Planner 可读字段。

**Files:**

- Modify: `agent/parser.py`
- Create/Modify: `tests/test_parser.py`

**建议接口：**

```python
def parse_structured_goal(user_text: str, use_llm: bool = True) -> dict

def parse_goal(user_text: str) -> dict:
    structured_goal = parse_structured_goal(user_text)
    return adapt_structured_goal_to_legacy_goal(structured_goal)
```

**为什么保留旧 parse_goal：**

- 现有 planner、tools、tests 仍然依赖旧格式。
- 可以逐步迁移，避免一次性大改导致 Demo 不稳定。

**验收：**

```bash
python3 -m pytest tests/test_parser.py -v
python3 -m pytest tests -q
```

---

## Phase 4：Planner/Scorer 消费 structured_goal

### Task 4.1 Planner 读取 planning_strategy

**Objective:** Planner 不只看 scenario，而要看 structured_goal 的策略字段。

**Files:**

- Modify: `agent/planner.py`
- Modify: `tests/test_planner.py`

**新增行为：**

1. friends + total=5 → availability 查询 people_count=5。
2. low_fatigue → 路线中优先低步行/短转场。
3. must_include_rest=True → 时间线里必须出现奶茶/咖啡/休息点。
4. relationship_type=couple → 避免朋友桌游/亲子活动。
5. family_with_seniors → 避免大三巴台阶路线。

**验收：**

```bash
python3 -m pytest tests/test_planner.py -v
```

---

### Task 4.2 Scorer 区分硬约束和软偏好

**Objective:** 让评分更合理，不只是固定场景权重。

**Files:**

- Modify: `agent/scorer.py`
- Modify: `tests/test_scorer.py`

**新增规则：**

- hard_constraints 不满足 → 每项强扣 15-30 分
- soft_preferences 不满足 → 每项轻扣 3-8 分
- planning_strategy 满足 → 加解释理由
- risks 要明确指出违反了哪些约束

**验收：**

```bash
python3 -m pytest tests/test_scorer.py -v
```

---

## Phase 5：Streamlit UI 展示需求拆解

### Task 5.1 UI 增加“LLM 需求拆解”区域

**Objective:** 让评委看到 Agent 是如何理解用户需求的。

**Files:**

- Modify: `app.py`

**展示内容：**

- relationship_type
- outing_intent
- people
- hard_constraints
- soft_preferences
- planning_strategy
- missing_info
- assumptions
- confidence

**验收：**

```bash
python3 -m py_compile app.py agent/*.py
python3 -m streamlit run app.py --server.headless true --server.port 8501
```

再检查：

```bash
python3 - <<'PY'
import urllib.request
with urllib.request.urlopen('http://localhost:8501', timeout=10) as r:
    print(r.status)
PY
```

预期：`200`

---

### Task 5.2 增加低置信度追问展示

**Objective:** 当用户输入太模糊时，不强行规划，而是展示需要追问的问题。

**示例输入：**

```text
下午出去玩一下
```

期望 UI 展示：

```text
我还需要确认：
1. 是一个人、情侣、朋友还是家庭出行？
2. 大概几个人？
3. 希望轻松一点还是可以多走路？
```

**Demo 策略：**

- confidence >= 0.75：直接规划
- 0.45 <= confidence < 0.75：基于假设规划，并显示 assumptions
- confidence < 0.45：先展示 clarification_questions

**验收：**

- 模糊输入能出现追问。
- 明确信息输入能直接规划。

---

## Phase 6：最终端到端验证

### Task 6.1 增加端到端测试用例

**Files:**

- Create: `tests/test_structured_goal_e2e.py`

**测试输入：**

1. `今天下午2男3女出去玩，安排一下。`
2. `我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。`
3. `今天下午想和对象约会，浪漫一点但别太累。`
4. `带5岁孩子玩几个小时，老婆想吃低卡一点。`
5. `下午出去玩一下。`

**验收重点：**

- 2男3女 → friends, total=5
- 爸妈 → family_with_seniors, avoid_stairs
- 对象约会 → couple, romantic, low_fatigue
- 孩子老婆 → family_with_children, kid_friendly, low_calorie_food
- 模糊输入 → clarification_needed=True

**验收：**

```bash
python3 -m pytest tests/test_structured_goal_e2e.py -v
python3 -m pytest tests -q
```

---

### Task 6.2 最终 smoke test

**命令：**

```bash
cd /Users/sara/Document/项目/UM比赛/macau-local-agent-demo
python3 -m pytest tests -v
python3 -m py_compile app.py agent/*.py
python3 - <<'PY'
from agent.planner import plan_day

cases = [
    '今天下午2男3女出去玩，安排一下。',
    '我爸妈来澳门，想带他们轻松逛逛，不要爬楼梯。',
    '今天下午想和对象约会，浪漫一点但别太累。',
    '带5岁孩子玩几个小时，老婆想吃低卡一点。',
]
for text in cases:
    result = plan_day(text)
    print(text)
    print(result['goal'])
    print(result['best_plan']['title'], result['best_plan']['score']['score'])
    assert result['best_plan']['timeline']
    assert result['tool_steps']
print('structured goal final smoke test ok')
PY
```

预期：

```text
structured goal final smoke test ok
```

---

## 五、推荐实际执行顺序

如果要最稳，我建议这样排：

### 第一天上午

1. `goal_schema.py`
2. `goal_validator.py`
3. `goal_enricher.py`
4. 完成所有 schema/validator/enricher 测试

### 第一天下午

5. `llm_goal_parser.py` mock 版本
6. LLM prompt 文档
7. parser.py 统一入口
8. 保证旧 tests 全部通过

### 第二天上午

9. Planner 读取 structured_goal
10. Scorer 区分硬约束和软偏好
11. 增加 2男3女、爸妈、带孩子、情侣、模糊输入测试

### 第二天下午

12. Streamlit UI 增加需求拆解展示
13. 低置信度追问展示
14. README/design.md 更新
15. 最终 smoke test 和演示话术

---

## 六、每一步开发后的检查标准

每完成一个功能，必须至少跑：

```bash
python3 -m pytest 对应测试文件 -v
```

每完成一个阶段，必须跑：

```bash
python3 -m pytest tests -q
python3 -m py_compile app.py agent/*.py
```

涉及 UI 的阶段，必须跑：

```bash
python3 -m streamlit run app.py --server.headless true --server.port 8501
```

并确认页面返回 200。

---

## 七、第一步应该做什么

第一步不是马上接真实 LLM，而是：

```text
Phase 1 / Task 1.1：创建 goal_schema.py 和 tests/test_goal_schema.py
```

原因：

1. Schema 是 LLM 输出的约束基础。
2. 没有 Schema，LLM 输出会散，后续 Planner 很难稳定消费。
3. Schema 可以先本地测试，不依赖 API key。
4. 后续 validator、enricher、Planner、UI 都围绕这个结构展开。

第一步完成后的验收命令：

```bash
cd /Users/sara/Document/项目/UM比赛/macau-local-agent-demo
python3 -m pytest tests/test_goal_schema.py -v
```

只有这个通过后，再进入 validator。

---

## 八、最终 Demo 展示效果

用户输入：

```text
今天下午2男3女出去玩，安排一下。
```

页面先展示：

```text
LLM 需求拆解：
- 人群关系：朋友聚会
- 人数：5人，2男3女
- 出行目的：半日休闲
- 硬约束：无明显硬约束
- 软偏好：社交、拍照、晚餐
- 规划策略：5人桌、奶茶休息、拍照点、聚餐餐厅
- 缺失信息：起点、预算、具体开始时间
- 默认假设：从澳门半岛出发，中等预算，下午2点开始
```

然后再展示：

```text
议事亭前地 → 玫瑰圣母堂 → 茶语澳门低糖奶茶 → 澳门城市展览空间 → 氹仔葡式小馆
```

并解释：

- 适合 5 人朋友局
- 有拍照点
- 中间有休息
- 餐厅支持 5 人聚餐
- 路线不明显折返

这样 Demo 会比现在更合理，也更像真正的本地生活 Agent。
