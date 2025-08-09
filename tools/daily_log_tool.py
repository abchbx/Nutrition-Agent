"""
每日饮食记录工具。
允许用户记录他们吃的食物，并将其添加到他们的健康日志中。
"""

import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Dict, Type, Optional, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import logging

# 导入项目模块
from config import agent_logger as logger
from user_memory import UserMemory
# 我们需要一个方法来获取食物的营养信息。
# 最好的方法是利用现有的 NutritionQueryTool 或 USDAFoodSearchTool。
# 为了降低耦合，我们可以接受一个查询函数作为参数，或者直接调用工具。
# 这里我们选择直接调用 USDAFoodSearchTool 来获取权威数据。
# 注意：这需要确保 USDA API key 已配置。
from tools.usda_food_search_tool import _search_food_nutrition_structured # 导入结构化查询函数

# --- 工具输入模型 ---
class DailyLogInput(BaseModel):
    """每日饮食记录工具输入模型"""
    user_id: str = Field(description="用户的唯一ID")
    date: str = Field(description="记录的日期，格式为 YYYY-MM-DD")
    food_description: str = Field(description="用户吃的食物描述，例如 '一个苹果' 或 '100克鸡胸肉'")

# --- 核心逻辑 ---
def _parse_food_description(description: str) -> Dict[str, Any]:
    """
    （简单示例）解析食物描述，提取食物名称和大概的数量/单位。
    实际应用中，这可能需要一个更复杂的NLP模型或规则引擎。
    """
    # 这是一个非常基础的解析器，仅作示例。
    # 在实际应用中，应该更健壮。
    import re
    description = description.strip().lower()
    
    # 尝试匹配 "数量 单位 食物" 或 "数量 食物" 的模式
    # 例如: "1个苹果", "100克鸡胸肉", "一杯牛奶"
    match = re.search(r"(\d*\.?\d+)\s*(\w*?)?\s*(.+)", description)
    if match:
        amount_str, unit, food_name = match.groups()
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 1.0 # 默认数量为1
        if not unit:
            unit = "份" # 默认单位
        return {
            "food_name": food_name.strip(),
            "amount": amount,
            "unit": unit.strip()
        }
    else:
        # 如果无法解析，将整个描述作为食物名称
        return {
            "food_name": description,
            "amount": 1.0,
            "unit": "份"
        }

def _get_nutrition_info(food_name: str) -> Optional[Dict[str, float]]:
    """
    通过 USDAFoodSearchTool 获取食物的营养信息。
    返回的是 per 100g 的结构化数据。
    """
    try:
        # 调用新的结构化查询函数
        structured_data = _search_food_nutrition_structured(food_name)
        if structured_data and "nutrients" in structured_data:
            return structured_data["nutrients"]
        else:
            return None
    except Exception as e:
        logger.error(f"获取食物 '{food_name}' 的营养信息时出错: {e}")
        return None

# --- LangChain BaseTool 类 ---
class DailyLogTool(BaseTool):
    """每日饮食记录工具"""

    name: str = "daily_log_tool"
    description: str = (
        "一个用于记录用户每日饮食的工具。"
        "当用户说'我今天吃了...'或'记录一下我刚吃的...'时，请使用此工具。"
        "需要用户提供用户ID、日期和食物描述。"
    )
    args_schema: Type[BaseModel] = DailyLogInput
    user_memory: UserMemory = Field(default_factory=UserMemory)

    def _run(self, user_id: str, date: str, food_description: str) -> str:
        """运行工具"""
        try:
            logger.info(f"用户 {user_id} 在 {date} 记录食物: {food_description}")
            
            # 1. 解析食物描述
            parsed_info = _parse_food_description(food_description)
            if not parsed_info:
                return f"无法解析食物描述: {food_description}"
            
            food_name = parsed_info["food_name"]
            amount = parsed_info["amount"]
            unit = parsed_info["unit"]
            
            logger.debug(f"解析结果: 食物={food_name}, 数量={amount}, 单位={unit}")

            # 2. 获取食物营养信息 (per 100g or per unit)
            # 注意：这里需要处理单位转换的复杂性。
            # 例如，“一个苹果”是多少克？这需要额外的知识库或估算。
            # 为了简化，我们假设所有查询都基于 per 100g 的数据，并且用户输入的数量是相对的。
            nutrition_per_100g = _get_nutrition_info(food_name)
            if not nutrition_per_100g:
                return f"无法获取食物 '{food_name}' 的营养信息。"
            
            logger.debug(f"食物 '{food_name}' 的营养信息 (per 100g): {nutrition_per_100g}")

            # 3. 计算实际摄入量 (简化处理)
            # 这里我们做一个非常粗略的估算：假设 amount 是相对于 100g 的倍数。
            # 例如，用户说 "200g 鸡胸肉"，则 amount=200, 我们计算 2 倍的营养。
            # 对于 "一个苹果"，amount=1, 我们就按 100g 的数据存入。
            # 这显然不准确，但作为一个起点是可以的。
            # 真正的解决方案需要一个食物份量数据库。
            scale_factor = amount / 100.0 if amount > 0 else 1.0
            if unit != "g" and unit != "克":
                 # 如果单位不是克，这是一个非常粗略的估算
                 logger.warning(f"非克单位 '{unit}' 的估算可能不准确。")
            
            actual_nutrition = {
                "calories": nutrition_per_100g.get("热量", 0) * scale_factor,
                "protein": nutrition_per_100g.get("蛋白质", 0) * scale_factor,
                "carbs": nutrition_per_100g.get("碳水化合物", 0) * scale_factor,
                "fat": nutrition_per_100g.get("总脂肪", 0) * scale_factor,
            }
            
            # 4. 准备要存储的条目数据
            entry_data = {
                "food_name": food_name,
                "amount": amount,
                "unit": unit,
                **actual_nutrition
            }
            
            # 5. 调用 UserMemory 添加记录
            success = self.user_memory.add_daily_log_entry(user_id, date, entry_data)
            
            if success:
                return (f"✅ 成功记录: {amount} {unit} {food_name} "
                        f"(热量: {actual_nutrition['calories']:.1f}kcal, "
                        f"蛋白质: {actual_nutrition['protein']:.1f}g) 到 {date} 的日志中。")
            else:
                return f"❌ 记录食物 '{food_description}' 到日志时失败。"

        except Exception as e:
            logger.error(f"执行每日饮食记录工具时发生错误: {e}", exc_info=True)
            return f"处理您的饮食记录请求时发生内部错误。"

    async def _arun(self, user_id: str, date: str, food_description: str) -> str:
        """异步运行工具"""
        # 对于这种 I/O 密集型操作（文件读写、可能的API调用），异步是有益的。
        # 但 UserMemory 的方法目前是同步的。为了保持一致性，我们暂时使用同步版本。
        # 未来可以考虑将 UserMemory 的方法也改为异步。
        return self._run(user_id, date, food_description)