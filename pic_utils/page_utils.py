# -*- coding: utf-8 -*-
# @Time : 2024/7/24 8:21
# @Author : guoxun
# @File : page_utils
import threading

from selenium import webdriver


def scroll_down(driver: webdriver.Chrome):
    """
    向下滚动界面，同步进行
    :param driver:
    :return:
    """
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")


def async_scroll_down(driver: webdriver.Chrome):
    """
    向下滚动界面，异步进行
    :param driver:
    :return:
    """
    threading.Thread(target=scroll_down, args=(driver,)).start()