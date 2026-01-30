"""
爱爱医病历数据采集模块 - 病例详情爬取模块

使用 JsonCssExtractionStrategy 进行结构化数据提取
"""

import asyncio
import json
from typing import Dict, List, Optional, Union
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

try:
    from .schemas import get_case_extraction_schema, get_simple_case_extraction_schema
    from .utils import (
        create_content_filter,
        extract_case_id_from_url,
        load_urls_from_file,
        save_case_data_to_json
    )
except ImportError:
    from schemas import get_case_extraction_schema, get_simple_case_extraction_schema
    from utils import (
        create_content_filter,
        extract_case_id_from_url,
        load_urls_from_file,
        save_case_data_to_json
    )


async def crawl_case_details_improved(
    url_file: str = "iiyi_case_urls.txt",
    output_dir: str = "case_details",
    max_concurrent: int = 3,
    start_index: int = 0,
    end_index: Optional[int] = None,
    verbose: bool = True
) -> Dict[str, Union[int, List[str]]]:
    """
    改进的病例详情爬取函数
    
    使用 JsonCssExtractionStrategy 进行结构化数据提取
    直接保存为JSON格式而不是markdown
    
    Args:
        url_file: URL文件路径
        output_dir: 输出目录
        max_concurrent: 最大并发数
        start_index: 起始URL索引
        end_index: 结束URL索引
        verbose: 是否显示详细信息
        
    Returns:
        包含统计信息的字典
    """
    
    if verbose:
        print("🔍 开始爬取病例详情页 (改进版)...")

    # ========== 第一阶段：加载URL列表 ==========
    all_urls = load_urls_from_file(url_file)

    if end_index is None:
        end_index = len(all_urls)

    urls_to_crawl = all_urls[start_index:end_index]

    if verbose:
        print(f"📄 总计 {len(all_urls)} 个URL，本次爬取 {len(urls_to_crawl)} 个 "
              f"(索引 {start_index} 到 {end_index-1})")

    # ========== 第二阶段：创建提取策略 ==========
    # 尝试主schema，如果失败则尝试简化schema
    schemas = [get_case_extraction_schema(), get_simple_case_extraction_schema()]
    
    failed_urls: List[str] = []
    success_count = 0

    async with AsyncWebCrawler() as crawler:
        # 配置markdown生成器 - 使用内容过滤器
        content_filter = create_content_filter()
        md_generator = DefaultMarkdownGenerator(
            content_filter=content_filter,
            options={
                "ignore_links": False,
                "escape_html": False
            }
        )

        if verbose:
            print(f"🚀 开始并发爬取 (最大并发数: {max_concurrent})...")

        # 分批爬取以控制并发
        for batch_start in range(0, len(urls_to_crawl), max_concurrent):
            batch_end = min(batch_start + max_concurrent, len(urls_to_crawl))
            batch_urls = urls_to_crawl[batch_start:batch_end]

            if verbose:
                print(f"\n📦 批次 {batch_start//max_concurrent + 1}: "
                      f"爬取 {len(batch_urls)} 个URL "
                      f"({batch_start+1}-{batch_end}/{len(urls_to_crawl)})")

            # 批量爬取
            results = await crawler.arun_many(batch_urls, config=None)

            # ========== 第四阶段：处理结果 ==========
            for i, result in enumerate(results):
                url = batch_urls[i]
                case_id = extract_case_id_from_url(url)

                if not result.success:
                    if verbose:
                        print(f"  ❌ 失败: {case_id} - {result.error_message}")
                    failed_urls.append(url)
                    continue

                extracted_data = {}
                
                try:
                    # 尝试使用结构化提取
                    extraction_success = False
                    for schema_idx, schema in enumerate(schemas):
                        try:
                            extraction_config = CrawlerRunConfig(
                                extraction_strategy=JsonCssExtractionStrategy(schema),
                                markdown_generator=md_generator,
                                verbose=False
                            )
                            
                            extraction_result = await crawler.arun(url, config=extraction_config)
                            
                            if extraction_result.success and hasattr(extraction_result, 'extracted_content'):
                                extracted_data = json.loads(extraction_result.extracted_content)
                                
                                extraction_success = True
                                if verbose and schema_idx > 0:
                                    print(f"  ⚠️ 主Schema失败，使用备用Schema成功: {case_id}")
                                break
                                
                        except Exception as e:
                            if verbose and schema_idx == 0:
                                print(f"  ⚠️ 主Schema失败，尝试备用Schema: {case_id} - {str(e)}")
                            continue

                    # ========== 直接保存为JSON格式 ==========
                    # 保存为JSON文件，直接使用提取的结构化数据
                    output_file = save_case_data_to_json(
                        url=url,
                        case_id=case_id,
                        extracted_data=extracted_data[0] if extracted_data else {},
                        extraction_success=extraction_success,
                        output_dir=output_dir
                    )

                    success_count += 1

                    if verbose:
                        print(f"  ✅ 成功: {case_id} → {output_file.name}")

                except Exception as e:
                    if verbose:
                        print(f"  ⚠️ 处理失败: {case_id} - {str(e)}")
                    failed_urls.append(url)

    # ========== 第五阶段：统计信息 ==========
    stats = {
        "total": len(urls_to_crawl),
        "success": success_count,
        "failed": len(failed_urls),
        "failed_urls": failed_urls
    }

    if verbose:
        print("\n" + "=" * 60)
        print("📊 爬取完成统计 (改进版)")
        print("=" * 60)
        print(f"✅ 成功: {stats['success']}/{stats['total']} "
              f"({stats['success']/stats['total']*100:.1f}%)")
        print(f"❌ 失败: {stats['failed']}/{stats['total']}")
        print(f"📁 输出格式: JSON (结构化数据)")

        if failed_urls:
            print(f"\n失败的URL (前5个):")
            for i, url in enumerate(failed_urls[:5], 1):
                print(f"  {i}. {url}")

    return stats


async def main_crawl_details_improved(
    url_file: str = "iiyi_case_urls.txt",
    output_dir: str = "case_details",
    max_concurrent: int = 3,
    start_index: int = 0,
    end_index: int = 3,
    verbose: bool = True
):
    """
    改进的病例详情爬取主函数
    
    Args:
        url_file: URL文件路径
        output_dir: 输出目录
        max_concurrent: 最大并发数
        start_index: 起始URL索引
        end_index: 结束URL索引
        verbose: 是否显示详细信息
    """
    print("=" * 60)
    print("爱爱医病历详情爬取工具 (改进版)")
    print("=" * 60)

    stats = await crawl_case_details_improved(
        url_file=url_file,
        output_dir=output_dir,
        max_concurrent=max_concurrent,
        start_index=start_index,
        end_index=end_index,
        verbose=verbose
    )

    print(f"\n总计: {stats['total']} 个URL")
    print(f"成功: {stats['success']} 个")
    print(f"失败: {stats['failed']} 个")
    print(f"📁 输出格式: JSON (结构化数据)")
