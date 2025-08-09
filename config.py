import os
import logging
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# OpenAI配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
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
# Nutritionix API 配置
NUTRITIONIX_API_URL = os.getenv("NUTRITIONIX_API_URL", "https://trackapi.nutritionix.com/v2/natural/nutrients")
NUTRITIONIX_APP_ID = os.getenv("NUTRITIONIX_APP_ID")
NUTRITIONIX_API_KEY = os.getenv("NUTRITIONIX_API_KEY")
# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
