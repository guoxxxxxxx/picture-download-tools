# -*- coding: utf-8 -*-
# @Time : 2024/7/23 17:11
# @Author : guoxun
# @File : google_pic_download
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
# Google 图片搜索 — 选择器定义（集中管理，方便后续更新）
# ═══════════════════════════════════════════════════════════════

GOOGLE_SEARCH_URL = "https://www.google.com/search?tbm=isch&q={query}"

# 搜索结果中的缩略图选择器
GOOGLE_THUMB_SELECTORS = [
    (By.CSS_SELECTOR, "img.rg_i"),
    (By.CSS_SELECTOR, "img.Q4LuWd"),
    (By.CSS_SELECTOR, "img.YQ4gaf"),
    (By.CSS_SELECTOR, "img[data-src]"),
    (By.CSS_SELECTOR, "g-img img"),
    (By.CSS_SELECTOR, "[jsname] img"),
]

# 点击后打开侧边面板的缩略图容器
GOOGLE_CLICK_SELECTORS = [
    (By.CSS_SELECTOR, "div.F0uyec"),
    (By.CSS_SELECTOR, "div[jsname][jsaction]"),
    (By.CSS_SELECTOR, "a[jsname]"),
    (By.CSS_SELECTOR, "div[data-ri]"),
    (By.CSS_SELECTOR, "[jsaction*='click'] div"),
]

# 侧边面板中的大图选择器
GOOGLE_FULL_IMG_SELECTORS = [
    (By.CSS_SELECTOR, "img.iPVvYb"),
    (By.CSS_SELECTOR, "img.sFlh5c"),
    (By.CSS_SELECTOR, "img.n3VNCb"),
    (By.CSS_SELECTOR, "img.r48jcc"),
    (By.CSS_SELECTOR, "[jsname] img[src*='http']"),
    (By.CSS_SELECTOR, "c-wiz img[src*='http']"),
]

# 下一张按钮选择器
GOOGLE_NEXT_SELECTORS = [
    (By.CSS_SELECTOR, "button[aria-label='Next']"),
    (By.CSS_SELECTOR, "[aria-label='下一张']"),
    (By.CSS_SELECTOR, "[jsaction*='next']"),
    (By.CSS_SELECTOR, "div[jsname] button:last-child"),
    (By.CSS_SELECTOR, "[data-tooltip='Next']"),
]


def run(query, driver: webdriver.Chrome | None, save_path="..", sleep_time=3,
        disable_gui=True, disable_logs=True, use_implicitly_wait=True,
        min_count=1000, high_quality=False, is_async=True, num_threads=5,
        shutdown_flag=None):
    """
    Google 图片下载入口。

    :param query:         搜索关键词（建议使用英文）
    :param driver:        可复用的 WebDriver
    :param save_path:     图片保存根目录
    :param sleep_time:    操作间的等待时间（秒）
    :param disable_gui:   是否隐藏浏览器界面
    :param disable_logs:  是否隐藏浏览器日志
    :param use_implicitly_wait: 是否使用隐式等待
    :param min_count:     目标下载数量（0 = 不限制）
    :param high_quality:  是否使用高清模式
    :param is_async:      是否异步下载
    :param num_threads:   下载线程数
    :param shutdown_flag: threading.Event，外部退出信号
    :return:              已下载的图片数量
    """
    # ── 初始化保存目录 ──────────────────────────────────────
    google_save_path = os.path.join(save_path, "google")
    os.makedirs(google_save_path, exist_ok=True)

    downloader = download_utlis.DownloadUtils(
        save_path=google_save_path, num_threads=num_threads
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
        search_url = GOOGLE_SEARCH_URL.format(query=query)
        log_utils.log_info(f"正在访问: {search_url}")
        driver.get(search_url)
        sleep(2)

        # 检查是否被 Google 封锁
        if _is_google_blocked(driver):
            log_utils.log_error(
                "⚠ Google 检测到自动化访问！请尝试：\n"
                "  1. 使用 --disable_gui 参数关闭无头模式，手动完成验证\n"
                "  2. 更换网络环境\n"
                "  3. 降低下载频率"
            )
            if own_driver:
                downloader.shutdown(wait=True)
            return 0

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
        "Engine": "Google",
        "Downloaded": count,
        "Successful": downloader.success_count,
        "Failed": downloader.failed_count,
        "Save Path": google_save_path,
    })
    return count


# ─── 标准模式 ────────────────────────────────────────────────

def _download_standard(driver, downloader, min_count, sleep_time,
                       is_async, shutdown_flag):
    """滚动页面下载缩略图 + base64 图片"""
    log_utils.log_info("Google 图片 → 标准模式下载")

    seen_urls = set()
    no_new_rounds = 0

    while True:
        if shutdown_flag and shutdown_flag.is_set():
            log_utils.log_info("收到退出信号，停止下载")
            break
        if min_count > 0 and downloader.check_images_count(min_count):
            break

        # 渐进式滚动
        page_utils.scroll_page(driver, 600, step=200)
        sleep(sleep_time * 0.6)

        # 1) JS 提取
        js_urls = page_utils.extract_image_urls(
            driver, min_width=80, min_height=80,
            exclude_patterns=['favicon', 'logo', 'avatar', 'icon',
                              'googlelogo', 'ggpht']
        )
        # 2) Selenium 选择器提取
        sel_urls = _extract_google_thumb_urls(driver)

        all_urls = set(js_urls) | set(sel_urls)
        new_urls = all_urls - seen_urls

        if not new_urls:
            no_new_rounds += 1
            if no_new_rounds >= 10:
                log_utils.log_info("连续多次无新图片，停止搜索")
                break
            continue
        else:
            no_new_rounds = 0

        log_utils.log_info(
            f"发现 {len(new_urls)} 张新图片 (累计 {len(seen_urls)})"
        )

        for url in new_urls:
            if shutdown_flag and shutdown_flag.is_set():
                break
            if min_count > 0 and downloader.check_images_count(min_count):
                break

            if url.startswith("data:image/"):
                # base64 图片
                downloader.save_base64(url)
            elif url.startswith("http"):
                downloader.link_download_tools(url, show_log=False, is_async=is_async)

        seen_urls.update(new_urls)

        # 页面整体滚动以加载更多
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(sleep_time * 0.4)

    sleep(1)
    log_utils.log_info(f"标准模式下载完成，共发现 {len(seen_urls)} 个唯一 URL")


# ─── 高清模式 ────────────────────────────────────────────────

def _download_high_quality(driver, downloader, min_count, is_async, shutdown_flag):
    """点击缩略图打开侧边面板，逐张下载高清原图"""
    log_utils.log_info("Google 图片 → 高清模式下载")

    if min_count <= 0:
        min_count = 300

    # 1. 先滚动几次加载缩略图
    for _ in range(4):
        if shutdown_flag and shutdown_flag.is_set():
            return
        page_utils.scroll_page(driver, 500, step=200)
        sleep(0.5)

    # 2. 点击第一张缩略图打开侧边面板
    clicked = False
    for by, selector in GOOGLE_CLICK_SELECTORS:
        try:
            elements = driver.find_elements(by, selector)
            for el in elements:
                if el.is_displayed():
                    driver.execute_script("arguments[0].click();", el)
                    clicked = True
                    break
            if clicked:
                break
        except Exception:
            continue

    if not clicked:
        log_utils.log_error("无法打开 Google 图片详情面板，回退到标准模式")
        _download_standard(driver, downloader, min_count, 3, is_async, shutdown_flag)
        return

    sleep(2)

    # 3. 逐张下载
    fail_streak = 0
    downloaded = 0
    pbar = tqdm(total=min_count, desc="Google 高清下载")

    while downloaded < min_count:
        if shutdown_flag and shutdown_flag.is_set():
            break

        # 提取侧边面板中的大图 URL
        url = None
        for by, selector in GOOGLE_FULL_IMG_SELECTORS:
            try:
                el = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                # 优先 src 属性，部分 Google 图片使用 data-src
                url = el.get_attribute("src") or el.get_attribute("data-src")
                if url and url.startswith("http") and len(url) > 50:
                    # 去掉 URL 参数（Google 图片经常有 ?token=xxx）
                    base_url = url.split("?")[0]
                    if base_url.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                        url = url.split("?")[0] if "?" in url else url
                    break
            except Exception:
                continue

        if url:
            downloader.link_download_tools(url, show_log=False, is_async=is_async)
            downloaded += 1
            fail_streak = 0
            pbar.update(1)
        else:
            fail_streak += 1
            if fail_streak >= 5:
                log_utils.log_error("连续 5 次获取大图失败，退出高清模式")
                break

        # 点击下一张
        next_clicked = False
        for by, selector in GOOGLE_NEXT_SELECTORS:
            try:
                el = driver.find_element(by, selector)
                if el.is_displayed():
                    el.click()
                    next_clicked = True
                    break
            except Exception:
                continue

        if not next_clicked:
            # 尝试键盘右箭头
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
                next_clicked = True
            except Exception:
                pass

        if not next_clicked:
            fail_streak += 1
            if fail_streak >= 5:
                log_utils.log_error("无法导航到下一张，退出高清模式")
                break

        sleep(0.6)

    pbar.close()
    log_utils.log_info(f"高清模式下载完成，尝试下载 {downloaded} 张")


# ─── 辅助函数 ────────────────────────────────────────────────

def _extract_google_thumb_urls(driver) -> list:
    """用 CSS 选择器提取 Google 缩略图 URL"""
    urls = []
    seen = set()

    for by, selector in GOOGLE_THUMB_SELECTORS:
        try:
            elements = driver.find_elements(by, selector)
            for el in elements:
                url = (el.get_attribute("src")
                       or el.get_attribute("data-src")
                       or el.get_attribute("data-iurl"))
                if url and url not in seen:
                    if url.startswith("http") or url.startswith("data:image/"):
                        urls.append(url)
                        seen.add(url)
        except Exception:
            continue
    return urls


def _is_google_blocked(driver) -> bool:
    """检测是否被 Google 反爬机制拦截"""
    page_source = ""
    try:
        page_source = driver.page_source.lower()
    except Exception:
        return True

    blocked_keywords = [
        "unusual traffic",
        "captcha",
        "sorry/index",
        "not a robot",
        "automated queries",
        "suspicious",
    ]
    for keyword in blocked_keywords:
        if keyword in page_source:
            return True

    # 也检查 title
    try:
        title = driver.title.lower()
        if "sorry" in title or "captcha" in title:
            return True
    except Exception:
        pass

    return False


# ─── 独立运行入口 ────────────────────────────────────────────

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--query', type=str, default='cat')
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
