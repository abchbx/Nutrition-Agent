import os
import sys
import unittest
from unittest.mock import mock_open, patch

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_memory import UserMemory


class TestUserMemory(unittest.TestCase):

    def setUp(self):
        # 创建 UserMemory 实例
        with patch("user_memory.os.makedirs"):
            self.user_memory = UserMemory(profiles_path="/tmp/test_profiles")

    def test_initialization(self):
        """测试 UserMemory 初始化"""
        self.assertEqual(self.user_memory.profiles_path, "/tmp/test_profiles")

    @patch("user_memory.os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"user_id": "test_user", "name": "Test User", "age": 30, "gender": "男", "height": 175.0, "weight": 70.0, "activity_level": "中度活动", "health_goal": "维持体重", "dietary_restrictions": "无", "preferences": "无", "created_at": "2023-01-01T00:00:00", "updated_at": "2023-01-01T00:00:00", "consultations": []}',
    )
    def test_get_user_profile(self, mock_file, mock_exists):
        """测试获取用户档案"""
        mock_exists.return_value = True

        profile = self.user_memory.get_user_profile("test_user")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.user_id, "test_user")
        self.assertEqual(profile.name, "Test User")

    @patch("user_memory.os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_user_profile(self, mock_file, mock_exists):
        """测试创建用户档案"""
        mock_exists.return_value = False

        result = self.user_memory.create_user_profile(
            user_id="new_user",
            name="New User",
            age=25,
            gender="女",
            height=165.0,
            weight=55.0,
            activity_level="轻度活动",
            health_goal="减肥",
            dietary_restrictions="素食",
            preferences="喜欢水果",
        )

        self.assertTrue(result)
        mock_file.assert_called_once()

    @patch("user_memory.os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"user_id": "test_user", "name": "Test User", "age": 30, "gender": "男", "height": 175.0, "weight": 70.0, "activity_level": "中度活动", "health_goal": "维持体重", "dietary_restrictions": "无", "preferences": "无", "created_at": "2023-01-01T00:00:00", "updated_at": "2023-01-01T00:00:00", "consultations": []}',
    )
    def test_update_user_profile(self, mock_file, mock_exists):
        """测试更新用户档案"""
        mock_exists.return_value = True

        result = self.user_memory.update_user_profile(user_id="test_user", name="Updated User", age=35)

        self.assertTrue(result)
        # 验证文件被打开过，但不验证具体调用次数，因为可能涉及多次打开（读取和写入）
        mock_file.assert_called()

    @patch("user_memory.os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"user_id": "test_user", "name": "Test User", "age": 30, "gender": "男", "height": 175.0, "weight": 70.0, "activity_level": "中度活动", "health_goal": "维持体重", "dietary_restrictions": "无", "preferences": "无", "created_at": "2023-01-01T00:00:00", "updated_at": "2023-01-01T00:00:00", "consultations": []}',
    )
    def test_add_consultation_record(self, mock_file, mock_exists):
        """测试添加咨询记录"""
        mock_exists.return_value = True

        result = self.user_memory.add_consultation_record(
            user_id="test_user", question="测试问题", answer="测试答案", category="general"
        )

        self.assertTrue(result)
        # 验证文件被打开过，但不验证具体调用次数，因为可能涉及多次打开（读取和写入）
        mock_file.assert_called()


if __name__ == "__main__":
    unittest.main()
