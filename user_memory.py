import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from config import USER_DATA_PATH

@dataclass
class UserProfile:
    """用户档案"""
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

@dataclass
class NutritionRecord:
    """营养记录"""
    record_id: str
    user_id: str
    date: str
    meal_type: str
    foods: List[Dict[str, Any]]
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    notes: str
    created_at: str

@dataclass
class ConsultationRecord:
    """咨询记录"""
    consultation_id: str
    user_id: str
    date: str
    question: str
    answer: str
    category: str
    created_at: str

class UserMemory:
    """用户记忆管理类"""
    
    def __init__(self, data_path: str = USER_DATA_PATH):
        """
        初始化用户记忆管理
        
        Args:
            data_path: 用户数据存储路径
        """
        self.data_path = data_path
        self.data = {
            "users": {},
            "nutrition_records": {},
            "consultation_records": {}
        }
        
        # 创建数据目录
        os.makedirs(os.path.dirname(data_path), exist_ok=True)
        
        # 加载数据
        self._load_data()
    
    def _load_data(self):
        """加载用户数据"""
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                print(f"✅ 成功加载用户数据: {len(self.data['users'])} 个用户")
            else:
                print("📝 用户数据文件不存在，创建新的数据文件...")
                self._save_data()
                
        except Exception as e:
            print(f"❌ 加载用户数据失败: {e}")
            self.data = {
                "users": {},
                "nutrition_records": {},
                "consultation_records": {}
            }
    
    def _save_data(self):
        """保存用户数据"""
        try:
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            print("✅ 用户数据保存成功")
        except Exception as e:
            print(f"❌ 保存用户数据失败: {e}")
    
    def create_user_profile(self, user_id: str, name: str, age: int, gender: str, 
                          height: float, weight: float, activity_level: str, 
                          health_goal: str, dietary_restrictions: str = "无", 
                          preferences: str = "无") -> bool:
        """
        创建用户档案
        
        Args:
            user_id: 用户ID
            name: 姓名
            age: 年龄
            gender: 性别
            height: 身高
            weight: 体重
            activity_level: 活动水平
            health_goal: 健康目标
            dietary_restrictions: 饮食限制
            preferences: 食物偏好
            
        Returns:
            是否创建成功
        """
        try:
            now = datetime.now().isoformat()
            
            profile = UserProfile(
                user_id=user_id,
                name=name,
                age=age,
                gender=gender,
                height=height,
                weight=weight,
                activity_level=activity_level,
                health_goal=health_goal,
                dietary_restrictions=dietary_restrictions,
                preferences=preferences,
                created_at=now,
                updated_at=now
            )
            
            self.data["users"][user_id] = asdict(profile)
            self._save_data()
            
            print(f"✅ 成功创建用户档案: {name} ({user_id})")
            return True
            
        except Exception as e:
            print(f"❌ 创建用户档案失败: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        获取用户档案
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户档案对象
        """
        try:
            user_data = self.data["users"].get(user_id)
            if user_data:
                return UserProfile(**user_data)
            return None
            
        except Exception as e:
            print(f"❌ 获取用户档案失败: {e}")
            return None
    
    def update_user_profile(self, user_id: str, **kwargs) -> bool:
        """
        更新用户档案
        
        Args:
            user_id: 用户ID
            **kwargs: 要更新的字段
            
        Returns:
            是否更新成功
        """
        try:
            if user_id not in self.data["users"]:
                return False
            
            # 更新字段
            for key, value in kwargs.items():
                if key in self.data["users"][user_id]:
                    self.data["users"][user_id][key] = value
            
            # 更新时间戳
            self.data["users"][user_id]["updated_at"] = datetime.now().isoformat()
            
            self._save_data()
            print(f"✅ 成功更新用户档案: {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ 更新用户档案失败: {e}")
            return False
    
    def add_nutrition_record(self, user_id: str, meal_type: str, foods: List[Dict[str, Any]], 
                           notes: str = "") -> bool:
        """
        添加营养记录
        
        Args:
            user_id: 用户ID
            meal_type: 餐食类型
            foods: 食物列表
            notes: 备注
            
        Returns:
            是否添加成功
        """
        try:
            # 计算营养总计
            total_calories = sum(food.get("calories", 0) for food in foods)
            total_protein = sum(food.get("protein", 0) for food in foods)
            total_carbs = sum(food.get("carbs", 0) for food in foods)
            total_fat = sum(food.get("fat", 0) for food in foods)
            
            now = datetime.now()
            record_id = f"{user_id}_{now.strftime('%Y%m%d_%H%M%S')}"
            
            record = NutritionRecord(
                record_id=record_id,
                user_id=user_id,
                date=now.strftime('%Y-%m-%d'),
                meal_type=meal_type,
                foods=foods,
                total_calories=total_calories,
                total_protein=total_protein,
                total_carbs=total_carbs,
                total_fat=total_fat,
                notes=notes,
                created_at=now.isoformat()
            )
            
            if user_id not in self.data["nutrition_records"]:
                self.data["nutrition_records"][user_id] = []
            
            self.data["nutrition_records"][user_id].append(asdict(record))
            self._save_data()
            
            print(f"✅ 成功添加营养记录: {meal_type} ({user_id})")
            return True
            
        except Exception as e:
            print(f"❌ 添加营养记录失败: {e}")
            return False
    
    def get_nutrition_records(self, user_id: str, date: Optional[str] = None) -> List[NutritionRecord]:
        """
        获取营养记录
        
        Args:
            user_id: 用户ID
            date: 日期 (YYYY-MM-DD格式)
            
        Returns:
            营养记录列表
        """
        try:
            records = self.data["nutrition_records"].get(user_id, [])
            
            if date:
                records = [r for r in records if r["date"] == date]
            
            return [NutritionRecord(**r) for r in records]
            
        except Exception as e:
            print(f"❌ 获取营养记录失败: {e}")
            return []
    
    def add_consultation_record(self, user_id: str, question: str, answer: str, category: str) -> bool:
        """
        添加咨询记录
        
        Args:
            user_id: 用户ID
            question: 问题
            answer: 回答
            category: 类别
            
        Returns:
            是否添加成功
        """
        try:
            now = datetime.now()
            consultation_id = f"{user_id}_{now.strftime('%Y%m%d_%H%M%S')}"
            
            record = ConsultationRecord(
                consultation_id=consultation_id,
                user_id=user_id,
                date=now.strftime('%Y-%m-%d'),
                question=question,
                answer=answer,
                category=category,
                created_at=now.isoformat()
            )
            
            if user_id not in self.data["consultation_records"]:
                self.data["consultation_records"][user_id] = []
            
            self.data["consultation_records"][user_id].append(asdict(record))
            self._save_data()
            
            print(f"✅ 成功添加咨询记录: {category} ({user_id})")
            return True
            
        except Exception as e:
            print(f"❌ 添加咨询记录失败: {e}")
            return False
    
    def get_consultation_records(self, user_id: str, limit: int = 10) -> List[ConsultationRecord]:
        """
        获取咨询记录
        
        Args:
            user_id: 用户ID
            limit: 限制数量
            
        Returns:
            咨询记录列表
        """
        try:
            records = self.data["consultation_records"].get(user_id, [])
            
            # 按时间倒序排序
            records.sort(key=lambda x: x["created_at"], reverse=True)
            
            # 限制数量
            records = records[:limit]
            
            return [ConsultationRecord(**r) for r in records]
            
        except Exception as e:
            print(f"❌ 获取咨询记录失败: {e}")
            return []
    
    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户总结
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户总结信息
        """
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return {}
            
            nutrition_records = self.get_nutrition_records(user_id)
            consultation_records = self.get_consultation_records(user_id)
            
            # 计算统计信息
            total_records = len(nutrition_records)
            total_consultations = len(consultation_records)
            
            # 计算平均营养摄入
            if nutrition_records:
                avg_calories = sum(r.total_calories for r in nutrition_records) / len(nutrition_records)
                avg_protein = sum(r.total_protein for r in nutrition_records) / len(nutrition_records)
                avg_carbs = sum(r.total_carbs for r in nutrition_records) / len(nutrition_records)
                avg_fat = sum(r.total_fat for r in nutrition_records) / len(nutrition_records)
            else:
                avg_calories = avg_protein = avg_carbs = avg_fat = 0
            
            summary = {
                "profile": asdict(profile),
                "statistics": {
                    "total_nutrition_records": total_records,
                    "total_consultations": total_consultations,
                    "avg_daily_calories": round(avg_calories, 1),
                    "avg_daily_protein": round(avg_protein, 1),
                    "avg_daily_carbs": round(avg_carbs, 1),
                    "avg_daily_fat": round(avg_fat, 1)
                },
                "recent_activities": {
                    "latest_nutrition_record": nutrition_records[-1].created_at if nutrition_records else None,
                    "latest_consultation": consultation_records[-1].created_at if consultation_records else None
                }
            }
            
            return summary
            
        except Exception as e:
            print(f"❌ 获取用户总结失败: {e}")
            return {}