from typing import Any, Type
from langchain_core.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI 
from langchain.chains import LLMChain
from pydantic import BaseModel, Field
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nutrition_database import NutritionDatabase
from config import AGENT_MODEL, AGENT_TEMPERATURE

class DietAdviceInput(BaseModel):
    """饮食建议工具输入模型"""
    age: int = Field(description="年龄")
    gender: str = Field(description="性别，男或女")
    height: float = Field(description="身高(cm)")
    weight: float = Field(description="体重(kg)")
    activity_level: str = Field(description="活动水平：久坐、轻度活动、中度活动、重度活动")
    health_goal: str = Field(description="健康目标：减肥、增重、维持体重、增肌、改善健康等")
    dietary_restrictions: str = Field(default="无", description="饮食限制：素食、无麸质、低糖等")
    preferences: str = Field(default="无", description="食物偏好或不喜欢")

class DietAdviceTool(BaseTool):
    """饮食建议生成工具"""
    name: str = "diet_advice"
    description: str = "根据用户的身体状况和健康目标生成个性化饮食建议"
    args_schema: Type[BaseModel] = DietAdviceInput
    database: NutritionDatabase

    # --- 修改开始：为字段提供默认值 None ---
    llm: Any = None
    diet_prompt: Any = None
    diet_chain: Any = None
    # --- 修改结束 ---

    def __init__(self, database: NutritionDatabase):
        super().__init__(database=database)

        self.llm = ChatOpenAI(
            model_name=AGENT_MODEL,
            temperature=AGENT_TEMPERATURE
        )
        self.diet_prompt = PromptTemplate(
            input_variables=["user_info", "available_foods"],
            template="""
你是一位专业的营养师，请根据以下用户信息生成个性化的饮食建议：

用户信息：
{user_info}

可用食物类别及营养特点：
{available_foods}

请提供以下内容：
1. 每日热量需求估算
2. 营养素分配建议（蛋白质、碳水化合物、脂肪的比例）
3. 一日三餐的具体建议（包括食物搭配和份量）
4. 针对健康目标的特别建议
5. 饮食注意事项和禁忌
6. 一周的饮食计划示例

请用专业、易懂的语言提供建议，并确保建议科学合理。

---
**格式要求：**
对于“一日三餐的具体建议”和“一周的饮食计划示例”部分，请严格使用Markdown的任务列表（todo list）格式输出。每一项饮食建议前都应有 `- [ ]`。

例如：
- [ ] 早餐：牛奶一杯、全麦面包两片
- [ ] 上午加餐：苹果一个
- [ ] 午餐：...
"""
        )
        self.diet_chain = LLMChain(llm=self.llm, prompt=self.diet_prompt)
    
    def _run(self, age: int, gender: str, height: float, weight: float,
             activity_level: str, health_goal: str, dietary_restrictions: str = "无",
             preferences: str = "无") -> str:
        # ... 此处及之后的代码无需改动 ...
        try:
            bmi = weight / ((height / 100) ** 2)
            if gender.lower() == "男":
                bmr = 10 * weight + 6.25 * height - 5 * age + 5
            else:
                bmr = 10 * weight + 6.25 * height - 5 * age - 161

            activity_multipliers = {"久坐": 1.2, "轻度活动": 1.375, "中度活动": 1.55, "重度活动": 1.725}
            activity_multiplier = activity_multipliers.get(activity_level, 1.375)
            total_calories = bmr * activity_multiplier

            if health_goal == "减肥":
                total_calories *= 0.8
            elif health_goal == "增重":
                total_calories *= 1.2
            elif health_goal == "增肌":
                total_calories *= 1.15

            available_foods = self._get_available_foods_info(dietary_restrictions)

            user_info = f"""
年龄: {age}岁
性别: {gender}
身高: {height}cm
体重: {weight}kg
BMI: {bmi:.1f}
基础代谢率: {bmr:.0f}千卡/天
总热量需求: {total_calories:.0f}千卡/天
活动水平: {activity_level}
健康目标: {health_goal}
饮食限制: {dietary_restrictions}
食物偏好: {preferences}
"""

            diet_advice = self.diet_chain.run(
                user_info=user_info,
                available_foods=available_foods
            )

            result = f"📊 健康数据计算结果：\n"
            result += f"• BMI: {bmi:.1f} ({self._get_bmi_status(bmi)})\n"
            result += f"• 基础代谢率: {bmr:.0f} 千卡/天\n"
            result += f"• 每日总热量需求: {total_calories:.0f} 千卡/天\n\n"
            result += "🍽️ 个性化饮食建议：\n"
            result += "=" * 50 + "\n"
            result += diet_advice
            return result

        except Exception as e:
            return f"生成饮食建议时发生错误: {str(e)}"

    def _get_available_foods_info(self, dietary_restrictions: str) -> str:
        try:
            categories = self.database.get_all_categories()
            foods_info = ""
            for category in categories:
                if dietary_restrictions == "素食" and category in ["肉类"]:
                    continue
                if dietary_restrictions == "无麸质" and category == "谷物":
                    foods_info += f"{category}: 建议选择无麸质谷物\n"
                    continue
                foods = self.database.get_foods_by_category(category)
                if foods:
                    food_names = [food["food_name"] for food in foods]
                    foods_info += f"{category}: {', '.join(food_names)}\n"
            return foods_info
        except Exception as e:
            return f"获取食物信息时发生错误: {str(e)}"

    def _get_bmi_status(self, bmi: float) -> str:
        if bmi < 18.5:
            return "偏瘦"
        elif bmi < 24:
            return "正常"
        elif bmi < 28:
            return "偏胖"
        else:
            return "肥胖"

class MealPlanInput(BaseModel):
    """膳食计划工具输入模型"""
    meals: str = Field(description="膳食类型：早餐、午餐、晚餐或加餐")
    calories_target: int = Field(description="目标热量")
    preferences: str = Field(default="无", description="食物偏好")

class MealPlanTool(BaseTool):
    """膳食计划生成工具"""
    name: str = "meal_plan"
    description: str = "生成特定膳食类型的具体食物搭配建议"
    args_schema: Type[BaseModel] = MealPlanInput
    database: NutritionDatabase

    # --- 修改开始：为字段提供默认值 None ---
    llm: Any = None
    meal_prompt: Any = None
    meal_chain: Any = None
    # --- 修改结束 ---

    def __init__(self, database: NutritionDatabase):
        super().__init__(database=database)

        self.llm = ChatOpenAI(
            model_name=AGENT_MODEL,
            temperature=AGENT_TEMPERATURE
        )
        self.meal_prompt = PromptTemplate(
            input_variables=["meal_type", "calories_target", "preferences", "available_foods"],
            template="""
你是一位专业营养师，请为用户生成一份 {meal_type} 的具体食物搭配建议。

**基础要求：**
- **目标热量：** 约 {calories_target} 千卡
- **用户偏好：** {preferences}
- **核心原则：** 营养均衡，包含蛋白质、碳水化合物、健康脂肪，并考虑食物多样性。

**可用食物参考：**
{available_foods}

---
**输出格式要求：**
请严格按照Markdown格式生成膳食计划，使用标题、表格和要点来组织内容。

### 🍽️ {meal_type} 计划 (约 {calories_target} 千卡)

#### 🍳 食物清单
* (在此处提供食物清单，使用表格列出每道菜的名称、热量和份量)

#### 🍳 制作建议
* (如果需要，请在此处提供简单的制作或准备步骤，使用要点罗列)

#### 👩‍⚕️ 营养师点评
* (在此处提供对这个膳食搭配的专业点评和建议)
"""
        )
        self.meal_chain = LLMChain(llm=self.llm, prompt=self.meal_prompt)

    def _run(self, meals: str, calories_target: int, preferences: str = "无") -> str:
        # ... 此处及之后的代码无需改动 ...
        try:
            available_foods = self._get_all_foods_info()
            meal_plan = self.meal_chain.run(
                meal_type=meals,
                calories_target=calories_target,
                preferences=preferences,
                available_foods=available_foods
            )

            result = f"🍽️ {meals}计划（目标热量：{calories_target}千卡）：\n"
            result += "=" * 50 + "\n"
            result += meal_plan
            return result

        except Exception as e:
            return f"生成膳食计划时发生错误: {str(e)}"

    def _get_all_foods_info(self) -> str:
        try:
            categories = self.database.get_all_categories()
            foods_info = ""
            for category in categories:
                foods = self.database.get_foods_by_category(category)
                if foods:
                    food_details = [
                        f"{food['food_name']}({food['calories']}千卡/100g)"
                        for food in foods
                    ]
                    foods_info += f"{category}: {', '.join(food_details)}\n"
            return foods_info
        except Exception as e:
            return f"获取食物信息时发生错误: {str(e)}"