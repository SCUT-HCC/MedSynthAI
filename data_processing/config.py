"""
爱爱医病历数据采集模块 - 配置参数管理

使用argparse管理所有配置参数
"""

import argparse
try:
    from typing import Namespace
except ImportError:
    from argparse import Namespace


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="爱爱医病历数据采集工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 采集URL列表
  python main.py --mode fetch-urls --start-page 1 --max-pages 5
  
  # 爬取病例详情
  python main.py --mode crawl-details --max-concurrent 3 --start-index 0 --end-index 10
  
  # 完整流程
  python main.py --mode full --max-pages 5 --max-concurrent 3
        """
    )
    
    # 模式选择
    parser.add_argument(
        '--mode',
        choices=['fetch-urls', 'crawl-details', 'full'],
        default='full',
        help='运行模式: fetch-urls(仅采集URL), crawl-details(仅爬取详情), full(完整流程)'
    )
    
    # URL采集相关参数
    parser.add_argument(
        '--start-page',
        type=int,
        default=1,
        help='起始页码 (默认: 1)'
    )
    
    parser.add_argument(
        '--end-page',
        type=int,
        default=None,
        help='结束页码 (默认: 自动检测)'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        default=100,
        help='最大页数限制 (默认: 100)'
    )
    
    # 病例详情爬取相关参数
    parser.add_argument(
        '--url-file',
        type=str,
        default='iiyi_case_urls.txt',
        help='URL文件路径 (默认: iiyi_case_urls.txt)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='case_details',
        help='输出目录 (默认: case_details)'
    )
    
    parser.add_argument(
        '--max-concurrent',
        type=int,
        default=3,
        help='最大并发数 (默认: 3)'
    )
    
    parser.add_argument(
        '--start-index',
        type=int,
        default=0,
        help='起始URL索引 (默认: 0)'
    )
    
    parser.add_argument(
        '--end-index',
        type=int,
        default=None,
        help='结束URL索引 (默认: 全部)'
    )
    
    # 通用参数
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=True,
        help='详细输出 (默认: True)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='静默模式'
    )
    
    return parser


def get_config(args: Namespace = None) -> Namespace:
    """获取配置参数"""
    parser = create_parser()
    
    if args is None:
        args = parser.parse_args()
    
    # 处理静默模式
    if args.quiet:
        args.verbose = False
    
    return args


# URL常量
LIST_PAGE_BASE = "https://www.iiyi.com/"  # 病历列表页基础URL
CASE_DETAIL_BASE = "https://bingli.iiyi.com/show"  # 病历详情页基础URL
LIST_PAGE_PATTERN = "https://www.iiyi.com/?a=b&p={page}"  # 列表页URL模式
