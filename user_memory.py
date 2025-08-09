import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from config import USER_DATA_PATH

# Setup logger for user_memory.py
from config import memory_logger as logger


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
                # Ensure 'consultations' field exists
                user_data.setdefault("consultations", [])
                # Ensure 'created_at' and 'updated_at' fields exist
                now_iso = datetime.now().isoformat()
                user_data.setdefault("created_at", now_iso)
                user_data.setdefault("updated_at", now_iso)

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
            if key in update_data:  # Only update existing fields
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
