# -*- coding: UTF-8 -*-
"""
@Project  : sync 
@File     : down.py
@Author   : Sorami
@GitHub   : https://github.com/Soramik
"""
import requests
import os
import sys


class Downloader:
    def __init__(self, url, file_path):
        self.url = url
        res_length = requests.get(self.url, stream=True)
        self.total_size = int(res_length.headers['Content-Length'])
        self.ori_file_path = file_path
        self.downloading_file_path = file_path+f"_temp_size_{self.total_size}"

    def start(self, print_flag=False):
        """

        :param print_flag: 如果为True, 则打印进度
        :return:
        """
        if os.path.exists(self.downloading_file_path):
            temp_size = os.path.getsize(self.downloading_file_path)
            print(f"当前：{temp_size} 字节， 总：{self.total_size} 字节， 已下载：{round(100 * temp_size / self.total_size)} ")
        else:
            temp_size = 0
            print(f"总：{self.total_size} 字节，开始下载...")

        headers = {'Range': 'bytes=%d-' % temp_size,
                   "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0"}
        res_left = requests.get(self.url, stream=True, headers=headers)

        with open(self.downloading_file_path, "ab") as f:
            for chunk in res_left.iter_content(chunk_size=1024):
                temp_size += len(chunk)
                f.write(chunk)
                f.flush()

                done = int(50 * temp_size / self.total_size)
                if print_flag is True:
                    sys.stdout.write("\r[%s%s] %d%%" % ('█' * done, ' ' * (50 - done), 100 * temp_size / self.total_size))
                    sys.stdout.flush()
        os.rename(self.downloading_file_path, self.ori_file_path)   # 下载完成，重命名
        print("\n")
        f.close()