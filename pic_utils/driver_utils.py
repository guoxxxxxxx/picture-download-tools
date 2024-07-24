# -*- coding: utf-8 -*-
# @Time : 2024/7/23 17:28
# @Author : guoxun
# @File : driver_utils
from selenium.webdriver.chrome.options import Options


def get_driver_options(disable_gui=True, disable_logs=True):
    chrome_options = Options()
    if disable_gui:
        chrome_options.add_argument("--headless")  # 无头模式
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    if disable_logs:
        # 禁用控制台日志
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return chrome_options