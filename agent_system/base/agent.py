import hashlib
import asyncio
import concurrent.futures
import json
import os
import sys
import re
import logging
from typing import Type, Dict, List, Optional, Union, Any, Set

from agno.agent import Agent, RunResponse
from agno.models.deepseek import DeepSeek
from agno.models.openai import OpenAIChat, OpenAILike
from agno.storage.agent.sqlite import SqliteAgentStorage

# 尝试导入ollama，如果失败则忽略
try:
    from agno.models.ollama import Ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from agent_system.base.response_model import BaseResponseModel
#设置动态项目目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from config import LLM_CONFIG

class BaseAgent:
    """基础代理类，封装了 Phidata Agent。
    
    此类为不同的 LLM 模型提供统一接口，支持结构化输出、缓存和同步/异步执行。
    
    Attributes:
        structured_outputs: 是否返回结构化模型输出
        response_model: 用于结构化响应的 Pydantic 模型
        cache: 可选的响应缓存机制
        agent: 底层的 Phidata Agent 实例
        num_requests: 用于冗余的并行请求数量
        llm_config: LLM 模型的配置
    """
    
    def __init__(
        self,
        model_type: str,
        description: str = "",
        instructions: List[str] = None,
        response_model: Optional[Type[BaseResponseModel]] = None,
        structured_outputs: bool = True,
        storage: Optional[SqliteAgentStorage] = None,
        use_cache: bool = False,
        markdown: bool = True,
        debug_mode: bool = False,
        num_requests: int = 1,
        llm_config: Dict[str, Any] = None,
        **kwargs
    ) -> None:
        """初始化 BaseAgent。
        
        Args:
            model_type: 要使用的模型类型（例如 'DeepSeek', 'OpenAIChat'）
            description: 代理目的的描述
            instructions: 给代理的指令列表
            response_model: 用于结构化响应的 Pydantic 模型
            structured_outputs: 是否强制结构化输出
            storage: 用于会话历史的可选存储后端
            use_cache: 是否启用响应缓存
            markdown: 是否启用 Markdown 格式化
            debug_mode: 是否启用调试模式
            num_requests: 用于冗余的并行请求数量
            llm_config: LLM 模型的配置字典
            **kwargs: 传递给代理的额外参数
        """
        # 初始化实例变量
        self.structured_outputs = structured_outputs
        self.response_model = response_model
        self.cache: Optional['Cache'] = Cache() if use_cache else None
        self.agent: Optional[Agent] = None
        self.num_requests = max(1, num_requests)  # 确保至少有 1 个请求
        self.llm_config = llm_config or LLM_CONFIG
        
        # 安全处理默认空列表
        if instructions is None:
            instructions = []

        # 使用提供的配置初始化代理
        self._init_agent(
            model_type=model_type,
            description=description,
            instructions=instructions,
            response_model=response_model,
            storage=storage,
            markdown=markdown,
            debug_mode=debug_mode,
            **kwargs
        )
    
    def _init_agent(
        self,
        model_type: str,
        description: str = "",
        instructions: List[str] = None,
        response_model: Optional[Type[BaseResponseModel]] = None,
        storage: Optional[SqliteAgentStorage] = None,
        markdown: bool = True,
        debug_mode: bool = False,
        **kwargs
    ) -> None:
        """初始化底层的 Agent 实例。
        
        Args:
            model_type: 要使用的模型类型
            description: 代理目的的描述
            instructions: 给代理的指令列表
            response_model: 用于结构化响应的 Pydantic 模型
            storage: 可选的存储后端
            markdown: 是否启用 Markdown 格式化
            debug_mode: 是否启用调试模式
            **kwargs: 额外参数
        
        Raises:
            ValueError: 如果模型初始化失败或请求了不支持的模型
        """
        if instructions is None:
            instructions = []
            
        # 定义可用的模型类
        model_classes = {
            "DeepSeek": DeepSeek,
            "OpenAIChat": OpenAIChat,
            "OpenAILike": OpenAILike,
        }
        
        # 如果可用则添加 Ollama
        if OLLAMA_AVAILABLE:
            model_classes["Ollama"] = Ollama

        # 获取模型配置
        model_config = self._get_model_config(model_type)
        
        # 验证模型可用性
        self._validate_model_availability(model_config)
        
        # 获取模型类和参数
        model_class = model_classes[model_config["class"]]
        model_kwargs = model_config["params"]

        # 初始化模型
        model = self._create_model_instance(model_class, model_kwargs)

        # 创建代理 - 不传入response_model以获取原始JSON字符串
        self.agent = Agent(
            model=model,
            description=description,
            instructions=instructions,
            markdown=markdown,
            debug_mode=debug_mode,
            storage=storage,
            **kwargs
        )
    
    def _get_model_config(self, model_type: str) -> Dict[str, Any]:
        """从 llm_config 中获取模型配置。
        
        Args:
            model_type: 请求的模型类型
            
        Returns:
            模型配置字典
        """
        llm_keys = self.llm_config.keys()
        
        if model_type not in llm_keys:
            # 如果模型类型不存在，使用配置中的第一个模型作为回退
            if not self.llm_config:
                raise ValueError("LLM_CONFIG 为空，无法获取任何模型配置。")
            
            fallback_key = next(iter(self.llm_config))
            print(f"警告: 模型类型 '{model_type}' 未在配置中找到。回退到使用 '{fallback_key}' 的配置。")
            
            model_config = self.llm_config[fallback_key].copy()
            model_config["params"]["id"] = model_type
            return model_config
        else:
            return self.llm_config[model_type]
    
    def _validate_model_availability(self, model_config: Dict[str, Any]) -> None:
        """验证请求的模型是否可用。
        
        Args:
            model_config: 模型配置字典
            
        Raises:
            ValueError: 如果请求了 Ollama 但不可用
        """
        if model_config["class"] == "Ollama" and not OLLAMA_AVAILABLE:
            raise ValueError(
                "请求了 Ollama 模型，但 ollama 包不可用。"
                "请安装 ollama 或使用不同的模型。"
            )
    
    def _create_model_instance(self, model_class: Type, model_kwargs: Dict[str, Any]) -> Any:
        """创建指定模型类的实例。
        
        Args:
            model_class: 要实例化的模型类
            model_kwargs: 模型初始化的关键字参数
            
        Returns:
            初始化后的模型实例
            
        Raises:
            ValueError: 如果模型初始化失败
        """
        try:
            return model_class(**model_kwargs)
        except Exception as e:
            raise ValueError(f"模型 {model_class.__name__} 初始化失败: {e}") from e
    
    def run(self, prompt: str, **kwargs) -> Union[str, BaseResponseModel]:
        """执行同步代理运行，支持缓存和结构化输出。
        
        Args:
            prompt: 发送给代理的输入提示
            **kwargs: 传递给代理的额外关键字参数
            
        Returns:
            字符串响应或结构化的 BaseResponseModel 实例
            
        Raises:
            RuntimeError: 如果所有尝试后都无法获得有效响应
        """
        # 首先检查缓存
        if self.cache and self.cache._check_cache_hit(prompt, **kwargs):
            return self.cache._get_cache()

        # 根据输出类型获取结果
        if self.structured_outputs:
            result = self._run_structured(prompt, **kwargs)
        else:
            result = self._run_unstructured(prompt, **kwargs)

        # 如果启用了缓存，则缓存结果
        self._cache_result(result)
        
        return result
    
    def _run_structured(self, prompt: str, **kwargs) -> BaseResponseModel:
        """执行结构化输出运行，带重试逻辑。
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            结构化响应模型实例
            
        Raises:
            RuntimeError: 如果无法获得有效的结构化响应
        """
        max_retries = 5
        
        for retry_count in range(max_retries):
            result = self._execute_parallel_structured_requests(prompt, **kwargs)
            
            if result is not None:
                return result
                
            print(f"解析响应的重试尝试 {retry_count + 1}")
        
        raise RuntimeError(
            f"在 {max_retries} 次重试尝试后无法获得有效的结构化响应，"
            f"每次尝试并行 {self.num_requests} 个请求。"
        )
    
    def _execute_parallel_structured_requests(self, prompt: str, **kwargs) -> Optional[BaseResponseModel]:
        """执行多个并行的结构化输出请求。
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            第一个有效的结构化响应，如果全部失败则返回 None
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_requests) as executor:
            # 不传入output_class，让agno返回原始字符串
            futures = [
                executor.submit(self.agent.run, prompt, **kwargs)
                for _ in range(self.num_requests)
            ]
            
            try:
                for future in concurrent.futures.as_completed(futures):
                    result = self._process_structured_response(future)
                    if result is not None:
                        # 取消剩余的 future 并返回结果
                        self._cancel_remaining_futures(futures)
                        return result
            finally:
                # 确保清理资源
                executor.shutdown(wait=False, cancel_futures=True)
                
        return None
    
    def _process_structured_response(self, future: concurrent.futures.Future) -> Optional[BaseResponseModel]:
        """处理单个结构化响应 future。
        
        Args:
            future: 要处理的已完成的 future
            
        Returns:
            处理后的结构化响应，如果处理失败则返回 None
        """
        try:
            response: RunResponse = future.result()
            potential_result = response.content
            
            # 强制进行手动JSON解析（绕过agno自动解析）
            if isinstance(potential_result, str):
                return self._parse_json_response(potential_result)
            elif isinstance(potential_result, self.response_model):
                # 如果agno已经解析过，直接返回
                return potential_result
                
        except Exception as e:
            print(f"代理运行失败: {e}")
            
        return None
    
    def _parse_json_response(self, response_str: str) -> Optional[BaseResponseModel]:
        """将 JSON 字符串响应解析为结构化模型。
        
        Args:
            response_str: 可能包含 JSON 的字符串响应
            
        Returns:
            解析后的模型实例，如果解析失败则返回 None
        """
        if not response_str or not response_str.strip():
            print(f"空响应字符串，无法解析JSON")
            return None
            
        # 清理响应字符串
        cleaned_str = response_str.strip()
        logging.debug(f"调试: 原始响应 = {repr(response_str[:200])}...")

        # 移除可能的代码块标记
        if cleaned_str.startswith('```json'):
            cleaned_str = cleaned_str[7:]
        if cleaned_str.endswith('```'):
            cleaned_str = cleaned_str[:-3]
        
        # 尝试提取JSON内容 - 支持嵌套JSON结构
        
        # 首先尝试查找完整的JSON对象（考虑嵌套结构）
        json_str = self._extract_complete_json(cleaned_str)
        if json_str:
            logging.debug(f"调试: 提取的完整JSON = {repr(json_str[:200])}...")
        else:
            json_str = cleaned_str.strip()
            print(f"调试: 未找到JSON结构，使用原始内容 = {repr(json_str[:200])}...")
            
        try:
            data_dict = json.loads(json_str)
            logging.debug(f"调试: 解析成功的字典 = {data_dict}")
            
            if self.response_model:
                try:
                    result = self.response_model(**data_dict)
                    logging.debug(f"成功创建模型实例 = {result}")
                    return result
                except Exception as e:
                    print(f"无法从字典创建模型实例: {e}")
                    return None
            else:
                return data_dict
                
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"尝试解析的内容: {repr(json_str)}")
            return None
    
    def _extract_complete_json(self, text: str) -> str:
        """
        从文本中提取完整的JSON对象，支持嵌套结构
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            提取的完整JSON字符串，如果未找到则返回None
        """
        # 查找第一个左大括号
        start_idx = text.find('{')
        if start_idx == -1:
            return None
            
        # 使用计数器匹配完整的JSON对象
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text[start_idx:], start_idx):
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\' and in_string:
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    
                    # 找到匹配的右大括号
                    if brace_count == 0:
                        return text[start_idx:i+1]
        
        # 如果没有找到匹配的大括号，返回从第一个{到末尾
        return text[start_idx:] if brace_count > 0 else None
    
    def _run_unstructured(self, prompt: str, **kwargs) -> str:
        """执行非结构化输出运行。
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            来自第一个完成请求的字符串响应
            
        Raises:
            RuntimeError: 如果第一个完成的请求失败
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_requests) as executor:
            futures = [
                executor.submit(self.agent.run, prompt, **kwargs)
                for _ in range(self.num_requests)
            ]
            
            try:
                # 等待第一个完成
                done, not_done = concurrent.futures.wait(
                    futures, return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                # 从第一个完成的 future 获取结果
                first_future = next(iter(done))
                try:
                    raw_response: RunResponse = first_future.result()
                    return raw_response.content
                except Exception as e:
                    raise RuntimeError(f"第一个代理运行失败: {e}") from e
                    
            finally:
                # 取消剩余的 futures
                self._cancel_remaining_futures(futures)
                executor.shutdown(wait=False, cancel_futures=True)
    
    def _cancel_remaining_futures(self, futures: List[concurrent.futures.Future]) -> None:
        """取消所有尚未完成的 futures。
        
        Args:
            futures: 要取消的 futures 列表
        """
        for future in futures:
            if not future.done():
                future.cancel()
    
    def _cache_result(self, result: Union[str, BaseResponseModel]) -> None:
        """如果启用了缓存，则缓存结果。
        
        Args:
            result: 要缓存的结果
        """
        if self.cache and result is not None:
            self.cache._save_cache(result)
    
    
    async def async_run(self, prompt: str, **kwargs) -> Union[str, BaseResponseModel]:
        """执行异步代理运行，支持缓存和结构化输出。
        
        Args:
            prompt: 发送给代理的输入提示
            **kwargs: 传递给代理的额外关键字参数
            
        Returns:
            字符串响应或结构化的 BaseResponseModel 实例
            
        Raises:
            RuntimeError: 如果无法获得有效响应
        """
        # 检查缓存
        if self.cache and self.cache._check_cache_hit(prompt, **kwargs):
            return self.cache._get_cache()

        # 根据输出类型获取结果
        if self.structured_outputs:
            result = await self._async_run_structured(prompt, **kwargs)
        else:
            result = await self._async_run_unstructured(prompt, **kwargs)

        # 缓存结果
        self._cache_result(result)
        
        return result
    
    async def _async_run_structured(self, prompt: str, **kwargs) -> BaseResponseModel:
        """异步执行结构化输出运行。
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            结构化响应模型实例
            
        Raises:
            RuntimeError: 如果无法获得有效的结构化响应
        """
        tasks = {
            asyncio.create_task(self.agent.arun(prompt, **kwargs))
            for _ in range(self.num_requests)
        }
        
        try:
            # 等待第一个完成的任务
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            while done:
                task = done.pop()
                try:
                    response: RunResponse = await task
                    result = self._process_async_structured_response(response)
                    
                    if result is not None:
                        return result
                        
                except Exception as e:
                    print(f"代理异步运行失败: {e}")
                    
                # 从任务集中移除已完成的任务
                tasks.discard(task)
                
                # 如果没有更多待处理的任务，跳出循环
                if not pending:
                    break
                    
                # 等待下一个任务完成
                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

            raise RuntimeError(f"在 {self.num_requests} 次并行尝试后无法获得有效的结构化响应")
            
        finally:
            await self._cancel_remaining_tasks(tasks)
    
    async def _async_run_unstructured(self, prompt: str, **kwargs) -> str:
        """异步执行非结构化输出运行。
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            字符串响应
            
        Raises:
            RuntimeError: 如果第一个完成的任务失败
        """
        tasks = {
            asyncio.create_task(self.agent.arun(prompt, **kwargs))
            for _ in range(self.num_requests)
        }
        
        try:
            # 等待第一个完成的任务
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            first_task = done.pop()
            try:
                raw_response: RunResponse = await first_task
                return raw_response.content
            except Exception as e:
                raise RuntimeError(f"第一个代理异步运行失败: {e}") from e
                
        finally:
            await self._cancel_remaining_tasks(tasks)
    
    def _process_async_structured_response(self, response: RunResponse) -> Optional[BaseResponseModel]:
        """处理异步结构化响应。
        
        Args:
            response: 代理运行响应
            
        Returns:
            处理后的结构化响应或 None
        """
        potential_result = response.content
        
        # 直接模型实例
        if isinstance(potential_result, self.response_model):
            return potential_result
            
        # 需要解析的字符串响应
        if isinstance(potential_result, str):
            return self._parse_json_response(potential_result)
            
        return None
    
    async def _cancel_remaining_tasks(self, tasks: Set[asyncio.Task]) -> None:
        """取消所有剩余的任务。
        
        Args:
            tasks: 要取消的任务集合
        """
        for task in tasks:
            if not task.done():
                task.cancel()
                
        # 等待所有任务完成或被取消
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

class Cache:
    """响应缓存类，用于缓存代理响应以提高性能。
    
    使用 MD5 哈希生成缓存键，基于提示和参数内容。
    """
    
    def __init__(self) -> None:
        """初始化缓存。"""
        self.cache: Dict[str, Union[str, BaseResponseModel]] = {}
        self.current_cache_key: Optional[str] = None

    def _set_cache_key(self, prompt: str, **kwargs) -> None:
        """为提示和参数生成唯一的缓存键。
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
        """
        # 创建结合提示和相关参数的字符串
        cache_str = prompt + str(sorted(kwargs.items()))
        # 生成字符串的哈希值
        self.current_cache_key = hashlib.md5(cache_str.encode('utf-8')).hexdigest()

    def _check_cache_hit(self, prompt: str, **kwargs) -> bool:
        """检查当前缓存键是否存在于缓存中。
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            如果缓存命中则返回 True
        """
        if self.current_cache_key is None:
            self._set_cache_key(prompt, **kwargs)
        return self.current_cache_key in self.cache

    def _save_cache(self, result: Union[str, BaseResponseModel]) -> None:
        """将结果保存到缓存中。
        
        Args:
            result: 要缓存的结果
        """
        if self.current_cache_key is not None:
            self.cache[self.current_cache_key] = result
            self.current_cache_key = None

    def _get_cache(self) -> Union[str, BaseResponseModel]:
        """从缓存中获取结果。
        
        Returns:
            缓存的结果
            
        Raises:
            KeyError: 如果缓存键不存在
        """
        if self.current_cache_key is None:
            raise ValueError("未设置缓存键")
            
        if self.current_cache_key not in self.cache:
            raise KeyError(f"缓存键 '{self.current_cache_key}' 不存在")
            
        result = self.cache[self.current_cache_key]
        self.current_cache_key = None
        return result
    
    def clear(self) -> None:
        """清空所有缓存。"""
        self.cache.clear()
        self.current_cache_key = None
    
    def size(self) -> int:
        """获取缓存中的项目数量。
        
        Returns:
            缓存项目数量
        """
        return len(self.cache)