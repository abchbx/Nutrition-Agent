"""
每日饮食记录工具。
允许用户记录他们吃的食物，并将其添加到他们的健康日志中。
"""

import os
import sys
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Dict, Type, Optional, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import logging

# 导入项目模块
from config import agent_logger as logger
# 导入 LLM 配置
from config import AGENT_MODEL, AGENT_TEMPERATURE, OPENAI_BASE_URL, OPENAI_API_KEY
# 有条件地导入 LLM 类 (假设使用 ChatOpenAI)
try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    logger.warning("langchain_openai not found, LLM-based parsing will be disabled.")
    LLM_AVAILABLE = False

from user_memory import UserMemory
# 我们需要一个方法来获取食物的营养信息。
from tools.usda_food_search_tool import _search_food_nutrition_structured # 导入结构化查询函数

# --- 工具输入模型 ---
class DailyLogInput(BaseModel):
    """每日饮食记录工具输入模型"""
    user_id: str = Field(description="用户的唯一ID")
    date: str = Field(description="记录的日期，格式为 YYYY-MM-DD")
    food_description: str = Field(description="用户吃的食物描述，例如 '一个苹果' 或 '100克鸡胸肉'")

# --- 核心逻辑 ---
def _decompose_food_description(description: str) -> List[str]:
    """
    使用 LLM 将复合食物描述分解为单个食物描述列表。
    """
    if not LLM_AVAILABLE:
        logger.info("LLM 不可用，回退到原始描述。")
        return [description] if description.strip() else []

    try:
        # 创建一个轻量级的 LLM 实例用于解析
        # 注意：复用主 LLM 的配置，但在生产环境中可能需要一个专用的、更快/更便宜的模型
        parsing_llm = ChatOpenAI(
            model_name=AGENT_MODEL, 
            temperature=0.0, # 解析任务应使用较低的温度以保证一致性
            openai_api_base=OPENAI_BASE_URL,
            openai_api_key=OPENAI_API_KEY
        )
        
        prompt = f"""
请将以下用户的饮食描述分解为一个或多个独立的食物项。
每个食物项应尽可能简洁，并包含数量和单位信息（如果有的话）。
请以严格的 JSON 列表格式返回，例如 ["1个苹果", "200ml 牛奶"]。

用户描述: {description}
"""
        response = parsing_llm.predict(prompt)
        # 尝试解析 LLM 的响应为 JSON
        return json.loads(response.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"LLM 返回的响应不是有效的 JSON: {e}. 响应内容: {response if 'response' in locals() else 'N/A'}")
    except Exception as e:
        logger.error(f"使用 LLM 分解食物描述失败: {e}")
    
    # 如果 LLM 失败，回退到原始描述
    return [description] if description.strip() else []


def _parse_food_description(description: str) -> Dict[str, Any]:
    """
    （改进版）解析单个食物描述，提取食物名称和大概的数量/单位。
    """
    # 这是一个改进的基础解析器。
    import re
    description = description.strip().lower()
    
    # 尝试匹配 "数量 单位 食物" 或 "数量 食物" 的模式
    # 例如: "1个苹果", "100克鸡胸肉", "一杯牛奶"
    # 改进：更灵活的数字匹配，支持分数 (如 "半杯")
    match = re.search(r"(\d*\.?\d+|\b半\b)?\s*(\w*?)?\s*(.+)", description)
    if match:
        amount_str, unit, food_name = match.groups()
        amount = 1.0 # 默认数量为1
        if amount_str:
            if amount_str.strip() == "半":
                amount = 0.5
            else:
                try:
                    amount = float(amount_str)
                except ValueError:
                    pass # 保持默认值1.0
        
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
            
            # 1. 使用 LLM 分解复合描述
            food_descriptions = _decompose_food_description(food_description)
            logger.debug(f"分解后的食物描述: {food_descriptions}")

            results = []
            total_calories = 0.0
            total_protein = 0.0

            for single_food_desc in food_descriptions:
                # 2. 解析单个食物描述
                parsed_info = _parse_food_description(single_food_desc)
                if not parsed_info:
                    results.append(f"无法解析食物描述: {single_food_desc}")
                    continue
                
                food_name = parsed_info["food_name"]
                amount = parsed_info["amount"]
                unit = parsed_info["unit"]
                
                logger.debug(f"解析结果: 食物={food_name}, 数量={amount}, 单位={unit}")

                # 3. 获取食物营养信息 (per 100g or per unit)
                nutrition_per_100g = _get_nutrition_info(food_name)
                if not nutrition_per_100g:
                    results.append(f"无法获取食物 '{food_name}' 的营养信息。")
                    continue
                
                logger.debug(f"食物 '{food_name}' 的营养信息 (per 100g): {nutrition_per_100g}")

                # 4. 计算实际摄入量 (简化处理)
                # 注意：这里仍然需要更精确的单位换算
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
                
                # 累计总营养
                total_calories += actual_nutrition['calories']
                total_protein += actual_nutrition['protein']

                # 5. 准备要存储的条目数据
                entry_data = {
                    "food_name": food_name,
                    "amount": amount,
                    "unit": unit,
                    **actual_nutrition
                }
                
                # 6. 调用 UserMemory 添加记录
                success = self.user_memory.add_daily_log_entry(user_id, date, entry_data)
                
                if success:
                    results.append(f"✅ 记录: {amount} {unit} {food_name} "
                                   f"(热量: {actual_nutrition['calories']:.1f}kcal, "
                                   f"蛋白质: {actual_nutrition['protein']:.1f}g)")
                else:
                    results.append(f"❌ 记录食物 '{single_food_desc}' 到日志时失败。")

            # 7. 汇总返回结果
            if not results:
                return "❌ 未能处理任何食物描述。"
            
            summary = f"### 📝 饮食记录摘要 ({date})\n\n"
            summary += "\n".join(results)
            summary += f"\n\n📊 **总计**: 热量 {total_calories:.1f}kcal, 蛋白质 {total_protein:.1f}g"
            
            return summary

        except Exception as e:
            logger.error(f"执行每日饮食记录工具时发生错误: {e}", exc_info=True)
            return f"处理您的饮食记录请求时发生内部错误。"

    async def _arun(self, user_id: str, date: str, food_description: str) -> str:
        """异步运行工具"""
        # 对于这种 I/O 密集型操作（文件读写、可能的API调用），异步是有益的。
        # 但 UserMemory 的方法目前是同步的。为了保持一致性，我们暂时使用同步版本。
        # 未来可以考虑将 UserMemory 的方法也改为异步。
        return self._run(user_id, date, food_description)