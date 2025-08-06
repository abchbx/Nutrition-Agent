# nutrition_agent.py
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
# 导入所有需要的组件，包括新的和修正过的
from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# 【核心修正】从新的库导入，并导入一个必要的渲染函数
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.tools.render import render_text_description
import sys
import os
import traceback

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nutrition_database import NutritionDatabase
from tools.nutrition_query_tool import NutritionQueryTool, CategorySearchTool
from tools.diet_advice_tool import DietAdviceTool, MealPlanTool
from tools.nutrition_qa_tool import NutritionQATool, NutritionMythTool
from user_memory import UserMemory, UserProfile
from config import AGENT_MODEL, AGENT_TEMPERATURE, EMBEDDING_MODEL

class NutritionAgent:
    """营养学Agent主类"""

    def __init__(self):
        """初始化营养学Agent"""
        print("🚀 初始化营养学Agent...")
        print("💡 正在加载共享的Embedding模型...")
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        print("✅ Embedding模型加载完成!")
        self.database = NutritionDatabase(embeddings=self.embeddings)
        self.memory = UserMemory()
        self.llm = ChatOpenAI(
            model_name=AGENT_MODEL,
            temperature=AGENT_TEMPERATURE,
            top_p=0.8,
            presence_penalty=1.05
        )
        self.tools = self._initialize_tools()
        self.agent_executor = self._initialize_agent_executor() 
        print("✅ 营养学Agent初始化完成!")

    def _initialize_tools(self) -> List:
        """初始化所有工具"""
        tools = [
            NutritionQueryTool(self.database),
            CategorySearchTool(self.database),
            DietAdviceTool(self.database),
            MealPlanTool(self.database),
            NutritionQATool(embeddings=self.embeddings),
            NutritionMythTool()
        ]
        return tools

    def _initialize_agent_executor(self) -> AgentExecutor:
            """使用最新的方法初始化Agent Executor"""
            system_prompt = """
    你是一位专业的营养学AI助手，拥有丰富的营养学知识和经验。你的任务是帮助用户解决各种营养相关问题。
    请根据下面提供的用户档案和历史对话，给出最精准、个性化的回答。
    在回答时，请自然地结合用户的最新情况和之前的对话内容，展现出你对用户的持续记忆和理解。

    你的能力包括：
    1. 查询食物营养成分信息
    2. 根据用户情况提供个性化饮食建议
    3. 回答营养学知识问题
    4. 辨析营养误区和流行说法
    5. 生成膳食计划和食物搭配建议

    工作原则：
    1. 科学准确：所有建议都基于营养学科学原理
    2. 个性化：根据用户的具体情况提供定制化建议
    3. 实用性：提供可操作的具体建议
    4. 全面性：考虑营养均衡和整体健康
    5. 谨慎性：对于医疗相关问题，建议咨询专业医生

    使用工具指南：
    - 当用户询问特定食物的营养信息时，使用nutrition_query工具
    - 当用户询问某类食物时，使用category_search工具
    - 当用户提供个人信息并要求饮食建议时，使用diet_advice工具
    - 当用户要求特定餐食计划时，使用meal_plan工具
    - 当用户询问营养学知识问题时，使用nutrition_qa工具
    - 当用户提到营养误区时，使用nutrition_myth工具

    请用专业、友好、易懂的语言与用户交流，让营养学知识变得简单实用。
    """

            # 1. 将工具绑定到LLM，这是新版Tool-calling agent的做法
            llm_with_tools = self.llm.bind_tools(self.tools)

            # 2. 创建Prompt模板，与你的原版基本一致
            #    注意：我们不再需要 .partial() 方法，因为输入将在链中动态提供
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])

            # 3. 【核心修正】构建Agent链 (Runnable Sequence)
            #    这部分取代了 create_structured_chat_agent 函数
            agent = (
                {
                    "input": lambda x: x["input"],
                    "chat_history": lambda x: x["chat_history"],
                    # 【关键】使用格式化函数处理 intermediate_steps
                    "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                        x["intermediate_steps"]
                    ),
                }
                | prompt
                | llm_with_tools
                | OpenAIToolsAgentOutputParser()
            )

            agent_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

            return AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                memory=agent_memory,
                handle_parsing_errors=True
            )
    def create_user_profile(self, user_id: str, **kwargs) -> bool:
        """创建或更新用户档案"""
        return self.memory.create_user_profile(user_id=user_id, **kwargs)

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取完整的UserProfile对象"""
        return self.memory.get_user_profile(user_id)

    def chat(self, user_id: str, message: str) -> str:
        """与用户进行有记忆的对话"""
        try:
            user_profile = self.get_user_profile(user_id)
            if not user_profile:
                print(f"📝 检测到新用户: {user_id}，正在创建默认档案...")
                self.create_user_profile(user_id=user_id, name=user_id)
                user_profile = self.get_user_profile(user_id)
            
            context_message = f"""
--- 用户完整档案 ---
姓名: {user_profile.name}
年龄: {user_profile.age}岁
性别: {user_profile.gender}
身高: {user_profile.height}cm
体重: {user_profile.weight}kg
活动水平: {user_profile.activity_level}
健康目标: {user_profile.health_goal}
饮食限制: {user_profile.dietary_restrictions}
食物偏好: {user_profile.preferences}
档案更新于: {user_profile.updated_at}
--- 历史对话回顾 (最近5次) ---
"""
            if user_profile.consultations:
                for convo in user_profile.consultations[-5:]:
                    context_message += f"- 用户曾问: {convo['question']}\\n- 你曾答: {convo['answer']}\\n"
            else:
                context_message += "这是我们第一次对话。\\n"

            context_message += f"\\n--- 用户本次问题 --- \\n{message}"

            response_dict = self.agent_executor.invoke({"input": context_message})
            answer = response_dict.get('output', '抱歉，我没有找到合适的答案。')

            self.memory.add_consultation_record(
                user_id=user_id,
                question=message,
                answer=answer,
                category="general"
            )

            return answer

        except Exception as e:
            error_msg = f"处理用户消息时发生错误: {str(e)}"
            traceback.print_exc()
            return error_msg