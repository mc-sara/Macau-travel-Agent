# 银龄澳门本地生活 Agent Demo

面向澳门长者及陪同家属的本地生活 Agent Demo。系统把一句自然语言需求转成可解释、低疲劳、便于执行的半日安排，并用 Mock QwenPaw 执行层模拟订位、点单、三句话路线卡和家属通知。

本仓库已经从早期多场景本地生活 Demo 收敛为“银龄澳门本地生活 Agent”。当前重点不是泛娱乐场景推荐，而是围绕长者真实出行痛点：少步行、不爬楼梯、有座椅/厕所、路线简单、餐饮清淡、家属容易理解和确认。

## 核心定位

一句话定位：

> 一个面向澳门长者及陪同家属的本地生活 Agent：解析长者出行需求，生成低疲劳可解释路线，并通过 QwenPaw 模拟完成订位、点单和路线卡通知。

典型输入：

```text
我想带爸妈下午轻松逛逛，不想爬楼梯，最好有地方坐，晚上吃点清淡的。
```

系统会优先满足：

- 长者友好、低疲劳、短步行
- 避开楼梯、陡坡、长队和复杂换乘
- 优先考虑座椅、厕所、室内/阴凉点位
- 餐饮偏清淡，可备注少油少盐、少糖少冰
- 输出适合家属转发和长者阅读的路线卡

## 当前可运行入口

1. `user_compact.html` + `web_server.py`
   - 推荐展示入口
   - 紧凑 HTML 单页
   - 使用 Python 标准库后端
   - 真实调用 `/api/plan` 和 `/api/execute`

2. `user_app.py`
   - Streamlit 用户版
   - 保留作开发和对照展示

3. `app.py`
   - Streamlit 开发/测试页

## 系统流程

用户输入一句自然语言后，系统会自动完成：

1. 使用 LLM/Mock LLM 拆解长者出行需求：陪同关系、人数、长者人数、时间、区域、步行/楼梯/休息/饮食约束
2. 通过 Schema Validator 修正人数、关系类型和枚举字段
3. 通过 Goal Enricher 补全适老规划策略：低疲劳、短步行、必须休息、避开楼梯、清淡餐饮、厕所/座椅优先
4. 查询澳门本地景点、无障碍信息、路线和商户 Mock 数据
5. 调用 Mock 地图 API 判断路线距离、时间和步行量
6. 按长者友好度、交通便利度、低疲劳程度、休息/厕所支持和执行可行性进行可解释评分
7. 生成澳门银龄半日路线和备选方案
8. 用户确认后模拟 QwenPaw 执行：餐厅订位、少油少盐/少糖少冰备注、路线卡和家属通知

## 快速启动

### 1. 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

`web_server.py` 使用 Python 标准库 `http.server`，不需要额外安装 Flask/FastAPI。

### 2. 启动推荐 HTML 用户版

```bash
python3 web_server.py
```

打开：

```text
http://127.0.0.1:8765/
```

### 3. 启动 Streamlit 用户版

```bash
python3 -m streamlit run user_app.py --server.port 8502
```

打开：

```text
http://localhost:8502
```

### 4. 启动开发/测试版

```bash
python3 -m streamlit run app.py --server.port 8501
```

打开：

```text
http://localhost:8501
```

## API

### `GET /`

返回 HTML 用户页。

### `GET /health`

返回：

```json
{"status": "ok"}
```

### `POST /api/plan`

请求：

```json
{
  "user_text": "我想带爸妈下午轻松逛逛，不想爬楼梯，最好有地方坐，晚上吃点清淡的。"
}
```

返回结构：

```json
{
  "status": "success",
  "result": {
    "goal": {},
    "best_plan": {},
    "alternatives": []
  }
}
```

### `POST /api/execute`

请求：

```json
{
  "user_text": "我想带爸妈下午轻松逛逛，不想爬楼梯，最好有地方坐，晚上吃点清淡的。",
  "plan_id": "senior_main",
  "plan_result": {}
}
```

返回结构：

```json
{
  "status": "success",
  "selected_plan_id": "senior_main",
  "selected_plan": {},
  "execution": {}
}
```

`plan_result` 是可选字段。前端会传入它，避免执行时重新规划导致用户选择的方案不一致。

## 示例输入

### 带爸妈低疲劳半日出行

```text
我想带爸妈下午轻松逛逛，不想爬楼梯，最好有地方坐，晚上吃点清淡的。
```

### 长者需要厕所和休息点

```text
下午带爷爷奶奶在澳门走走，路不要太长，中途最好有厕所和座椅。
```

### 雨天室内适老路线

```text
如果下午下雨，想带妈妈找室内地方慢慢逛，少走路，晚饭不要太油。
```

### 轮椅/电梯优先

```text
外婆走路慢，最好全程有电梯或无障碍通道，可以安排一条轻松路线吗？
```

## 项目结构

```text
Macau-travel-Agent/
  web_server.py        # 标准库 HTTP 后端，提供 HTML 页面和 /api/plan、/api/execute
  user_compact.html    # 紧凑 HTML 用户版
  user_app.py          # Streamlit 用户版
  app.py               # 开发/测试版 Streamlit 页面
  requirements.txt
  README.md
  agent/               # 解析、规划、评分、执行逻辑
  data/                # 澳门景点、交通、商户 Mock 数据
  docs/                # 设计文档和 Prompt 文档
  scripts/             # 测试脚本
  tests/               # pytest 回归测试
```

## 本地验证

```bash
python3 -m py_compile web_server.py app.py user_app.py agent/*.py tests/*.py scripts/test_real_llm_cases.py
python3 -m pytest tests -q
```

当前全量测试基线：

```text
74 passed
```

HTML/API 版本可额外验证：

```bash
python3 -m pytest tests/test_web_server.py -v
```

## Demo 展示重点

这个 Demo 不是普通景点推荐系统，而是一个面向银龄场景的本地生活任务执行 Agent。

它强调：

- 能用 LLM/Mock LLM 拆解自然语言里的长者、陪同人、人数、时间、区域、硬约束和软偏好
- 能通过 Validator / Enricher 把模糊需求稳定补全为适老规划策略
- 不以景点热度、拍照价值或社交氛围为主，而是优先考虑疲劳、台阶、步行、排队、厕所、座椅、交通换乘和清淡饮食
- 使用 Mock 地图 API 展示导航距离和时间
- 使用评分解释说明为什么这个方案更适合长者
- 用户确认后由 Mock QwenPaw 执行层模拟订位、点单备注、三句话路线卡和家属通知

## QwenPaw 执行层说明

QwenPaw 在本 Demo 中是执行层助手，不是路线规划大脑。

规划由 Agent 完成，QwenPaw 负责在用户确认后模拟执行：

- 清淡餐厅订位
- 少油少盐/少糖少冰点单备注
- 生成适合长者阅读的三句话路线卡
- 生成家属通知文案
- 返回 Mock 执行状态

## 注意

- 这是比赛/演示用本地 Demo，商户、路线、预约、点单和消息发送均为 Mock 数据。
- 不要把 `.env` 或真实 API key 提交到仓库。
- 如需接入真实 ASR/TTS、微信、地图、商户订位或 SIP 电话，应作为后续阶段单独实现。
