# -*- coding: utf-8 -*-
# @Time : 2024/7/24 11:06
# @Author : guoxun
# @File : main
import threading
from argparse import ArgumentParser
from webpic import google_pic_download, baidu_pic_download, sougou_pic_download

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--query', type=str, default='tank')  # 搜索关键词
    parser.add_argument('--engine', type=str, default='google baidu sougou')  # 所采用的搜索引擎
    parser.add_argument('--disable_gui', type=bool, default=True)  # 是否关闭浏览器界面
    parser.add_argument('--disable_logs', type=bool, default=True)  # 是否关闭警告日志
    parser.add_argument('--save_path', type=str, default='..')  # 保存路径
    parser.add_argument('--sleep_time', type=float, default=3)  # 网页刷新最大等待时间
    parser.add_argument('--use_implicitly_wait', type=bool, default=True)  # 是否采用隐式等待(这种等待方式可以缩短实际等待时间)
    parser.add_argument('--min_count', type=int, default=100)  # 当下载图片数量大于该数值时，程序停止
    args = parser.parse_args()

    if 'google' in args.engine:
        google_pic_download.run(query=args.query, driver=None, disable_gui=args.disable_gui,
                                disable_logs=args.disable_logs,
                                save_path=args.save_path, sleep_time=args.sleep_time,
                                use_implicitly_wait=args.use_implicitly_wait,
                                min_count=args.min_count)
    if 'baidu' in args.engine:
        baidu_pic_download.run(query=args.query, driver=None, disable_gui=args.disable_gui,
                               disable_logs=args.disable_logs,
                               save_path=args.save_path, sleep_time=args.sleep_time,
                               use_implicitly_wait=args.use_implicitly_wait,
                               min_count=args.min_count)
    if 'sougou' in args.engine:
        sougou_pic_download.run(query=args.query, driver=None, disable_gui=args.disable_gui,
                                disable_logs=args.disable_logs,
                                save_path=args.save_path, sleep_time=args.sleep_time,
                                use_implicitly_wait=args.use_implicitly_wait,
                                min_count=args.min_count)
