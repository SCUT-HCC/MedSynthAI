"""
爱爱医病历数据采集模块 (改进版)

使用 crawl4ai 的 JsonCssExtractionStrategy 和 PruningContentFilter
进行精确的结构化数据提取。

主要改进:
1. 使用 CSS 选择器进行精确数据提取
2. 结合 PruningContentFilter 优化内容质量
3. 生成结构化的 JSON 数据

功能模块:
    1. URL采集模块 (fetch_all_case_urls) - 保持不变
    2. 病例详情爬取模块 (crawl_case_details_improved)
       - 使用 JsonCssExtractionStrategy 进行结构化提取
       - 使用 PruningContentFilter 优化内容质量
       - 直接保存结构化的 JSON 数据

使用示例:
    # 改进的完整流程
    asyncio.run(main_improved())

    # 仅采集URL
    asyncio.run(main_fetch_urls())

    # 仅爬取详情（使用改进版）
    asyncio.run(main_crawl_details_improved())

输出说明:
    - iiyi_case_urls.txt: 病历URL列表文件（每行一个URL）
    - case_details/: 病例JSON文件目录（每个病例一个.json文件）
"""

import asyncio
import re
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Union, Optional, Set
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from bs4 import BeautifulSoup


# 爱爱医病历相关URL配置
LIST_PAGE_BASE = "https://www.iiyi.com/"  # 病历列表页基础URL
CASE_DETAIL_BASE = "https://bingli.iiyi.com/show"  # 病历详情页基础URL
LIST_PAGE_PATTERN = "https://www.iiyi.com/?a=b&p={page}"  # 列表页URL模式


# ========== 改进的数据提取Schema ==========
def get_case_extraction_schema() -> Dict:
    """
    获取病例详情提取的JSON Schema
    
    基于对HTML结构的分析，设计精确的CSS选择器来提取：
    - 发布人信息
    - 病例摘要
    - 病案介绍
    - 诊治过程
    - 分析总结
    """
    
    schema = {
        "name": "爱爱医病例详情",
        "baseSelector": "body",  # 整个页面作为基础
        "fields": [
            {
                "name": "title", 
                "selector": "h2", 
                "type": "text"
            },
            {
                "name": "publisher_info", 
                "selector": ".doctor_desc", 
                "type": "text",
                "transformers": ["clean_text"]
            },
            {
                "name": "publisher_name", 
                "selector": ".doctor_desc span", 
                "type": "text"
            },
            {
                "name": "publisher_title", 
                "selector": ".doctor_desc i", 
                "type": "text"
            },
            {
                "name": "publisher_update_time", 
                "selector": ".doctor_desc p:last-child", 
                "type": "text"
            },
            {
                "name": "case_summary", 
                "selector": ".case_summary.position1", 
                "type": "text",
                "transformers": ["clean_text"]
            },
            {
                "name": "case_summary_structured", 
                "selector": ".case_summary.position1 .situation p", 
                "type": "multiple",
                "fields": [
                    {
                        "name": "label", 
                        "selector": "var", 
                        "type": "text"
                    },
                    {
                        "name": "content", 
                        "selector": "span", 
                        "type": "text"
                    }
                ]
            },
            {
                "name": "case_introduction", 
                "selector": ".case_study.position2", 
                "type": "text",
                "transformers": ["clean_text"]
            },
            {
                "name": "diagnosis_treatment", 
                "selector": ".case_study.position3", 
                "type": "text",
                "transformers": ["clean_text"]
            },
            {
                "name": "analysis_summary", 
                "selector": ".case_study.position4", 
                "type": "text",
                "transformers": ["clean_text"]
            },
            {
                "name": "tags", 
                "selector": ".doctors_excel a.on span", 
                "type": "text"
            },
            {
                "name": "department", 
                "selector": ".breadcrumbs a:last-child", 
                "type": "text"
            },
            {
                "name": "images", 
                "selector": ".case_focus_map img", 
                "type": "multiple",
                "fields": [
                    {
                        "name": "src", 
                        "selector": "", 
                        "type": "attribute", 
                        "attribute": "src"
                    },
                    {
                        "name": "alt", 
                        "selector": "", 
                        "type": "attribute", 
                        "attribute": "alt"
                    }
                ]
            }
        ]
    }
    
    return schema


def get_simple_case_extraction_schema() -> Dict:
    """
    简化的病例提取Schema，处理可能的选择器变化
    """
    
    schema = {
        "name": "爱爱医病例详情_简化版",
        "baseSelector": "body",
        "fields": [
            {
                "name": "page_title", 
                "selector": "title", 
                "type": "text"
            },
            {
                "name": "case_title", 
                "selector": "h2", 
                "type": "text"
            },
            {
                "name": "publisher_info", 
                "selector": ".doctor_desc, .doctor_desc_left", 
                "type": "text"
            },
            {
                "name": "case_summary", 
                "selector": ".case_summary, .case_summary.position1, .situation", 
                "type": "text"
            },
            {
                "name": "case_content", 
                "selector": ".case_study, .case_study.position2, .case_study.position3, .case_study.position4", 
                "type": "text"
            },
            {
                "name": "main_content", 
                "selector": ".case_details_left, .case_details_cont", 
                "type": "text"
            }
        ]
    }
    
    return schema


# ========== URL获取函数 (保持不变) ==========

async def fetch_all_case_urls(
    start_page: int = 1,
    end_page: Optional[int] = None,
    max_pages: int = 100,
    verbose: bool = True
) -> List[str]:
    """
    获取爱爱医网站的所有病历URL - 保持原有逻辑不变
    """
    # ... (保持原有的fetch_all_case_urls函数代码)
    if verbose:
        print("🔍 开始获取爱爱医病历 URL...")

    case_urls: Set[str] = set()

    # ========== 第一阶段：确定页面范围 ==========
    if end_page is None:
        if verbose:
            print("🔎 自动探测最后一页...")
        end_page = await _detect_last_page(start_page, max_pages, verbose)
        if verbose:
            print(f"✅ 检测到最后一页: 第 {end_page} 页")

    # 限制最大页数
    if end_page - start_page + 1 > max_pages:
        if verbose:
            print(f"⚠️ 页面范围超过最大限制 {max_pages}，将只爬取前 {max_pages} 页")
        end_page = start_page + max_pages - 1

    total_pages = end_page - start_page + 1
    if verbose:
        print(f"📄 将爬取 {total_pages} 个列表页 (第 {start_page} 页到第 {end_page} 页)")

    # ========== 第二阶段：批量爬取列表页 ==========
    async with AsyncWebCrawler() as crawler:
        # 生成所有列表页URL
        list_page_urls = [
            LIST_PAGE_PATTERN.format(page=page)
            for page in range(start_page, end_page + 1)
        ]

        # 配置爬虫
        crawl_config = CrawlerRunConfig(
            only_text=False,
            verbose=verbose
        )

        if verbose:
            print(f"\n🚀 开始并发爬取 {len(list_page_urls)} 个列表页...")

        # 批量爬取所有列表页
        results = await crawler.arun_many(list_page_urls, config=crawl_config)

        # ========== 第三阶段：提取病历链接 ==========
        page_count = 0
        for result in results:
            page_count += 1

            if not result.success:
                if verbose:
                    print(f"⚠️ 第 {page_count} 页爬取失败: {result.url}")
                continue

            # 从HTML中提取所有病历详情页链接
            case_links = _extract_case_urls_from_html(result.html)
            case_urls.update(case_links)

            if verbose:
                print(f"✓ 第 {page_count}/{total_pages} 页: 发现 {len(case_links)} 个病历链接 "
                      f"(累计 {len(case_urls)} 个)")

    # ========== 第四阶段：转换为列表并排序 ==========
    final_urls = sorted(list(case_urls))

    if verbose:
        print(f"\n✅ 完成！共发现 {len(final_urls)} 个唯一病历 URL")

    return final_urls


async def _detect_last_page(
    start_page: int = 1,
    max_pages: int = 100,
    verbose: bool = False
) -> int:
    """检测最后一页 - 保持原有逻辑"""
    async def _page_has_cases(page_num: int) -> bool:
        """检查指定页码是否包含病历"""
        url = LIST_PAGE_PATTERN.format(page=page_num)

        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(verbose=False)
            result = await crawler.arun(url, config=config)

            if not result.success:
                return False

            # 检查是否包含病历链接
            case_links = _extract_case_urls_from_html(result.html)
            return len(case_links) > 0

    # 二分查找最后一页
    left = start_page
    right = start_page + max_pages
    last_valid_page = start_page

    while left <= right:
        mid = (left + right) // 2

        if verbose:
            print(f"  检查第 {mid} 页...")

        has_cases = await _page_has_cases(mid)

        if has_cases:
            last_valid_page = mid
            left = mid + 1
        else:
            right = mid - 1

    return last_valid_page


def _extract_case_urls_from_html(html: str) -> List[str]:
    """从HTML中提取病历URL - 保持原有逻辑"""
    case_urls: Set[str] = set()

    # 匹配各种可能的URL格式
    patterns = [
        r'https?://bingli\.iiyi\.com/show/[^"\'<>\s]+\.html',
        r'//bingli\.iiyi\.com/show/[^"\'<>\s]+\.html',
        r'/show/[^"\'<>\s]+\.html',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html)
        for match in matches:
            # 规范化URL
            if match.startswith('//'):
                url = 'https:' + match
            elif match.startswith('/show/'):
                url = 'https://bingli.iiyi.com' + match
            else:
                url = match

            # 验证URL格式：必须包含"-"
            filename_match = re.search(r'/show/([^/]+)\.html', url)
            if filename_match:
                filename = filename_match.group(1)
                if '-' in filename:
                    case_urls.add(url)

    return list(case_urls)


async def save_case_urls_to_file(
    urls: List[str],
    output_file: str = "iiyi_case_urls.txt"
) -> None:
    """保存URL到文件 - 保持原有逻辑"""
    with open(output_file, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(f"{url}\n")

    print(f"💾 已保存 {len(urls)} 个 URL 到 {output_file}")


def _load_urls_from_file(url_file: str) -> List[str]:
    """从文件加载URL - 保持原有逻辑"""
    with open(url_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    return urls


def _extract_case_id_from_url(url: str) -> str:
    """从URL提取病例ID - 保持原有逻辑"""
    match = re.search(r'/show/([^/]+)\.html', url)
    if match:
        return match.group(1)
    return str(hash(url))


# ========== 改进的数据提取函数 ==========

def _create_content_filter():
    """创建优化的内容过滤器"""
    return PruningContentFilter(
        threshold=0.45,           # 内容密度阈值
        threshold_type="dynamic", # 动态阈值
        min_word_threshold=3      # 最少词数
    )


def _clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text.strip())
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    return text


def _extract_publisher_from_structured_data(data: Dict) -> str:
    """从结构化数据中提取发布人信息"""
    publisher_parts = []
    
    # 提取姓名
    if 'publisher_name' in data and data['publisher_name']:
        publisher_parts.append(data['publisher_name'])
    
    # 提取职称
    if 'publisher_title' in data and data['publisher_title']:
        publisher_parts.append(data['publisher_title'])
    
    # 提取更新时间
    if 'publisher_update_time' in data and data['publisher_update_time']:
        time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', data['publisher_update_time'])
        if time_match:
            publisher_parts.append(f"更新时间：{time_match.group(1)}")
    
    return " | ".join(publisher_parts) if publisher_parts else "发布人信息提取失败"


def _format_case_summary_structured(data: Dict) -> str:
    """格式化结构化的病例摘要"""
    summary_parts = []
    
    # 处理结构化的病例摘要
    if 'case_summary_structured' in data and data['case_summary_structured']:
        for item in data['case_summary_structured']:
            if isinstance(item, dict) and 'label' in item and 'content' in item:
                summary_parts.append(f"{item['label']} {item['content']}")
    
    # 如果没有结构化数据，尝试从普通文本中提取
    if not summary_parts and 'case_summary' in data:
        summary_text = data['case_summary']
        # 尝试提取关键信息
        patterns = {
            '基本信息': r'【基本信息】([^【]+)',
            '发病原因': r'【发病原因】([^【]+)',
            '临床诊断': r'【临床诊断】([^【]+)',
            '治疗方案': r'【治疗方案】([^【]+)',
            '治疗结果': r'【治疗结果】([^【]+)',
            '病案重点': r'【病案重点】([^【]+)'
        }
        
        for label, pattern in patterns.items():
            match = re.search(pattern, summary_text)
            if match:
                summary_parts.append(f"{label}：{match.group(1).strip()}")
    
    return "\n".join(summary_parts) if summary_parts else "病例摘要提取失败"


async def crawl_case_details_improved(
    url_file: str = "iiyi_case_urls.txt",
    output_dir: str = "case_details",
    max_concurrent: int = 3,  # 减少并发数以提高成功率
    start_index: int = 0,
    end_index: Optional[int] = None,
    verbose: bool = True
) -> Dict[str, Union[int, List[str]]]:
    """
    改进的病例详情爬取函数
    
    使用 JsonCssExtractionStrategy 进行结构化数据提取
    直接保存为JSON格式而不是markdown
    """
    
    if verbose:
        print("🔍 开始爬取病例详情页 (改进版)...")

    # ========== 第一阶段：加载URL列表 ==========
    all_urls = _load_urls_from_file(url_file)

    if end_index is None:
        end_index = len(all_urls)

    urls_to_crawl = all_urls[start_index:end_index]

    if verbose:
        print(f"📄 总计 {len(all_urls)} 个URL，本次爬取 {len(urls_to_crawl)} 个 "
              f"(索引 {start_index} 到 {end_index-1})")

    # ========== 第二阶段：创建输出目录 ==========
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # ========== 第三阶段：创建提取策略 ==========
    # 尝试主schema，如果失败则尝试简化schema
    schemas = [get_case_extraction_schema(), get_simple_case_extraction_schema()]
    
    failed_urls: List[str] = []
    success_count = 0

    async with AsyncWebCrawler() as crawler:
        # 配置markdown生成器 - 使用内容过滤器
        content_filter = _create_content_filter()
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
                case_id = _extract_case_id_from_url(url)

                if not result.success:
                    if verbose:
                        print(f"  ❌ 失败: {case_id} - {result.error_message}")
                    failed_urls.append(url)
                    continue

                extracted_data = {}
                raw_markdown = ""
                
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
                    json_data = {
                        "url": url,
                        "case_id": case_id,
                        "extracted_data": extracted_data[0],
                        "extraction_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "extraction_success": extraction_success,
                        "data_source": "爱爱医 (iiyi.com)"
                    }
                    
                    # 保存为JSON文件
                    output_file = output_path / f"{case_id}.json"
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)

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


# ========== 示例用法 ==========

async def main_fetch_urls():
    """采集URL列表"""
    print("=" * 60)
    print("爱爱医病历 URL 采集工具")
    print("=" * 60)

    case_urls = await fetch_all_case_urls(
        start_page=1,
        end_page=None,
        max_pages=5,  # 测试用，减少页数
        verbose=True
    )

    if case_urls:
        await save_case_urls_to_file(case_urls, "iiyi_case_urls.txt")
        print(f"\n总计发现: {len(case_urls)} 个唯一病历 URL")


async def main_crawl_details_improved():
    """改进的病例详情爬取"""
    print("=" * 60)
    print("爱爱医病例详情爬取工具 (改进版)")
    print("=" * 60)

    stats = await crawl_case_details_improved(
        url_file="iiyi_case_urls.txt",
        output_dir="case_details",
        max_concurrent=3,
        start_index=0,
        end_index=3,  # 测试用，只爬取前3个
        verbose=True
    )

    print(f"\n总计: {stats['total']} 个URL")
    print(f"成功: {stats['success']} 个")
    print(f"失败: {stats['failed']} 个")
    print(f"📁 输出格式: JSON (结构化数据)")


async def main_improved():
    """改进的完整工作流"""
    print("\n" + "=" * 80)
    print(" 爱爱医病历数据采集完整流程 (改进版)")
    print("=" * 80)

    # 第一步：采集URL列表
    print("\n【第一步】采集病历URL列表")
    print("-" * 80)
    await main_fetch_urls()

    # 第二步：爬取病例详情
    print("\n\n【第二步】爬取病例详情页 (改进版)")
    print("-" * 80)
    await main_crawl_details_improved()

    print("\n" + "=" * 80)
    print(" 完成！所有病历数据已保存到 case_details/ 目录 (JSON格式)")
    print("=" * 80)


if __name__ == "__main__":
    # 运行改进版完整流程
    asyncio.run(main_improved())
