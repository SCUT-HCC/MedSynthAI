import asyncio
import json
import os
import random
from typing import List, Dict, Optional
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# -------------------------- 基础配置 --------------------------
OUTPUT_DIR = "medical_cases_crawl4ai"
os.makedirs(OUTPUT_DIR, exist_ok=True)
ERROR_LOG_PATH = "error_pages_crawl4ai.txt"

# -------------------------- 工具函数 --------------------------
def log_error(page_num: int, error_msg: str):
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"Page {page_num}: {error_msg}\n")
    print(f"❌ 第 {page_num} 页错误：{error_msg}")

# -------------------------- 选择器配置 --------------------------
CASE_LIST_SCHEMA = {
    "name": "MedicalCaseList",
    "baseSelector": "div.iiyi-list-contn > div.li",
    "fields": [
        {"name": "case_title", "selector": "div.ri > a.t", "type": "text"},
        {"name": "case_url", "selector": "div.ri > a.t", "type": "attribute", "attribute": "href"}
    ]
}

CASE_DETAIL_SCHEMA = {
    "name": "MedicalCaseDetail",
    "baseSelector": "body",
    "fields": [
        {"name": "case_title", "selector": "div.case_details_cont h2", "type": "text"},
        {"name": "primary_department", "selector": "div.breadcrumbs > a:nth-child(2)", "type": "text"},
        {"name": "secondary_department", "selector": "div.breadcrumbs > a:nth-child(3)", "type": "text"},
        {"name": "basic_info", "selector": "div.case_summary.position1 > div.situation > p:nth-child(1) > span", "type": "text"},
        {"name": "html_content1", "selector": "div.case_study.position2", "type": "html"},
        {"name": "html_content2", "selector": "div.case_study.position3", "type": "html"},
        {"name": "html_content3", "selector": "div.case_study.position4", "type": "html"}
    ]
}

# -------------------------- User-Agent 池 --------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
]

# -------------------------- 滑块检测与等待函数 (新逻辑) --------------------------
async def handle_verification_if_needed(crawler: AsyncWebCrawler, url: str, max_attempts: int = 10) -> bool:
    """
    检测是否存在滑块验证。如果存在，则等待一个递增的随机时间后重试。
    """
    if url.startswith("https://"):
        url = url.replace("https://", "http://", 1)

    for attempt in range(1, max_attempts + 1):
        # 每次尝试都使用新的 User-Agent
        crawler.browser_config.user_agent = random.choice(USER_AGENTS)
        print(f"🔄 [滑块检测] 使用随机 User-Agent: {crawler.browser_config.user_agent}")

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=30000,
            wait_for="css:body",
        )
        result = await crawler.arun(url=url, config=config)

        if not result.success:
            print(f"❌ 无法访问详情页：{url}，错误：{result.error_message}")
            wait_time = 3600 * attempt + random.uniform(0, 600) # 访问失败也增加等待
            print(f"   访问失败，等待 {wait_time / 60:.2f} 分钟后重试...")
            await asyncio.sleep(wait_time)
            continue

        page_content = result.html
        has_verification = (
            "img_verification" in page_content or
            "图形验证" in page_content or
            "拖动左边滑块完成上方拼图" in page_content or
            "请先完成图片验证" in page_content
        )

        if not has_verification:
            print(f"✅ 页面正常，未检测到滑块验证。")
            return True  # 页面正常，可以爬取

        # 如果检测到滑块
        print(f"⚠️ 检测到滑块验证 (第 {attempt}/{max_attempts} 次尝试)。URL: {url}")
        if attempt < max_attempts:
            # 递增等待时间：1小时、2小时、3小时... 每次再加一个随机数
            wait_time = 3600 * attempt + random.uniform(0, 1800)
            print(f"   将在 {wait_time / 3600:.2f} 小时后再次尝试...")
            await asyncio.sleep(wait_time)
        else:
            print(f"❌ 已达到最大尝试次数 ({max_attempts}次)，仍存在滑块验证。放弃该 URL。")
            return False # 达到最大尝试次数，放弃

    print(f"❌ 经过 {max_attempts} 次尝试后，仍无法正常访问页面。放弃该 URL。")
    return False

# -------------------------- 列表页爬取 --------------------------
async def extract_case_links(crawler: AsyncWebCrawler, page_url: str) -> List[Dict]:
    # 每次请求都使用新的 User-Agent
    crawler.browser_config.user_agent = random.choice(USER_AGENTS)
    print(f"🔄 [列表页] 使用随机 User-Agent: {crawler.browser_config.user_agent}")

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=JsonCssExtractionStrategy(schema=CASE_LIST_SCHEMA),
        wait_for="css:div.iiyi-list-contn > div.li",
        page_timeout=30000
    )
    result = await crawler.arun(url=page_url, config=config)
    if not result.success:
        raise Exception(f"列表页爬取失败：{result.error_message}")

    try:
        case_links = json.loads(result.extracted_content)
        from urllib.parse import urljoin
        for case in case_links:
            if case.get("case_url"):
                case["case_url"] = urljoin(page_url, case["case_url"])
        return case_links
    except json.JSONDecodeError:
        raise Exception(f"链接解析失败：{result.extracted_content[:200]}...")

# -------------------------- 详情页爬取 --------------------------
async def extract_case_details(crawler: AsyncWebCrawler, case_url: str, referer_url: str) -> Optional[Dict]:
    """
    爬取详情页数据
    新增 referer_url 参数来伪造 Referer 请求头
    """
    if case_url.startswith("https://"):
        case_url = case_url.replace("https://", "http://", 1)

    # 每次请求都使用新的 User-Agent
    crawler.browser_config.user_agent = random.choice(USER_AGENTS)
    print(f"🔄 [详情页] 使用随机 User-Agent: {crawler.browser_config.user_agent}")

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=JsonCssExtractionStrategy(schema=CASE_DETAIL_SCHEMA),
        wait_for="css:div.case_study",
        page_timeout=60000,
    )

    try:
        result = await crawler.arun(
            url=case_url,
            config=config,
            headers={"Referer": referer_url}
        )
        if not result.success:
            print(f"⚠️ 详情页 {case_url} 爬取失败：{result.error_message}")
            return None

        extracted_data = json.loads(result.extracted_content)
        raw_detail = extracted_data[0] if isinstance(extracted_data, list) and extracted_data else extracted_data if isinstance(extracted_data, dict) else None
        if not raw_detail:
            print(f"⚠️ 详情页 {case_url}：提取结果格式异常或为空")
            return None

        raw_detail["case_url"] = case_url
        html_content1 = raw_detail.get("html_content1", "")
        html_content2 = raw_detail.get("html_content2", "")
        html_content3 = raw_detail.get("html_content3", "")

        target_case_struct = {
            "case_url": raw_detail.get("case_url", ""),
            "case_title": raw_detail.get("case_title", "").strip(),
            "primary_department": raw_detail.get("primary_department", "").strip(),
            "secondary_department": raw_detail.get("secondary_department", "").strip(),
            "basic_info": raw_detail.get("basic_info", "").strip(),
            "case_introduction": {},
            "diagnosis_treatment_process": {},
            "analysis_summary": ""
        }

        for html_content in [html_content1, html_content2, html_content3]:
            if not html_content: continue
            soup = BeautifulSoup(html_content, "html.parser")
            for section in soup.select("div.case_study"):
                section_title_element = section.select_one("h2")
                if not section_title_element: continue
                section_name = section_title_element.get_text(strip=True)

                target_field = None
                if "病案介绍" in section_name: target_field = target_case_struct["case_introduction"]
                elif "诊治过程" in section_name: target_field = target_case_struct["diagnosis_treatment_process"]
                elif "分析总结" in section_name:
                    target_case_struct["analysis_summary"] = section.get_text(strip=True).replace(section_name, "", 1).strip()
                    continue
                else: continue

                for sub_section in section.select("div"):
                    sub_title_element = sub_section.select_one("h3 > em")
                    if not sub_title_element: continue
                    sub_title_name = sub_title_element.get_text(strip=True)
                    sub_content = sub_section.get_text(strip=True).replace(sub_title_name, "", 1).strip()
                    
                    field_map = {
                        "主诉": "chief_complaint", "现病史": "history_of_present_illness",
                        "既往史": "past_medical_history", "查体": "physical_examination",
                        "辅助检查": "auxiliary_examinations", "初步诊断": "preliminary_diagnosis",
                        "诊断依据": "diagnostic_basis", "鉴别诊断": "differential_diagnosis",
                        "诊治经过": "treatment_course", "诊断结果": "final_diagnosis"
                    }
                    for key, value in field_map.items():
                        if key in sub_title_name:
                            target_field[value] = sub_content
                            break
        return target_case_struct
    except Exception as e:
        print(f"⚠️ 详情页 {case_url} 解析失败：{str(e)}")
        return None

# -------------------------- 单页爬取 (新逻辑) --------------------------
async def crawl_single_page(crawler: AsyncWebCrawler, page_num: int, total_pages: int) -> List[Dict]:
    """爬取单页数据，不使用代理"""
    page_url = f"http://www.iiyi.com/?a=b&page={page_num}"
    print(f"\n📄 正在爬取列表页 {page_num}/{total_pages}：{page_url}")

    try:
        case_links = await extract_case_links(crawler, page_url)
    except Exception as e:
        log_error(page_num, str(e))
        return []

    print(f"✅ 第 {page_num} 页发现 {len(case_links)} 个病例")
    if not case_links:
        log_error(page_num, "未提取到任何病例链接")
        return []

    page_cases = []
    for idx, case in enumerate(case_links, 1):
        case_url = case.get("case_url")
        if not case_url: continue

        # --- 每个详情页请求前的随机延迟 ---
        request_delay = random.uniform(8, 15)
        print(f"   ...等待 {request_delay:.2f} 秒后处理下一个病例...")
        await asyncio.sleep(request_delay)

        print(f"正在处理第 {idx}/{len(case_links)} 个病例：{case_url}")
        try:
            # 检测滑块验证，如果失败则跳过
            if not await handle_verification_if_needed(crawler, case_url):
                print(f"⚠️ 滑块验证最终失败，跳过该病例：{case_url}")
                continue

            # 滑块验证通过，继续爬取
            # 注意：传入了 page_url 作为 referer
            case_detail = await extract_case_details(crawler, case_url, referer_url=page_url)
            if case_detail:
                page_cases.append(case_detail)
                print(f"✅ 成功提取病例：{case_detail.get('case_title', '未知标题')}")
            else:
                print(f"⚠️ 详情页提取失败：{case_url}")
        except Exception as e:
            print(f"❌ 处理详情页时发生严重错误：{str(e)}")
            continue

    return page_cases

# -------------------------- 主爬取逻辑 (新逻辑) --------------------------
async def main(start_page: int, end_page: int):
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        user_agent=random.choice(USER_AGENTS),
        # 3. 新增：开启 Stealth 模式
        # stealth=True
    )

    all_cases = []
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for page_num in range(start_page, end_page + 1):
            # 之前在这里更新UA的逻辑已被移到具体请求函数中

            page_cases = await crawl_single_page(crawler, page_num, end_page)
            all_cases.extend(page_cases)

            # --- 每个列表页爬取完成后的长延迟 ---
            if page_num < end_page:
                page_delay = random.uniform(60, 120)
                print(f"\n--- 第 {page_num} 页处理完毕，休息 {page_delay:.2f} 秒后进入下一页 ---")
                await asyncio.sleep(page_delay)

    if all_cases:
        summary_path = os.path.join(OUTPUT_DIR, "all_cases_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(all_cases, f, ensure_ascii=False, indent=2)
        print(f"\n🎉 爬取完成！共获取 {len(all_cases)} 个有效病例，汇总文件：{summary_path}")
    else:
        print(f"\n⚠️  爬取完成，但未获取有效病例")

# -------------------------- 启动入口 --------------------------
if __name__ == "__main__":
    TARGET_START_PAGE = 2
    TARGET_END_PAGE = 1000
    asyncio.run(main(start_page=TARGET_START_PAGE, end_page=TARGET_END_PAGE))