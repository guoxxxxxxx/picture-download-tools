# -*- coding: utf-8 -*-
# @Time : 2024/7/24 11:06
# @Author : guoxun
# @File : main
import threading
from argparse import ArgumentParser
from webpic import google_pic_download, baidu_pic_download, sougou_pic_download
from pic_utils import log_utils

if __name__ == '__main__':
    parser = ArgumentParser()
    # 建议使用google引擎爬取图片时使用英文关键词
    parser.add_argument('--query', type=str, default='蜡笔小新')  # 搜索关键词 建议google引擎使用英文进行搜索
    parser.add_argument('--engine', type=str, default='google')  # 所采用的搜索引擎 可选项 google，baidu，sougou
    parser.add_argument('--disable_gui', type=bool, default=False)  # 是否关闭浏览器界面 建议在使用google关闭此选项
    parser.add_argument('--disable_logs', type=bool, default=True)  # 是否关闭警告日志
    parser.add_argument('--save_path', type=str, default='./download/weather/shachenbao')  # 保存路径
    parser.add_argument('--sleep_time', type=float, default=3)  # 网页刷新最大等待时间
    parser.add_argument('--use_implicitly_wait', type=bool, default=True)  # 是否采用隐式等待(这种等待方式可以缩短实际等待时间)
    parser.add_argument('--min_count', type=int, default=1000)  # 当下载图片数量大于该数值时，程序停止 # 若为0则无限下载
    parser.add_argument('--high_quality', type=bool, default=True)  # 是否采用高质量图片下载模式， 注：采用该模式可能下载速度较慢
    parser.add_argument('--is_async', type=bool, default=True)  # 是否采用异步下载的方式下载图片
    args = parser.parse_args()

    if 'google' in args.engine:
        log_utils.log_info(f'Downloading Image From Google...')
        google_pic_download.run(query=args.query, driver=None, disable_gui=args.disable_gui,
                                disable_logs=args.disable_logs,
                                save_path=args.save_path, sleep_time=args.sleep_time,
                                use_implicitly_wait=args.use_implicitly_wait,
                                min_count=args.min_count,
                                high_quality=args.high_quality)
    if 'baidu' in args.engine:
        log_utils.log_info(f'Downloading Image From Baidu...')
        baidu_pic_download.run(query=args.query, driver=None, disable_gui=args.disable_gui,
                               disable_logs=args.disable_logs,
                               save_path=args.save_path, sleep_time=args.sleep_time,
                               use_implicitly_wait=args.use_implicitly_wait,
                               min_count=args.min_count,
                               high_quality=args.high_quality)
    if 'sougou' in args.engine:
        log_utils.log_info(f'Downloading Image From Sougou...')
        sougou_pic_download.run(query=args.query, driver=None, disable_gui=args.disable_gui,
                                disable_logs=args.disable_logs,
                                save_path=args.save_path, sleep_time=args.sleep_time,
                                use_implicitly_wait=args.use_implicitly_wait,
                                min_count=args.min_count)
