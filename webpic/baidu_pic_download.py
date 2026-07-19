# -*- coding: utf-8 -*-
# @Time : 2024/7/23 17:11
# @Author : guoxun
# @File : baidu_pic_download
import os
import time
from argparse import ArgumentParser
from time import sleep

from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pic_utils import driver_utils, log_utils, download_utlis, page_utils

# ═══════════════════════════════════════════════════════════════
# 百度图片搜索 — 选择器定义（集中管理，方便后续更新）
# ═══════════════════════════════════════════════════════════════

BAIDU_SEARCH_URL = "https://image.baidu.com/search/index?tn=baiduimage&word={query}"

# 搜索结果页中的图片选择器（按优先级排列）
BAIDU_THUMB_SELECTORS = [
    (By.CSS_SELECTOR, "img.main_img"),
    (By.CSS_SELECTOR, ".imgbox img"),
    (By.CSS_SELECTOR, ".imgitem img"),
    (By.CSS_SELECTOR, "[data-imgurl]"),
    (By.CSS_SELECTOR, "[data-thumburl]"),
    (By.CSS_SELECTOR, "img[src*='baidu']"),
]

# 可点击进入大图的容器
BAIDU_CLICK_SELECTORS = [
    (By.CSS_SELECTOR, ".imgbox"),
    (By.CSS_SELECTOR, ".imgitem"),
    (By.CSS_SELECTOR, "li[data-objurl]"),
    (By.CSS_SELECTOR, "[data-objurl]"),
]

# 高清大图界面：当前大图的 img 选择器
BAIDU_FULL_IMG_SELECTORS = [
    (By.CSS_SELECTOR, "img.currentImg"),
    (By.CSS_SELECTOR, "#srcPic img"),
    (By.CSS_SELECTOR, "div#srcPic img"),
    (By.CSS_SELECTOR, "#bigImg img"),
    (By.CSS_SELECTOR, "img#bigImg"),
    (By.CSS_SELECTOR, ".viewer-pic img"),
]

# 高清大图界面：下一张按钮
BAIDU_NEXT_SELECTORS = [
    (By.CSS_SELECTOR, "span.img-next"),
    (By.CSS_SELECTOR, ".img-next"),
    (By.CSS_SELECTOR, "[class*='next']"),
    (By.CSS_SELECTOR, ".viewer-next"),
    (By.XPATH, "//span[contains(@class,'next')]"),
]


def run(query, driver: webdriver.Chrome | None, save_path="..", sleep_time=3,
        disable_gui=True, disable_logs=True, use_implicitly_wait=True,
        min_count=1000, high_quality=False, is_async=True, num_threads=5,
        shutdown_flag=None):
    """
    百度图片下载入口。

    :param query:         搜索关键词
    :param driver:        可复用的 WebDriver（为 None 时会自动创建）
    :param save_path:     图片保存根目录
    :param sleep_time:    操作间的等待时间（秒）
    :param disable_gui:   是否隐藏浏览器界面
    :param disable_logs:  是否隐藏浏览器日志
    :param use_implicitly_wait: 是否使用隐式等待
    :param min_count:     目标下载数量（0 = 不限制）
    :param high_quality:  是否使用高清模式
    :param is_async:      是否异步下载
    :param num_threads:   下载线程数
    :param shutdown_flag: threading.Event，用于接收外部退出信号
    :return:              已下载的图片数量
    """
    # ── 初始化保存目录 ──────────────────────────────────────
    baidu_save_path = os.path.join(save_path, "baidu")
    os.makedirs(baidu_save_path, exist_ok=True)

    downloader = download_utlis.DownloadUtils(
        save_path=baidu_save_path, num_threads=num_threads
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
        # 直接导航到搜索结果页（无需操作搜索框）
        search_url = BAIDU_SEARCH_URL.format(query=query)
        log_utils.log_info(f"正在访问: {search_url}")
        driver.get(search_url)
        sleep(1)

        if high_quality:
            _download_high_quality(
                driver, downloader, min_count, is_async, shutdown_flag
            )
        else:
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
        "Engine": "Baidu",
        "Downloaded": count,
        "Successful": downloader.success_count,
        "Failed": downloader.failed_count,
        "Save Path": baidu_save_path,
    })
    return count


# ─── 标准模式 ────────────────────────────────────────────────

def _download_standard(driver, downloader, min_count, sleep_time,
                       is_async, shutdown_flag):
    """滚动页面并下载缩略图"""
    log_utils.log_info("百度图片 → 标准模式下载")

    seen_urls = set()
    no_new_rounds = 0

    while True:
        if shutdown_flag and shutdown_flag.is_set():
            log_utils.log_info("收到退出信号，停止下载")
            break
        if min_count > 0 and downloader.check_images_count(min_count):
            break

        # 滚动并等待新内容加载
        page_utils.scroll_page(driver, 800, step=300)
        sleep(sleep_time * 0.5)

        # 通过 JS 提取图片 URL（最稳健的方式）
        js_urls = page_utils.extract_image_urls(
            driver, min_width=100, min_height=100,
            exclude_patterns=['favicon', 'logo', 'avatar', 'icon']
        )
        # 也尝试 data-imgurl / data-thumburl 属性
        data_urls = _extract_data_urls(driver)

        all_urls = set(js_urls) | set(data_urls)
        new_urls = all_urls - seen_urls

        if not new_urls:
            no_new_rounds += 1
            # 尝试用 Selenium 选择器补充提取
            selenium_urls = _extract_by_selectors(driver)
            new_urls = set(selenium_urls) - seen_urls
            if not new_urls:
                if no_new_rounds >= 10:
                    log_utils.log_info("连续多次无新图片，可能已到达页面底部")
                    break
                continue
        else:
            no_new_rounds = 0

        log_utils.log_info(
            f"发现 {len(new_urls)} 张新图片 (累计已发现 {len(seen_urls)} 张)"
        )

        for url in new_urls:
            if shutdown_flag and shutdown_flag.is_set():
                break
            if min_count > 0 and downloader.check_images_count(min_count):
                break
            downloader.link_download_tools(url, show_log=False, is_async=is_async)

        seen_urls.update(new_urls)

        # 滚动到底部加载更多
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(sleep_time * 0.5)

    # 等待下载任务收尾
    sleep(1)
    log_utils.log_info(f"标准模式下载完成，共发现 {len(seen_urls)} 个唯一 URL")


# ─── 高清模式 ────────────────────────────────────────────────

def _download_high_quality(driver, downloader, min_count, is_async, shutdown_flag):
    """点击缩略图 → 打开大图预览 → 逐张下载高清原图"""
    log_utils.log_info("百度图片 → 高清模式下载")

    if min_count <= 0:
        min_count = 500  # 高清模式默认上限

    # 1. 先滚动几次加载足够的缩略图
    for _ in range(5):
        if shutdown_flag and shutdown_flag.is_set():
            return
        page_utils.scroll_page(driver, 600, step=300)
        sleep(0.5)

    # 2. 找到并点击第一张图片的容器，打开大图预览
    clickable = None
    for by, selector in BAIDU_CLICK_SELECTORS:
        try:
            elements = driver.find_elements(by, selector)
            if elements:
                # 找到第一个可见的
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        clickable = el
                        break
                if clickable:
                    break
        except Exception:
            continue

    if clickable is None:
        log_utils.log_error("无法找到可点击的缩略图，回退到标准模式")
        _download_standard(driver, downloader, min_count, 3, is_async, shutdown_flag)
        return

    try:
        clickable.click()
    except Exception:
        # 可能被其他元素遮挡，用 JS 点击
        driver.execute_script("arguments[0].click();", clickable)

    sleep(2)

    # 切换窗口（如果有新窗口）
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[-1])
        sleep(1)

    # 3. 逐张下载
    fail_streak = 0
    downloaded = 0

    pbar = tqdm(total=min_count, desc="百度高清下载")
    while downloaded < min_count:
        if shutdown_flag and shutdown_flag.is_set():
            break

        # 提取当前大图 URL
        high_quality_url = None
        for by, selector in BAIDU_FULL_IMG_SELECTORS:
            try:
                el = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((by, selector))
                )
                high_quality_url = el.get_attribute("src")
                if high_quality_url and high_quality_url.startswith("http"):
                    break
            except Exception:
                continue

        if high_quality_url:
            downloader.link_download_tools(
                high_quality_url, show_log=False, is_async=is_async
            )
            downloaded += 1
            fail_streak = 0
            pbar.update(1)
        else:
            fail_streak += 1
            if fail_streak >= 5:
                log_utils.log_error("连续 5 次获取大图失败，退出高清模式")
                break

        # 点击下一张
        clicked = False
        for by, selector in BAIDU_NEXT_SELECTORS:
            try:
                el = driver.find_element(by, selector)
                if el.is_displayed():
                    el.click()
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            # 尝试按右箭头键
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
                clicked = True
            except Exception:
                pass

        if not clicked:
            fail_streak += 1
            if fail_streak >= 5:
                log_utils.log_error("无法导航到下一张，退出高清模式")
                break

        sleep(0.4)  # 给图片加载留一点时间

    pbar.close()
    log_utils.log_info(f"高清模式下载完成，尝试下载 {downloaded} 张")


# ─── 辅助函数 ────────────────────────────────────────────────

def _extract_data_urls(driver) -> list:
    """从 data-imgurl / data-thumburl / data-objurl 属性提取 URL"""
    urls = []
    for attr in ["data-imgurl", "data-thumburl", "data-objurl"]:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, f"[{attr}]")
            for el in elements:
                url = el.get_attribute(attr)
                if url and url.startswith("http"):
                    urls.append(url)
        except Exception:
            continue
    return urls


def _extract_by_selectors(driver) -> list:
    """通过 CSS 选择器提取图片 URL（JS 提取失败的降级方案）"""
    urls = []
    seen = set()
    for by, selector in BAIDU_THUMB_SELECTORS:
        try:
            elements = driver.find_elements(by, selector)
            for el in elements:
                # 尝试多种属性
                for attr in ["src", "data-imgurl", "data-thumburl"]:
                    url = el.get_attribute(attr)
                    if url and url.startswith("http") and url not in seen:
                        urls.append(url)
                        seen.add(url)
                        break
        except Exception:
            continue
    return urls


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
    parser.add_argument('--high_quality', action='store_true', default=False)
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
        high_quality=args.high_quality,
        is_async=args.is_async,
        num_threads=args.num_threads,
    )
