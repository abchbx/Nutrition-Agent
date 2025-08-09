# 添加项目根目录到路径
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Dict, Type

import requests
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from config import NUTRITIONIX_API_URL, NUTRITIONIX_APP_ID, NUTRITIONIX_API_KEY
from nutrition_database import NutritionDatabase

# Setup logger for nutrition_query_tool.py
from config import agent_logger as logger  # Re-use agent logger or create a new one if needed


class NutritionQueryInput(BaseModel):
    """营养成分查询工具输入模型"""

    food_name: str = Field(description="要查询的食物名称，可以是简单的食物，也可以是'一杯牛奶和两个鸡蛋'这样的自然语言描述")
    detailed: bool = Field(default=False, description="是否返回详细信息")


class NutritionQueryTool(BaseTool):
    """营养成分查询工具"""

    name: str = "nutrition_query_tool"
    description: str = "查询食物的营养成分信息。优先查询本地数据库，如果找不到，则会尝试调用外部API进行自然语言查询。"
    args_schema: Type[BaseModel] = NutritionQueryInput
    database: Any

    def __init__(self, database: NutritionDatabase):
        super().__init__(database=database)
        self.database = database

    def _run(self, food_name: str, detailed: bool = False) -> str:
        logger.info("开始查询食物营养信息: %s", food_name)
        # 步骤 1: 优先查询本地数据库
        try:
            nutrition_info = self.database.get_nutrition_by_name(food_name)
            if nutrition_info:
                print(f"✅ 在本地数据库中找到 '{food_name}'")
                logger.info("在本地数据库中找到 '%s'", food_name)
                return self._format_local_nutrition_info(nutrition_info, detailed)

            # 如果本地找不到精确匹配，模糊搜索一下
            search_results = self.database.search_nutrition(food_name, top_k=3)
            if search_results:
                # 检查是否有一个非常接近的匹配
                for result in search_results:
                    # 使用简单的字符串相似度检查
                    if (
                        result["food_name"].lower() == food_name.lower()
                        or food_name.lower() in result["food_name"].lower()
                        or result["food_name"].lower() in food_name.lower()
                    ):
                        logger.info("通过模糊搜索找到相似食物 '%s' 匹配查询 '%s'", result["food_name"], food_name)
                        return self._format_local_nutrition_info(result, detailed)

                # 如果没有精确或接近的匹配，返回最相似的结果供用户选择
                logger.info("本地数据库未找到精确匹配，返回最相似的%d个结果", len(search_results))
                similar_foods = [f"'{result['food_name']}'" for result in search_results]
                return f"本地数据库中未找到'{food_name}'，您是否想查询: {', '.join(similar_foods)}？"

        except Exception as e:
            print(f"⚠️ 查询本地数据库时出错: {e}")
            logger.error("查询本地数据库时出错: %s", e)

        # 步骤 2: 如果本地找不到，调用 Nutritionix API
        print(f"ℹ️ 本地未找到 '{food_name}'，尝试调用 Nutritionix API...")
        logger.info("本地未找到 '%s'，尝试调用 Nutritionix API...", food_name)
        if not (NUTRITIONIX_APP_ID and NUTRITIONIX_API_KEY):
            logger.warning("未配置 Nutritionix API 密钥")
            return f"抱歉，本地数据库中未找到'{food_name}'，且未配置外部API密钥。"

        headers = {"x-app-id": NUTRITIONIX_APP_ID, "x-app-key": NUTRITIONIX_API_KEY, "Content-Type": "application/json"}
        data = {"query": food_name}

        try:
            # 添加超时设置
            response = requests.post(NUTRITIONIX_API_URL, headers=headers, json=data, timeout=10)
            response.raise_for_status()  # 如果请求失败 (如 4xx or 5xx), 会抛出异常
            api_data = response.json()
            if api_data and "foods" in api_data and api_data["foods"]:
                logger.info("通过 Nutritionix API 成功查询到 '%s' 的营养信息", food_name)
                return self._format_api_nutrition_info(api_data)
            else:
                logger.info("通过 Nutritionix API 未能查询到 '%s' 的营养信息", food_name)
                return f"抱歉，通过API也未能查询到 '{food_name}' 的营养信息。"
        except requests.exceptions.Timeout:
            logger.error("API 请求超时")
            return "API 请求超时，请稍后再试。"
        except requests.exceptions.HTTPError as e:
            logger.error("API 请求失败: %s %s", e.response.status_code, e.response.text)
            return f"API 请求失败: {e.response.status_code} {e.response.text}"
        except Exception as e:
            logger.error("调用API时发生未知错误: %s", str(e))
            return f"调用API时发生未知错误: {str(e)}"

    def _format_local_nutrition_info(self, info: Dict[str, Any], detailed: bool) -> str:
        """格式化本地数据库查询结果，符合 Agent 的 nutrition_query 模板"""
        food_name = info["food_name"]
        result = "### 🍎 食物营养查询\n\n"
        result += f"*   **食物名称**: {food_name}\n"
        result += "*   **来源**: 本地数据\n"
        result += "*   **基础营养 (每100g)**:\n"
        result += f"    *   热量: {info['calories']} 千卡\n"
        result += f"    *   蛋白质: {info['protein']} g\n"
        result += f"    *   碳水化合物: {info['carbs']} g\n"
        result += f"    *   脂肪: {info['fat']} g\n"

        if detailed:
            result += "*   **详细营养 (每100g)**:\n"
            result += f"    *   膳食纤维: {info['fiber']} g\n"
            result += f"    *   维生素C: {info['vitamin_c']} mg\n"
            result += f"    *   钙: {info['calcium']} mg\n"
            result += f"    *   铁: {info['iron']} mg\n"
        return result

    def _format_api_nutrition_info(self, api_data: Dict[str, Any]) -> str:
        """格式化API查询结果，符合 Agent 的 nutrition_query 模板"""
        # Nutritionix API 通常返回的是具体份量的食物信息，而不是每100g的。
        # 我们直接列出每个食物项，并在最后给出总计。
        foods = api_data["foods"]
        result = "### 🍎 食物营养查询\n\n"

        # 如果只有一个食物项，可以尝试给出标准化信息
        if len(foods) == 1:
            food = foods[0]
            food_name = food.get("food_name", "未知食物")
            result += f"*   **食物名称**: {food_name}\n"
            result += "*   **来源**: 来自 Nutritionix API\n"
            result += f"*   **基础营养 (份量: {food.get('serving_qty', '')} {food.get('serving_unit', '')})**:\n"
            result += f"    *   热量: {food.get('nf_calories', 0):.2f} 千卡\n"
            result += f"    *   蛋白质: {food.get('nf_protein', 0):.2f} g\n"
            result += f"    *   碳水化合物: {food.get('nf_total_carbohydrate', 0):.2f} g\n"
            result += f"    *   脂肪: {food.get('nf_total_fat', 0):.2f} g\n"
        else:
            # 多个食物项，列出每个并给出总计
            result += "*   **来源**: 来自 Nutritionix API (复合查询)\n"
            result += "*   **总计营养**:\n"
            total_calories = sum(food.get("nf_calories", 0) for food in foods)
            total_protein = sum(food.get("nf_protein", 0) for food in foods)
            total_carbs = sum(food.get("nf_total_carbohydrate", 0) for food in foods)
            total_fat = sum(food.get("nf_total_fat", 0) for food in foods)
            result += f"    *   热量: {total_calories:.2f} 千卡\n"
            result += f"    *   蛋白质: {total_protein:.2f} g\n"
            result += f"    *   碳水化合物: {total_carbs:.2f} g\n"
            result += f"    *   脂肪: {total_fat:.2f} g\n"
            result += "\n*   **详细列表**:\n"
            for food in foods:
                result += (
                    f"    *   {food.get('serving_qty', '')} "
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
    database: Any

    def __init__(self, database: NutritionDatabase):
        super().__init__(database=database)
        self.database = database

    def _run(self, category: str) -> str:
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
