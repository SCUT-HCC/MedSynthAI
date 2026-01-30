"""
爱爱医病历数据采集模块 - 工具函数

包含内容清理、URL处理、文件操作等通用工具函数
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Union, Optional, Set
from crawl4ai.content_filter_strategy import PruningContentFilter


def create_content_filter():
    """创建优化的内容过滤器"""
    return PruningContentFilter(
        threshold=0.45,           # 内容密度阈值
        threshold_type="dynamic", # 动态阈值
        min_word_threshold=3      # 最少词数
    )


def clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text.strip())
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    return text


def extract_publisher_from_structured_data(data: Dict) -> str:
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


def format_case_summary_structured(data: Dict) -> str:
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


def extract_case_urls_from_html(html: str) -> List[str]:
    """从HTML中提取病历URL"""
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


def extract_case_id_from_url(url: str) -> str:
    """从URL提取病例ID"""
    match = re.search(r'/show/([^/]+)\.html', url)
    if match:
        return match.group(1)
    return str(hash(url))


async def save_case_urls_to_file(
    urls: List[str],
    output_file: str = "iiyi_case_urls.txt"
) -> None:
    """保存URL到文件"""
    with open(output_file, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(f"{url}\n")

    print(f"💾 已保存 {len(urls)} 个 URL 到 {output_file}")


def load_urls_from_file(url_file: str) -> List[str]:
    """从文件加载URL"""
    with open(url_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    return urls


def save_case_data_to_json(
    url: str,
    case_id: str,
    extracted_data: Dict,
    extraction_success: bool,
    output_dir: str = "case_details"
) -> Path:
    """保存病例数据为JSON文件"""
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 准备JSON数据
    json_data = {
        "url": url,
        "case_id": case_id,
        "extracted_data": extracted_data,
        "extraction_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "extraction_success": extraction_success,
        "data_source": "爱爱医 (iiyi.com)"
    }
    
    # 保存为JSON文件
    output_file = output_path / f"{case_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    return output_file
