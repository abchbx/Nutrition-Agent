import requests
from typing import Dict, Any, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nutrition_database import NutritionDatabase
from config import NUTRITIONIX_API_URL, NUTRITIONIX_APP_ID, NUTRITIONIX_API_KEY

class NutritionQueryInput(BaseModel):
    """营养成分查询工具输入模型"""
    food_name: str = Field(description="要查询的食物名称，可以是简单的食物，也可以是'一杯牛奶和两个鸡蛋'这样的自然语言描述")
    detailed: bool = Field(default=False, description="是否返回详细信息")

class NutritionQueryTool(BaseTool):
    """营养成分查询工具"""
    name: str = "nutrition_query_tool"
    description: str = "查询食物的营养成分信息。优先查询本地数据库，如果找不到，则会尝试调用外部API进行自然语言查询。"
    args_schema: Type[BaseModel] = NutritionQueryInput
    database: NutritionDatabase

    def __init__(self, database: NutritionDatabase):
        super().__init__(database=database)

    def _run(self, food_name: str, detailed: bool = False) -> str:
        # 步骤 1: 优先查询本地数据库
        try:
            nutrition_info = self.database.get_nutrition_by_name(food_name)
            if nutrition_info:
                print(f"✅ 在本地数据库中找到 '{food_name}'")
                return self._format_local_nutrition_info(nutrition_info, detailed)

            # 如果本地找不到精确匹配，模糊搜索一下
            search_results = self.database.search_nutrition(food_name, top_k=1)
            if search_results and search_results[0]['food_name'] == food_name:
                 return self._format_local_nutrition_info(search_results[0], detailed)

        except Exception as e:
            print(f"⚠️ 查询本地数据库时出错: {e}")

        # 步骤 2: 如果本地找不到，调用 Nutritionix API
        print(f"ℹ️ 本地未找到 '{food_name}'，尝试调用 Nutritionix API...")
        if not (NUTRITIONIX_APP_ID and NUTRITIONIX_API_KEY):
            return f"抱歉，本地数据库中未找到'{food_name}'，且未配置外部API密钥。"

        headers = {
            'x-app-id': NUTRITIONIX_APP_ID,
            'x-app-key': NUTRITIONIX_API_KEY,
            'Content-Type': 'application/json'
        }
        data = {
            'query': food_name
        }

        try:
            response = requests.post(NUTRITIONIX_API_URL, headers=headers, json=data)
            response.raise_for_status()  # 如果请求失败 (如 4xx or 5xx), 会抛出异常
            api_data = response.json()
            if api_data and 'foods' in api_data and api_data['foods']:
                return self._format_api_nutrition_info(api_data)
            else:
                return f"抱歉，通过API也未能查询到 '{food_name}' 的营养信息。"
        except requests.exceptions.HTTPError as e:
            return f"API 请求失败: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"调用API时发生未知错误: {str(e)}"

    def _format_local_nutrition_info(self, info: Dict[str, Any], detailed: bool) -> str:
        # ... (这个函数和您之前的版本保持一致) ...
        food_name = info["food_name"]
        category = info["category"]
        result = f"🍎 {food_name}（{category}）[本地数据] 营养信息：\n\n"
        result += f"📊 基础营养（每100g）：\n"
        result += f"• 热量: {info['calories']} 千卡\n"
        result += f"• 蛋白质: {info['protein']} g\n"
        result += f"• 碳水化合物: {info['carbs']} g\n"
        result += f"• 脂肪: {info['fat']} g\n"

        if detailed:
            result += f"\n🌟 详细营养（每100g）：\n"
            result += f"• 膳食纤维: {info['fiber']} g\n"
            result += f"• 维生素C: {info['vitamin_c']} mg\n"
            result += f"• 钙: {info['calcium']} mg\n"
            result += f"• 铁: {info['iron']} mg\n"
        return result

    def _format_api_nutrition_info(self, api_data: Dict[str, Any]) -> str:
        total_calories = sum(food.get('nf_calories', 0) for food in api_data['foods'])
        total_protein = sum(food.get('nf_protein', 0) for food in api_data['foods'])
        total_carbs = sum(food.get('nf_total_carbohydrate', 0) for food in api_data['foods'])
        total_fat = sum(food.get('nf_total_fat', 0) for food in api_data['foods'])

        result = f"营养成分查询结果 [来自 Nutritionix API]:\n"
        result += "----------------------------------------\n"
        result += f"查询内容: '{api_data['foods'][0]['food_name']}'\n"
        result += f"总计热量: {total_calories:.2f} 千卡\n"
        result += f"总计蛋白质: {total_protein:.2f} g\n"
        result += f"总计碳水化合物: {total_carbs:.2f} g\n"
        result += f"总计脂肪: {total_fat:.2f} g\n"
        result += "----------------------------------------\n"

        # 列出每个食物的详细信息
        for food in api_data['foods']:
            result += (
                f"- {food.get('serving_qty', '')} "
                f"{food.get('serving_unit', '')} "
                f"{food.get('food_name', '')}: "
                f"{food.get('nf_calories', 0):.2f} 千卡\n"
            )
        return result

# --- CategorySearchTool 保持不变 ---
class CategorySearchInput(BaseModel):
    """类别搜索工具输入模型"""
    category: str = Field(description="要搜索的食物类别")

class CategorySearchTool(BaseTool):
    """食物类别搜索工具"""
    name: str = "category_search"
    description: str = "搜索特定类别的所有食物，如水果、蔬菜、肉类等"
    args_schema: Type[BaseModel] = CategorySearchInput
    database: NutritionDatabase

    def __init__(self, database: NutritionDatabase):
        super().__init__(database=database)

    def _run(self, category: str) -> str:
        # ... (这部分代码无需修改) ...
        try:
            foods = self.database.get_foods_by_category(category)
            if not foods:
                all_categories = self.database.get_all_categories()
                return f"未找到类别'{category}'的食物。可用类别包括：{', '.join(all_categories)}"

            result_text = f"📂 {category}类食物列表：\n\n"
            for food in foods:
                result_text += f"• {food['food_name']}\n"
                result_text += f"  热量: {food['calories']}千卡/100g | "
                result_text += f"蛋白质: {food['protein']}g/100g\n"

            result_text += f"\n💡 共找到 {len(foods)} 种{category}类食物"
            return result_text

        except Exception as e:
            return f"搜索类别时发生错误: {str(e)}"
