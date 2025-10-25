import os
from dotenv import load_dotenv

# 从 .env 文件加载环境变量
load_dotenv()

# 从环境变量中获取 API Keys 和 Base URLs
ALIBABA_API_KEY = os.getenv("ALIBABA_API_KEY")
ALIBABA_BASE_URL = os.getenv("ALIBABA_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://100.82.33.121:19090/v1")

LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "local")
LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:8000/v1")


# {project_root}/medsynthai
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# LLM model configuration based on agno
LLM_CONFIG = {
    "deepseek": {
        "class": "DeepSeek",
        "params": {
            "id": "deepseek-chat",
            "api_key": DEEPSEEK_API_KEY,
            "base_url": DEEPSEEK_BASE_URL
        }
    },
    "gpt-oss:latest": {
        "class": "OpenAILike",
        "params": {
            "id": "gpt-oss",
            "base_url": OLLAMA_BASE_URL,  # Ollama OpenAI兼容端点
            "api_key": OLLAMA_API_KEY  # Ollama不需要真实API密钥，任意字符串即可
        }
    },
    "phi4": {
        "class": "OpenAILike",
        "params": {
            "id": "microsoft/phi-4",
            "base_url": LOCAL_BASE_URL,  # 本地模型 OpenAI兼容端点
            "api_key": LOCAL_API_KEY  # 不需要真实API密钥，任意字符串即可
        }
    },
    "Qwen3-7B": {
        "class": "OpenAILike",
        "params": {
            "id": "qwen3",
            "base_url": OLLAMA_BASE_URL,  # Ollama OpenAI兼容端点
            "api_key": OLLAMA_API_KEY  # Ollama不需要真实API密钥，任意字符串即可
        }
    },
    "Gemma3-4b": {
        "class": "OpenAILike",
        "params": {
            "id": "gemma-3-4b-it",
            "base_url": OLLAMA_BASE_URL,  # Ollama OpenAI兼容端点
            "api_key": OLLAMA_API_KEY  # Ollama不需要真实API密钥，任意字符串即可
        }
    },
    "deepseek-v3": {
        "class": "OpenAILike",
        "params": {
            "id": "deepseek-v3",
            "base_url": ALIBABA_BASE_URL,
            "api_key": ALIBABA_API_KEY
        }
    },
    "deepseek-r1": {
        "class": "OpenAILike",
        "params": {
            "id": "deepseek-r1",
            "base_url": ALIBABA_BASE_URL,
            "api_key": ALIBABA_API_KEY
        }
    },
    "qwen-max": {
        "class": "OpenAILike",
        "params": {
            "id": "qwen-max",
            "base_url": ALIBABA_BASE_URL,
            "api_key": ALIBABA_API_KEY
        }
    },
    "qwen-vl-max": {
        "class": "OpenAILike",  # 使用OpenAI兼容类
        "params": {
            "id": "qwen-vl-max",
            "base_url": ALIBABA_BASE_URL,  # OpenAI兼容端点
            "api_key": ALIBABA_API_KEY
        }
    },
    "aliyun": {
        "class": "OpenAILike",
        "params": {
            "id": "qwen-max",  # 默认使用qwen-max模型
            "base_url": ALIBABA_BASE_URL,
            "api_key": ALIBABA_API_KEY
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
