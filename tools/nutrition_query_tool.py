from typing import Dict, Any, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from nutrition_database import NutritionDatabase

class NutritionQueryInput(BaseModel):
    """营养成分查询工具输入模型"""
    food_name: str = Field(description="要查询的食物名称")
    detailed: bool = Field(default=False, description="是否返回详细信息")

class NutritionQueryTool(BaseTool):
    """营养成分查询工具"""
    name: str = "nutrition_query_tool"
    description: str = "查询食物的营养成分信息，包括热量、蛋白质、碳水化合物、脂肪、维生素等"
    args_schema: Type[BaseModel] = NutritionQueryInput
    database: NutritionDatabase

    def __init__(self, database: NutritionDatabase):
        super().__init__(database=database)

    def _run(self, food_name: str, detailed: bool = False) -> str:
        try:
            nutrition_info = self.database.get_nutrition_by_name(food_name)
            if nutrition_info:
                return self._format_nutrition_info(nutrition_info, detailed)

            search_results = self.database.search_nutrition(food_name, top_k=3)
            if search_results:
                if len(search_results) == 1:
                    return self._format_nutrition_info(search_results[0], detailed)
                else:
                    result_text = f"未找到精确匹配'{food_name}'，但找到了以下相似食物：\n\n"
                    for i, result in enumerate(search_results, 1):
                        result_text += f"{i}. {result['food_name']}（{result['category']}）\n"
                        result_text += f"   热量: {result['calories']}千卡/100g\n"
                        result_text += f"   蛋白质: {result['protein']}g/100g\n\n"
                    result_text += "请指定您想了解的具体食物名称。"
                    return result_text

            return f"抱歉，未找到食物'{food_name}'的营养信息。请尝试其他食物名称。"

        except Exception as e:
            return f"查询营养信息时发生错误: {str(e)}"

    def _format_nutrition_info(self, nutrition_info: Dict[str, Any], detailed: bool) -> str:
        food_name = nutrition_info["food_name"]
        category = nutrition_info["category"]
        result_text = f"🍎 {food_name}（{category}）营养信息：\n\n"
        result_text += f"📊 基础营养（每100g）：\n"
        result_text += f"• 热量: {nutrition_info['calories']} 千卡\n"
        result_text += f"• 蛋白质: {nutrition_info['protein']} g\n"
        result_text += f"• 碳水化合物: {nutrition_info['carbs']} g\n"
        result_text += f"• 脂肪: {nutrition_info['fat']} g\n"

        if detailed:
            result_text += f"\n🌟 详细营养（每100g）：\n"
            result_text += f"• 膳食纤维: {nutrition_info['fiber']} g\n"
            result_text += f"• 维生素C: {nutrition_info['vitamin_c']} mg\n"
            result_text += f"• 钙: {nutrition_info['calcium']} mg\n"
            result_text += f"• 铁: {nutrition_info['iron']} mg\n"

        result_text += f"\n💡 营养评价：\n"
        result_text += self._get_nutrition_evaluation(nutrition_info)
        return result_text

    def _get_nutrition_evaluation(self, nutrition_info: Dict[str, Any]) -> str:
        category = nutrition_info["category"]
        calories = nutrition_info["calories"]
        protein = nutrition_info["protein"]
        evaluations = []

        if calories < 50:
            evaluations.append("低热量食物，适合减肥期间食用")
        elif calories > 200:
            evaluations.append("高热量食物，适量食用")
        else:
            evaluations.append("适中热量食物")

        if protein > 15:
            evaluations.append("富含蛋白质，有助于肌肉生长")
        elif protein < 2:
            evaluations.append("蛋白质含量较低")

        if category == "水果":
            evaluations.append("富含维生素和矿物质，建议每天食用")
        elif category == "蔬菜":
            evaluations.append("富含膳食纤维，有助于消化健康")
        elif category == "肉类":
            evaluations.append("优质蛋白质来源，但注意控制脂肪摄入")
        elif category == "谷物":
            evaluations.append("碳水化合物主要来源，提供能量")
        elif category == "乳制品":
            evaluations.append("富含钙质，有助于骨骼健康")

        return "；".join(evaluations) + "。"

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