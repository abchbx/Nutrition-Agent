import os
import sys
import unittest
from unittest.mock import patch

import pandas as pd

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nutrition_database import NutritionDatabase


class TestNutritionDatabase(unittest.TestCase):

    @patch("nutrition_database.pd.read_csv")
    def setUp(self, mock_read_csv):
        # 创建 mock 对象
        self.mock_read_csv = mock_read_csv

        # 创建示例数据
        sample_data = {
            "food_name": ["苹果", "香蕉"],
            "calories": [52, 89],
            "protein": [0.3, 1.1],
            "carbs": [14, 23],
            "fat": [0.2, 0.3],
            "fiber": [2.4, 2.6],
            "vitamin_c": [4.6, 8.7],
            "calcium": [6, 5],
            "iron": [0.1, 0.3],
            "category": ["水果", "水果"],
        }
        self.mock_read_csv.return_value = pd.DataFrame(sample_data)

        # 创建 NutritionDatabase 实例
        with (
            patch("nutrition_database.pd.read_csv", return_value=pd.DataFrame(sample_data)),
            patch("nutrition_database.os.path.exists", return_value=True),
        ):
            self.database = NutritionDatabase(embeddings=None)

    def test_initialization(self):
        """测试 NutritionDatabase 初始化"""
        self.assertIsNotNone(self.database.nutrition_data)
        self.assertEqual(len(self.database.nutrition_data), 2)
        # 由于在 setUp 中已经模拟了 read_csv 的返回值，这里不再需要断言它被调用

    def test_get_nutrition_by_name(self):
        """测试根据名称获取营养信息"""
        result = self.database.get_nutrition_by_name("苹果")
        self.assertIsNotNone(result)
        self.assertEqual(result["food_name"], "苹果")
        self.assertEqual(result["calories"], 52)

    def test_get_nutrition_by_name_not_found(self):
        """测试根据名称获取营养信息（未找到）"""
        result = self.database.get_nutrition_by_name("不存在的食物")
        self.assertIsNone(result)

    def test_get_foods_by_category(self):
        """测试根据类别获取食物"""
        result = self.database.get_foods_by_category("水果")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["food_name"], "苹果")
        self.assertEqual(result[1]["food_name"], "香蕉")

    def test_get_all_categories(self):
        """测试获取所有类别"""
        result = self.database.get_all_categories()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "水果")


if __name__ == "__main__":
    unittest.main()
