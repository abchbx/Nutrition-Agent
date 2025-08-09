import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import USER_DATA_PATH

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
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
    consultations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ConsultationRecord:
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
                if "consultations" not in user_data:
                    user_data["consultations"] = []
                now_iso = datetime.now().isoformat()
                if "created_at" not in user_data:
                    user_data["created_at"] = now_iso
                if "updated_at" not in user_data:
                    user_data["updated_at"] = now_iso
                return UserProfile(**user_data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"❌ 读取或解析用户档案 {filepath} 失败: {e}")
            return None

    def _save_user_profile(self, profile: UserProfile) -> bool:
        filepath = self._get_user_filepath(profile.user_id)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(asdict(profile), f, ensure_ascii=False, indent=4)
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
        profile = UserProfile(**profile_data)

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

        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.updated_at = datetime.now().isoformat()

        if self._save_user_profile(profile):
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
        record = ConsultationRecord(
            consultation_id=f"{user_id}_{now.strftime('%Y%m%d_%H%M%S')}",
            user_id=user_id,
            date=now.strftime("%Y-%m-%d"),
            question=question,
            answer=answer,
            category=category,
            created_at=now.isoformat(),
        )

        profile.consultations.append(asdict(record))
        profile.updated_at = now.isoformat()

        if self._save_user_profile(profile):
            print(f"✅ 成功添加咨询记录到用户 {user_id} 的档案中")
            logger.info("成功添加咨询记录到用户 %s 的档案中", user_id)
            return True
        logger.error("添加咨询记录到用户 %s 的档案中失败", user_id)
        return False
