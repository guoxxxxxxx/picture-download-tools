# -*- coding: utf-8 -*-
# @Time : 2024/7/23 17:11
# @Author : guoxun
# @File : baidu_pic
import os.path
import random
from argparse import ArgumentParser
from time import sleep
from tqdm import tqdm

from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By

from pic_utils import driver_utils, log_utils, download_utlis, page_utils


def run(query, driver: webdriver.Chrome | None, save_path="..", sleep_time=3, disable_gui=True, disable_logs=True,
        use_implicitly_wait=True, min_count=1000):
    url = "https://pic.sogou.com/"
    # 创建图片存储文件夹
    if not os.path.exists(os.path.join(save_path, query, "sougou")):
        os.makedirs(os.path.join(save_path, query, "sougou"))
    # 初始化下载器
    if save_path != '.' or save_path != '..':
        # 创建图片存储文件夹
        if not os.path.exists(os.path.join(save_path, "sougou")):
            os.makedirs(os.path.join(save_path, "sougou"))
        downloader = download_utlis.DownloadUtils(save_path=os.path.join(save_path, "sougou"))
    else:
        # 创建图片存储文件夹
        if not os.path.exists(os.path.join(save_path, query, "sougou")):
            os.makedirs(os.path.join(save_path, query, "sougou"))
        downloader = download_utlis.DownloadUtils(save_path=os.path.join(save_path, query, "sougou"))
    # 初始化WebDriver
    chrome_options = driver_utils.get_driver_options(disable_logs=disable_logs, disable_gui=disable_gui)
    # 如果未传入driver则新建driver
    if driver is None:
        driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    # 定位输入框
    driver.find_element(By.CSS_SELECTOR, ".query.query-defalut").send_keys(query)
    sleep(0.01)
    # 点击搜索按钮
    driver.find_element(By.CLASS_NAME, "search-btn").click()
    idx = 0     # 页面索引
    pre_length = 0
    while True:
        if downloader.check_images_count(min_count) and min_count != 0:
            driver.close()
            log_utils.log_info(f'sougou中的图片已爬取完成! 共计爬取图片{downloader.get_download_images_count()}张!')
            return downloader.get_download_images_count()
        img_url_list = []
        img_urls_content = None
        if use_implicitly_wait:
            driver.implicitly_wait(sleep_time)      # 隐式等待响应时间
        else:
            sleep(sleep_time)       # 等待界面加载完毕所需等待时间
        try:
            img_urls_content = driver.find_elements(By.CSS_SELECTOR, "div.img-layout>a")[pre_length:]
            pre_length += len(img_urls_content)
        except:
            delta = random.randrange(5, 100) * 0.1
            log_utils.log_info(f'第{idx}页图片获取失败! {delta}s 后继续尝试...')
            try:
                img_urls_content = driver.find_elements(By.CSS_SELECTOR, "div.img-layout>a")[pre_length:]
                pre_length += len(img_urls_content)
            except:
                log_utils.log_info(f'再次尝试失败, 放弃该页面图片的获取, {delta}s 后程序继续执行...')
        idx += 1
        # 异步更新界面
        page_utils.async_scroll_down(driver)
        # 对元素内容进行解析, 获得图片网络资源地址
        for el in tqdm(img_urls_content, desc='正在解析图片路径'):
            if el.get_attribute("drag-img") is not None:
                img_url_list.append(el.get_attribute("drag-img"))
        for url in tqdm(img_url_list, desc='正在下载图片'):
            # 使用下载工具对图片进行下载
            downloader.link_download_tools(url)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--query', type=str, default='')  # 搜索关键词
    parser.add_argument('--min_count', type=int, default=1000)  # 当下载图片数量大于该数值时，程序停止
    parser.add_argument('--disable_gui', type=bool, default=False)  # 是否关闭浏览器界面
    parser.add_argument('--disable_logs', type=bool, default=True)  # 是否关闭警告日志
    parser.add_argument('--save_path', type=str, default='..')  # 保存路径
    parser.add_argument('--sleep_time', type=float, default=3)  # 网页刷新最大等待时间
    parser.add_argument('--use_implicitly_wait', type=bool, default=True)  # 是否采用隐式等待(这种等待方式可以缩短实际等待时间)
    args = parser.parse_args()
    run(query=args.query, driver=None, disable_gui=args.disable_gui, disable_logs=args.disable_logs,
        save_path=args.save_path, sleep_time=args.sleep_time, use_implicitly_wait=args.use_implicitly_wait,
        min_count=args.min_count)
