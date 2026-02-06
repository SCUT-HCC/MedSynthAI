import os
from dotenv import load_dotenv

# 从 .env 文件加载环境变量
load_dotenv('.env')

# 从环境变量中获取 API_KEY 和 BASE_URL
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

if not API_KEY or not BASE_URL:
    raise ValueError("未找到 API_KEY 或 BASE_URL。请确保在项目根目录中创建了 .env 文件并设置了它们。")

LLM_CONFIG = {
    "deepseek": {
        "class": "OpenAILike", 
        "params": {
            "id": "deepseek-chat",
            "api_key": API_KEY,
            "base_url": BASE_URL
        }
    },
    "glm-4.6": {
        "class": "OpenAILike",
        "params": {
            "id": "glm-4.6",
            "api_key": API_KEY,
            "base_url": BASE_URL
        }
    },
    "gpt-oss": {
        "class": "OpenAILike",
        "params": {
            "id": "gpt-oss-20b",
            "api_key": API_KEY,
            "base_url": BASE_URL
        }
    },
    "MiniMax-M2": {
        "class": "OpenAILike",
        "params": {
            "id": "MiniMax-M2",
            "api_key": API_KEY,
            "base_url": BASE_URL
        }
    }
}