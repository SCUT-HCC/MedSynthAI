import os
from dotenv import load_dotenv

# 项目根目录 {project_root}
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 从 .env 文件加载环境变量
load_dotenv(os.path.join(BASE_DIR, '.env'))

# 从环境变量中获取 API_KEY 和 BASE_URL
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

if not API_KEY or not BASE_URL:
    raise ValueError("未找到 API_KEY 或 BASE_URL。请确保在项目根目录中创建了 .env 文件并设置了它们。")

LLM_CONFIG = {
    # 将 "deepseek-chat" 的配置键名改为更通用的 "deepseek"
    "deepseek": {
        # 关键修改：将 class 从 "DeepSeek" 改为 "OpenAILike"
        "class": "OpenAILike", 
        "params": {
            # 将模型 ID 放在 id 或 model 参数中，agno 会处理
            "id": "deepseek-chat",
            "api_key": API_KEY,
            "base_url": BASE_URL
        }
    }
}