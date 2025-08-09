import streamlit as st
from nutrition_agent import NutritionAgent
import time
import ast  # 用于安全地将字符串转换为Python对象

# --------------------------------------------------------------------------
# ── 1. 全局配置与常量 (GLOBAL CONFIG & CONSTANTS) ─────────────────────────
# 遵循原则 1 (色彩与主题) 和 6 (代码风格)
# --------------------------------------------------------------------------

# 定义亮色主题的配色方案
PRIMARY_COLOR = "#FF5F5F"
BACKGROUND_COLOR = "#FAFAFA"
SECONDARY_BACKGROUND_COLOR = "#FFFFFF"  # 卡片背景色，比主背景更白
TEXT_COLOR = "#262730"
SECONDARY_TEXT_COLOR = "#57606A"
BORDER_COLOR = "#EAEAEA"

# 定义暗色主题的配色方案
DARK_PRIMARY_COLOR = "#58A6FF"
DARK_BACKGROUND_COLOR = "#0D1117"
DARK_SECONDARY_BACKGROUND_COLOR = "#161B22"
DARK_TEXT_COLOR = "#C9D1D9"
DARK_SECONDARY_TEXT_COLOR = "#8B949E"
DARK_BORDER_COLOR = "#30363D"

# --------------------------------------------------------------------------
# ── 2. 核心函数 (CORE FUNCTIONS) ──────────────────────────────────────────
# 遵循原则 6 (函数化)
# --------------------------------------------------------------------------


def get_themed_css():
    """根据常量生成主题化的CSS。"""
    return f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* --- 亮色主题变量 --- */
    :root {{
        --primary-color: {PRIMARY_COLOR};
        --background-color: {BACKGROUND_COLOR};
        --secondary-background-color: {SECONDARY_BACKGROUND_COLOR};
        --text-color: {TEXT_COLOR};
        --secondary-text-color: {SECONDARY_TEXT_COLOR};
        --border-color: {BORDER_COLOR};
        --bubble-bot-background: {SECONDARY_BACKGROUND_COLOR};
        --bubble-user-background: {PRIMARY_COLOR};
        --body-font: 'Inter', 'SF Pro Text', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
    }}

    /* --- 暗色主题变量 --- */
    body.dark-mode {{
        --primary-color: {DARK_PRIMARY_COLOR};
        --background-color: {DARK_BACKGROUND_COLOR};
        --secondary-background-color: {DARK_SECONDARY_BACKGROUND_COLOR};
        --text-color: {DARK_TEXT_COLOR};
        --secondary-text-color: {DARK_SECONDARY_TEXT_COLOR};
        --border-color: {DARK_BORDER_COLOR};
        --bubble-bot-background: {DARK_SECONDARY_BACKGROUND_COLOR};
        --bubble-user-background: {DARK_PRIMARY_COLOR};
    }}

    body {{
        font-family: var(--body-font);
        background-color: var(--background-color);
        color: var(--text-color);
        transition: background-color 0.3s, color 0.3s;
    }}

    /* 隐藏Streamlit原生组件 */
    #MainMenu, footer {{
        display: none;
    }}

    /* --- 卡片化布局 --- */
    [data-testid="stAppViewContainer"] > .main > div:first-child {{
        background-color: var(--secondary-background-color);
        padding: 1rem 1rem 2rem 1rem;
        border-radius: 24px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.05);
        border: 1px solid var(--border-color);
        transition: background-color 0.3s, border-color 0.3s;
    }}

    /* --- 侧边栏样式 --- */
    [data-testid="stSidebar"] {{
        background-color: transparent;
        border-right: none;
        padding: 1rem;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        padding-top: 0;
        background-color: var(--secondary-background-color);
        border-radius: 16px;
        padding: 1rem;
        border: 1px solid var(--border-color);
    }}
    [data-testid="stSidebar"] h1 {{
        font-size: 24px;
        font-weight: 700;
    }}

    /* --- 聊天消息样式 --- */
    .stChatMessage {{
        border-radius: 18px;
        padding: 12px 16px;
        box-shadow: none;
        border: 1px solid var(--border-color);
        transition: background-color 0.3s;
    }}
    .stChatMessage[data-testid="stChatMessage-user"] {{
        background-color: var(--bubble-user-background);
        border-color: transparent;
    }}
    .stChatMessage[data-testid="stChatMessage-user"] p {{
        color: white;
    }}
    .stChatMessage[data-testid="stChatMessage-assistant"] {{
        background-color: var(--bubble-bot-background);
    }}

    /* --- 按钮样式 (原则 3) --- */
    .stButton>button {{
        background-color: var(--primary-color);
        color: white;
        border-radius: 10px;
        border: none;
        transition: background-color 0.2s ease, transform 0.1s ease;
    }}
    .stButton>button:hover {{
        background-color: color-mix(in srgb, var(--primary-color) 85%, black);
        transform: scale(1.02);
    }}
    .stButton>button:active {{
        transform: scale(0.98);
    }}
    /* 次要按钮 (描边) - 示例 */
    .stButton.secondary>button {{
        background-color: transparent;
        color: var(--primary-color);
        border: 1px solid var(--primary-color);
    }}
</style>
"""


@st.cache_resource
def load_agent():
    """加载并缓存Agent核心。"""
    print("--- 正在加载Agent核心... ---")
    agent = NutritionAgent()
    print("--- Agent核心加载完成! ---")
    return agent


@st.cache_data
def generate_example_prompts(_user_profile):
    """
    根据用户档案调用大模型生成个性化的示例问题。
    遵循原则 5 (错误处理)。
    """
    try:
        health_goal = _user_profile.health_goal if _user_profile else "改善健康"
        meta_prompt = (
            f"我的健康目标是'{health_goal}'。请为我这位营养助手的用户，生成3个简短、多样化且适合作为按钮示例的问题。"
            "请直接返回一个Python列表字符串，不要包含任何其他解释或代码块。"
            "例如: ['问题1', '问题2', '问题3']"
        )
        # 使用一个专用的ID来调用，避免污染用户聊天记录
        agent = load_agent()
        response = agent.chat("system_prompt_generator", meta_prompt)
        prompts = ast.literal_eval(response.strip())

        if isinstance(prompts, list) and all(isinstance(p, str) for p in prompts) and len(prompts) > 0:
            return prompts
        else:
            # 如果大模型返回格式不正确，则提供一个安全的备用方案
            return ["苹果的营养成分", f"如何为'{health_goal}'目标制定饮食计划？", "我今天吃了什么？"]
    except Exception as e:
        print(f"生成示例问题时出错: {e}")
        # 如果发生任何错误，都返回一个通用的备用列表
        return ["苹果的营养成分", "我该如何减肥？", "蛋白质的良好来源有哪些？"]


# --------------------------------------------------------------------------
# ── 3. UI渲染函数 (UI RENDERING FUNCTIONS) ─────────────────────────────────
# 遵循原则 2 (排版与留白), 3 (组件美化), 6 (函数化)
# --------------------------------------------------------------------------


def render_sidebar(agent, current_user_id):
    """渲染侧边栏，包括用户切换和档案编辑。"""
    with st.sidebar:
        st.title("👤 用户档案")

        # 主题切换
        is_dark = st.toggle("切换暗黑模式", value=st.session_state.theme_dark, key="theme_toggle")
        if is_dark != st.session_state.theme_dark:
            st.session_state.theme_dark = is_dark
            st.rerun()

        st.divider()  # 遵循原则 2 (留白)

        # 用户切换
        user_ids = [f"user_{i:03d}" for i in range(1, 21)]

        def on_user_change():
            st.session_state.messages = []
            generate_example_prompts.clear()  # 切换用户时，清空示例问题的缓存

        user_id = st.selectbox(
            "切换用户",
            options=user_ids,
            index=user_ids.index(current_user_id),
            on_change=on_user_change,
            key="user_id_selector",
        )
        st.session_state.user_id = user_id
        profile = agent.get_user_profile(user_id)

        # 档案编辑表单
        with st.expander("编辑您的档案", expanded=False):
            with st.form("user_profile_form", border=False):
                name = st.text_input("姓名", value=profile.name if profile else "")
                age = st.number_input("年龄", min_value=1, max_value=120, value=profile.age if profile else 25)
                # ... (其他表单项与原代码相同) ...
                gender_options = ["男", "女", "未知"]
                gender_index = (
                    gender_options.index(profile.gender) if profile and profile.gender in gender_options else 0
                )
                gender = st.selectbox("性别", gender_options, index=gender_index)
                height = st.number_input("身高 (cm)", value=profile.height if profile else 175.0, step=0.5)
                weight = st.number_input("体重 (kg)", value=profile.weight if profile else 70.0, step=0.1)
                activity_options = ["久坐", "轻度活动", "中度活动", "重度活动"]
                activity_index = (
                    activity_options.index(profile.activity_level)
                    if profile and profile.activity_level in activity_options
                    else 1
                )
                activity_level = st.selectbox("活动水平", activity_options, index=activity_index)
                goal_options = ["减肥", "增重", "维持体重", "增肌", "改善健康"]
                goal_index = (
                    goal_options.index(profile.health_goal) if profile and profile.health_goal in goal_options else 4
                )
                health_goal = st.selectbox("健康目标", goal_options, index=goal_index)
                dietary_restrictions = st.text_input(
                    "饮食限制", value=profile.dietary_restrictions if profile else "无"
                )
                preferences = st.text_area("食物偏好", value=profile.preferences if profile else "")

                if st.form_submit_button("💾 保存或更新档案", use_container_width=True):  # 原则 3 (按钮)
                    success = agent.create_user_profile(
                        user_id=user_id,
                        name=name,
                        age=age,
                        gender=gender,
                        height=height,
                        weight=weight,
                        activity_level=activity_level,
                        health_goal=health_goal,
                        dietary_restrictions=dietary_restrictions,
                        preferences=preferences,
                    )
                    if success:
                        st.success("用户档案已成功保存！")
                        st.balloons()
                        generate_example_prompts.clear()  # 保存后清空缓存以生成新建议
                    else:
                        st.error("保存用户档案失败。")

        st.divider()  # 遵循原则 2 (留白)

        if st.button("🗑️ 清空聊天记录", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        return profile


def render_chat_interface(profile):
    """渲染主聊天界面。"""
    st.title("🍎 营养学 AI 助手")
    st.caption(f"你好，**{profile.name if profile else st.session_state.user_id}**！我是你的专属营养师，随时为你服务。")

    # 显示历史消息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 遵循原则 2 (留白)
    st.markdown("<br>", unsafe_allow_html=True)

    # 动态示例问题区域
    example_prompts = generate_example_prompts(profile)

    def on_example_click(prompt):
        st.session_state.messages.append({"role": "user", "content": prompt})

    # 使用栅格布局 (原则 2)
    if example_prompts and len(example_prompts) >= 3:
        cols = st.columns([1, 1, 1])
        for i, col in enumerate(cols):
            with col:
                st.button(
                    example_prompts[i],
                    key=f"ex{i}",
                    use_container_width=True,  # 原则 3 (按钮)
                    on_click=on_example_click,
                    args=(example_prompts[i],),
                )


def handle_user_input_and_response(agent):
    """处理用户输入和AI回复的逻辑。"""
    if prompt := st.chat_input("请输入您的问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # 如果最后一条消息是用户发的，则生成AI回复
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        user_prompt = st.session_state.messages[-1]["content"]
        with st.chat_message("assistant"):
            # 遵循原则 4 (加载动画)
            with st.spinner("⏳ 营养师正在思考..."):
                try:  # 遵循原则 5 (错误处理)
                    response = agent.chat(st.session_state.user_id, user_prompt)
                    message_placeholder = st.empty()
                    full_response = ""
                    # 遵循原则 4 (过渡动画) - 打字机效果
                    for char in response:
                        full_response += char
                        time.sleep(0.01)
                        message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    error_message = f"📌 抱歉，处理您的请求时遇到问题。请稍后再试。\n\n**技术细节:** {e}"
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
        st.rerun()


# --------------------------------------------------------------------------
# ── 4. 主应用逻辑 (MAIN APP LOGIC) ─────────────────────────────────────────
# --------------------------------------------------------------------------


def main():
    """主函数，运行整个Streamlit应用。"""
    # ── 0. 页面与状态初始化 ──
    st.set_page_config(page_title="营养学AI助手", page_icon="🍎", layout="centered")
    # 遵循原则 5 (状态管理)
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "user_id" not in st.session_state:
        st.session_state.user_id = "user_001"
    if "theme_dark" not in st.session_state:
        st.session_state.theme_dark = False

    # 注入核心CSS
    st.markdown(get_themed_css(), unsafe_allow_html=True)

    # ── 1. 加载核心组件 ──
    agent = load_agent()

    # ── 2. 渲染UI组件 ──
    profile = render_sidebar(agent, st.session_state.user_id)
    render_chat_interface(profile)

    # ── 3. 处理用户输入与AI响应 ──
    handle_user_input_and_response(agent)

    # ── 4. 主题切换JS注入 (最后执行) ──
    # 将JS注入放在最后，确保body元素已加载
    js_code = (
        f"<script>document.body.classList.toggle('dark-mode', {str(st.session_state.theme_dark).lower()});</script>"
    )
    st.html(js_code)


if __name__ == "__main__":
    main()
