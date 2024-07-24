# -*- coding: utf-8 -*-
# @Time : 2024/7/23 17:11
# @Author : guoxun
# @File : baidu_pic
import os.path
import random
from time import sleep
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.by import By

from argparse import ArgumentParser

from pic_utils import driver_utils, log_utils, download_utlis, page_utils


def run(query, driver: webdriver.Chrome | None, save_path="..", sleep_time=3, disable_gui=True, disable_logs=True,
        use_implicitly_wait=True, min_count=1000):
    url = "https://images.google.com/"
    # 创建图片存储文件夹
    if not os.path.exists(os.path.join(save_path, query, "google")):
        os.makedirs(os.path.join(save_path, query, "google"))
    # 初始化下载器
    downloader = download_utlis.DownloadUtils(save_path=os.path.join(save_path, query, "google"))
    # 初始化WebDriver
    chrome_options = driver_utils.get_driver_options(disable_logs=disable_logs, disable_gui=disable_gui)
    # 如果未传入driver则新建driver
    if driver is None:
        driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    # 定位输入框
    driver.find_element(By.CLASS_NAME, 'gLFyf').send_keys(query)
    sleep(0.01)
    # 点击搜索按钮
    driver.find_element(By.CSS_SELECTOR, ".HZVG1b.Tg7LZd").click()
    idx = 0     # 页面索引
    pre_length = 0
    zero_times = 0
    while True:
        if downloader.check_images_count(min_count):
            driver.close()
            log_utils.log_info(f'google中的图片已爬取完成! 共计爬取图片{downloader.get_download_images_count()}张!')
            return
        img_url_list = []
        img_urls_content = None
        if use_implicitly_wait:
            driver.implicitly_wait(sleep_time)      # 隐式等待响应时间
        else:
            sleep(sleep_time)       # 等待界面加载完毕所需等待时间
        try:
            img_urls_content = driver.find_elements(By.CLASS_NAME, "YQ4gaf")[pre_length:]
            pre_length += len(img_urls_content)
        except:
            delta = random.randrange(5, 100) * 0.1
            log_utils.log_info(f'第{idx}页图片获取失败! {delta}s 后继续尝试...')
            try:
                img_urls_content = driver.find_elements(By.CLASS_NAME, "YQ4gaf")[pre_length:]
                pre_length += len(img_urls_content)
            except:
                log_utils.log_info(f'再次尝试失败, 放弃该页面图片的获取, {delta}s 后程序继续执行...')
        # 异步更新界面
        page_utils.async_scroll_down(driver)
        # 对元素中图片进行解析并初次筛选
        if len(img_urls_content) <= 0:
            zero_times += 1
            if zero_times >= 10:
                log_utils.log_info(f'google图片已经抓取完毕，该关键词无可再抓取的文件!')
                driver.close()
                return
        for el in tqdm(img_urls_content, desc='正在解析连接'):
            if el.get_attribute("src") is not None and 'favicon' not in el.get_attribute("src") and 'gif' not in el.get_attribute("src"):
                img_url_list.append(el.get_attribute("src"))
        for url in tqdm(img_url_list, desc='downloading'):
            # 若为网络资源路径则直接进行下载
            if 'http' or 'https' in url:
                downloader.link_download_tools(url)
            # 若为base64编码则直接保存
            elif 'jpeg' or 'png' in url and 'base64' in url:
                downloader.save_base64(url)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--query', type=str, default='')      # 搜索关键词
    parser.add_argument('--disable_gui', type=bool, default=True)     # 是否关闭浏览器界面
    parser.add_argument('--disable_logs', type=bool, default=True)    # 是否关闭警告日志
    parser.add_argument('--save_path', type=str, default='..')      # 保存路径
    parser.add_argument('--sleep_time', type=float, default=3)    # 网页刷新最大等待时间
    parser.add_argument('--min_count', type=int, default=1000)  # 当下载图片数量大于该数值时，程序停止
    parser.add_argument('--use_implicitly_wait', type=bool, default=True)     # 是否采用隐式等待(这种等待方式可以缩短实际等待时间)
    args = parser.parse_args()
    run(query=args.query, driver=None, disable_gui=args.disable_gui, disable_logs=args.disable_logs,
        save_path=args.save_path, sleep_time=args.sleep_time, use_implicitly_wait=args.use_implicitly_wait,
        min_count=args.min_count)
