"""
爱爱医病历数据采集模块 - 主入口文件

提供命令行接口和完整的工作流程
"""

import asyncio
try:
    from .config import get_config
    from .url_fetcher import main_fetch_urls
    from .case_crawler import main_crawl_details_improved
except ImportError:
    from config import get_config
    from url_fetcher import main_fetch_urls
    from case_crawler import main_crawl_details_improved


async def main():
    """主函数 - 根据配置参数执行相应的工作流程"""
    
    # 获取配置参数
    config = get_config()
    
    if config.mode == 'fetch-urls':
        # 仅采集URL
        await main_fetch_urls(
            start_page=config.start_page,
            max_pages=config.max_pages,
            verbose=config.verbose
        )
    
    elif config.mode == 'crawl-details':
        # 仅爬取病例详情
        await main_crawl_details_improved(
            url_file=config.url_file,
            output_dir=config.output_dir,
            max_concurrent=config.max_concurrent,
            start_index=config.start_index,
            end_index=config.end_index,
            verbose=config.verbose
        )
    
    elif config.mode == 'full':
        # 完整流程
        print("\n" + "=" * 80)
        print(" 爱爱医病历数据采集完整流程 (改进版)")
        print("=" * 80)

        # 第一步：采集URL列表
        print("\n【第一步】采集病历URL列表")
        print("-" * 80)
        await main_fetch_urls(
            start_page=config.start_page,
            max_pages=config.max_pages,
            verbose=config.verbose
        )

        # 第二步：爬取病例详情
        print("\n\n【第二步】爬取病例详情页 (改进版)")
        print("-" * 80)
        await main_crawl_details_improved(
            url_file=config.url_file,
            output_dir=config.output_dir,
            max_concurrent=config.max_concurrent,
            start_index=config.start_index,
            end_index=config.end_index,
            verbose=config.verbose
        )

        print("\n" + "=" * 80)
        print(" 完成！所有病历数据已保存到 case_details/ 目录 (JSON格式)")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
