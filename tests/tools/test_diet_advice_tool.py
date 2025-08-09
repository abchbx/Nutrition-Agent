import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.diet_advice_tool import DietAdviceTool, MealPlanTool


class TestDietAdviceTool(unittest.TestCase):

    @patch("tools.diet_advice_tool.NutritionDatabase")
    @patch("tools.diet_advice_tool.ChatOpenAI")
    def setUp(self, mock_chat_openai, mock_nutrition_database):
        # 创建 mock 对象
        self.mock_database = mock_nutrition_database.return_value
        self.mock_llm = mock_chat_openai.return_value

        # 创建 DietAdviceTool 实例
        self.tool = DietAdviceTool(database=self.mock_database)

    def test_name_and_description(self):
        """测试工具的名称和描述"""
        self.assertEqual(self.tool.name, "diet_advice")
        self.assertEqual(self.tool.description, "根据用户的身体状况和健康目标生成个性化饮食建议")

    def test_get_bmi_status(self):
        """测试 BMI 状态计算"""
        self.assertEqual(self.tool._get_bmi_status(18.0), "偏瘦")
        self.assertEqual(self.tool._get_bmi_status(22.0), "正常")
        self.assertEqual(self.tool._get_bmi_status(26.0), "偏胖")
        self.assertEqual(self.tool._get_bmi_status(30.0), "肥胖")

    def test_run(self):
        """测试运行工具"""
        # 设置 mock 返回值
        self.mock_database.get_all_categories.return_value = ["水果", "蔬菜"]
        self.mock_database.get_foods_by_category.return_value = [
            {"food_name": "苹果", "calories": 52},
            {"food_name": "香蕉", "calories": 89},
        ]

        # 创建 mock 链
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "测试饮食建议"
        self.tool.diet_chain = mock_chain

        # 调用工具
        result = self.tool._run(
            age=30, gender="男", height=175.0, weight=70.0, activity_level="中度活动", health_goal="维持体重"
        )

        # 验证结果
        self.assertIn("测试饮食建议", result)
        self.mock_database.get_all_categories.assert_called_once()


class TestMealPlanTool(unittest.TestCase):

    @patch("tools.diet_advice_tool.NutritionDatabase")
    @patch("tools.diet_advice_tool.ChatOpenAI")
    def setUp(self, mock_chat_openai, mock_nutrition_database):
        # 创建 mock 对象
        self.mock_database = mock_nutrition_database.return_value
        self.mock_llm = mock_chat_openai.return_value

        # 创建 MealPlanTool 实例
        self.tool = MealPlanTool(database=self.mock_database)

    def test_name_and_description(self):
        """测试工具的名称和描述"""
        self.assertEqual(self.tool.name, "meal_plan")
        self.assertEqual(self.tool.description, "生成特定膳食类型的具体食物搭配建议")

    def test_run(self):
        """测试运行工具"""
        # 设置 mock 返回值
        self.mock_database.get_all_categories.return_value = ["水果", "蔬菜"]
        self.mock_database.get_foods_by_category.return_value = [
            {"food_name": "苹果", "calories": 52},
            {"food_name": "香蕉", "calories": 89},
        ]

        # 创建 mock 链
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "测试膳食计划"
        self.tool.meal_chain = mock_chain

        # 调用工具
        result = self.tool._run(meals="早餐", calories_target=300)

        # 验证结果
        self.assertIn("测试膳食计划", result)
        self.mock_database.get_all_categories.assert_called_once()


if __name__ == "__main__":
    unittest.main()
