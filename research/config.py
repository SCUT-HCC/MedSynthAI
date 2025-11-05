import os
from dotenv import load_dotenv

# {project_root}/medsynthai
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 从 .env 文件加载环境变量
# .env 文件应位于项目根目录 (BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, '.env'))

# 从环境变量中获取 API_KEY
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise ValueError("未找到 API_KEY。请确保在项目根目录中创建了 .env 文件并设置了 API_KEY。")

# LLM model configuration based on agno
LLM_CONFIG = {
    "deepseek": {
        "class": "DeepSeek",
        "params": {
            "id": "deepseek-chat",
            "api_key": API_KEY,
            "base_url": "https://api.deepseek.com"
        }
    },
    "C": {
        "class": "OpenAILike",
        "params": {
            "id": "gpt-oss",
            "base_url": "http://100.82.33.121:19090/v1",  # Ollama OpenAI兼容端点
            "api_key": "gpustack_d402860477878812_9ec494a501497d25b565987754f4db8c"  # Ollama不需要真实API密钥，任意字符串即可
        }
    },
    "phi4": {
        "class": "OpenAILike",
        "params": {
            "id": "microsoft/phi-4",
            "base_url": "http://127.0.0.1:8000/v1",  # Ollama OpenAI兼容端点
            "api_key": "gpustack_d402860477878812_9ec494a501497d25b565987754f4db8c"  # Ollama不需要真实API密钥，任意字符串即可
        }
    },
    "Qwen3-7B": {
        "class": "OpenAILike",
        "params": {
            "id": "qwen3",
            "base_url": "http://100.82.33.121:19090/v1",  # Ollama OpenAI兼容端点
            "api_key": "gpustack_d402860477878812_9ec494a501497d25b565987754f4db8c"  # Ollama不需要真实API密钥，任意字符串即可
        }
    },
    "Gemma3-4b": {
        "class": "OpenAILike",
        "params": {
            "id": "gemma-3-4b-it",
            "base_url": "http://100.82.33.121:19090/v1",  # Ollama OpenAI兼容端点
            "api_key": "gpustack_d402860477878812_9ec494a501497d25b565987754f4db8c"  # Ollama不需要真实API密钥，任意字符串即可
        }
    },
    "deepseek-v3": {
        "class": "OpenAILike",
        "params": {
            "id": "deepseek-v3",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": API_KEY
        }
    },
    "deepseek-r1": {
        "class": "OpenAILike",
        "params": {
            "id": "deepseek-r1",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": API_KEY
        }
    },
    "qwen-max": {
        "class": "OpenAILike",
        "params": {
            "id": "qwen-max",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": API_KEY
        }
    },
    "qwen-vl-max": {
        "class": "OpenAILike",  # 使用OpenAI兼容类
        "params": {
            "id": "qwen-vl-max",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",  # OpenAI兼容端点      # 降低随机性，提高结果一致性
            "api_key": API_KEY
        }
    },
    "aliyun": {
        "class": "OpenAILike",
        "params": {
            "id": "qwen-max",  # 默认使用qwen-max模型
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": API_KEY
        }
    }
    
}

AGENT_CONFIG = {
    "medical_image_analysis_agent": "qwen-vl-max"
}

RAG_CONFIG = {
    "lightrag": {
        "working_dir": "./Vector_DB_Med",
        "tokenizer_name": "trueto/medbert-base-chinese",
        "model_name": "trueto/medbert-base-chinese",
        "embedding_dim": 768,
        "max_token_size": 512
    },
    "chroma_db": {
        "api_key": API_KEY,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "collection_name": "doctor",
        "batch_size": 100,
        "chroma_db_path": os.path.join(BASE_DIR, "static/rag/chroma_db"),
        "csv_path": os.path.join(BASE_DIR, "static/files/zhongkang_doctor_list.csv")
    }
}
