import time
from typing import Any, Dict, List, Optional

import streamlit as st

from agent.executor import execute_plan
from agent.planner import plan_day


EXAMPLES = {
    "朋友密室": "今天下午2男3女想玩密室，顺便吃饭，别太贵。",
    "亲子轻松玩": "今天下午想和老婆孩子出去玩几个小时，别离家太远。",
    "情侣约会": "今天下午想和对象约会，浪漫一点但别太累。",
    "带爸妈低疲劳": "今天下午带爸妈在澳门轻松逛逛，不要爬楼梯，想吃本地特色。",
}

SCENARIO_LABELS = {
    "family": "家庭 / 亲子 / 长辈",
    "friends": "朋友结伴",
    "couple": "情侣约会",
    "general": "普通出行",
}

PREFERENCE_LABELS = {
    "escape_room": "密室 / 剧本杀",
    "indoor_activity": "室内活动",
    "social": "适合聊天聚会",
    "photo_friendly": "适合拍照",
    "dinner_together": "一起吃饭",
    "chat_friendly": "适合聊天",
    "kid_friendly": "适合小朋友",
    "senior_friendly": "适合长辈",
    "low_fatigue": "不要太累",
    "low_calorie": "低卡饮食",
    "low_calorie_food": "低卡饮食",
    "avoid_stairs": "避免楼梯",
    "romantic": "浪漫氛围",
    "surprise_action": "惊喜安排",
    "short_walking_distance": "少走路",
    "local_specialty": "本地特色",
    "budget_control": "控制预算",
}


st.set_page_config(
    page_title="澳游半日管家",
    page_icon="🇲🇴",
    layout="wide",
    initial_sidebar_state="collapsed",
)


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&display=swap');

:root {
    --brand: #ff385c;
    --brand-dark: #e00b41;
    --ink: #222222;
    --muted: #6a6a6a;
    --soft: #fff7f3;
    --line: #eeeeee;
    --green: #0f766e;
    --card-shadow: rgba(0,0,0,0.02) 0px 0px 0px 1px, rgba(0,0,0,0.04) 0px 2px 6px, rgba(0,0,0,0.10) 0px 4px 8px;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(255, 56, 92, 0.10), transparent 34%),
        linear-gradient(180deg, #ffffff 0%, #fffaf7 46%, #ffffff 100%);
    color: var(--ink);
}

.main .block-container {
    max-width: 1180px;
    padding-top: 32px;
    padding-bottom: 56px;
}

.hero-card, .section-card, .plan-card, .confirm-card, .execution-card {
    background: rgba(255,255,255,0.97);
    border: 1px solid rgba(0,0,0,0.04);
    box-shadow: var(--card-shadow);
}

.hero-card {
    border-radius: 32px;
    padding: 34px 36px;
    margin-bottom: 22px;
}

.hero-kicker {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 999px;
    background: #fff0f3;
    color: var(--brand-dark);
    font-weight: 800;
    font-size: 13px;
    margin-bottom: 14px;
}

.hero-title {
    font-size: 44px;
    line-height: 1.06;
    letter-spacing: -0.8px;
    font-weight: 900;
    color: var(--ink);
    margin: 0 0 12px;
}

.hero-subtitle {
    color: var(--muted);
    font-size: 17px;
    line-height: 1.6;
    max-width: 780px;
    margin-bottom: 0;
}

.section-card, .plan-card, .confirm-card, .execution-card {
    border-radius: 24px;
    padding: 24px;
    margin-bottom: 18px;
}

.section-title {
    font-size: 22px;
    font-weight: 900;
    letter-spacing: -0.35px;
    color: var(--ink);
    margin: 0 0 6px;
}

.section-desc {
    color: var(--muted);
    font-size: 14px;
    margin: 0 0 16px;
}

.step-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 30px;
    height: 30px;
    border-radius: 50%;
    background: var(--brand);
    color: #ffffff;
    font-weight: 900;
    margin-right: 8px;
}

.helper-note {
    border-left: 4px solid var(--brand);
    background: #fff7f3;
    border-radius: 14px;
    padding: 14px 16px;
    color: #4a2a2a;
    font-size: 14px;
    line-height: 1.55;
}

.metric-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    padding: 8px 12px;
    background: #f7f7f7;
    color: #222222;
    margin: 4px 6px 4px 0;
    font-weight: 700;
    font-size: 13px;
}

.pref-chip {
    display: inline-flex;
    border-radius: 999px;
    padding: 7px 11px;
    background: #fff0f3;
    color: #b32505;
    margin: 4px 6px 4px 0;
    font-weight: 800;
    font-size: 12px;
}

.timeline-row {
    display: flex;
    gap: 14px;
    align-items: flex-start;
    padding: 12px 0;
    border-bottom: 1px solid #f0f0f0;
}

.timeline-time {
    min-width: 58px;
    color: var(--brand-dark);
    font-weight: 900;
}

.timeline-name {
    color: var(--ink);
    font-weight: 800;
}

.route-line {
    padding: 10px 0;
    border-bottom: 1px dashed #e7e7e7;
    color: #444444;
    font-size: 14px;
    line-height: 1.5;
}

.reason-box {
    border-radius: 16px;
    background: #f3fbf9;
    color: #0f4f49;
    padding: 12px 14px;
    margin-bottom: 10px;
    font-weight: 700;
    line-height: 1.5;
}

.risk-box {
    border-radius: 16px;
    background: #fff7ed;
    color: #9a3412;
    padding: 12px 14px;
    margin-bottom: 10px;
    font-weight: 700;
    line-height: 1.5;
}

.selected-badge {
    display: inline-flex;
    background: #222222;
    color: #ffffff;
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 900;
    margin-left: 8px;
}

.plan-title {
    font-size: 24px;
    font-weight: 900;
    letter-spacing: -0.35px;
    margin: 0 0 8px;
}

.small-muted {
    color: var(--muted);
    font-size: 13px;
}

.stButton > button {
    border-radius: 999px !important;
    font-weight: 800 !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    box-shadow: none !important;
}

.stButton > button[kind="primary"] {
    background: var(--brand) !important;
    border-color: var(--brand) !important;
    color: white !important;
}

textarea {
    border-radius: 18px !important;
}

@media (max-width: 900px) {
    .hero-title { font-size: 34px; }
    .hero-card { padding: 26px 22px; border-radius: 26px; }
}
</style>
"""


st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


if "user_text" not in st.session_state:
    st.session_state.user_text = EXAMPLES["朋友密室"]
if "plan_result" not in st.session_state:
    st.session_state.plan_result = None
if "selected_plan_id" not in st.session_state:
    st.session_state.selected_plan_id = None
if "execution_result" not in st.session_state:
    st.session_state.execution_result = None


def preference_label(pref: str) -> str:
    return PREFERENCE_LABELS.get(pref, pref)


def all_plans(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not result:
        return []
    return [result["best_plan"]] + result.get("alternatives", [])


def selected_plan(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    plans = all_plans(result)
    if not plans:
        return None
    selected_id = st.session_state.get("selected_plan_id")
    for plan in plans:
        if plan.get("id") == selected_id:
            return plan
    st.session_state.selected_plan_id = result["best_plan"].get("id")
    return result["best_plan"]


def run_analysis(user_text: str) -> Dict[str, Any]:
    progress = st.progress(0, text="正在理解你的需求...")
    steps = [
        (18, "正在识别人数、男女比例和出行关系..."),
        (42, "正在提取活动偏好、预算和低疲劳要求..."),
        (68, "正在匹配澳门路线、活动、餐厅和可预约时间..."),
        (92, "正在生成推荐方案和备选方案..."),
    ]
    for value, text in steps:
        time.sleep(0.12)
        progress.progress(value, text=text)
    result = plan_day(user_text)
    progress.progress(100, text="分析完成，已生成推荐方案。")
    time.sleep(0.12)
    progress.empty()
    return result


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-kicker">🇲🇴 澳门本地生活 Agent</div>
            <h1 class="hero-title">一句话，安排今天的澳门半日行程</h1>
            <p class="hero-subtitle">
                告诉我你想和谁去、几个人、想玩什么。系统会帮你理解需求、确认关键信息，
                再推荐可执行的路线、活动、餐厅和预约安排。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_input() -> None:
    st.markdown(
        """
        <div class="section-card">
            <h2 class="section-title"><span class="step-pill">1</span>告诉我你今天想怎么玩</h2>
            <p class="section-desc">可以直接说自然语言，例如“2男3女想玩密室，顺便吃饭，别太贵”。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    input_col, tip_col = st.columns([1.35, 0.85], gap="large")
    with input_col:
        user_text = st.text_area(
            "你的需求",
            value=st.session_state.user_text,
            height=150,
            placeholder="例如：今天下午2男3女想玩密室，顺便吃饭，别太贵。",
            label_visibility="collapsed",
        )
        st.session_state.user_text = user_text

        st.caption("快速示例")
        example_cols = st.columns(4)
        for index, (label, text) in enumerate(EXAMPLES.items()):
            if example_cols[index].button(label, use_container_width=True):
                st.session_state.user_text = text
                st.session_state.plan_result = None
                st.session_state.selected_plan_id = None
                st.session_state.execution_result = None
                st.rerun()

        if st.button("开始规划", type="primary", use_container_width=True):
            st.session_state.plan_result = run_analysis(st.session_state.user_text)
            st.session_state.selected_plan_id = st.session_state.plan_result["best_plan"].get("id")
            st.session_state.execution_result = None
            st.rerun()

    with tip_col:
        st.markdown(
            """
            <div class="helper-note">
                <b>建议补充这些信息：</b><br>
                1. 几个人，男女各几个<br>
                2. 和谁去：朋友 / 情侣 / 亲子 / 父母<br>
                3. 想玩什么：密室、拍照、亲子、浪漫约会<br>
                4. 特别要求：不要太累、低卡、预算、室内优先
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_confirmation(result: Dict[str, Any]) -> None:
    goal = result["goal"]
    structured = goal.get("structured_goal", {})
    people = goal.get("people", {})
    preferences = goal.get("preferences", [])

    st.markdown(
        """
        <div class="confirm-card">
            <h2 class="section-title"><span class="step-pill">2</span>确认你的需求</h2>
            <p class="section-desc">我已经先帮你理解了一遍。如果不准确，可以修改上方输入后重新规划。</p>
        """,
        unsafe_allow_html=True,
    )

    chips = [
        f"出行类型：{SCENARIO_LABELS.get(goal.get('scenario'), goal.get('scenario', '-'))}",
        f"总人数：{people.get('total', '-')}人",
        f"男生：{people.get('male', 0)}人",
        f"女生：{people.get('female', 0)}人",
        f"儿童：{people.get('children', 0)}人",
        f"长辈：{people.get('seniors', 0)}人",
        f"时长：{goal.get('duration_hours', '-')}小时",
        f"起点：{goal.get('origin', '家')}",
    ]
    st.markdown("".join(f"<span class='metric-chip'>{chip}</span>" for chip in chips), unsafe_allow_html=True)

    if preferences:
        st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
        st.markdown(
            "".join(f"<span class='pref-chip'>{preference_label(pref)}</span>" for pref in preferences),
            unsafe_allow_html=True,
        )

    if result.get("clarification_needed") or structured.get("clarification_needed"):
        st.warning("还差一点信息，补充后方案会更准确：")
        for question in result.get("clarification_questions", structured.get("clarification_questions", [])):
            st.write(f"- {question}")
    else:
        st.success("关键信息已经足够，我会基于这些需求生成可执行方案。")

    missing_info = structured.get("missing_info", [])
    assumptions = structured.get("assumptions", [])
    if missing_info or assumptions:
        with st.expander("默认假设 / 可补充信息", expanded=False):
            if missing_info:
                st.write("可补充：", "、".join(missing_info))
            if assumptions:
                st.write("默认假设：", "、".join(assumptions))

    st.markdown("</div>", unsafe_allow_html=True)


def render_plan_details(plan: Dict[str, Any], compact: bool = False) -> None:
    timeline_col, reason_col = st.columns([1.1, 0.9], gap="large")
    with timeline_col:
        st.markdown("#### 行程时间线")
        for step in plan.get("timeline", []):
            st.markdown(
                f"""
                <div class="timeline-row">
                    <div class="timeline-time">{step.get('time', '')}</div>
                    <div class="timeline-name">{step.get('name', '')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not compact:
            st.markdown("#### 路线导航")
            for route in plan.get("routes", []):
                st.markdown(
                    f"""
                    <div class="route-line">
                        <b>{route.get('origin')} → {route.get('destination')}</b><br>
                        {route.get('duration_min')}分钟，{route.get('route_distance_km')}km，步行{route.get('walking_distance_m')}m。{route.get('route_summary')}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with reason_col:
        st.markdown("#### 为什么这样安排")
        for reason in plan.get("score", {}).get("reasons", []):
            st.markdown(f"<div class='reason-box'>{reason}</div>", unsafe_allow_html=True)

        st.markdown("#### 预算与可执行性")
        budget = plan.get("budget", {})
        st.markdown(
            f"<span class='metric-chip'>预计总预算：{budget.get('currency', 'MOP')} {budget.get('estimated_total', '-')}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span class='metric-chip'>综合评分：{plan.get('score', {}).get('score', '-')} 分</span>",
            unsafe_allow_html=True,
        )

        for item in plan.get("availability", []):
            if item.get("available"):
                st.success(f"{item.get('name')}：{item.get('message')}，排队 {item.get('queue_minutes', 0)} 分钟")
            else:
                st.error(f"{item.get('name', item.get('item_id'))}：不可用")

        risks = plan.get("score", {}).get("risks", [])
        if risks:
            st.markdown("#### 风险提示")
            for risk in risks:
                st.markdown(f"<div class='risk-box'>{risk}</div>", unsafe_allow_html=True)


def render_plan_selector(result: Dict[str, Any]) -> None:
    current = selected_plan(result)
    if current is None:
        return

    st.markdown(
        """
        <div class="plan-card">
            <h2 class="section-title"><span class="step-pill">3</span>推荐方案</h2>
            <p class="section-desc">你可以直接使用推荐方案，也可以改选下面的备选方案。</p>
        """,
        unsafe_allow_html=True,
    )

    selected_badge = "<span class='selected-badge'>当前选择</span>" if current.get("id") == result["best_plan"].get("id") else ""
    st.markdown(f"<div class='plan-title'>{result['best_plan']['title']}{selected_badge}</div>", unsafe_allow_html=True)
    render_plan_details(result["best_plan"])
    if st.button("选择推荐方案", type="primary", use_container_width=True, key="select_best_plan"):
        st.session_state.selected_plan_id = result["best_plan"].get("id")
        st.session_state.execution_result = None
        st.rerun()

    alternatives = result.get("alternatives", [])
    if alternatives:
        st.markdown("#### 备选方案")
        for index, plan in enumerate(alternatives, start=1):
            is_selected = current.get("id") == plan.get("id")
            with st.expander(f"备选 {index}：{plan.get('title')} · {plan.get('score', {}).get('score')} 分" + (" · 当前选择" if is_selected else ""), expanded=is_selected):
                st.write(" → ".join(step.get("name", "") for step in plan.get("timeline", [])))
                st.caption("推荐理由：" + " / ".join(plan.get("score", {}).get("reasons", [])[:2]))
                if st.button("改用这个备选方案", use_container_width=True, key=f"select_alt_{plan.get('id')}"):
                    st.session_state.selected_plan_id = plan.get("id")
                    st.session_state.execution_result = None
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_execution(result: Dict[str, Any]) -> None:
    plan = selected_plan(result)
    if plan is None:
        return

    st.markdown(
        """
        <div class="execution-card">
            <h2 class="section-title"><span class="step-pill">4</span>开始执行安排</h2>
            <p class="section-desc">执行会模拟预约活动、订餐厅、提前点饮品/礼物，并生成同行通知消息。</p>
        """,
        unsafe_allow_html=True,
    )
    st.info(f"当前已选择：{plan.get('title')} · {plan.get('score', {}).get('score')} 分")

    if st.button("开始执行安排", type="primary", use_container_width=True):
        status = st.status("正在执行安排...", expanded=True)
        status.write("检查活动可预约时间")
        time.sleep(0.12)
        status.write("模拟活动预约和餐厅订位")
        time.sleep(0.12)
        status.write("生成同行通知消息")
        st.session_state.execution_result = execute_plan(plan, result["goal"])
        status.update(label="执行完成", state="complete", expanded=False)
        st.rerun()

    execution = st.session_state.get("execution_result")
    if execution:
        st.success("已完成以下安排")
        for booking in execution.get("bookings", []):
            st.markdown(
                f"<div class='reason-box'><b>{booking.get('type')}</b> · {booking.get('order_id')}<br>{booking.get('message')}</div>",
                unsafe_allow_html=True,
            )
        st.markdown("#### 可发送给同行人的消息")
        st.info(execution.get("final_message", ""))

    st.markdown("</div>", unsafe_allow_html=True)


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="section-card">
            <h2 class="section-title"><span class="step-pill">2</span>等待开始规划</h2>
            <p class="section-desc">点击“开始规划”后，我会依次完成需求理解、信息确认、方案推荐和执行安排。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    preview_cols = st.columns(4)
    preview_items = [
        ("理解需求", "识别人数、关系、偏好"),
        ("确认信息", "缺什么就问得更具体"),
        ("推荐方案", "路线、理由、预算、可预约"),
        ("开始执行", "模拟预约、订位、点单"),
    ]
    for col, (title, desc) in zip(preview_cols, preview_items):
        with col:
            st.markdown(f"**{title}**")
            st.caption(desc)


render_hero()
render_input()

if st.session_state.plan_result is None:
    render_empty_state()
else:
    render_confirmation(st.session_state.plan_result)
    render_plan_selector(st.session_state.plan_result)
    render_execution(st.session_state.plan_result)
