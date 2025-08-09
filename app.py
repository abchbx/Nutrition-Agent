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
            f"我的健康目标是'{health_goal}'。请为我这位营养助手的用户，生成3个简短、多样化且适合作为按钮示例的问题。" "直接返回一个Python列表，例如：['问题1','问题2']，不要多余解释。"
        )
        response = agent.chat("system_prompt_generator", meta_prompt)

        # 1) 先尝试 JSON
        try:
            return json.loads(response.strip())[:3]
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
        # 确保当前用户ID在列表中（对于新创建的用户尤其重要）
        if current_user_id not in user_ids:
            user_ids.append(current_user_id)
            user_ids.sort() # 保持列表有序

        def on_user_change():
            st.session_state.messages = []
            # generate_example_prompts.clear() # 不再需要手动清除，由缓存键自动处理
            # 退出编辑/新增模式
            st.session_state.editing_profile = False
            st.session_state.adding_user = False

        user_id = st.selectbox(
            "切换用户", user_ids, index=user_ids.index(current_user_id), on_change=on_user_change, key="uid_selector"
        )
        st.session_state.user_id = user_id
        profile = agent.get_user_profile(user_id)

        # --- 编辑档案功能 ---
        st.divider()
        if st.button("📝 编辑档案", use_container_width=True):
            st.session_state.editing_profile = True
            st.session_state.adding_user = False # 确保不同时处于新增模式

        if st.session_state.get("editing_profile", False):
            st.write("---")
            st.subheader("✏️ 编辑用户档案")
            
            # 使用表单确保提交一致性
            with st.form(key="profile_edit_form"):
                # 预填充当前值
                new_name = st.text_input("姓名", value=profile.name if profile else user_id)
                new_age = st.number_input("年龄", min_value=1, max_value=120, value=profile.age if profile else 30)
                new_gender = st.selectbox("性别", options=["男", "女", "其他"], index=["男", "女", "其他"].index(profile.gender if profile and profile.gender in ["男", "女", "其他"] else "其他"))
                new_height = st.number_input("身高 (cm)", min_value=50.0, max_value=250.0, value=profile.height if profile else 170.0)
                new_weight = st.number_input("体重 (kg)", min_value=10.0, max_value=300.0, value=profile.weight if profile else 65.0)
                new_activity_level = st.selectbox("活动水平", options=["久坐", "轻度活动", "中度活动", "重度活动"], index=["久坐", "轻度活动", "中度活动", "重度活动"].index(profile.activity_level if profile and profile.activity_level in ["久坐", "轻度活动", "中度活动", "重度活动"] else "轻度活动"))
                new_health_goal = st.text_input("健康目标", value=profile.health_goal if profile else "维持体重")
                new_dietary_restrictions = st.text_area("饮食限制", value=profile.dietary_restrictions if profile else "无")
                new_preferences = st.text_area("食物偏好", value=profile.preferences if profile else "无")

                # 提交和取消按钮
                col1, col2 = st.columns(2)
                with col1:
                    submit_button = st.form_submit_button("💾 保存更改")
                with col2:
                    cancel_button = st.form_submit_button("❌ 取消")

            if submit_button:
                # 调用 Agent 的方法更新用户档案
                update_success = agent.update_user_profile(
                    user_id,
                    name=new_name,
                    age=new_age,
                    gender=new_gender,
                    height=new_height,
                    weight=new_weight,
                    activity_level=new_activity_level,
                    health_goal=new_health_goal,
                    dietary_restrictions=new_dietary_restrictions,
                    preferences=new_preferences
                )
                if update_success:
                    st.success("✅ 档案更新成功!")
                    # 更新本地 profile 变量以反映更改
                    profile = agent.get_user_profile(user_id) 
                    # 关闭编辑模式
                    st.session_state.editing_profile = False
                    # 可选：刷新页面以显示更新
                    st.rerun()
                else:
                    st.error("❌ 档案更新失败!")

            if cancel_button:
                # 关闭编辑模式
                st.session_state.editing_profile = False
                st.rerun()

            st.write("---")

        # --- 新增用户功能 ---
        if st.button("🆕 新增用户", use_container_width=True):
            st.session_state.adding_user = True
            st.session_state.editing_profile = False # 确保不同时处于编辑模式

        if st.session_state.get("adding_user", False):
            st.write("---")
            st.subheader("👤 新增用户")
            
            with st.form(key="add_user_form"):
                # 自动生成一个建议的ID
                import random
                suggested_id = f"user_{random.randint(1000, 9999)}"
                new_user_id = st.text_input("用户ID", value=suggested_id)
                
                # 输入初始档案信息 (可以简化)
                new_name = st.text_input("姓名", value=new_user_id)
                new_age = st.number_input("年龄", min_value=1, max_value=120, value=30, key="new_age")
                new_gender = st.selectbox("性别", options=["男", "女", "其他"], index=0, key="new_gender")
                new_height = st.number_input("身高 (cm)", min_value=50.0, max_value=250.0, value=170.0, key="new_height")
                new_weight = st.number_input("体重 (kg)", min_value=10.0, max_value=300.0, value=65.0, key="new_weight")
                new_activity_level = st.selectbox("活动水平", options=["久坐", "轻度活动", "中度活动", "重度活动"], index=1, key="new_activity_level")
                new_health_goal = st.text_input("健康目标", value="维持体重", key="new_health_goal")
                new_dietary_restrictions = st.text_area("饮食限制", value="无", key="new_dietary_restrictions")
                new_preferences = st.text_area("食物偏好", value="无", key="new_preferences")

                col1, col2 = st.columns(2)
                with col1:
                    create_button = st.form_submit_button("✅ 创建用户")
                with col2:
                    cancel_add_button = st.form_submit_button("❌ 取消")

            if create_button:
                # 简单验证ID是否唯一（在当前会话列表中）
                # 注意：实际应用中应在后端检查
                if new_user_id in user_ids:
                    st.error("❌ 用户ID已存在，请选择另一个。")
                elif not new_user_id.strip():
                    st.error("❌ 用户ID不能为空。")
                else:
                    # 调用 Agent 创建用户
                    create_success = agent.create_user_profile(
                        user_id=new_user_id,
                        name=new_name,
                        age=new_age,
                        gender=new_gender,
                        height=new_height,
                        weight=new_weight,
                        activity_level=new_activity_level,
                        health_goal=new_health_goal,
                        dietary_restrictions=new_dietary_restrictions,
                        preferences=new_preferences
                    )
                    if create_success:
                        st.success(f"✅ 用户 {new_user_id} 创建成功!")
                        # 将新用户添加到列表并切换
                        # 注意：user_ids 是局部变量，我们需要更新 session state 或通过重新加载获取更新
                        # 一个简单的方法是刷新页面或重新运行，让 user_ids 重新从 st.session_state.user_id 和预设列表生成
                        st.session_state.user_id = new_user_id
                        st.session_state.adding_user = False
                        # 由于 user_ids 是在函数内生成的，我们通过 rerun 来重新加载整个侧边栏
                        st.rerun() 
                    else:
                        st.error("❌ 用户创建失败!")

            if cancel_add_button:
                st.session_state.adding_user = False
                st.rerun()
                
            st.write("---")


        st.divider()
        if st.button("清空聊天记录", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        return profile


# ------------------------ 主界面 --------------------------
def render_chat_interface(profile):
    """渲染主聊天界面，包括标题、历史消息和示例问题。"""
    st.title("🍎 营养学 AI 助手")
    st.caption(f"你好，**{profile.name if profile else st.session_state.user_id}**！我是你的专属营养师，随时为你服务。")

    # 显示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 初始化并获取示例问题
    if "example_refresh_counter" not in st.session_state:
        st.session_state.example_refresh_counter = 0
    prompts = generate_example_prompts(st.session_state.user_id, st.session_state.example_refresh_counter)

    # 限制只显示前3个示例
    display_prompts = prompts[:3] if prompts else []

    if display_prompts:
        cols = st.columns(3)
        for c, p in zip(cols, display_prompts):
            if c.button(
                p, use_container_width=True, key=f"example_btn_{hash(p)}_{st.session_state.example_refresh_counter}"
            ):
                st.session_state.messages.append({"role": "user", "content": p})
                st.rerun()

    # --- 代码修复 ---
    # 刷新按钮，点击时手动清除缓存
    if st.button("🔄 刷新示例", key="refresh_examples", use_container_width=True):
        # 核心修复：手动清除 generate_example_prompts 函数的缓存
        generate_example_prompts.clear()
        # 增加计数器以确保st.rerun后，函数参数不同，但清除缓存是关键
        st.session_state.example_refresh_counter += 1
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
    # 初始化用户管理的 Session State 标志
    if "editing_profile" not in st.session_state:
        st.session_state.editing_profile = False
    if "adding_user" not in st.session_state:
        st.session_state.adding_user = False

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
