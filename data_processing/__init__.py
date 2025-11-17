"""
爱爱医病历数据采集模块

使用 crawl4ai 的 JsonCssExtractionStrategy 和 PruningContentFilter
进行精确的结构化数据提取。

主要改进:
1. 使用 CSS 选择器进行精确数据提取
2. 结合 PruningContentFilter 优化内容质量
3. 生成结构化的 JSON 数据
4. 模块化设计，便于维护和扩展

功能模块:
    1. URL采集模块 (url_fetcher) - 获取病历URL列表
    2. 病例详情爬取模块 (case_crawler) - 结构化数据提取
    3. 数据提取Schema (schemas) - CSS选择器定义
    4. 工具函数 (utils) - 通用工具函数
    5. 配置管理 (config) - 命令行参数管理

使用示例:
    # 完整流程
    python -m data_processing.main --mode full --max-pages 5 --max-concurrent 3
    
    # 仅采集URL
    python -m data_processing.main --mode fetch-urls --start-page 1 --max-pages 5
    
    # 仅爬取详情
    python -m data_processing.main --mode crawl-details --max-concurrent 3 --start-index 0 --end-index 10

输出说明:
    - iiyi_case_urls.txt: 病历URL列表文件（每行一个URL）
    - case_details/: 病例JSON文件目录（每个病例一个.json文件）
"""

try:
    # 尝试相对导入（作为模块运行时）
    from .config import get_config, create_parser
    from .url_fetcher import fetch_all_case_urls, main_fetch_urls
    from .case_crawler import crawl_case_details_improved, main_crawl_details_improved
    from .schemas import get_case_extraction_schema, get_simple_case_extraction_schema
    from .utils import (
        create_content_filter,
        clean_text,
        extract_publisher_from_structured_data,
        format_case_summary_structured,
        extract_case_urls_from_html,
        extract_case_id_from_url,
        save_case_urls_to_file,
        load_urls_from_file,
        save_case_data_to_json
    )
except ImportError:
    # 回退到绝对导入（直接运行时）
    from config import get_config, create_parser
    from url_fetcher import fetch_all_case_urls, main_fetch_urls
    from case_crawler import crawl_case_details_improved, main_crawl_details_improved
    from schemas import get_case_extraction_schema, get_simple_case_extraction_schema
    from utils import (
        create_content_filter,
        clean_text,
        extract_publisher_from_structured_data,
        format_case_summary_structured,
        extract_case_urls_from_html,
        extract_case_id_from_url,
        save_case_urls_to_file,
        load_urls_from_file,
        save_case_data_to_json
    )

__version__ = "2.0.0"
__author__ = "MedSynthAI Team"

__all__ = [
    # 配置管理
    "get_config",
    "create_parser",
    
    # URL采集
    "fetch_all_case_urls",
    "main_fetch_urls",
    
    # 病例详情爬取
    "crawl_case_details_improved",
    "main_crawl_details_improved",
    
    # 数据提取Schema
    "get_case_extraction_schema",
    "get_simple_case_extraction_schema",
    
    # 工具函数
    "create_content_filter",
    "clean_text",
    "extract_publisher_from_structured_data",
    "format_case_summary_structured",
    "extract_case_urls_from_html",
    "extract_case_id_from_url",
    "save_case_urls_to_file",
    "load_urls_from_file",
    "save_case_data_to_json",
]
