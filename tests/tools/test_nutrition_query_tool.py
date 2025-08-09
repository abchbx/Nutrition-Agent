import os
import sys
import unittest
from unittest.mock import patch

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.nutrition_query_tool import NutritionQueryTool


class TestNutritionQueryTool(unittest.TestCase):

    @patch("tools.nutrition_query_tool.NutritionDatabase")
    def setUp(self, mock_nutrition_database):
        # 创建 mock 对象
        self.mock_database = mock_nutrition_database.return_value

        # 创建 NutritionQueryTool 实例
        self.tool = NutritionQueryTool(database=self.mock_database)

    def test_name_and_description(self):
        """测试工具的名称和描述"""
        self.assertEqual(self.tool.name, "nutrition_query_tool")
        self.assertEqual(
            self.tool.description,
            "查询食物的营养成分信息。优先查询本地数据库，如果找不到，则会尝试调用外部API进行自然语言查询。",
        )

    def test_local_database_query(self):
        """测试本地数据库查询"""
        # 设置 mock 返回值
        mock_nutrition_info = {
            "food_name": "苹果",
            "category": "水果",
            "calories": 52,
            "protein": 0.3,
            "carbs": 14,
            "fat": 0.2,
            "fiber": 2.4,
            "vitamin_c": 4.6,
            "calcium": 6,
            "iron": 0.1,
        }
        self.mock_database.get_nutrition_by_name.return_value = mock_nutrition_info

        # 调用工具
        result = self.tool._run("苹果")

        # 验证结果
        self.assertIn("苹果", result)
        self.assertIn("52", result)
        self.mock_database.get_nutrition_by_name.assert_called_once_with("苹果")

    def test_local_database_query_not_found(self):
        """测试本地数据库查询（未找到）"""
        # 设置 mock 返回值
        self.mock_database.get_nutrition_by_name.return_value = None
        self.mock_database.search_nutrition.return_value = []

        # 调用工具
        result = self.tool._run("不存在的食物")

        # 验证结果包含错误信息
        self.assertIn("API 请求失败", result)
        self.mock_database.get_nutrition_by_name.assert_called_once_with("不存在的食物")
        self.mock_database.search_nutrition.assert_called_once_with("不存在的食物", top_k=1)


if __name__ == "__main__":
    unittest.main()
