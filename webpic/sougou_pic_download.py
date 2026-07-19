# -*- coding: utf-8 -*-
# @Time : 2024/7/23 17:11
# @Author : guoxun
# @File : sougou_pic_download
import os
import time
from argparse import ArgumentParser
from time import sleep

from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pic_utils import driver_utils, log_utils, download_utlis, page_utils

# ═══════════════════════════════════════════════════════════════
# 搜狗图片搜索 — 选择器定义（集中管理，方便后续更新）
# ═══════════════════════════════════════════════════════════════

SOUGOU_SEARCH_URL = "https://pic.sogou.com/pics?query={query}"

# 搜索结果中的图片选择器
SOUGOU_IMG_SELECTORS = [
    (By.CSS_SELECTOR, "div.img-layout img"),
    (By.CSS_SELECTOR, ".img-layout img"),
    (By.CSS_SELECTOR, "[drag-img]"),
    (By.CSS_SELECTOR, "img[src*='img']"),
    (By.CSS_SELECTOR, "img[src*='sogoucdn']"),
    (By.CSS_SELECTOR, ".pic-item img"),
    (By.CSS_SELECTOR, ".img-item img"),
    (By.CSS_SELECTOR, "a img"),
]

# "加载更多"按钮选择器
LOAD_MORE_SELECTORS = [
    (By.XPATH, "//span[contains(text(),'加载更多')]"),
    (By.XPATH, "//a[contains(text(),'加载更多')]"),
    (By.XPATH, "//div[contains(text(),'加载更多')]"),
    (By.CSS_SELECTOR, ".load-more"),
    (By.CSS_SELECTOR, ".loadmore"),
    (By.CSS_SELECTOR, "[class*='load-more']"),
]


def run(query, driver: webdriver.Chrome | None, save_path="..", sleep_time=3,
        disable_gui=True, disable_logs=True, use_implicitly_wait=True,
        min_count=1000, is_async=True, num_threads=5, shutdown_flag=None):
    """
    搜狗图片下载入口。

    :param query:         搜索关键词
    :param driver:        可复用的 WebDriver
    :param save_path:     图片保存根目录
    :param sleep_time:    操作间的等待时间（秒）
    :param disable_gui:   是否隐藏浏览器界面
    :param disable_logs:  是否隐藏浏览器日志
    :param use_implicitly_wait: 是否使用隐式等待
    :param min_count:     目标下载数量（0 = 不限制）
    :param is_async:      是否异步下载
    :param num_threads:   下载线程数
    :param shutdown_flag: threading.Event，外部退出信号
    :return:              已下载的图片数量
    """
    # ── 初始化保存目录 ──────────────────────────────────────
    sougou_save_path = os.path.join(save_path, "sougou")
    os.makedirs(sougou_save_path, exist_ok=True)

    downloader = download_utlis.DownloadUtils(
        save_path=sougou_save_path, num_threads=num_threads
    )

    # ── 初始化 WebDriver ────────────────────────────────────
    own_driver = driver is None
    if own_driver:
        driver = driver_utils.create_driver(
            disable_gui=disable_gui, disable_logs=disable_logs
        )
    if use_implicitly_wait:
        driver.implicitly_wait(sleep_time)

    try:
        # 直接导航到搜索结果页
        search_url = SOUGOU_SEARCH_URL.format(query=query)
        log_utils.log_info(f"正在访问: {search_url}")
        driver.get(search_url)
        sleep(2)

        # 搜狗图片搜索无高清模式，统一走标准流程
        _download_standard(
            driver, downloader, min_count, sleep_time,
            is_async, shutdown_flag
        )
    finally:
        if own_driver:
            try:
                driver.quit()
            except Exception:
                pass
        downloader.shutdown(wait=True)

    count = downloader.get_downloaded_count()
    log_utils.log_summary({
        "Engine": "Sougou",
        "Downloaded": count,
        "Successful": downloader.success_count,
        "Failed": downloader.failed_count,
        "Save Path": sougou_save_path,
    })
    return count


# ─── 标准模式 ────────────────────────────────────────────────

def _download_standard(driver, downloader, min_count, sleep_time,
                       is_async, shutdown_flag):
    """滚动页面 + 点击"加载更多"，提取并下载图片"""
    log_utils.log_info("搜狗图片 → 标准模式下载")

    seen_urls = set()
    no_new_rounds = 0
    load_more_fail_count = 0

    while True:
        if shutdown_flag and shutdown_flag.is_set():
            log_utils.log_info("收到退出信号，停止下载")
            break
        if min_count > 0 and downloader.check_images_count(min_count):
            break

        # 1) 滚动页面加载当前批次
        page_utils.scroll_page(driver, 600, step=300)
        sleep(sleep_time * 0.6)

        # 2) 点击"加载更多"按钮（搜狗用按钮翻页，不用无限滚动）
        if not _click_load_more(driver):
            load_more_fail_count += 1
        else:
            load_more_fail_count = 0
            sleep(sleep_time * 0.8)

        # 3) JS 提取
        js_urls = page_utils.extract_image_urls(
            driver, min_width=80, min_height=80,
            exclude_patterns=['favicon', 'logo', 'avatar', 'icon', 'sogoucdn/pic/pc']
        )

        # 4) drag-img 属性提取（搜狗特有）
        drag_urls = _extract_drag_img_urls(driver)

        # 5) 选择器提取
        sel_urls = _extract_sougou_urls(driver)

        all_urls = set(js_urls) | set(drag_urls) | set(sel_urls)
        new_urls = all_urls - seen_urls

        if not new_urls:
            no_new_rounds += 1
            if no_new_rounds >= 8 and load_more_fail_count >= 3:
                log_utils.log_info("无新图片且无法加载更多，停止搜索")
                break
            # 再滚动一次试试
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(sleep_time)
            continue
        else:
            no_new_rounds = 0

        log_utils.log_info(
            f"发现 {len(new_urls)} 张新图片 (累计 {len(seen_urls)})"
        )

        for url in tqdm(new_urls, desc="搜狗下载"):
            if shutdown_flag and shutdown_flag.is_set():
                break
            if min_count > 0 and downloader.check_images_count(min_count):
                break
            downloader.link_download_tools(url, show_log=False, is_async=is_async)

        seen_urls.update(new_urls)

    sleep(1)
    log_utils.log_info(f"标准模式下载完成，共发现 {len(seen_urls)} 个唯一 URL")


# ─── 辅助函数 ────────────────────────────────────────────────

def _extract_drag_img_urls(driver) -> list:
    """从搜狗特有的 drag-img 属性提取 URL"""
    urls = []
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "[drag-img]")
        for el in elements:
            url = el.get_attribute("drag-img")
            if url and url.startswith("http"):
                urls.append(url)
    except Exception:
        pass
    return urls


def _extract_sougou_urls(driver) -> list:
    """通过 CSS 选择器提取搜狗图片 URL"""
    urls = []
    seen = set()

    for by, selector in SOUGOU_IMG_SELECTORS:
        try:
            elements = driver.find_elements(by, selector)
            for el in elements:
                # 搜狗图片的多种 URL 来源
                for attr in ["src", "drag-img", "data-src", "data-original"]:
                    url = el.get_attribute(attr)
                    if url and url.startswith("http") and url not in seen:
                        urls.append(url)
                        seen.add(url)
                        break
        except Exception:
            continue
    return urls


def _click_load_more(driver) -> bool:
    """点击搜狗页面上的'加载更多'按钮"""
    for by, selector in LOAD_MORE_SELECTORS:
        try:
            elements = driver.find_elements(by, selector)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script("arguments[0].click();", el)
                    return True
        except Exception:
            continue
    return False


# ─── 独立运行入口 ────────────────────────────────────────────

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--query', type=str, default='风景')
    parser.add_argument('--disable_gui', action='store_true', default=False)
    parser.add_argument('--disable_logs', action='store_true', default=False)
    parser.add_argument('--save_path', type=str, default='../download/tmp')
    parser.add_argument('--sleep_time', type=float, default=3)
    parser.add_argument('--use_implicitly_wait', action='store_true', default=True)
    parser.add_argument('--min_count', type=int, default=50)
    parser.add_argument('--is_async', action='store_true', default=True)
    parser.add_argument('--num_threads', type=int, default=5)
    args = parser.parse_args()

    run(
        query=args.query, driver=None,
        disable_gui=args.disable_gui,
        disable_logs=args.disable_logs,
        save_path=args.save_path,
        sleep_time=args.sleep_time,
        use_implicitly_wait=args.use_implicitly_wait,
        min_count=args.min_count,
        is_async=args.is_async,
        num_threads=args.num_threads,
    )
