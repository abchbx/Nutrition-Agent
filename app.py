import streamlit as st
import json
import ast
import time
from nutrition_agent import NutritionAgent


@st.cache_resource
def load_agent():
    return NutritionAgent()


# ------------- 生成示例问题（已修复正则 & 变量） -------------
@st.cache_data
def generate_example_prompts(_user_id, _refresh_counter=0):
    try:
        agent = load_agent()
        profile = agent.get_user_profile(_user_id)
        health_goal = profile.health_goal if profile else "改善健康"
        meta_prompt = (
            f"我的健康目标是'{health_goal}'。请为我这位营养助手的用户，生成5个简短、多样化且适合作为按钮示例的问题。" "直接返回一个Python列表，例如：['问题1','问题2']，不要多余解释。"
        )
        response = agent.chat("system_prompt_generator", meta_prompt)

        # 1) 先尝试 JSON
        try:
            return json.loads(response.strip())[:5]
        except Exception:
            pass

        # 2) 再尝试 AST
        try:
            return ast.literal_eval(response.strip())[:5]
        except Exception:
            pass

        # 3) 兜底
        return ["苹果的营养成分", "如何减肥？", "蛋白质来源有哪些？"]
    except Exception:
        return ["苹果的营养成分", "如何减肥？", "蛋白质来源有哪些？"]


# ------------------------ 侧边栏 --------------------------
def render_sidebar(agent, current_user_id):
    with st.sidebar:
        st.title("👤 用户档案")

        # 主题切换 - 使用 Streamlit 内置 toggle 和 session state
        # 主题应用逻辑已移至 CSS 中通过 data属性控制，避免直接注入 JS
        dark_mode = st.toggle("暗黑模式", value=st.session_state.get("theme_dark", False))
        st.session_state.theme_dark = dark_mode

        st.divider()

        user_ids = [f"user_{i:03d}" for i in range(1, 21)]

        def on_user_change():
            st.session_state.messages = []
            # generate_example_prompts.clear() # 不再需要手动清除，由缓存键自动处理

        user_id = st.selectbox(
            "切换用户", user_ids, index=user_ids.index(current_user_id), on_change=on_user_change, key="uid_selector"
        )
        st.session_state.user_id = user_id
        profile = agent.get_user_profile(user_id)

        st.divider()
        if st.button("清空聊天记录", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        return profile


# ------------------------ 主界面 --------------------------
def render_chat_interface(profile):
    st.title("🍎 营养学 AI 助手")
    st.caption(f"你好，**{profile.name if profile else st.session_state.user_id}**！" "我是你的专属营养师，随时为你服务。")

    # 历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 示例问题
    if "example_refresh_counter" not in st.session_state:
        st.session_state.example_refresh_counter = 0
    # 传递 user_id 而不是 profile 对象
    prompts = generate_example_prompts(st.session_state.user_id, st.session_state.example_refresh_counter)

    # 限制只显示3个示例问题
    display_prompts = prompts[:3] if prompts else []

    if display_prompts:
        # 使用固定三列布局，确保按钮大小一致
        cols = st.columns(3)
        for c, p in zip(cols, display_prompts):
            # 使用 use_container_width=True 确保按钮填满列宽
            if c.button(
                p, use_container_width=True, key=f"example_btn_{hash(p)}_{st.session_state.example_refresh_counter}"
            ):
                st.session_state.messages.append({"role": "user", "content": p})
                st.rerun()

        # 刷新按钮与示例问题按钮宽度对齐
        if st.button("🔄 刷新示例", key="refresh_examples", use_container_width=True):
            st.session_state.example_refresh_counter += 1
            # 不再需要手动清除缓存 generate_example_prompts.clear()
            st.rerun()


# -------------------- 聊天响应逻辑 -----------------------
def handle_user_input_and_response(agent):
    if prompt := st.chat_input("请输入您的问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        user_prompt = st.session_state.messages[-1]["content"]
        with st.chat_message("assistant"):
            with st.spinner("⏳ 营养师正在思考..."):
                try:
                    resp = agent.chat(st.session_state.user_id, user_prompt)
                    placeholder = st.empty()
                    full = ""
                    for ch in resp:
                        full += ch
                        time.sleep(0.01)
                        placeholder.markdown(full + "▌")
                    placeholder.markdown(full)
                    st.session_state.messages.append({"role": "assistant", "content": full})
                except Exception as e:
                    st.error(f"📌 出现错误：{e}")
                    st.session_state.messages.append({"role": "assistant", "content": f"抱歉，处理请求时出错：{e}"})
        st.rerun()


# ------------------------ 主函数 --------------------------
def main():
    st.set_page_config(page_title="营养学AI助手", page_icon="🍎", layout="centered")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "user_id" not in st.session_state:
        st.session_state.user_id = "user_001"
    if "theme_dark" not in st.session_state:
        st.session_state.theme_dark = False

    # 应用主题 - 通过 HTML data 属性和 CSS 控制，避免直接注入 JS
    theme_class = "dark" if st.session_state.theme_dark else "light"

    # 注入基础样式和主题变量
    st.markdown(
        f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

    /* Light Theme Variables */
    :root {{
        --primary-color: #FF5F5F;
        --background-color: #FAFAFA;
        --card-background-color: #FFFFFF;
        --text-color: #262730;
        --border-color: #e0e0e0;
    }}

    /* Dark Theme Variables */
    [data-theme="dark"] {{
        --primary-color: #58A6FF;
        --background-color: #0D1117;
        --card-background-color: #161B22;
        --text-color: #C9D1D9;
        --border-color: #30363d;
    }}

    /* Apply base styles */
    body {{
        font-family: 'Inter', sans-serif;
        background-color: var(--background-color);
        color: var(--text-color);
    }}

    /* Streamlit container styling */
    [data-testid="stAppViewContainer"] > .main > div:first-child {{
        background-color: var(--card-background-color);
        border-radius: 24px;
        padding: 1rem 1rem 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.05);
        border: 1px solid var(--border-color);
    }}

    /* Button styling */
    .stButton > button {{
        background-color: var(--primary-color);
        color: white;
        border-radius: 10px;
        border: none;
        transition: transform .1s;
    }}
    .stButton > button:hover {{
        transform: scale(1.02);
    }}
    </style>
    <div data-theme="{theme_class}"> </div>
    """,
        unsafe_allow_html=True,
    )

    agent = load_agent()
    profile = render_sidebar(agent, st.session_state.user_id)
    render_chat_interface(profile)
    handle_user_input_and_response(agent)


if __name__ == "__main__":
    main()
