# -*- coding: utf-8 -*-
# @Time : 2024/7/23 16:27
# @Author : guoxun
# @File : DownloadUtils
import base64
import hashlib
import io
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from pic_utils import log_utils


class DownloadUtils:

    def __init__(self, url=None, save_path=None, min_size=80, num_threads=5):
        """
        :param url: 目标图片地址
        :param save_path: 保存路径
        :param min_size: 最小图片尺寸（像素），低于此值跳过
        :param num_threads: 并发下载线程数
        """
        self.filename = 'blank.jpg'
        self.url = url
        self.save_path = save_path
        self.save_path_and_name = os.path.join(self.save_path, self.filename)
        self.min_size = min_size
        self.num_threads = num_threads
        self.thread_pool = ThreadPoolExecutor(max_workers=num_threads)
        self._failed_count = 0  # 下载失败计数
        self._success_count = 0  # 下载成功计数
        self._skip_count = 0     # 跳过的小图/GIF 计数

    # ─── 工具方法 ────────────────────────────────────────────

    def _should_skip_image(self, img: Image.Image) -> bool:
        """判断图片是否需要跳过（GIF / 尺寸太小）"""
        if img.format == 'GIF':
            return True
        if img.size[0] < self.min_size or img.size[1] < self.min_size:
            return True
        return False

    def _convert_and_save(self, img: Image.Image):
        """将图片转为 JPG 并保存"""
        if img.format == 'PNG' and img.mode != 'P':
            img = img.convert('RGB')
        elif img.mode == 'P':
            img = img.convert('RGB')
        img.save(self.save_path_and_name, 'JPEG', quality=92)

    def _check_disk_image(self, file_path: str) -> bool:
        """从磁盘读取并校验图片文件，返回是否有效"""
        try:
            with Image.open(file_path) as img:
                if self._should_skip_image(img):
                    return False
                self._convert_and_save(img)
                return True
        except Exception:
            return False

    # ─── 下载方法 ────────────────────────────────────────────

    def download_carry_headers(self, url: str) -> bool:
        """使用带重试和自定义头的 requests.Session 下载"""
        assert url is not None, 'url should not be None'
        self.url = url
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://image.baidu.com/',
        }

        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        try:
            response = session.get(url, headers=headers, timeout=15)
            if response.status_code == 200 and len(response.content) > 512:
                with open(self.save_path_and_name, 'wb') as f:
                    f.write(response.content)
                # 校验图片
                if not self._check_disk_image(self.save_path_and_name):
                    os.remove(self.save_path_and_name)
                    return False
                return True
            return False
        except requests.exceptions.RequestException:
            return False

    def urllib_download(self, url: str) -> bool:
        """使用 urllib 下载图片"""
        assert url is not None, 'url should not be None'
        self.url = url
        try:
            temp_filename, _ = urllib.request.urlretrieve(self.url)
            result = self._check_disk_image(temp_filename)
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            return result
        except Exception:
            return False

    def requests_download(self, url: str) -> bool:
        """使用 requests 下载并直接解析为 PIL Image"""
        assert url is not None, 'url should not be None'
        self.url = url
        try:
            response = requests.get(self.url, timeout=15)
            if response.status_code == 200 and len(response.content) > 512:
                image = Image.open(io.BytesIO(response.content))
                if self._should_skip_image(image):
                    self._skip_count += 1
                    return False
                self._convert_and_save(image)
                return True
            return False
        except Exception:
            return False

    def save_base64(self, base64_string: str, min_size: int = 32) -> bool:
        """保存 base64 编码的图片"""
        assert base64_string is not None, 'base64 should not be None'

        # 处理 data:image/xxx;base64, 前缀
        if ',' in base64_string and 'base64' in base64_string:
            base64_string = base64_string.split(',', 1)[1]

        self.filename = hashlib.md5(base64_string[:200].encode()).hexdigest() + '.jpg'
        self.save_path_and_name = os.path.join(self.save_path, self.filename)

        try:
            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data))
            if image.size[0] < min_size or image.size[1] < min_size:
                self._skip_count += 1
                return False
            if image.format == 'GIF':
                return False
            if image.format == 'PNG' and image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(self.save_path_and_name, 'JPEG', quality=92)
            return True
        except Exception:
            return False

    # ─── 链式下载（多方法降级） ──────────────────────────────

    def link_download_tools(self, url, show_log=True, is_async=True):
        """链式下载入口：依次尝试多种下载方式"""
        if url is None or url == '':
            return False

        if is_async:
            # 非阻塞提交到线程池
            self.thread_pool.submit(self._async_link_download, url, show_log)
        else:
            return self._async_link_download(url, show_log)

    def _async_link_download(self, url: str, show_log: bool = True) -> bool:
        """实际执行链式下载（多种方式降级尝试）"""
        # 生成文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()
        self.filename = f"{url_hash}.jpg"
        self.save_path_and_name = os.path.join(self.save_path, self.filename)

        # 如果文件已存在则跳过
        if os.path.exists(self.save_path_and_name):
            return True

        # 依次尝试
        if self.download_carry_headers(url):
            self._success_count += 1
            return True
        elif self.requests_download(url):
            self._success_count += 1
            return True
        elif self.urllib_download(url):
            self._success_count += 1
            return True
        else:
            self._failed_count += 1
            if show_log and self._failed_count % 50 == 0:
                log_utils.log_warning(
                    f"累计 {self._failed_count} 张图片下载失败 (最近: {url[:80]}...)"
                )
            return False

    # ─── 计数与状态 ──────────────────────────────────────────

    def check_images_count(self, min_count: int) -> bool:
        """检查已下载图片数量是否达到目标"""
        if min_count <= 0:
            return False
        try:
            return len(os.listdir(self.save_path)) >= min_count
        except FileNotFoundError:
            return False

    def get_downloaded_count(self) -> int:
        """获取已下载的图片数量"""
        try:
            return len(os.listdir(self.save_path))
        except FileNotFoundError:
            return 0

    @property
    def failed_count(self):
        return self._failed_count

    @property
    def success_count(self):
        return self._success_count

    # ─── 生命周期 ────────────────────────────────────────────

    def shutdown(self, wait: bool = True):
        """关闭线程池，等待所有下载任务完成"""
        log_utils.log_info("正在关闭下载线程池...")
        self.thread_pool.shutdown(wait=wait)
        log_utils.log_info("线程池已关闭。")
