# -*- coding: utf-8 -*-
# @Time : 2024/7/24 8:21
# @Author : guoxun
# @File : page_utils
import random
import time
import threading

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scroll_page(driver: webdriver.Chrome, pixels: int, step: int = 300):
    """
    渐进式向下滚动指定像素。
    动态页面需要逐步滚动才能触发懒加载，一次性 scrollTo 到底容易失效。

    :param driver: WebDriver 实例
    :param pixels: 需要滚动的总像素
    :param step: 每步滚动的像素
    """
    current = 0
    while current < pixels:
        current += step
        driver.execute_script(f"window.scrollBy(0, {step});")
        time.sleep(0.15)  # 给 DOM 渲染留一点时间


def scroll_to_bottom(driver: webdriver.Chrome, max_scrolls: int = 50, pause: float = 0.5):
    """
    连续滚动到页面底部，直到没有新内容加载。
    对比每次滚动前后的 pageHeight，若不变则认为已到底。

    :param driver: WebDriver 实例
    :param max_scrolls: 最大滚动次数（防止无限循环）
    :param pause: 每次滚动后的等待间隔（秒）
    :return: 实际滚动次数
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0

    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

        # 尝试点击"加载更多"按钮（如果有的话）
        _try_click_load_more(driver)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            scroll_count += 1
            if scroll_count >= 3:  # 连续 3 次高度不变才退出
                break
        else:
            scroll_count = 0
        last_height = new_height

    return scroll_count


def _try_click_load_more(driver: webdriver.Chrome):
    """尝试点击页面上的"加载更多"按钮"""
    load_more_selectors = [
        "//span[contains(text(), '加载更多')]",
        "//a[contains(text(), '加载更多')]",
        "//button[contains(text(), '加载更多')]",
        "//div[contains(text(), '加载更多')]",
        "//span[contains(text(), '更多')]",
    ]
    for selector in load_more_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    el.click()
                    time.sleep(0.3)
                    return
        except Exception:
            continue


def wait_for_images(driver: webdriver.Chrome, timeout: int = 10, min_count: int = 5):
    """
    等待页面上出现足够数量的 <img> 标签。
    返回找到的 img 元素列表。

    :param driver: WebDriver 实例
    :param timeout: 最长等待时间（秒）
    :param min_count: 至少需要多少个 img 标签才认为加载完成
    :return: img 元素列表
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.TAG_NAME, "img")) >= min_count
        )
    except Exception:
        pass  # 超时不抛异常，有多少返回多少
    return driver.find_elements(By.TAG_NAME, "img")


def extract_image_urls(
    driver: webdriver.Chrome,
    min_width: int = 80,
    min_height: int = 80,
    exclude_patterns: list = None
) -> list:
    """
    通过 JavaScript 从 DOM 中提取所有符合条件的图片 URL。

    相比 Selenium find_elements，JS 方式：
    1. 可以直接获取 naturalWidth/naturalHeight 做尺寸过滤
    2. 可以读取 computed style
    3. 不依赖特定 CSS 类名

    :param driver: WebDriver 实例
    :param min_width: 最小宽度（像素），小于此值的图片被过滤
    :param min_height: 最小高度（像素），小于此值的图片被过滤
    :param exclude_patterns: 需要排除的 URL 模式列表
    :return: 去重的图片 URL 列表
    """
    if exclude_patterns is None:
        exclude_patterns = ['favicon', 'logo', 'icon', 'avatar', 'data:image/svg']

    js_script = """
    const minW = arguments[0];
    const minH = arguments[1];
    const excludePatterns = arguments[2];

    const urls = new Set();
    const imgs = document.querySelectorAll('img');
    for (const img of imgs) {
        // 优先使用 src，没有则尝试 data-src
        let src = img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src');
        if (!src || src.startsWith('data:image/svg')) continue;

        // 排除 base64 小图标
        if (src.startsWith('data:') && src.length < 500) continue;

        // 排除特定模式
        let skip = false;
        for (const p of excludePatterns) {
            if (src.toLowerCase().includes(p.toLowerCase())) {
                skip = true;
                break;
            }
        }
        if (skip) continue;

        // 尺寸过滤：用 naturalWidth/naturalHeight，未加载的用 width/height 属性
        const w = img.naturalWidth || img.width || 0;
        const h = img.naturalHeight || img.height || 0;
        if (minW > 0 && w > 0 && w < minW) continue;
        if (minH > 0 && h > 0 && h < minH) continue;

        urls.add(src);
    }

    // 也检查 data-thumburl、data-imgurl、data-objurl 等常见数据属性
    const elements = document.querySelectorAll('[data-imgurl], [data-thumburl], [data-objurl]');
    for (const el of elements) {
        const url = el.getAttribute('data-imgurl')
                 || el.getAttribute('data-thumburl')
                 || el.getAttribute('data-objurl');
        if (url) urls.add(url);
    }

    return Array.from(urls);
    """
    try:
        urls = driver.execute_script(js_script, min_width, min_height, exclude_patterns)
        return urls if urls else []
    except Exception:
        return []


def safe_find_element(driver: webdriver.Chrome, selectors: list, timeout: int = 5):
    """
    依次尝试多个选择器，返回第一个找到的元素。
    支持 CSS selector 和 XPath。

    :param driver: WebDriver 实例
    :param selectors: 选择器列表，每个元素为 (By.XXX, "selector_string") 元组
    :param timeout: 每个选择器的最长等待时间
    :return: WebElement 或 None
    """
    for by, selector in selectors:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except Exception:
            continue
    return None


def safe_find_elements(driver: webdriver.Chrome, selectors: list, timeout: int = 5):
    """
    依次尝试多个选择器，返回第一个找到的非空元素列表。

    :param driver: WebDriver 实例
    :param selectors: 选择器列表
    :param timeout: 最长等待时间
    :return: 元素列表（可能为空）
    """
    for by, selector in selectors:
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            elements = driver.find_elements(by, selector)
            if elements:
                return elements
        except Exception:
            continue
    return []


def scroll_and_collect_urls(
    driver: webdriver.Chrome,
    target_count: int,
    max_scrolls: int = 30,
    min_size: int = 80
) -> set:
    """
    滚动页面并持续收集图片 URL，直到达到目标数量或无法加载更多。

    :param driver: WebDriver 实例
    :param target_count: 目标 URL 数量
    :param max_scrolls: 最大滚动次数
    :param min_size: 最小图片尺寸
    :return: 收集到的 URL 集合
    """
    all_urls = set()
    no_new_count = 0

    for _ in range(max_scrolls):
        scroll_page(driver, 600, step=200)
        time.sleep(0.5)

        new_urls = extract_image_urls(driver, min_width=min_size, min_height=min_size)
        prev_count = len(all_urls)
        all_urls.update(new_urls)

        if len(all_urls) == prev_count:
            no_new_count += 1
        else:
            no_new_count = 0

        # 连续 3 次无新 URL 且未达到目标，继续
        if no_new_count >= 5:
            break

        if target_count > 0 and len(all_urls) >= target_count * 2:
            break  # 收集到目标的 2 倍 URL 后停止滚动（留足备选）

    return all_urls
