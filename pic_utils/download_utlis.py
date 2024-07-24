# -*- coding: utf-8 -*-
# @Time : 2024/7/23 16:27
# @Author : guoxun
# @File : DownloadUtils
import base64
import hashlib
import urllib.request
from PIL import Image
import os
import requests
import io
import wget

from pic_utils import log_utils


class DownloadUtils:

    def __init__(self, url=None, save_path=None, min_size=32):
        """
        构造函数
        :param url: 目标图片地址
        :param save_path: 保存路径
        """
        self.filename = 'blank.jpg'
        self.url = url
        self.save_path = save_path
        self.save_path_and_name = os.path.join(self.save_path, self.filename)
        self.min_size = min_size

    def convert2jpg_and_save(self, file_path):
        """
        将png图片转化为jpg格式并进行保存
        :param file_path: 图片地址
        :return:
        """
        with Image.open(file_path) as img:
            if img.format == 'GIF':
                return
            elif img.size[0] < self.min_size or img.size[1] < self.min_size:
                return True
            elif img.format == 'PNG':
                rgb_img = img.convert('RGB')
                rgb_img.save(self.save_path_and_name)
            else:
                img.save(self.save_path_and_name)

    def urllib_download(self, url):
        """
        使用urllib方法对图像进行下载
        :return:
        """
        assert url is not None, 'url should not be None'
        self.url = url
        try:
            temp_filename, _ = urllib.request.urlretrieve(self.url)
            self.convert2jpg_and_save(temp_filename)
            os.remove(temp_filename)
            return True
        except Exception as e:
            # log_utils.log_info(f'urllib download error: {e}')
            return False

    def requests_download(self, url):
        """
        使用requests库对图像进行下载
        :return:
        """
        assert url is not None, 'url should not be None'
        self.url = url
        try:
            response = requests.get(self.url)
            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content))
                if image.format == 'GIF':
                    return
                elif image.size[0] < self.min_size or image.size[1] < self.min_size:
                    return True
                elif image.format == 'PNG':
                    if image.mode != 'P':
                        image = image.convert('RGB')
                image.save(self.save_path_and_name)
                return True
            else:
                return False
        except Exception as e:
            # log_utils.log_info(f'requests download error: {e}')
            return False

    def wget_download(self, url):
        """
        使用wget库对图像进行下载
        :return:
        """
        assert url is not None, 'url should not be None'
        self.url = url
        try:
            temp_filename = wget.download(self.url)
            self.convert2jpg_and_save(temp_filename)
            os.remove(temp_filename)
            return True
        except Exception as e:
            # log_utils.log_info(f'wget download error: {e}')
            return False
    def save_base64(self, base64_string=None, min_size=32):
        """
        保存base64格式的文件, 此函数用于保存google中的部分图片
        @:param base64_string: base64的文本内容
        @:param min_size: 最小尺寸，当图片宽或高小于该尺寸时，忽略该图片
        :return:
        """
        assert base64_string is not None, 'base64 should not be None'
        # base64编码太长了，截取前200位用于图片名称的生成
        self.filename = hashlib.md5(base64_string[:200].encode()).hexdigest()
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        # 当图片尺寸小于min_size时自动略过该图片的下载
        if image.size[0] < min_size or image.size[1] < min_size:
            return True
        if image.format == 'GIF':
            return
        elif image.format == 'png':
            if image.mode != 'RGB':
                image = image.convert('RGB')
        image.save(self.save_path_and_name)
        return True

    def link_download_tools(self, url):
        """
        链式下载
        :param url:
        :return:
        """
        self.filename = hashlib.md5(url.encode()).hexdigest() + '.jpg'
        self.save_path_and_name = os.path.join(self.save_path, self.filename)
        if self.urllib_download(url) is True:
            return True
        elif self.requests_download(url) is True:
            return True
        elif self.wget_download(url) is True:
            return True
        else:
            log_utils.log_info(f'3种下载方式均失败, 放弃当前图片: {url}')
            return False

    def check_images_count(self, min_count):
        """
        检查图片数量是否已经到达所设置的数量
        :param min_count:
        :return:
        """
        if len(os.listdir(self.save_path)) >= min_count:
            return True
        else:
            return False

    def get_download_images_count(self):
        """
        获取已经下载的图片的数量
        :return:
        """
        return len(os.listdir(self.save_path))
