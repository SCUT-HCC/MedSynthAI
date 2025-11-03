"""
滑块检测与固定等待策略模块

说明:
- 提供 wait_and_detect(detect_fn, total_minutes=20, check_interval=30) 主函数
- detect_fn: 无参数函数，返回 True 表示检测到滑块/阻塞（需要继续等待），返回 False 表示无滑块（可继续爬取）
- 示例中包含 Selenium 检测函数模板（注释）
- 日志会输出到控制台并写入 data_processing/logs/slider_wait.log
"""
from __future__ import annotations
import time
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Callable, List, Dict, Any, Optional

# 配置日志
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "slider_wait.log"

logger = logging.getLogger("slider_wait")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(ch)
    logger.addHandler(fh)


def wait_and_detect(
    detect_fn: Callable[[], bool],
    total_minutes: int = 20,
    check_interval_seconds: int = 30,
) -> Dict[str, Any]:
    """
    在固定时间窗口内循环检测滑块状态。

    参数:
    - detect_fn: 返回 True 表示滑块存在（需要等待），False 表示滑块不存在（可继续）
    - total_minutes: 总等待时长（分钟），到期后停止并返回超时状态
    - check_interval_seconds: 两次检测之间的睡眠间隔（秒）

    返回字典:
    {
      "start_time": datetime,
      "end_time": datetime,
      "elapsed_seconds": int,
      "final_state": "continue"|"wait_timeout",
      "checks": [ { "ts": str, "detected": bool }... ]
    }
    """
    start_time = datetime.now()
    end_deadline = start_time + timedelta(minutes=total_minutes)
    checks: List[Dict[str, Any]] = []

    logger.info("开始滑块检测循环: total_minutes=%s, check_interval_seconds=%s",
                total_minutes, check_interval_seconds)
    logger.info("检测开始时间: %s", start_time.isoformat())

    while True:
        now = datetime.now()
        detected = False
        try:
            detected = bool(detect_fn())
        except Exception as e:
            # 检测函数异常也记录并继续（可根据需要改为中断）
            logger.exception("检测函数执行异常，将视为检测到滑块以继续等待: %s", e)
            detected = True

        checks.append({"ts": now.isoformat(), "detected": detected})
        logger.info("检测结果: %s (time: %s)", ("滑块存在" if detected else "未检测到滑块"), now.isoformat())

        # 如果未检测到滑块，立即返回继续爬取
        if not detected:
            logger.info("滑块已消失，继续爬取。检测耗时: %s", (now - start_time))
            return {
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "elapsed_seconds": int((datetime.now() - start_time).total_seconds()),
                "final_state": "continue",
                "checks": checks,
            }

        # 如果当前时间超过截止时间，则超时返回等待超时
        if now >= end_deadline:
            logger.warning("等待超时 (%s 分钟) 后滑块仍存在，停止等待并标记为 timeout", total_minutes)
            return {
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "elapsed_seconds": int((datetime.now() - start_time).total_seconds()),
                "final_state": "wait_timeout",
                "checks": checks,
            }

        # 继续等待并睡眠
        remaining = (end_deadline - now).total_seconds()
        sleep_for = min(check_interval_seconds, int(remaining))
        logger.info("检测到滑块，继续等待 %.0f 秒（离截止时间还有 %.0f 秒）", sleep_for, remaining)
        time.sleep(sleep_for)


# ====== Selenium 示例检测函数 (注释) ======
# 以下为示例，实际使用时请解除注释并根据项目的 Selenium driver 调整。
#
# from selenium.common.exceptions import NoSuchElementException
# def detect_slider_selenium(driver, slider_selector: str = ".slider-selector") -> bool:
#     """
#     使用 Selenium 检测滑块元素是否存在。
#     返回 True 表示滑块存在（页面被拦截），False 表示未检测到滑块。
#     """
#     try:
#         el = driver.find_element("css selector", slider_selector)
#         # 可扩展判断条件：例如判断可见性、阻塞遮罩层、特定属性等
#         return el is not None
#     except NoSuchElementException:
#         return False
#
# 用法示例:
# from selenium import webdriver
# driver = webdriver.Chrome(...)
# detect_fn = lambda: detect_slider_selenium(driver, "#slider")
# result = wait_and_detect(detect_fn, total_minutes=20, check_interval_seconds=30)
# ============================================


def example_simple_detect() -> None:
    """
    本地示例：使用一个简单的模拟检测函数（随机或固定返回），
    便于在没有浏览器环境下验证等待逻辑。
    """
    import random

    def fake_detect():
        # 模拟滑块存在 70% 的概率
        return random.random() < 0.7

    res = wait_and_detect(fake_detect, total_minutes=1, check_interval_seconds=5)
    logger.info("示例完成，结果：%s", res)


if __name__ == "__main__":
    # 仅做快速本地验证使用（将 total_minutes 调小）
    example_simple_detect()
