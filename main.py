# -*- coding: utf-8 -*-
# @Time : 2024/7/24 11:06
# @Author : guoxun
# @File : main
import atexit
import signal
import sys
import threading
from argparse import ArgumentParser, ArgumentTypeError

from webpic import google_pic_download, baidu_pic_download, sougou_pic_download
from pic_utils import log_utils


# ─── 全局退出信号 ────────────────────────────────────────────

shutdown_flag = threading.Event()


def _signal_handler(signum, frame):
    signame = signal.Signals(signum).name
    log_utils.log_warning(f"\n收到 {signame} 信号，正在优雅退出...")
    shutdown_flag.set()


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


@atexit.register
def _cleanup():
    """确保退出时设置 shutdown 标志"""
    shutdown_flag.set()


# ─── 参数解析辅助 ────────────────────────────────────────────

def str2bool(v):
    """
    正确处理命令行布尔值。
    支持: True/False, true/false, yes/no, y/n, 1/0, t/f
    """
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ArgumentTypeError(
            f"无效的布尔值: '{v}'. 请使用 yes/no, true/false, 1/0"
        )


def parse_engine_list(engine_str: str) -> list:
    """解析引擎参数，返回引擎名称列表"""
    engines = [e.strip().lower() for e in engine_str.split(",") if e.strip()]
    valid = {"google", "baidu", "sougou", "sogou"}
    result = []
    for e in engines:
        if e in valid:
            # 统一搜狗的两种拼写
            result.append("sougou" if e == "sogou" else e)
        else:
            log_utils.log_warning(f"忽略未知引擎: '{e}' (支持的引擎: google, baidu, sougou)")
    return result


# ─── 主入口 ──────────────────────────────────────────────────

if __name__ == '__main__':
    parser = ArgumentParser(
        description="多搜索引擎图片批量下载工具",
        epilog="示例: python main.py --engine google,baidu --query cat --min_count 500 --disable_gui"
    )

    parser.add_argument('--query', type=str, default='蜡笔小新',
                        help='搜索关键词（Google 建议使用英文）')
    parser.add_argument('--engine', type=str, default='sougou',
                        help='搜索引擎，支持多个（用逗号分隔）：google, baidu, sougou')
    parser.add_argument('--disable_gui', type=str2bool, default=False,
                        help='是否隐藏浏览器界面 (true/false)')
    parser.add_argument('--disable_logs', type=str2bool, default=True,
                        help='是否隐藏浏览器控制台日志 (true/false)')
    parser.add_argument('--save_path', type=str, default='./download/tmp',
                        help='图片保存路径')
    parser.add_argument('--sleep_time', type=float, default=3,
                        help='页面操作的等待间隔（秒），网络慢时可调大')
    parser.add_argument('--use_implicitly_wait', type=str2bool, default=True,
                        help='是否使用 Selenium 隐式等待')
    parser.add_argument('--min_count', type=int, default=200,
                        help='每个引擎的目标下载数量（0 = 不限）')
    parser.add_argument('--high_quality', type=str2bool, default=True,
                        help='是否启用高清模式（仅百度/Google 支持）')
    parser.add_argument('--is_async', type=str2bool, default=True,
                        help='是否启用异步下载')
    parser.add_argument('--num_threads', type=int, default=5,
                        help='并发下载线程数')

    args = parser.parse_args()

    # 解析引擎列表
    engines = parse_engine_list(args.engine)
    if not engines:
        log_utils.log_error("未指定有效的搜索引擎，退出。")
        sys.exit(1)

    log_utils.log_info(f"搜索引擎: {engines}")
    log_utils.log_info(f"搜索关键词: {args.query}")
    log_utils.log_info(f"目标数量: {args.min_count}/引擎")
    log_utils.log_info(f"保存路径: {args.save_path}")
    log_utils.log_info(f"下载线程数: {args.num_threads}")
    log_utils.log_info("=" * 50)

    # 依次运行各引擎
    results = {}
    for engine in engines:
        if shutdown_flag.is_set():
            log_utils.log_info("检测到退出信号，跳过剩余引擎。")
            break

        try:
            if engine == 'google':
                count = google_pic_download.run(
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
                    shutdown_flag=shutdown_flag,
                )
            elif engine == 'baidu':
                count = baidu_pic_download.run(
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
                    shutdown_flag=shutdown_flag,
                )
            elif engine == 'sougou':
                count = sougou_pic_download.run(
                    query=args.query, driver=None,
                    disable_gui=args.disable_gui,
                    disable_logs=args.disable_logs,
                    save_path=args.save_path,
                    sleep_time=args.sleep_time,
                    use_implicitly_wait=args.use_implicitly_wait,
                    min_count=args.min_count,
                    is_async=args.is_async,
                    num_threads=args.num_threads,
                    shutdown_flag=shutdown_flag,
                )
            else:
                continue

            results[engine] = count
            log_utils.log_info(f"✅ {engine} 引擎完成，下载 {count} 张图片")

        except Exception as e:
            log_utils.log_error(f"❌ {engine} 引擎出错: {e}")
            results[engine] = -1

    # ── 最终汇总 ────────────────────────────────────────────
    log_utils.log_summary({
        "关键词": args.query,
        "搜索引擎": ", ".join(engines),
        "各引擎结果": ", ".join(f"{k}: {v} 张" for k, v in results.items()),
        "总计": sum(v for v in results.values() if v > 0),
        "保存路径": args.save_path,
    })

    log_utils.log_info("程序运行完毕。")
