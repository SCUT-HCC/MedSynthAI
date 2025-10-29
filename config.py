"""
项目配置模块。

该模块负责从环境变量（.env文件）中加载敏感配置（如API密钥），
并定义了整个项目中使用的各种静态配置。

本模块使用了延迟加载（Lazy Loading）模式和线程安全的初始化：
配置只在第一次被访问时才会从环境变量中加载和验证。
这避免了仅仅导入本模块就可能因缺少配置而导致程序崩溃的问题，
并确保在多线程环境下的安全性。
"""
import os
import threading
from typing import Dict, Any, Optional, TYPE_CHECKING

# 导入 Pydantic 相关模块
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# 仅在类型检查时为IDE和类型检查器提供类型提示
if TYPE_CHECKING:
    LLM_CONFIG: Dict[str, Dict[str, Any]]
    AGENT_CONFIG: Dict[str, str]
    RAG_CONFIG: Dict[str, Dict[str, Any]]

# 将 AppSettings 定义在模块级别，以避免在函数内重复创建
class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    ALIBABA_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    ALIBABA_BASE_URL: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    OLLAMA_API_KEY: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_API_KEY: str = "local"
    LOCAL_BASE_URL: str = "http://localhost:11434/v1"

# 内部缓存变量
_settings: Optional[AppSettings] = None
_llm_config: Optional[Dict[str, Any]] = None
_agent_config: Optional[Dict[str, str]] = None
_rag_config: Optional[Dict[str, Any]] = None

# 为每个延迟加载的配置创建线程锁
_settings_lock = threading.Lock()
_llm_config_lock = threading.Lock()
_agent_config_lock = threading.Lock()
_rag_config_lock = threading.Lock()


# 项目根目录路径
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))

def _get_settings() -> AppSettings:
    """
    内部函数：获取并缓存Pydantic配置实例（线程安全）。
    """
    global _settings
    if _settings is None:
        with _settings_lock:
            if _settings is None:  # 双重检查锁定
                try:
                    _settings = AppSettings()
                except ValidationError as e:
                    raise RuntimeError(
                        "配置加载失败。请执行以下步骤：\n"
                        "1. 复制 .env.example 到 .env\n"
                        "2. 填写必要的 API 密钥\n"
                        f"详细错误: {e}"
                    ) from e
    return _settings

def _build_llm_config() -> Dict[str, Dict[str, Any]]:
    """构建并缓存 LLM 配置（线程安全）。"""
    global _llm_config
    if _llm_config is None:
        with _llm_config_lock:
            if _llm_config is None:
                settings = _get_settings()
                
                # 运行时验证：确保至少配置了一个云服务 LLM 提供商的 API 密钥
                if not settings.ALIBABA_API_KEY and not settings.DEEPSEEK_API_KEY:
                    print("警告: ALIBABA_API_KEY 和 DEEPSEEK_API_KEY 均未在 .env 文件中设置。将无法使用云服务 LLM。")

                _llm_config = {
                    "alibaba": {
                        "api_key": settings.ALIBABA_API_KEY,
                        "base_url": settings.ALIBABA_BASE_URL,
                        "models": ["qwen-long", "qwen-max", "qwen-plus", "qwen-turbo"],
                    },
                    "deepseek": {
                        "api_key": settings.DEEPSEEK_API_KEY,
                        "base_url": settings.DEEPSEEK_BASE_URL,
                        "models": ["deepseek-chat", "deepseek-coder"],
                    },
                    "ollama": {
                        "api_key": settings.OLLAMA_API_KEY,
                        "base_url": settings.OLLAMA_BASE_URL,
                        "models": ["gemma:7b", "llama3:8b"],
                    },
                    "local": {
                        "api_key": settings.LOCAL_API_KEY,
                        "base_url": settings.LOCAL_BASE_URL,
                        "models": ["local-model"],
                    },
                }
    return _llm_config

def _build_agent_config() -> Dict[str, str]:
    """构建并缓存 Agent 配置（线程安全）。"""
    global _agent_config
    if _agent_config is None:
        with _agent_config_lock:
            if _agent_config is None:
                _agent_config = {
                    "controller": "deepseek:deepseek-chat",
                    "triager": "deepseek:deepseek-chat",
                    "virtual_patient": "alibaba:qwen-long",
                    "inquirer": "alibaba:qwen-long",
                    "evaluator": "deepseek:deepseek-chat",
                }
    return _agent_config

def _build_rag_config() -> Dict[str, Dict[str, Any]]:
    """构建并缓存 RAG 配置（线程安全）。"""
    global _rag_config
    if _rag_config is None:
        with _rag_config_lock:
            if _rag_config is None:
                _rag_config = {
                    "guidance_path": os.path.join(BASE_DIR, "guidance"),
                    "retriever_config": {
                        "embedding_model": "alibaba:text-embedding-v2",
                        "vector_store_path": os.path.join(BASE_DIR, "vector_store"),
                    },
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