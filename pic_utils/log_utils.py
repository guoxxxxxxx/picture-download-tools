# -*- coding: utf-8 -*-
# @Time : 2024/7/24 8:38
# @Author : guoxun
# @File : log_utils
import datetime


def _timestamp():
    """返回当前时间戳字符串"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_info(message):
    """打印普通信息日志"""
    print(f"[{_timestamp()}] [INFO] {message}")


def log_error(message):
    """打印错误日志"""
    print(f"[{_timestamp()}] [ERROR] {message}")


def log_warning(message):
    """打印警告日志"""
    print(f"[{_timestamp()}] [WARN] {message}")


def log_summary(stats: dict):
    """打印统计摘要"""
    print(f"\n{'='*50}")
    print(f"[{_timestamp()}] 📊 Summary")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print(f"{'='*50}\n")
