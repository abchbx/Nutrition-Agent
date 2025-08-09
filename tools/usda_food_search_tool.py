"""
USDA FoodData Central API 工具，用于搜索食品营养信息。
"""

import os
import sys

# 添加项目根目录到路径，以便导入 config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Dict, Type, Optional, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import requests
import config  # 导入配置文件

# 从配置中获取API密钥和基础URL
API_KEY = config.USDA_API_KEY
BASE_URL = config.USDA_API_BASE_URL

# 定义需要关注的营养素ID和名称映射 (可以根据需要扩展)
NUTRIENTS_OF_INTEREST = {
    "1003": "蛋白质",  # Protein
    "1004": "总脂肪",  # Total lipid (fat)
    "1005": "碳水化合物",  # Carbohydrate, by difference
    "1008": "热量",  # Energy (kcal)
    "1079": "纤维",  # Fiber, total dietary
    "1062": "糖",    # Sugars, Total
    "1087": "钙",    # Calcium, Ca
    "1089": "铁",    # Iron, Fe
    "1110": "维生素D", # Vitamin D (D2 + D3)
    "1162": "维生素C", # Vitamin C, total ascorbic acid
    "1109": "维生素B12", # Vitamin B-12
    # 可以添加更多...
}

# --- 工具输入模型 ---
class USDAFoodSearchInput(BaseModel):
    """USDA 食品营养查询工具输入模型"""
    food_name: str = Field(description="要查询的食品名称，例如 '苹果', '鸡胸肉', '全麦面包'")

# --- 工具核心逻辑函数 ---
def _search_food_nutrition_structured(food_query: str, page_size: int = 5) -> Optional[Dict[str, Any]]:
    """
    根据食品名称查询其营养信息，并以结构化字典形式返回。

    Args:
        food_query (str): 用户查询的食品名称。
        page_size (int): 返回结果的数量，默认为5。

    Returns:
        Optional[Dict[str, Any]]: 包含食品名称和营养信息的字典，如果查询失败则返回None。
        Example:
        {
            "food_name": "Apple",
            "nutrients": {
                "热量": 52.0,
                "蛋白质": 0.3,
                "总脂肪": 0.2,
                "碳水化合物": 14.0,
                ...
            }
        }
    """
    if not API_KEY:
        # print("警告: USDA_API_KEY 未配置，无法查询USDA数据库。")
        return None

    url = f"{BASE_URL}/foods/search"
    params = {
        "api_key": API_KEY,
        "query": food_query,
        "pageSize": page_size,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("foods"):
            return None

        # 处理返回的第一个最相关的食品
        food_item = data["foods"][0]
        food_name = food_item.get("description", "未知食品")

        nutrients = food_item.get("foodNutrients", [])
        
        # 创建一个字典来存储我们关心的营养素
        nutrient_values = {}
        for nutrient in nutrients:
            nutrient_id = str(nutrient.get("nutrientId"))
            if nutrient_id in NUTRIENTS_OF_INTEREST:
                nutrient_name = NUTRIENTS_OF_INTEREST[nutrient_id]
                value = nutrient.get("value", 0.0)
                # unit = nutrient.get("unitName", "")
                nutrient_values[nutrient_name] = float(value)

        return {
            "food_name": food_name,
            "nutrients": nutrient_values
        }

    except requests.exceptions.RequestException as e:
        # print(f"USDA API 请求错误: {e}")
        return None
    except Exception as e:
        # print(f"处理USDA API响应时发生错误: {e}")
        return None


def _search_food_nutrition(food_query: str, page_size: int = 5) -> Optional[str]:
    """
    根据食品名称查询其营养信息，并以格式化字符串形式返回。

    Args:
        food_query (str): 用户查询的食品名称。
        page_size (int): 返回结果的数量，默认为5。

    Returns:
        Optional[str]: 格式化后的营养信息字符串，如果查询失败则返回None。
    """
    structured_data = _search_food_nutrition_structured(food_query, page_size)
    if not structured_data:
        return f"未找到与 '{food_query}' 相关的食品信息或查询失败。"

    food_name = structured_data["food_name"]
    nutrients = structured_data["nutrients"]

    # 格式化输出
    result_lines = [f"食品: {food_name}"]
    if nutrients:
        result_lines.append("主要营养成分 (每100g或默认份量):")
        # 按照一定顺序展示关键营养素
        key_nutrients = ["热量", "蛋白质", "总脂肪", "碳水化合物", "纤维", "糖", "钙", "铁", "维生素C"]
        for key in key_nutrients:
            if key in nutrients:
                 # 特别处理热量，通常展示为整数
                if key == "热量":
                    kcal_value = int(nutrients[key])
                    result_lines.append(f"  - {key}: {kcal_value} kcal")
                else:
                    result_lines.append(f"  - {key}: {nutrients[key]} g")
        
        # 添加其他找到的营养素
        for name, value in nutrients.items():
            if name not in key_nutrients:
                 # 特别处理热量，通常展示为整数
                if name == "热量":
                    kcal_value = int(value)
                    result_lines.append(f"  - {name}: {kcal_value} kcal")
                else:
                    result_lines.append(f"  - {name}: {value} g")

    else:
        result_lines.append("未找到详细的营养成分信息。")

    # 添加来源说明
    result_lines.append("\n(数据来源: USDA FoodData Central)")

    return "\n".join(result_lines)

# --- LangChain BaseTool 类 ---
class USDAFoodSearchTool(BaseTool):
    """USDA 食品营养查询工具"""

    name: str = "usda_food_search_tool"
    description: str = (
        "一个用于查询食品营养信息的工具，数据来源于权威的美国农业部(USDA)食品数据库。"
        "当用户询问特定食品（如苹果、鸡胸肉、牛奶等）的热量、蛋白质、脂肪、碳水化合物或其他营养成分时，请使用此工具。"
        "输入应为食品的名称。"
    )
    args_schema: Type[BaseModel] = USDAFoodSearchInput

    def _run(self, food_name: str) -> str:
        """运行工具 (返回格式化字符串)"""
        return _search_food_nutrition(food_name)

    async def _arun(self, food_name: str) -> str:
        """异步运行工具 (如果需要)"""
        return _search_food_nutrition(food_name)

# --- 为 LangChain 工具准备的包装函数 (如果直接传递函数给 Agent) ---
def get_usda_food_search_tool():
    """
    返回一个可被 LangChain Agent 调用的工具函数。
    这个函数可以被直接传递给 Agent。
    (当前项目结构使用 Tool 类，这个函数主要用于演示或兼容性)
    """
    def tool_func(food_name: str) -> str:
        """根据食品名称查询其营养信息。"""
        return _search_food_nutrition(food_name)
    
    # 设置工具的元数据，供 LangChain Agent 识别
    tool_func.name = "usda_food_search"
    tool_func.description = (
        "一个用于查询食品营养信息的工具。"
        "当用户询问特定食品的热量、蛋白质、脂肪、碳水化合物或其他营养成分时，请使用此工具。"
        "输入应为食品的名称，例如 '苹果', '鸡胸肉', '全麦面包'。"
    )
    return tool_func

# --- 示例用法 ---
if __name__ == "__main__":
    # 测试API调用
    # 注意：直接运行此脚本时，需要确保 config.py 在正确的路径下
    # 或者从项目根目录运行: python -m tools.usda_food_search_tool
    query = "苹果"
    result = _search_food_nutrition(query)
    if result:
        print("--- 格式化输出 ---")
        print(result)
        
        print("\n--- 结构化输出 ---")
        structured_result = _search_food_nutrition_structured(query)
        if structured_result:
            print(structured_result)
        else:
            print("结构化查询失败。")
    else:
        print("查询失败。")