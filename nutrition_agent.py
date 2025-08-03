from typing import List, Dict, Any, Optional
from langchain.agents import AgentType, initialize_agent
from langchain_community.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nutrition_database import NutritionDatabase
from tools.nutrition_query_tool import NutritionQueryTool, CategorySearchTool
from tools.diet_advice_tool import DietAdviceTool, MealPlanTool
from tools.nutrition_qa_tool import NutritionQATool, NutritionMythTool
from user_memory import UserMemory
from config import AGENT_MODEL, AGENT_TEMPERATURE

class NutritionAgent:
    """营养学Agent主类"""

    def __init__(self):
        """初始化营养学Agent"""
        print("🚀 初始化营养学Agent...")

        # 初始化数据库
        self.database = NutritionDatabase()

        # 初始化用户记忆
        self.memory = UserMemory()

        # 初始化LLM
        self.llm = ChatOpenAI(
            model_name=AGENT_MODEL,
            temperature=AGENT_TEMPERATURE,
            top_p=0.8,
            presence_penalty=1.05
        )

        # 初始化工具
        self.tools = self._initialize_tools()

        # 初始化Agent
        self.agent = self._initialize_agent()

        print("✅ 营养学Agent初始化完成!")

    def _initialize_tools(self) -> List:
        """
        初始化所有工具
        
        Returns:
            工具列表
        """
        tools = [
            # 营养查询工具
            NutritionQueryTool(self.database),
            CategorySearchTool(self.database),

            # 饮食建议工具
            DietAdviceTool(self.database),
            MealPlanTool(self.database),

            # 营养学问答工具
            NutritionQATool(),
            NutritionMythTool()
        ]

        return tools

    def _initialize_agent(self):
        """
        初始化Agent
        
        Returns:
            Agent实例
        """
        # 创建系统提示
        system_prompt = """
你是一位专业的营养学AI助手，拥有丰富的营养学知识和经验。你的任务是帮助用户解决各种营养相关问题。

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

        # 创建对话记忆
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        # 创建Agent提示模板
        agent_prompt = PromptTemplate(
            input_variables=["input", "chat_history", "agent_scratchpad"],
            template=f"""{system_prompt}

聊天历史：
{{chat_history}}

用户输入：
{{input}}

{{agent_scratchpad}}

请根据用户的需求选择合适的工具来回答问题。如果不需要使用工具，请直接基于你的知识回答。
"""
        )

        # 初始化Agent
        agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            memory=memory,
            agent_kwargs={
                "system_message": SystemMessage(content=system_prompt),
                "prompt": agent_prompt
            }
        )

        return agent

    def create_user_profile(self, user_id: str, name: str, age: int, gender: str, 
                          height: float, weight: float, activity_level: str, 
                          health_goal: str, dietary_restrictions: str = "无", 
                          preferences: str = "无") -> bool:
        """
        创建用户档案
        
        Args:
            user_id: 用户ID
            name: 姓名
            age: 年龄
            gender: 性别
            height: 身高
            weight: 体重
            activity_level: 活动水平
            health_goal: 健康目标
            dietary_restrictions: 饮食限制
            preferences: 食物偏好
            
        Returns:
            是否创建成功
        """
        return self.memory.create_user_profile(
            user_id=user_id,
            name=name,
            age=age,
            gender=gender,
            height=height,
            weight=weight,
            activity_level=activity_level,
            health_goal=health_goal,
            dietary_restrictions=dietary_restrictions,
            preferences=preferences
        )

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户档案
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户档案信息
        """
        profile = self.memory.get_user_profile(user_id)
        if profile:
            return {
                "user_id": profile.user_id,
                "name": profile.name,
                "age": profile.age,
                "gender": profile.gender,
                "height": profile.height,
                "weight": profile.weight,
                "activity_level": profile.activity_level,
                "health_goal": profile.health_goal,
                "dietary_restrictions": profile.dietary_restrictions,
                "preferences": profile.preferences
            }
        return None

    def chat(self, user_id: str, message: str) -> str:
        """
        与用户对话
        
        Args:
            user_id: 用户ID
            message: 用户消息
            
        Returns:
            Agent回复
        """
        try:
            # 获取用户档案（如果有）
            user_profile = self.get_user_profile(user_id)

            # 如果有用户档案，在消息中添加上下文
            if user_profile:
                context_message = f"""
用户信息：
姓名: {user_profile['name']}
年龄: {user_profile['age']}岁
性别: {user_profile['gender']}
身高: {user_profile['height']}cm
体重: {user_profile['weight']}kg
活动水平: {user_profile['activity_level']}
健康目标: {user_profile['health_goal']}
饮食限制: {user_profile['dietary_restrictions']}
食物偏好: {user_profile['preferences']}

用户问题：{message}
"""
                response = self.agent.run(context_message)
            else:
                response = self.agent.run(message)

            # 记录咨询历史
            self.memory.add_consultation_record(
                user_id=user_id,
                question=message,
                answer=response,
                category="general"
            )

            return response

        except Exception as e:
            error_msg = f"处理用户消息时发生错误: {str(e)}"
            print(error_msg)
            return error_msg

    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户使用总结
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户总结信息
        """
        return self.memory.get_user_summary(user_id)

    def add_nutrition_record(self, user_id: str, meal_type: str, foods: List[Dict[str, Any]], 
                           notes: str = "") -> bool:
        """
        添加营养记录
        
        Args:
            user_id: 用户ID
            meal_type: 餐食类型
            foods: 食物列表
            notes: 备注
            
        Returns:
            是否添加成功
        """
        return self.memory.add_nutrition_record(
            user_id=user_id,
            meal_type=meal_type,
            foods=foods,
            notes=notes
        )

    def get_nutrition_records(self, user_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取营养记录
        
        Args:
            user_id: 用户ID
            date: 日期
            
        Returns:
            营养记录列表
        """
        records = self.memory.get_nutrition_records(user_id, date)
        return [asdict(record) for record in records]

if __name__ == "__main__":
    agent = NutritionAgent()

    print("\n🍎 欢迎使用营养学AI助手！")
    print("输入 'exit' 退出对话\n")

    user_id = input("请输入用户ID（如：user001）：").strip()

    while True:
        message = input("\n你：").strip()
        if message.lower() in {"exit", "quit", "退出"}:
            print("👋 感谢使用，再见！")
            break

        response = agent.chat(user_id, message)
        print(f"\n🤖 营养师：{response}")