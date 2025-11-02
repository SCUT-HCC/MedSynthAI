import json
import os
import time
import hashlib
from typing import List, Dict

# -------------------------- 配置 --------------------------
RAW_DATA_PATH = "medical_cases_crawl4ai/all_cases_summary.json"  # 原始数据路径（需与爬虫模块一致）
OUTPUT_DIR = "medical_cases_processed"  # 处理后数据目录
os.makedirs(OUTPUT_DIR, exist_ok=True)
REPORT_PATH = os.path.join(OUTPUT_DIR, "deduplication_report.md")  # 报告路径
PROCESSED_DATA_PATH = os.path.join(OUTPUT_DIR, "deduplicated_cases.json")  # 去重后数据路径

# -------------------------- 数据去重函数 --------------------------
def deduplicate_cases(raw_cases: List[Dict]) -> tuple[List[Dict], Dict]:
    """
    对原始病例数据去重并统计
    返回：(去重后的数据, 统计指标)
    """
    stats = {
        "raw_total": len(raw_cases),  # 原始数据总量
        "url_duplicate_count": 0,     # URL重复数量
        "content_duplicate_count": 0, # 内容重复数量
        "deduplicated_total": 0,      # 去重后数量
        "total_duplicate_count": 0,   # 总重复数量
        "url_duplicate_ratio": 0.0,   # URL重复占比
        "content_duplicate_ratio": 0.0, # 内容重复占比
        "deduplication_rate": 0.0     # 去重率
    }

    crawled_urls = set()
    crawled_content_hashes = set()
    deduplicated_cases = []

    for case in raw_cases:
        case_url = case.get("case_url", "")
        
        # 1. URL去重
        if not case_url or case_url in crawled_urls:
            stats["url_duplicate_count"] += 1
            continue
        
        # 2. 内容去重（基于核心字段的哈希）
        core_content = f"{case.get('case_title', '')}_{case.get('basic_info', '')}_{case.get('analysis_summary', '')}"
        content_hash = hashlib.md5(core_content.encode("utf-8")).hexdigest()
        if content_hash in crawled_content_hashes:
            stats["content_duplicate_count"] += 1
            continue
        
        # 3. 无重复，保留数据
        deduplicated_cases.append(case)
        crawled_urls.add(case_url)
        crawled_content_hashes.add(content_hash)

    # 计算统计指标
    stats["deduplicated_total"] = len(deduplicated_cases)
    stats["total_duplicate_count"] = stats["url_duplicate_count"] + stats["content_duplicate_count"]
    
    if stats["raw_total"] > 0:
        stats["url_duplicate_ratio"] = stats["url_duplicate_count"] / stats["raw_total"]
        stats["content_duplicate_ratio"] = stats["content_duplicate_count"] / stats["raw_total"]
        stats["deduplication_rate"] = stats["total_duplicate_count"] / stats["raw_total"]

    return deduplicated_cases, stats

# -------------------------- 报告生成函数 --------------------------
def generate_report(stats: Dict, output_path: str):
    """生成详细的去重分析报告"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"""# 医疗病例数据去重分析报告
生成时间：{time.strftime("%Y-%m-%d %H:%M:%S")}

## 一、数据质量指标（去重前后对比）
| 指标                | 去重前 | 去重后 | 变化量 |
|---------------------|--------|--------|--------|
| 原始数据总量        | {stats['raw_total']:,}  | -      | -      |
| 去重后有效数据量    | -      | {stats['deduplicated_total']:,}  | -      |
| URL重复数据量       | {stats['url_duplicate_count']:,}  | 0      | 减少{stats['url_duplicate_count']:,} 条 |
| 内容重复数据量      | {stats['content_duplicate_count']:,}  | 0      | 减少{stats['content_duplicate_count']:,} 条 |
| 总重复数据量        | {stats['total_duplicate_count']:,}  | 0      | 减少{stats['total_duplicate_count']:,} 条 |
| **数据去重率**      | -      | -      | {stats['deduplication_rate']:.2%} |

## 二、重复数据分析
- URL重复占比：{stats['url_duplicate_ratio']:.2%}（同一URL多次爬取）
- 内容重复占比：{stats['content_duplicate_ratio']:.2%}（不同URL但内容一致）

## 三、数据质量提升效果
1. 完整性：所有有效字段（主诉、现病史等）均完整保留
2. 准确性：消除重复数据对后续分析的干扰
3. 存储优化：减少 {stats['total_duplicate_count']:,} 条冗余数据

## 四、去重配置说明
- URL去重：基于病例详情页URL完全匹配
- 内容去重：基于「标题+基本信息+分析总结」的MD5哈希
""")

# -------------------------- 主处理逻辑 --------------------------
def main():
    """读取原始数据，执行去重、统计和报告生成"""
    # 1. 读取原始爬取数据
    if not os.path.exists(RAW_DATA_PATH):
        print(f"❌ 原始数据文件不存在：{RAW_DATA_PATH}")
        return

    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        raw_cases = json.load(f)
    print(f"📊 读取原始数据：{len(raw_cases)} 条病例")

    # 2. 执行去重
    deduplicated_cases, stats = deduplicate_cases(raw_cases)
    print(f"🔍 去重完成：原始 {stats['raw_total']} 条，去重后 {stats['deduplicated_total']} 条，去重率 {stats['deduplication_rate']:.2%}")

    # 3. 保存去重后的数据
    with open(PROCESSED_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(deduplicated_cases, f, ensure_ascii=False, indent=2)
    print(f"💾 去重后数据保存至：{PROCESSED_DATA_PATH}")

    # 4. 生成分析报告
    generate_report(stats, REPORT_PATH)
    print(f"📑 分析报告生成至：{REPORT_PATH}")

if __name__ == "__main__":
    main()