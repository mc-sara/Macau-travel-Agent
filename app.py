import streamlit as st

from agent.executor import execute_plan
from agent.planner import plan_day


EXAMPLES = {
    "亲子家庭": "今天下午想和老婆孩子出去玩几个小时，别离家太远。",
    "朋友聚会": "今天下午和朋友4个人出去玩，2男2女，安排一下。",
    "情侣约会": "今天下午想和对象约会，浪漫一点但别太累。",
}


st.set_page_config(page_title="澳游半日管家 Agent", page_icon="🇲🇴", layout="wide")
st.title("🇲🇴 澳游半日管家 Agent")
st.caption("一句话输入目标，Agent 自动规划澳门半日吃喝玩路线，并模拟预约、订位、点单和消息通知。")

if "user_text" not in st.session_state:
    st.session_state.user_text = EXAMPLES["亲子家庭"]
if "plan_result" not in st.session_state:
    st.session_state.plan_result = None
if "execution_result" not in st.session_state:
    st.session_state.execution_result = None

with st.sidebar:
    st.header("输入需求")
    for label, text in EXAMPLES.items():
        if st.button(label, use_container_width=True):
            st.session_state.user_text = text
            st.session_state.plan_result = None
            st.session_state.execution_result = None

    user_text = st.text_area("一句话告诉 Agent 你的目标", value=st.session_state.user_text, height=120)
    st.session_state.user_text = user_text

    if st.button("开始规划", type="primary", use_container_width=True):
        st.session_state.plan_result = plan_day(user_text)
        st.session_state.execution_result = None


def show_goal(goal):
    st.subheader("1. 需求解析")
    structured = goal.get("structured_goal", {})
    cols = st.columns(4)
    cols[0].metric("场景", goal["scenario"])
    cols[1].metric("时长", f"{goal['duration_hours']}小时")
    cols[2].metric("人数", goal.get("people", {}).get("total", "-") )
    cols[3].metric("起点", goal.get("origin", "家"))
    st.write("偏好：", "、".join(goal.get("preferences", [])))

    if structured:
        with st.expander("LLM 需求拆解结果", expanded=True):
            top_cols = st.columns(3)
            top_cols[0].metric("人群关系", structured.get("relationship_type", "-"))
            top_cols[1].metric("出行目的", structured.get("outing_intent", "-"))
            top_cols[2].metric("置信度", structured.get("confidence", "-"))
            st.markdown("**人数结构**")
            st.json(structured.get("people", {}))
            st.markdown("**硬约束**")
            st.write("、".join(structured.get("hard_constraints", [])) or "无")
            st.markdown("**软偏好**")
            st.write("、".join(structured.get("soft_preferences", [])) or "无")
            st.markdown("**规划策略**")
            st.json(structured.get("planning_strategy", {}))
            st.markdown("**缺失信息 / 默认假设**")
            st.write("缺失信息：", "、".join(structured.get("missing_info", [])) or "无")
            st.write("默认假设：", "、".join(structured.get("assumptions", [])) or "无")


def show_tool_steps(tool_steps):
    st.subheader("2. Agent 工具调用链路")
    for index, step in enumerate(tool_steps, start=1):
        with st.expander(f"Step {index}: {step['tool']} ✅", expanded=index <= 2):
            st.write(step["summary"])
            st.json(step)


def show_plan(plan):
    st.subheader("3. 推荐方案")
    st.markdown(f"### {plan['title']}")
    st.metric("综合评分", f"{plan['score']['score']} 分")

    col_left, col_right = st.columns([1.2, 1])
    with col_left:
        st.markdown("#### 时间线")
        for step in plan["timeline"]:
            st.write(f"**{step['time']}**  {step['name']}")

        st.markdown("#### 路线导航 Mock API")
        for route in plan["routes"]:
            st.write(
                f"{route['origin']} → {route['destination']}："
                f"{route['duration_min']}分钟，{route['route_distance_km']}km，"
                f"步行{route['walking_distance_m']}m。{route['route_summary']}"
            )

    with col_right:
        st.markdown("#### 推荐理由")
        for reason in plan["score"]["reasons"]:
            st.success(reason)

        st.markdown("#### 风险提示")
        risks = plan["score"].get("risks", [])
        if risks:
            for risk in risks:
                st.warning(risk)
        else:
            st.info("暂无明显风险。")

        st.markdown("#### 预算")
        budget = plan.get("budget", {})
        st.write(f"预计总预算：{budget.get('currency', 'MOP')} {budget.get('estimated_total', '-')}")

    st.markdown("#### 可执行性检查")
    for item in plan.get("availability", []):
        if item.get("available"):
            st.success(f"{item.get('name')}：{item.get('message')}，排队 {item.get('queue_minutes', 0)} 分钟")
        else:
            st.error(f"{item.get('name', item.get('item_id'))}：不可用")


def show_execution(execution):
    st.subheader("4. 执行结果")
    for booking in execution["bookings"]:
        st.success(f"{booking['type']} | {booking['order_id']} | {booking['message']}")
    st.markdown("#### 可发送消息")
    st.info(execution["final_message"])


result = st.session_state.plan_result
if result is None:
    st.info("请在左侧输入需求，然后点击“开始规划”。")
else:
    show_goal(result["goal"])
    if result.get("clarification_needed"):
        st.warning("当前输入信息较少，Agent 已基于默认假设生成轻量方案。建议补充以下信息后规划会更准确：")
        for question in result.get("clarification_questions", []):
            st.write(f"- {question}")
    show_tool_steps(result["tool_steps"])
    show_plan(result["best_plan"])

    st.divider()
    if st.button("确认并安排", type="primary"):
        st.session_state.execution_result = execute_plan(result["best_plan"], result["goal"])

    if st.session_state.execution_result:
        show_execution(st.session_state.execution_result)

    if result.get("alternatives"):
        with st.expander("备选方案"):
            for plan in result["alternatives"]:
                st.write(f"{plan['title']}：{plan['score']['score']} 分")
                st.write(" → ".join(step["name"] for step in plan["timeline"]))
