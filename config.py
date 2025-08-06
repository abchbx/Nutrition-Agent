import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# OpenAI配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# 数据库配置
DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/nutrition_data.csv")
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/faiss_index")

# Agent配置
AGENT_MODEL = os.getenv("AGENT_MODEL", "glm-4-flash")
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.7"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
# 用户数据存储
USER_DATA_PATH = os.getenv("USER_DATA_PATH", "./user_profiles")

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
