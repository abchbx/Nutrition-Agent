# app.py

import streamlit as st
from nutrition_agent import NutritionAgent # 从您的后端文件导入Agent类
import time

# --- 页面基础设置 ---
st.set_page_config(
    page_title="营养学AI助手",
    page_icon="🍎",
    layout="wide" # 将布局设置为 'wide' 以便更好地展示内容
)

st.title("🍎 营养学 AI 助手")
st.caption("我是您的专属营养师，随时为您解答营养问题，提供饮食建议。")


# --- Agent 初始化 ---
# 使用 st.cache_resource 来缓存Agent实例，避免每次交互都重新加载模型，这对于性能至关重要！
@st.cache_resource
def load_agent():
    """
    加载并缓存NutritionAgent，只在第一次运行时执行。
    """
    print("--- 正在加载Agent核心... ---")
    # 这里我们假设 NutritionAgent 类在 nutrition_agent.py 文件中定义
    agent = NutritionAgent()
    print("--- Agent核心加载完成! ---")
    return agent

# 加载Agent
agent = load_agent()


# --- 聊天记录管理 ---
# 使用 session_state 来跨交互保存聊天记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 用户档案管理 (侧边栏) ---
with st.sidebar:
    st.title("👤 用户档案")
    user_id = st.text_input("请输入您的用户ID", "user_streamlit")
    st.info(f"当前用户ID: **{user_id}**")

    # 使用表单来收集用户信息，可以避免每次输入都刷新页面
    with st.form("user_profile_form"):
        st.subheader("基本信息")
        name = st.text_input("姓名", "小明")
        age = st.number_input("年龄", min_value=1, max_value=120, value=25)
        gender = st.selectbox("性别", ["男", "女"])
        
        st.subheader("身体数据")
        height = st.number_input("身高 (cm)", min_value=50.0, max_value=250.0, value=175.0, step=0.5)
        weight = st.number_input("体重 (kg)", min_value=10.0, max_value=200.0, value=70.0, step=0.1)

        st.subheader("生活习惯与目标")
        activity_level = st.selectbox("活动水平", ["久坐", "轻度活动", "中度活动", "重度活动"])
        health_goal = st.selectbox("健康目标", ["减肥", "增重", "维持体重", "增肌", "改善健康"])
        dietary_restrictions = st.text_input("饮食限制 (如: 素食, 无麸质)", "无")
        preferences = st.text_area("食物偏好或不喜欢的食物", "喜欢吃鱼，不喜欢吃苦瓜")

        # 表单提交按钮
        submitted = st.form_submit_button("保存或更新档案")
        if submitted:
            # 调用后端的 create_user_profile 方法
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
            # 注意：这里的 user_id 是从侧边栏获取的
            response = agent.chat(user_id, prompt)
            
            # 使用打字机效果显示回复
            message_placeholder = st.empty()
            full_response = ""
            # .split() 对于复杂的Markdown可能效果不佳，我们按字符流模拟
            for char in response:
                full_response += char
                time.sleep(0.01) # 控制打字速度
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
    
    # 将AI的回复也添加到聊天记录
    st.session_state.messages.append({"role": "assistant", "content": response})
