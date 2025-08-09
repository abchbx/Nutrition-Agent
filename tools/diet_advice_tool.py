# 添加项目根目录到路径
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Type

from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import AGENT_MODEL, AGENT_TEMPERATURE
from nutrition_database import NutritionDatabase

# Setup logger for diet_advice_tool.py
from config import agent_logger as logger  # Re-use agent logger or create a new one if needed


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
    database: Any

    llm: Any = None
    diet_prompt: Any = None
    diet_chain: Any = None

    def __init__(self, database: NutritionDatabase):
        super().__init__(database=database)

        self.llm = ChatOpenAI(model_name=AGENT_MODEL, temperature=AGENT_TEMPERATURE)
        self.diet_prompt = PromptTemplate(
            input_variables=["user_info", "available_foods"],
            template="""
你是一位经验丰富的注册营养师 (RDN)，名叫"小营"。请根据以下用户信息，为用户生成一份结构清晰、科学专业的个性化饮食建议报告。

**用户信息:**
{user_info}

**可用食物类别参考:**
{available_foods}

---
**## 报告输出要求**
请严格按照以下 Markdown 格式组织报告内容，确保每个部分都有明确的二级标题，并且内容具体、可操作：

## 📊 健康数据与热量评估
* **每日总热量需求:** (计算结果) 千卡
* **宏量营养素分配:**
    * 蛋白质: (百分比和克数)
    * 碳水化合物: (百分比和克数)
    * 脂肪: (百分比和克数)

## 🎯 针对性饮食核心原则
* (根据用户的健康目标，列出3-4条核心饮食原则，每条原则应具体且可执行)

## 🍽️ 一日三餐饮食示例
* **早餐 (约XX千卡):**
    * 主食: (食物与份量)
    * 蛋白质: (食物与份量)
    * 蔬果: (食物与份量)
* **午餐 (约XX千卡):**
    * 主食: (食物与份量)
    * 蛋白质: (食物与份量)
    * 蔬果: (食物与份量)
* **晚餐 (约XX千卡):**
    * 主食: (食物与份量)
    * 蛋白质: (食物与份量)
    * 蔬果: (食物与份量)
* **加餐 (可选):**
    * (建议的加餐食物与份量)

## 💡 特别建议与注意事项
* (针对用户的健康目标和饮食限制，提供具体的建议)
* (列出需要注意的饮食禁忌或潜在风险)

## 📅 一周饮食计划概览 (可选)
* (以表格或列表形式，简洁地展示一周的饮食安排，例如: 周一: 高蛋白; 周二: 清淡...)

请确保语言专业、易懂，建议科学合理且具有可操作性。
合理使用表情符号和格式化来增强可读性。
重要信息要突出显示，复杂概念要用简单语言解释。
""",
        )
        self.diet_chain = self.diet_prompt | self.llm

    def _run(
        self,
        age: int,
        gender: str,
        height: float,
        weight: float,
        activity_level: str,
        health_goal: str,
        dietary_restrictions: str = "无",
        preferences: str = "无",
    ) -> str:
        try:
            logger.info(
                "开始生成饮食建议: 年龄=%d, 性别=%s, 身高=%.1f, 体重=%.1f, 活动水平=%s, 健康目标=%s",
                age,
                gender,
                height,
                weight,
                activity_level,
                health_goal,
            )
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
- **年龄:** {age}岁
- **性别:** {gender}
- **身高:** {height}cm
- **体重:** {weight}kg
- **BMI:** {bmi:.1f}
- **基础代谢率:** {bmr:.0f}千卡/天
- **活动水平:** {activity_level}
- **健康目标:** {health_goal}
- **饮食限制:** {dietary_restrictions}
- **食物偏好:** {preferences}
"""

            diet_advice = self.diet_chain.invoke({"user_info": user_info, "available_foods": available_foods})

            result = "📊 **健康数据计算结果**\n"
            result += f"- **BMI:** {bmi:.1f} ({self._get_bmi_status(bmi)})\n"
            result += f"- **基础代谢率:** {bmr:.0f} 千卡/天\n"
            result += f"- **估算每日总热量需求:** {total_calories:.0f} 千卡/天\n\n"
            result += "--- \n"
            result += "🍽️ **个性化饮食建议报告**\n"
            result += diet_advice

            logger.info("成功生成饮食建议")
            return result

        except Exception as e:
            logger.error("生成饮食建议时发生错误: %s", str(e))
            return f"生成饮食建议时发生错误: {str(e)}"

    def _get_available_foods_info(self, dietary_restrictions: str) -> str:
        try:
            categories = self.database.get_all_categories()
            foods_info = ""
            for category in categories:
                if dietary_restrictions == "素食" and category in ["肉类"]:
                    continue
                if dietary_restrictions == "无麸质" and category == "谷物":
                    foods_info += f"- **{category}:** 建议选择无麸质谷物\n"
                    continue
                foods = self.database.get_foods_by_category(category)
                if foods:
                    food_names = [food["food_name"] for food in foods]
                    foods_info += f"- **{category}:** {', '.join(food_names)}\n"
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
    database: Any

    llm: Any = None
    meal_prompt: Any = None
    meal_chain: Any = None

    def __init__(self, database: NutritionDatabase):
        super().__init__(database=database)

        self.llm = ChatOpenAI(model_name=AGENT_MODEL, temperature=AGENT_TEMPERATURE)
        self.meal_prompt = PromptTemplate(
            input_variables=["meal_type", "calories_target", "preferences", "available_foods"],
            template="""
你是一位经验丰富的注册营养师 (RDN)，名叫"小营"。请为用户生成一份详细的 **{meal_type}** 计划。

**## 核心要求**
* **🎯 目标热量:** 约 {calories_target} 千卡
* **👍 用户偏好:** {preferences}
* **⚖️ 核心原则:** 确保营养均衡，必须包含优质蛋白质、复合碳水化合物和健康脂肪，并考虑食物多样性。

**## 可用食物参考**
{available_foods}

---
**## 输出格式要求**
请严格按照以下 Markdown 格式生成膳食计划，使用标题、表格和 Emoji 来增强可读性。

### 🍽️ {meal_type} 营养计划 (约 {calories_target} 千卡)

#### 📝 食物清单
| 食物类别 | 食物名称 | 份量 (克) | 估算热量 (千卡) |
| :--- | :--- | :--- | :--- |
| **主食** | (例如: 糙米饭) | (例如: 150) | (例如: 200) |
| **蛋白质** | (例如: 烤鸡胸肉) | (例如: 100) | (例如: 165) |
| **蔬菜** | (例如: 清炒西兰花) | (例如: 200) | (例如: 70) |
| **脂肪** | (例如: 橄榄油) | (例如: 10) | (例如: 90) |
| **总计** | - | - | **(总热量)** |

#### 👨‍🍳 制作建议 (可选)
* (如果需要，请在此处提供简单的制作或准备步骤，使用要点罗列)

#### 👩‍⚕️ 营养师点评
* (在此处提供对这个膳食搭配的专业点评和建议，说明其优点和注意事项)

请确保语言专业、易懂，建议科学合理且具有可操作性。
合理使用表情符号和格式化来增强可读性。
重要信息要突出显示，复杂概念要用简单语言解释。
""",
        )
        self.meal_chain = self.meal_prompt | self.llm

    def _run(self, meals: str, calories_target: int, preferences: str = "无") -> str:
        try:
            logger.info("开始生成膳食计划: 餐食类型=%s, 目标热量=%d, 偏好=%s", meals, calories_target, preferences)
            available_foods = self._get_all_foods_info()
            meal_plan = self.meal_chain.invoke(
                {
                    "meal_type": meals,
                    "calories_target": calories_target,
                    "preferences": preferences,
                    "available_foods": available_foods,
                }
            )
            logger.info("成功生成膳食计划")
            return meal_plan
        except Exception as e:
            logger.error("生成膳食计划时发生错误: %s", str(e))
            return f"生成膳食计划时发生错误: {str(e)}"

    def _get_all_foods_info(self) -> str:
        try:
            categories = self.database.get_all_categories()
            foods_info = ""
            for category in categories:
                foods = self.database.get_foods_by_category(category)
                if foods:
                    food_details = [f"{food['food_name']}({food['calories']}千卡/100g)" for food in foods]
                    foods_info += f"- **{category}:** {', '.join(food_details)}\n"
            return foods_info
        except Exception as e:
            return f"获取食物信息时发生错误: {str(e)}"
