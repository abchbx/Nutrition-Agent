import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from config import USER_DATA_PATH

# Setup logger for user_memory.py
from config import memory_logger as logger


# --- 新增的数据模型 ---

class DailyLogEntry(BaseModel):
    """单条饮食记录条目"""
    food_name: str
    amount: float # 数量
    unit: str    # 单位 (e.g., "g", "杯", "个")
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    # 可以根据需要添加更多营养素字段

class DailyLog(BaseModel):
    """某一天的饮食记录"""
    date: str # YYYY-MM-DD
    entries: List[DailyLogEntry] = Field(default_factory=list)
    # total_nutrition 可以实时计算，也可以存储

class Goal(BaseModel):
    """用户健康目标"""
    goal_id: str
    description: str
    target_value: float # 目标值 (e.g., -2.0 for weight loss of 2kg)
    unit: str # 单位 (e.g., "kg", "%")
    start_date: str # YYYY-MM-DD
    target_date: str # YYYY-MM-DD
    status: str = "active" # "active", "achieved", "failed", "cancelled"

class UserProfile(BaseModel):
    user_id: str
    name: str
    age: int
    gender: str
    height: float
    weight: float
    activity_level: str
    health_goal: str
    dietary_restrictions: str
    preferences: str
    created_at: str
    updated_at: str
    consultations: List[Dict[str, Any]] = Field(default_factory=list)
    # --- 新增字段 ---
    daily_logs: List[DailyLog] = Field(default_factory=list)
    goals: List[Goal] = Field(default_factory=list)
    # reports: List[Dict[str, Any]] = Field(default_factory=list) # 可选：存储报告摘要

# --- 保留原有的 ConsultationRecord 模型 ---
class ConsultationRecord(BaseModel):
    consultation_id: str
    user_id: str
    date: str
    question: str
    answer: str
    category: str
    created_at: str


class UserMemory:
    def __init__(self, profiles_path: str = USER_DATA_PATH):
        self.profiles_path = profiles_path
        os.makedirs(self.profiles_path, exist_ok=True)
        print(f"👤 用户档案目录已确认: {self.profiles_path}")

    def _get_user_filepath(self, user_id: str) -> str:
        return os.path.join(self.profiles_path, f"{user_id}.json")

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        filepath = self._get_user_filepath(user_id)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                user_data = json.load(f)
                # Ensure old fields exist for backward compatibility
                user_data.setdefault("consultations", [])
                now_iso = datetime.now().isoformat()
                user_data.setdefault("created_at", now_iso)
                user_data.setdefault("updated_at", now_iso)
                # Ensure new fields exist for backward compatibility
                user_data.setdefault("daily_logs", [])
                user_data.setdefault("goals", [])
                # user_data.setdefault("reports", []) # 可选

                # Use Pydantic model's parse_obj method for robust deserialization
                return UserProfile.parse_obj(user_data)
        except (json.JSONDecodeError, Exception) as e:  # Catch broader exceptions for Pydantic validation
            print(f"❌ 读取或解析用户档案 {filepath} 失败: {e}")
            logger.error(f"读取或解析用户档案 {filepath} 失败: {e}")
            return None

    def _save_user_profile(self, profile: UserProfile) -> bool:
        filepath = self._get_user_filepath(profile.user_id)
        try:
            # Use Pydantic model's dict() method for serialization
            profile_data = profile.dict()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, ensure_ascii=False, indent=4)
            logger.info("成功保存用户档案: %s", filepath)
            return True
        except Exception as e:
            print(f"❌ 保存用户档案 {filepath} 失败: {e}")
            logger.error("保存用户档案 %s 失败: %s", filepath, e)
            return False

    def create_user_profile(self, user_id: str, **kwargs) -> bool:
        filepath = self._get_user_filepath(user_id)
        if os.path.exists(filepath):
            return self.update_user_profile(user_id, **kwargs)

        now = datetime.now().isoformat()
        profile_data = {
            "user_id": user_id,
            "name": kwargs.get("name", user_id),
            "age": kwargs.get("age", 30),
            "gender": kwargs.get("gender", "未知"),
            "height": kwargs.get("height", 170.0),
            "weight": kwargs.get("weight", 65.0),
            "activity_level": kwargs.get("activity_level", "轻度活动"),
            "health_goal": kwargs.get("health_goal", "维持体重"),
            "dietary_restrictions": kwargs.get("dietary_restrictions", "无"),
            "preferences": kwargs.get("preferences", "无"),
            "created_at": now,
            "updated_at": now,
            "consultations": [],
            # --- 初始化新增字段 ---
            "daily_logs": [],
            "goals": [],
            # "reports": [], # 可选
        }
        try:
            # Use Pydantic model for validation
            profile = UserProfile(**profile_data)
        except Exception as e:
            logger.error(f"创建用户档案时数据验证失败: {e}")
            return False

        if self._save_user_profile(profile):
            print(f"✅ 成功创建用户档案: {profile.name} ({user_id})")
            logger.info("成功创建用户档案: %s (%s)", profile.name, user_id)
            return True
        logger.error("创建用户档案失败: %s", user_id)
        return False

    def update_user_profile(self, user_id: str, **kwargs) -> bool:
        profile = self.get_user_profile(user_id)
        if not profile:
            # 如果档案不存在，直接尝试创建
            print(f"⚠️ 用户 {user_id} 档案不存在，将为您创建一个新档案。")
            return self.create_user_profile(user_id, **kwargs)

        # Update fields dynamically
        update_data = profile.dict()  # Convert to dict for easy updating
        for key, value in kwargs.items():
            if key in update_data:  # Only update existing fields in the original model
                update_data[key] = value

        update_data["updated_at"] = datetime.now().isoformat()

        try:
            # Re-validate and create the updated profile object
            updated_profile = UserProfile(**update_data)
        except Exception as e:
            logger.error(f"更新用户档案时数据验证失败: {e}")
            return False

        if self._save_user_profile(updated_profile):
            print(f"✅ 成功更新用户档案: {user_id}")
            return True
        return False

    def add_consultation_record(self, user_id: str, question: str, answer: str, category: str) -> bool:
        profile = self.get_user_profile(user_id)
        if not profile:
            print(f"⚠️ 尝试为不存在的用户 {user_id} 添加咨询记录。")
            logger.warning("尝试为不存在的用户 %s 添加咨询记录", user_id)
            return False

        now = datetime.now()
        record_data = {
            "consultation_id": f"{user_id}_{now.strftime('%Y%m%d_%H%M%S')}",
            "user_id": user_id,
            "date": now.strftime("%Y-%m-%d"),
            "question": question,
            "answer": answer,
            "category": category,
            "created_at": now.isoformat(),
        }

        try:
            # Validate record data
            record = ConsultationRecord(**record_data)
        except Exception as e:
            logger.error(f"创建咨询记录时数据验证失败: {e}")
            return False

        # Update profile
        profile.consultations.append(record.dict())  # Convert record to dict for JSON serialization
        profile.updated_at = now.isoformat()

        if self._save_user_profile(profile):
            print(f"✅ 成功添加咨询记录到用户 {user_id} 的档案中")
            logger.info("成功添加咨询记录到用户 %s 的档案中", user_id)
            return True
        logger.error("添加咨询记录到用户 %s 的档案中失败", user_id)
        return False
    
    # --- 新增方法用于管理动态健康日志 ---

    def _get_or_create_daily_log(self, profile: UserProfile, date_str: str) -> DailyLog:
        """获取或创建指定日期的 DailyLog 对象"""
        for log in profile.daily_logs:
            if log.date == date_str:
                return log
        # 如果没有找到，创建一个新的
        new_log = DailyLog(date=date_str)
        profile.daily_logs.append(new_log)
        # 为了保持日期顺序（可选但推荐），可以进行排序
        profile.daily_logs.sort(key=lambda x: x.date)
        return new_log

    def add_daily_log_entry(self, user_id: str, date_str: str, food_entry_data: Dict[str, Any]) -> bool:
        """为用户添加一条每日饮食记录"""
        profile = self.get_user_profile(user_id)
        if not profile:
            logger.warning("尝试为不存在的用户 %s 添加饮食记录。", user_id)
            return False

        try:
            # 验证食物条目数据
            food_entry = DailyLogEntry(**food_entry_data)
        except Exception as e:
            logger.error(f"创建饮食记录条目时数据验证失败: {e}")
            return False

        # 获取或创建当天的 DailyLog
        daily_log = self._get_or_create_daily_log(profile, date_str)
        
        # 添加条目
        daily_log.entries.append(food_entry)
        
        # 更新档案修改时间
        profile.updated_at = datetime.now().isoformat()

        # 保存档案
        if self._save_user_profile(profile):
            logger.info("成功为用户 %s 在 %s 添加饮食记录条目: %s", user_id, date_str, food_entry.food_name)
            return True
        logger.error("为用户 %s 添加饮食记录条目失败", user_id)
        return False

    def get_daily_logs_for_period(self, user_id: str, start_date_str: str, end_date_str: str) -> Optional[List[DailyLog]]:
        """获取用户在指定日期范围内的所有饮食日志"""
        profile = self.get_user_profile(user_id)
        if not profile:
            logger.warning("尝试获取不存在的用户 %s 的饮食记录。", user_id)
            return None
        
        # 过滤出日期范围内的日志
        filtered_logs = [
            log for log in profile.daily_logs 
            if start_date_str <= log.date <= end_date_str
        ]
        # 按日期排序
        filtered_logs.sort(key=lambda x: x.date)
        return filtered_logs

    def set_user_goal(self, user_id: str, goal_data: Dict[str, Any]) -> bool:
        """为用户设置一个新的健康目标"""
        profile = self.get_user_profile(user_id)
        if not profile:
            logger.warning("尝试为不存在的用户 %s 设置健康目标。", user_id)
            return False

        # 生成一个唯一的 goal_id
        goal_id = f"{user_id}_goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        goal_data["goal_id"] = goal_id

        try:
            # 验证目标数据
            goal = Goal(**goal_data)
        except Exception as e:
            logger.error(f"创建健康目标时数据验证失败: {e}")
            return False
        
        # 添加目标
        profile.goals.append(goal)
        
        # 更新档案修改时间
        profile.updated_at = datetime.now().isoformat()

        # 保存档案
        if self._save_user_profile(profile):
            logger.info("成功为用户 %s 设置健康目标: %s", user_id, goal.description)
            return True
        logger.error("为用户 %s 设置健康目标失败", user_id)
        return False

    def update_goal_status(self, user_id: str, goal_id: str, new_status: str) -> bool:
        """更新用户某个健康目标的状态"""
        profile = self.get_user_profile(user_id)
        if not profile:
            logger.warning("尝试更新不存在的用户 %s 的健康目标。", user_id)
            return False
        
        goal_found = False
        for goal in profile.goals:
            if goal.goal_id == goal_id:
                goal.status = new_status
                goal_found = True
                break
        
        if not goal_found:
            logger.warning("未找到用户 %s 的目标 ID: %s", user_id, goal_id)
            return False

        # 更新档案修改时间
        profile.updated_at = datetime.now().isoformat()

        # 保存档案
        if self._save_user_profile(profile):
            logger.info("成功更新用户 %s 的目标 %s 状态为 %s", user_id, goal_id, new_status)
            return True
        logger.error("更新用户 %s 的目标 %s 状态失败", user_id, goal_id)
        return False

    # --- 可选：添加报告摘要存储方法 ---
    # def add_report_summary(self, user_id: str, report_data: Dict[str, Any]) -> bool:
    #     ... (实现逻辑类似上面的方法)
