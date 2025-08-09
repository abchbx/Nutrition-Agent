import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nutrition_agent import NutritionAgent


class TestNutritionAgent(unittest.TestCase):

    @patch("nutrition_agent.NutritionDatabase")
    @patch("nutrition_agent.UserMemory")
    @patch("nutrition_agent.ChatOpenAI")
    @patch("nutrition_agent.HuggingFaceEmbeddings")
    def setUp(self, mock_embeddings, mock_chat_openai, mock_user_memory, mock_nutrition_database):
        # 创建 mock 对象
        self.mock_database = mock_nutrition_database.return_value
        self.mock_memory = mock_user_memory.return_value
        self.mock_llm = mock_chat_openai.return_value
        self.mock_embeddings = mock_embeddings.return_value

        # 为 embed_documents 方法提供模拟返回值
        self.mock_embeddings.embed_documents.return_value = [
            [0.1, 0.2, 0.3, 0.4, 0.5],
            [0.2, 0.3, 0.4, 0.5, 0.6],
            [0.3, 0.4, 0.5, 0.6, 0.7],
        ]

        # 创建 NutritionAgent 实例
        with (
            patch("nutrition_agent.HuggingFaceEmbeddings", return_value=self.mock_embeddings),
            patch("nutrition_agent.NutritionDatabase", return_value=self.mock_database),
            patch("nutrition_agent.UserMemory", return_value=self.mock_memory),
            patch("nutrition_agent.ChatOpenAI", return_value=self.mock_llm),
        ):
            self.agent = NutritionAgent()

    def test_initialization(self):
        """测试 NutritionAgent 初始化"""
        self.assertIsNotNone(self.agent.database)
        self.assertIsNotNone(self.agent.memory)
        self.assertIsNotNone(self.agent.llm)
        self.assertIsNotNone(self.agent.tools)
        self.assertIsNotNone(self.agent.agent_executor)

    @patch("nutrition_agent.UserProfile")
    def test_chat_with_existing_user(self, mock_user_profile):
        """测试与现有用户的对话"""
        # 设置 mock 返回值
        mock_user_profile_instance = mock_user_profile.return_value
        mock_user_profile_instance.name = "Test User"
        mock_user_profile_instance.age = 30
        mock_user_profile_instance.gender = "男"
        mock_user_profile_instance.height = 175.0
        mock_user_profile_instance.weight = 70.0
        mock_user_profile_instance.activity_level = "中度活动"
        mock_user_profile_instance.health_goal = "维持体重"
        mock_user_profile_instance.dietary_restrictions = "无"
        mock_user_profile_instance.preferences = "无"
        mock_user_profile_instance.updated_at = "2023-01-01T00:00:00"
        mock_user_profile_instance.consultations = []

        self.mock_memory.get_user_profile.return_value = mock_user_profile_instance
        self.mock_agent_executor = MagicMock()
        self.mock_agent_executor.invoke.return_value = {"output": "测试回复"}
        self.agent.agent_executor = self.mock_agent_executor

        # 调用 chat 方法
        result = self.agent.chat("test_user", "测试问题")

        # 验证结果
        self.assertEqual(result, "测试回复")
        self.mock_memory.get_user_profile.assert_called_once_with("test_user")
        self.mock_agent_executor.invoke.assert_called_once()

    def test_chat_with_new_user(self):
        """测试与新用户的对话"""
        # 设置 mock 返回值
        # 模拟第一次调用 get_user_profile 返回 None（用户不存在）
        # 模拟第二次调用 get_user_profile 返回用户档案（用户已创建）
        self.mock_memory.get_user_profile.side_effect = [
            None,
            MagicMock(
                name="New User",
                age=30,
                gender="男",
                height=175.0,
                weight=70.0,
                activity_level="中度活动",
                health_goal="维持体重",
                dietary_restrictions="无",
                preferences="无",
                updated_at="2023-01-01T00:00:00",
                consultations=[],
            ),
        ]
        self.mock_memory.create_user_profile.return_value = True
        self.mock_agent_executor = MagicMock()
        self.mock_agent_executor.invoke.return_value = {"output": "测试回复"}
        self.agent.agent_executor = self.mock_agent_executor

        # 调用 chat 方法
        result = self.agent.chat("new_user", "测试问题")

        # 验证结果
        self.assertEqual(result, "测试回复")
        # 验证 get_user_profile 被调用了两次
        self.assertEqual(self.mock_memory.get_user_profile.call_count, 2)
        self.mock_memory.get_user_profile.assert_any_call("new_user")
        self.mock_memory.create_user_profile.assert_called_once_with(user_id="new_user", name="new_user")
        self.mock_agent_executor.invoke.assert_called_once()


if __name__ == "__main__":
    unittest.main()
