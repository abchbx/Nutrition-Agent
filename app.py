# app.py

import streamlit as st
from nutrition_agent import NutritionAgent # 从您的后端文件导入Agent类
import time

# --- 页面基础设置 ---
st.set_page_config(
    page_title="营养学AI助手",
    page_icon="🍎",
    layout="wide"
)

st.title("🍎 营养学 AI 助手")
st.caption("我是您的专属营养师，随时为您解答营养问题，提供饮食建议。")


# --- Agent 初始化 ---
@st.cache_resource
def load_agent():
    """
    加载并缓存NutritionAgent，只在第一次运行时执行。
    """
    print("--- 正在加载Agent核心... ---")
    agent = NutritionAgent()
    print("--- Agent核心加载完成! ---")
    return agent

# 加载Agent
agent = load_agent()


# --- 聊天记录管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 用户档案管理 (侧边栏) ---
with st.sidebar:
    st.title("👤 用户档案")
    user_id = st.text_input("请输入您的用户ID", "user_018")
    st.info(f"当前用户ID: **{user_id}**")

    # 每次user_id变化时，都尝试重新加载档案
    profile = agent.get_user_profile(user_id)

    # 如果档案存在，显示一个成功的提示
    if profile:
        st.success("已成功加载您的档案！")

    # 使用表单来收集用户信息
    with st.form("user_profile_form"):
        st.subheader("基本信息")
        # --- 核心修改：使用对象的属性来设置默认值 ---
        name = st.text_input("姓名", value=profile.name if profile else "小明")
        age = st.number_input("年龄", min_value=1, max_value=120, value=profile.age if profile else 25)
        
        # 为了处理selectbox的默认值，我们需要知道默认选项的索引
        gender_options = ["男", "女", "未知"]
        gender_index = gender_options.index(profile.gender) if profile and profile.gender in gender_options else 0
        gender = st.selectbox("性别", gender_options, index=gender_index)
        
        st.subheader("身体数据")
        height = st.number_input("身高 (cm)", min_value=50.0, max_value=250.0, value=profile.height if profile else 175.0, step=0.5)
        weight = st.number_input("体重 (kg)", min_value=10.0, max_value=200.0, value=profile.weight if profile else 70.0, step=0.1)

        st.subheader("生活习惯与目标")
        activity_options = ["久坐", "轻度活动", "中度活动", "重度活动"]
        activity_index = activity_options.index(profile.activity_level) if profile and profile.activity_level in activity_options else 1
        activity_level = st.selectbox("活动水平", activity_options, index=activity_index)

        goal_options = ["减肥", "增重", "维持体重", "增肌", "改善健康"]
        goal_index = goal_options.index(profile.health_goal) if profile and profile.health_goal in goal_options else 4
        health_goal = st.selectbox("健康目标", goal_options, index=goal_index)
        
        dietary_restrictions = st.text_input("饮食限制 (如: 素食, 无麸质)", value=profile.dietary_restrictions if profile else "无")
        preferences = st.text_area("食物偏好或不喜欢的食物", value=profile.preferences if profile else "喜欢吃鱼，不喜欢吃苦瓜")

        # 表单提交按钮
        submitted = st.form_submit_button("保存或更新档案")
        if submitted:
            # 调用后端的 create_user_profile 方法，它现在也负责更新
            success = agent.create_user_profile(
                user_id=user_id, name=name, age=age, gender=gender,
                height=height, weight=weight, activity_level=activity_level,
                health_goal=health_goal, dietary_restrictions=dietary_restrictions,
                preferences=preferences
            )
            if success:
                st.success("用户档案已成功保存！")
                st.balloons()
            else:
                st.error("保存用户档案失败，请检查后端逻辑。")


# --- 聊天界面渲染 ---
# 1. 显示已有的聊天记录
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. 获取用户的新输入
if prompt := st.chat_input("请输入您的问题..."):
    # 将用户输入添加到聊天记录并显示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 显示思考动画，并调用Agent获取回复
    with st.chat_message("assistant"):
        with st.spinner("营养师正在思考..."):
            # 调用您的Agent的chat方法
            response = agent.chat(user_id, prompt)
            
            # 使用打字机效果显示回复
            message_placeholder = st.empty()
            full_response = ""
            for char in response:
                full_response += char
                time.sleep(0.01) # 控制打字速度
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
    
    # 将AI的回复也添加到聊天记录
    st.session_state.messages.append({"role": "assistant", "content": response})