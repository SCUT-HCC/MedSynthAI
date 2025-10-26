"""
项目配置模块。

该模块负责从环境变量（.env文件）中加载敏感配置（如API密钥），
并定义了整个项目中使用的各种静态配置，包括：
- LLM 提供商的 API Keys 和 Base URLs。
- 项目根目录路径。
- 不同 LLM 模型的配置信息 (LLM_CONFIG)。
- Agent 的特定模型配置 (AGENT_CONFIG)。
- RAG (检索增强生成) 的相关配置 (RAG_CONFIG)。

所有配置项都应在此文件中统一定义，以便于管理和维护。
本模块使用 Pydantic 进行配置的加载和验证。
"""
import os
from typing import Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    """
    使用 Pydantic 定义和加载应用配置。
    它会自动从 .env 文件和环境变量中读取配置。
    """
    # model_config 用于配置Pydantic的行为
    # env_file: 指定 .env 文件路径
    # extra='ignore': 忽略 .env 文件中未在模型中定义的额外变量
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # --- 必填项 (如果缺失，启动时会报错) ---
    ALIBABA_API_KEY: str
    DEEPSEEK_API_KEY: str

    # --- 可选项 (带有默认值) ---
    ALIBABA_BASE_URL: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    OLLAMA_API_KEY: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_API_KEY: str = "local"
    LOCAL_BASE_URL: str = "http://localhost:11434/v1"

# 创建一个全局的配置实例。
# 如果必填项缺失，程序将在此处停止并抛出 ValidationError。
settings = AppSettings()

# 项目根目录路径
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# LLM 模型配置
LLM_CONFIG: Dict[str, Any] = {
    "deepseek": {
        "class": "DeepSeek",
        "params": {
            "id": "deepseek-chat",
            "api_key": settings.DEEPSEEK_API_KEY,
            "base_url": settings.DEEPSEEK_BASE_URL
        }
    },
    "gpt-oss:latest": {
        "class": "OpenAILike",
        "params": {
            "id": "gpt-oss",
            "base_url": settings.OLLAMA_BASE_URL,
            "api_key": settings.OLLAMA_API_KEY
        }
    },
    "phi4": {
        "class": "OpenAILike",
        "params": {
            "id": "microsoft/phi-4",
            "base_url": settings.LOCAL_BASE_URL,
            "api_key": settings.LOCAL_API_KEY
        }
    },
    "Qwen3-7B": {
        "class": "OpenAILike",
        "params": {
            "id": "qwen3",
            "base_url": settings.OLLAMA_BASE_URL,
            "api_key": settings.OLLAMA_API_KEY
        }
    },
    "Gemma3-4b": {
        "class": "OpenAILike",
        "params": {
            "id": "gemma-3-4b-it",
            "base_url": settings.OLLAMA_BASE_URL,
            "api_key": settings.OLLAMA_API_KEY
        }
    },
    "deepseek-v3": {
        "class": "OpenAILike",
        "params": {
            "id": "deepseek-v3",
            "base_url": settings.ALIBABA_BASE_URL,
            "api_key": settings.ALIBABA_API_KEY
        }
    },
    "deepseek-r1": {
        "class": "OpenAILike",
        "params": {
            "id": "deepseek-r1",
            "base_url": settings.ALIBABA_BASE_URL,
            "api_key": settings.ALIBABA_API_KEY
        }
    },
    "qwen-max": {
        "class": "OpenAILike",
        "params": {
            "id": "qwen-max",
            "base_url": settings.ALIBABA_BASE_URL,
            "api_key": settings.ALIBABA_API_KEY
        }
    },
    "qwen-vl-max": {
        "class": "OpenAILike",
        "params": {
            "id": "qwen-vl-max",
            "base_url": settings.ALIBABA_BASE_URL,
            "api_key": settings.ALIBABA_API_KEY
        }
    },
    "aliyun": {
        "class": "OpenAILike",
        "params": {
            "id": "qwen-max",
            "base_url": settings.ALIBABA_BASE_URL,
            "api_key": settings.ALIBABA_API_KEY
        }
    }
}

# Agent 特定模型配置
AGENT_CONFIG: Dict[str, str] = {
    "medical_image_analysis_agent": "qwen-vl-max"
}

# RAG 相关配置
RAG_CONFIG: Dict[str, Any] = {
    "lightrag": {
        "working_dir": "./Vector_DB_Med",
        "tokenizer_name": "trueto/medbert-base-chinese",
        "model_name": "trueto/medbert-base-chinese",
        "embedding_dim": 768,
        "max_token_size": 512
    },
    "chroma_db": {
        "api_key": settings.ALIBABA_API_KEY,
        "base_url": settings.ALIBABA_BASE_URL,
        "collection_name": "doctor",
        "batch_size": 100,
        "chroma_db_path": os.path.join(BASE_DIR, "static/rag/chroma_db"),
        "csv_path": os.path.join(BASE_DIR, "static/files/zhongkang_doctor_list.csv")
    }
}