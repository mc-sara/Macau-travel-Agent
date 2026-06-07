# 澳游半日管家 Agent Demo

基于澳门本地景点数据、Mock 地图路线 API 和 Mock 商户数据的本地生活 Agent Demo。

本仓库上传的是之前已经跑通的 Streamlit 用户版：`user_app.py`。
原来的 `app.py` 保留为开发/测试展示页。

用户输入一句自然语言，系统会自动完成：

1. 使用 LLM/Mock LLM 做人类语言需求拆解：人群关系、出行目的、人数、硬约束、软偏好、缺失信息
2. 通过 Schema Validator 修正人数、关系类型和枚举字段
3. 通过 Goal Enricher 补全规划策略：低疲劳、餐桌人数、休息点、避让策略
4. 查询景点和本地商户
5. 调用 Mock 地图 API 判断路线距离、时间、步行量
6. 根据用户类型、硬约束和软偏好进行可解释评分
7. 生成澳门半日吃喝玩路线
8. 点击确认后模拟预约、订位、点单和消息通知

## 技术栈

- Python
- Streamlit
- pandas
- openpyxl
- pytest
- 本地 Excel / JSON Mock 数据

## 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

## 启动用户版 Demo

```bash
python3 -m streamlit run user_app.py --server.port 8502
```

然后打开：

```text
http://localhost:8502
```

## 启动开发/测试版 Demo

```bash
python3 -m streamlit run app.py --server.port 8501
```

然后打开：

```text
http://localhost:8501
```

## 示例输入

### 朋友密室

```text
我们几个朋友出去玩，5个人，有男有女，想去密室。
```

系统会识别为朋友组队室内活动，并推荐密室路线；如果只说“有男有女”但没有给出几男几女，会提示：

```text
请补充男女各有几个人？
```

### 朋友聚会：2男3女

```text
今天下午2男3女想玩密室，顺便吃饭，别太贵。
```

推荐路线会包含：

```text
澳门悬疑密室体验馆
```

### 亲子家庭

```text
今天下午想和老婆孩子出去玩几个小时，别离家太远。
```

### 情侣约会

```text
今天下午想和对象约会，浪漫一点但别太累。
```

### 带长辈

```text
今天下午带爸妈轻松逛逛，不要爬楼梯。
```

## 项目结构

```text
Macau-travel-Agent/
  user_app.py          # 用户版 Streamlit 页面
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
python3 -m py_compile app.py user_app.py agent/*.py
python3 -m pytest tests -q
```

## Demo 展示重点

这个 Demo 不是普通景点推荐系统，而是一个本地生活任务执行 Agent。

它强调：

- 能用 LLM/Mock LLM 拆解自然语言里的关系、人数、目的、硬约束和软偏好
- 能理解用户类型和约束，并通过 Validator / Enricher 做校验和补全
- 不只看景点热度，而是考虑疲劳、台阶、步行、排队、路线转场
- 使用 Mock 地图 API 展示导航距离和时间
- 使用评分解释说明为什么这个方案合理
- 用户确认后模拟执行预约、订位、点单、消息通知
