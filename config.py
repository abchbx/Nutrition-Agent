import logging
import os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv


# 加载环境变量
load_dotenv()


# --- 移除原有的 basicConfig ---
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
load_dotenv()

# --- 移除原有的 basicConfig ---
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# --- 新的详细日志配置 ---
def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """配置一个带有文件轮转和格式化的日志记录器"""
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")

    # 文件处理器，带轮转
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)  # 5MB, 3 backups
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 避免重复添加处理器（如果模块被多次导入）
    logger.propagate = False

    return logger


# 为不同模块创建日志记录器
app_logger = setup_logger("app", "logs/app.log")
config_logger = setup_logger("config", "logs/config.log")
agent_logger = setup_logger("nutrition_agent", "logs/agent.log")
database_logger = setup_logger("nutrition_database", "logs/database.log")
memory_logger = setup_logger("user_memory", "logs/memory.log")

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
# USDA API 配置
USDA_API_KEY = os.getenv("USDA_API_KEY")
USDA_API_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
if not USDA_API_KEY:
    config_logger.warning("USDA_API_KEY environment variable is not set. USDA food search tool will not function.")

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
