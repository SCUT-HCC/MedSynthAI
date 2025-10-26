"""
项目配置模块。

该模块负责从环境变量（.env文件）中加载敏感配置（如API密钥），
并定义了整个项目中使用的各种静态配置。

本模块使用了延迟加载（Lazy Loading）模式：
配置只在第一次被访问时才会从环境变量中加载和验证。
这避免了仅仅导入本模块就可能因缺少配置而导致程序崩溃的问题。
"""
import os
from typing import Dict, Any, Optional

# 占位符，表示这些变量将通过 __getattr__ 动态加载
LLM_CONFIG: Dict[str, Any]
AGENT_CONFIG: Dict[str, Any]
RAG_CONFIG: Dict[str, Any]

_settings: Optional['AppSettings'] = None
_llm_config: Optional[Dict[str, Any]] = None
_agent_config: Optional[Dict[str, str]] = None
_rag_config: Optional[Dict[str, Any]] = None

# 项目根目录路径，这个可以立即定义
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _get_settings() -> 'AppSettings':
    """
    内部函数：获取并缓存Pydantic配置实例。
    """
    global _settings
    # 只有在第一次调用时才导入 pydantic 并加载配置
    if _settings is None:
        from pydantic_settings import BaseSettings, SettingsConfigDict

        class AppSettings(BaseSettings):
            model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
            ALIBABA_API_KEY: str
            DEEPSEEK_API_KEY: str
            ALIBABA_BASE_URL: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
            OLLAMA_API_KEY: str = "ollama"
            OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
            LOCAL_API_KEY: str = "local"
            LOCAL_BASE_URL: str = "http://localhost:11434/v1"
        
        _settings = AppSettings()
    return _settings

def _build_llm_config() -> Dict[str, Any]:
    """内部函数：构建LLM配置字典。"""
    global _llm_config
    if _llm_config is None:
        settings = _get_settings()
        _llm_config = {
            "deepseek": {"class": "DeepSeek", "params": {"id": "deepseek-chat", "api_key": settings.DEEPSEEK_API_KEY, "base_url": settings.DEEPSEEK_BASE_URL}},
            "gpt-oss:latest": {"class": "OpenAILike", "params": {"id": "gpt-oss", "base_url": settings.OLLAMA_BASE_URL, "api_key": settings.OLLAMA_API_KEY}},
            "phi4": {"class": "OpenAILike", "params": {"id": "microsoft/phi-4", "base_url": settings.LOCAL_BASE_URL, "api_key": settings.LOCAL_API_KEY}},
            "Qwen3-7B": {"class": "OpenAILike", "params": {"id": "qwen3", "base_url": settings.OLLAMA_BASE_URL, "api_key": settings.OLLAMA_API_KEY}},
            "Gemma3-4b": {"class": "OpenAILike", "params": {"id": "gemma-3-4b-it", "base_url": settings.OLLAMA_BASE_URL, "api_key": settings.OLLAMA_API_KEY}},
            "deepseek-v3": {"class": "OpenAILike", "params": {"id": "deepseek-v3", "base_url": settings.ALIBABA_BASE_URL, "api_key": settings.ALIBABA_API_KEY}},
            "deepseek-r1": {"class": "OpenAILike", "params": {"id": "deepseek-r1", "base_url": settings.ALIBABA_BASE_URL, "api_key": settings.ALIBABA_API_KEY}},
            "qwen-max": {"class": "OpenAILike", "params": {"id": "qwen-max", "base_url": settings.ALIBABA_BASE_URL, "api_key": settings.ALIBABA_API_KEY}},
            "qwen-vl-max": {"class": "OpenAILike", "params": {"id": "qwen-vl-max", "base_url": settings.ALIBABA_BASE_URL, "api_key": settings.ALIBABA_API_KEY}},
            "aliyun": {"class": "OpenAILike", "params": {"id": "qwen-max", "base_url": settings.ALIBABA_BASE_URL, "api_key": settings.ALIBABA_API_KEY}},
        }
    return _llm_config

def _build_agent_config() -> Dict[str, str]:
    """内部函数：构建Agent配置字典。"""
    global _agent_config
    if _agent_config is None:
        _agent_config = {
            "medical_image_analysis_agent": "qwen-vl-max"
        }
    return _agent_config

def _build_rag_config() -> Dict[str, Any]:
    """内部函数：构建RAG配置字典。"""
    global _rag_config
    if _rag_config is None:
        settings = _get_settings()
        _rag_config = {
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
    return _rag_config

def __getattr__(name: str) -> Any:
    """
    模块级别的延迟加载实现。
    只在第一次访问 LLM_CONFIG, AGENT_CONFIG, RAG_CONFIG 时被调用。
    """
    if name == "LLM_CONFIG":
        return _build_llm_config()
    if name == "AGENT_CONFIG":
        return _build_agent_config()
    if name == "RAG_CONFIG":
        return _build_rag_config()
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")