# -*- coding: utf-8 -*-
# @Time : 2024/7/23 17:28
# @Author : guoxun
# @File : driver_utils
import random

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def get_driver_options(disable_gui=True, disable_logs=True):
    """构建 Chrome 浏览器选项"""
    chrome_options = Options()

    if disable_gui:
        chrome_options.add_argument("--headless=new")  # 新版无头模式
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

    # ---- 反检测措施 ----
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-popup-blocking")

    # 移除自动化标记
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # 随机 User-Agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

    # 禁用 "Chrome is being controlled" 信息栏
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2,  # 禁用通知
    }
    chrome_options.add_experimental_option("prefs", prefs)

    if disable_logs:
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")

    return chrome_options


def create_driver(disable_gui=True, disable_logs=True):
    """创建并返回一个配置好的 Chrome WebDriver 实例"""
    options = get_driver_options(disable_gui=disable_gui, disable_logs=disable_logs)
    driver = webdriver.Chrome(options=options)

    # 执行反检测 JS：隐藏 webdriver 属性
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    # 伪造 chrome.runtime 防止检测
    driver.execute_script(
        "window.chrome = { runtime: {} };"
    )
    # 伪造 permissions 防止检测
    driver.execute_script(
        "const originalQuery = window.navigator.permissions.query;"
        "window.navigator.permissions.query = (parameters) => ("
        "  parameters.name === 'notifications' ? "
        "  Promise.resolve({state: Notification.permission}) : "
        "  originalQuery(parameters)"
        ");"
    )

    return driver
