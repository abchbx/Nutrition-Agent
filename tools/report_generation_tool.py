"""
报告生成工具。
根据用户的健康日志数据生成周报或月报。
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Type, Optional, List

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# 导入项目模块
from config import agent_logger as logger
from user_memory import UserMemory, DailyLog


# --- 工具输入模型 ---
class ReportGenerationInput(BaseModel):
    """报告生成工具输入模型"""
    user_id: str = Field(description="用户的唯一ID")
    report_type: str = Field(description="报告类型，'weekly' 或 'monthly'")
    # date: str = Field(description="报告的结束日期，格式为 YYYY-MM-DD。如果为空，则默认为今天。") # 可选优化

# --- 核心逻辑 (占位符) ---
def _generate_report_content(user_id: str, report_type: str, end_date_str: str) -> str:
    """
    (占位符) 根据用户日志生成报告内容。
    这是一个复杂的功能，需要实现：
    1. 计算日期范围
    2. 从 UserMemory 获取该范围内的日志
    3. 分析营养摄入数据（平均值、总和等）
    4. 与用户目标进行比较
    5. 生成自然语言分析和建议
    """
    # TODO: 实现完整的报告生成逻辑
    # 这将涉及数据分析和可能调用 LLM 来生成自然语言摘要
    
    # 示例占位符逻辑
    try:
        user_memory = UserMemory()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        if report_type == "weekly":
            start_date = end_date - timedelta(days=7)
            period_str = "过去一周"
        elif report_type == "monthly":
            # 简单地减去30天作为示例
            start_date = end_date - timedelta(days=30)
            period_str = "过去一个月"
        else:
            return f"不支持的报告类型: {report_type}"

        start_date_str = start_date.strftime("%Y-%m-%d")
        
        logs: Optional[List[DailyLog]] = user_memory.get_daily_logs_for_period(user_id, start_date_str, end_date_str)
        
        if not logs:
            return f"在 {period_str} ({start_date_str} 至 {end_date_str}) 内未找到任何饮食记录。"
            
        total_calories = 0.0
        total_protein = 0.0
        total_days = len(logs)
        
        for log in logs:
            for entry in log.entries:
                total_calories += entry.calories or 0
                total_protein += entry.protein or 0
        
        avg_calories = total_calories / total_days if total_days > 0 else 0
        avg_protein = total_protein / total_days if total_days > 0 else 0

        # 这里应该加入更多分析和与用户目标的对比
        # 以及调用 LLM 生成更自然、个性化的文本
        
        report = (
            f"### 📊 您的{period_str}营养报告 ({start_date_str} 至 {end_date_str})\n\n"
            f"- **记录天数**: {total_days} 天\n"
            f"- **平均每日热量摄入**: {avg_calories:.1f} kcal\n"
            f"- **平均每日蛋白质摄入**: {avg_protein:.1f} g\n\n"
            f"**初步分析**:\n"
            f"您的平均热量和蛋白质摄入量已计算得出。建议结合您的个人健康目标（如减重、增肌）进行更深入的分析。\n\n"
            f"**(此为初步报告框架，完整功能待实现)**"
        )
        return report
        
    except Exception as e:
        logger.error(f"生成用户 {user_id} 的 {report_type} 报告时出错: {e}", exc_info=True)
        return f"生成报告时发生错误。"


# --- LangChain BaseTool 类 ---
class ReportGenerationTool(BaseTool):
    """报告生成工具"""

    name: str = "report_generation_tool"
    description: str = (
        "一个用于为用户生成营养周报或月报的工具。"
        "当用户要求查看他们的周报、月报，或询问关于他们近期饮食习惯的总结时，请使用此工具。"
        "需要用户提供用户ID和报告类型 ('weekly' 或 'monthly')。"
    )
    args_schema: Type[BaseModel] = ReportGenerationInput

    def _run(self, user_id: str, report_type: str) -> str:
        """运行工具"""
        logger.info(f"为用户 {user_id} 生成 {report_type} 报告")
        # 使用今天作为报告的结束日期
        end_date_str = datetime.now().strftime("%Y-%m-%d")
        return _generate_report_content(user_id, report_type, end_date_str)

    async def _arun(self, user_id: str, report_type: str) -> str:
        """异步运行工具"""
        return self._run(user_id, report_type)