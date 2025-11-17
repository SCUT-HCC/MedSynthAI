"""
爱爱医病历数据采集模块 - URL采集模块

负责从爱爱医网站采集所有病历URL列表
"""

import asyncio
from typing import List, Optional, Set
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

try:
    from .config import LIST_PAGE_PATTERN
    from .utils import extract_case_urls_from_html, save_case_urls_to_file
except ImportError:
    from config import LIST_PAGE_PATTERN
    from utils import extract_case_urls_from_html, save_case_urls_to_file


async def fetch_all_case_urls(
    start_page: int = 1,
    end_page: Optional[int] = None,
    max_pages: int = 100,
    verbose: bool = True
) -> List[str]:
    """
    获取爱爱医网站的所有病历URL
    
    Args:
        start_page: 起始页码
        end_page: 结束页码，如果为None则自动检测
        max_pages: 最大页数限制
        verbose: 是否显示详细信息
        
    Returns:
        病历URL列表
    """
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
            case_links = extract_case_urls_from_html(result.html)
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
    """
    检测最后一页
    
    Args:
        start_page: 起始页码
        max_pages: 最大检测页数
        verbose: 是否显示详细信息
        
    Returns:
        最后一页的页码
    """
    async def _page_has_cases(page_num: int) -> bool:
        """检查指定页码是否包含病历"""
        url = LIST_PAGE_PATTERN.format(page=page_num)

        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(verbose=False)
            result = await crawler.arun(url, config=config)

            if not result.success:
                return False

            # 检查是否包含病历链接
            case_links = extract_case_urls_from_html(result.html)
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


async def main_fetch_urls(start_page: int = 1, max_pages: int = 5, verbose: bool = True):
    """
    采集URL列表的主函数
    
    Args:
        start_page: 起始页码
        max_pages: 最大页数
        verbose: 是否显示详细信息
    """
    print("=" * 60)
    print("爱爱医病历 URL 采集工具")
    print("=" * 60)

    case_urls = await fetch_all_case_urls(
        start_page=start_page,
        end_page=None,
        max_pages=max_pages,
        verbose=verbose
    )

    if case_urls:
        await save_case_urls_to_file(case_urls, "iiyi_case_urls.txt")
        print(f"\n总计发现: {len(case_urls)} 个唯一病历 URL")
