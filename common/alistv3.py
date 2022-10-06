# -*- coding: UTF-8 -*-
"""
@Project  : SonepDown 
@File     : alistv3.py
@Author   : Sorami
@GitHub   : https://github.com/Soramik
"""
import requests
import traceback
import json
import os
import threading
import random
import time
import shutil
from copy import deepcopy
from urllib import parse
from requests_toolbelt.multipart.encoder import MultipartEncoder

from common.log import log
from common.down import Downloader
from common.rclone import RcloneOperation

TrackPrintEnable = True

lock = threading.Lock()


def myThread(func, *args, **kwargs):
    """
    多线程处理, 把多线程任务推送到队列中

    :param func: 需要执行的函数
    :param args: 参数
    :param kwargs: 参数
    """
    t = threading.Thread(target=func, args=args, kwargs=kwargs)
    return t


class AlistException:
    """
    AlistManage的错误处理类型
    """

    def __init__(self, exp):
        self.exp = exp

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except self.exp as e:
                raise e
            except requests.exceptions.ConnectionError:
                raise self.exp("Alist连接失败")
            except requests.exceptions.InvalidURL:
                raise self.exp("Alist的URL输入错误")
            except KeyError:
                raise self.exp(f"Alist响应结果异常")
            except self.BaseError as e:  # 属于Exp类的异常
                raise self.exp(e)
            except Exception:
                # 未知异常
                if TrackPrintEnable is True:
                    traceback.print_exc()  # 打印异常
                raise self.exp

        return wrapper

    class BaseError(Exception):
        """
        基础错误类型，AlistManage类的异常抛出都基于此类
        """

        def __init__(self):
            self.err_msg = ""
            self.err_msg_detail = ""

    class InitError(BaseError):
        """
        类初始化错误
        """

        def __init__(self, err_msg=None):
            if err_msg is None:
                err_msg = "未知错误"
            self.err_msg = "初始化出错"
            self.err_msg_detail = err_msg
            Exception.__init__(self, self.err_msg, self.err_msg_detail)

    class RenameError(BaseError):
        """
        重命名操作错误类型
        """

        def __init__(self, err_msg=None):
            if err_msg is None:
                err_msg = "未知错误"
            self.err_msg = "重命名操作出错"
            self.err_msg_detail = err_msg
            Exception.__init__(self, self.err_msg, self.err_msg_detail)

    class GetPathError(BaseError):
        """
        获取目录操作错误类型
        """

        def __init__(self, err_msg=None):
            if err_msg is None:
                err_msg = "未知错误"
            self.err_msg = "获取目录操作出错"
            self.err_msg_detail = err_msg
            Exception.__init__(self, self.err_msg, self.err_msg_detail)

    class MkdirError(BaseError):
        """
        创建目录操作错误类型
        """

        def __init__(self, err_msg=None):
            if err_msg is None:
                err_msg = "未知错误"
            self.err_msg = "创建目录操作出错"
            self.err_msg_detail = err_msg
            Exception.__init__(self, self.err_msg, self.err_msg_detail)

    class DelError(BaseError):
        """
        删除操作错误类型
        """

        def __init__(self, err_msg=None):
            if err_msg is None:
                err_msg = "未知错误"
            self.err_msg = "删除操作出错"
            self.err_msg_detail = err_msg
            Exception.__init__(self, self.err_msg, self.err_msg_detail)

    class MoveError(BaseError):
        """
        移动文件操作错误类型
        """

        def __init__(self, err_msg=None):
            if err_msg is None:
                err_msg = "未知错误"
            self.err_msg = "移动文件操作出错"
            self.err_msg_detail = err_msg
            Exception.__init__(self, self.err_msg, self.err_msg_detail)

    class CopyError(BaseError):
        """
        复制文件操作错误类型
        """

        def __init__(self, err_msg=None):
            if err_msg is None:
                err_msg = "未知错误"
            self.err_msg = "复制文件操作出错"
            self.err_msg_detail = err_msg
            Exception.__init__(self, self.err_msg, self.err_msg_detail)

    class DownloadError(BaseError):
        """
        下载文件操作错误类型
        """

        def __init__(self, err_msg=None):
            if err_msg is None:
                err_msg = "未知错误"
            self.err_msg = "下载文件操作出错"
            self.err_msg_detail = err_msg
            Exception.__init__(self, self.err_msg, self.err_msg_detail)

    class UploadError(BaseError):
        """
        上传文件操作错误类型
        """

        def __init__(self, err_msg=None):
            if err_msg is None:
                err_msg = "未知错误"
            self.err_msg = "上传文件操作出错"
            self.err_msg_detail = err_msg
            Exception.__init__(self, self.err_msg, self.err_msg_detail)

    class SyncError(BaseError):
        """
        同步文件操作错误类型
        """

        def __init__(self, err_msg=None):
            if err_msg is None:
                err_msg = "未知错误"
            self.err_msg = "同步文件操作出错"
            self.err_msg_detail = err_msg
            Exception.__init__(self, self.err_msg, self.err_msg_detail)


class AlistV3:
    _MAIN_URL = "http://127.0.0.1:5244"
    _HEADERS = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/'
                      '105.0.0.0 Safari/537.36 Edg/105.0.1343.27',
        'sec-ch-ua': '"Microsoft Edge";v="105", " Not;A Brand";v="99", "Chromium";v="105"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    # 请求会话
    s = requests.session()

    @AlistException(AlistException.InitError)
    def _init(self, user, passwd):
        """
        初始化配置
        """
        self._LIST_URL = f"{self._MAIN_URL}/api/fs/list"
        self._GET_URL = f"{self._MAIN_URL}/api/fs/get"
        self._LOGIN_URL = f"{self._MAIN_URL}/api/auth/login"
        self._RENAME_URL = f"{self._MAIN_URL}/api/fs/rename"
        self._MKDIR_URL = f"{self._MAIN_URL}/api/fs/mkdir"
        self._DEL_URL = f"{self._MAIN_URL}/api/fs/remove"
        self._MOVE_URL = f"{self._MAIN_URL}/api/fs/move"
        self._COPY_URL = f"{self._MAIN_URL}/api/fs/copy"
        self._UPLOAD_URL = f"{self._MAIN_URL}/api/fs/form"
        self._login(user, passwd)  # 登录

    def _login(self, user, passwd):
        json_data = {
            'username': user,
            'password': passwd,
            'otp_code': '',
        }
        res = self.s.post(self._LOGIN_URL, headers=self._HEADERS, json=json_data)
        if res.status_code == 200:
            self._HEADERS['Authorization'] = json.loads(res.text).get("data").get("token")
            self.s.headers = self._HEADERS
        else:
            raise AlistException.InitError("登录失败，密码可能错误，或者账号权限不足。")

    def __init__(self, user, passwd, alist_url=None, local_driver=None):
        if alist_url is not None:
            self._MAIN_URL = alist_url
        if local_driver is None:
            self.local_driver = {}
        else:
            self.local_driver = local_driver
        self._init(user, passwd)

    @AlistException(AlistException.RenameError)
    def rename(self, file_p, newname):
        """
        重命名
        :param file_p: 需要重命名的文件
        :param newname: 新名字
        :return:
        """
        json_data = {
            'name': newname,
            'path': file_p,
        }
        res = self.s.post(self._RENAME_URL, json=json_data).text
        if json.loads(res)['code'] == 200:
            log.info(f"{file_p} --已重命名--> {newname}")
            return
        else:
            raise AlistException.RenameError(f"重命名失败, 响应结果: {res}")

    @AlistException(AlistException.GetPathError)
    def getpath(self, dst_path) -> dict:
        """
        获取alist的路径信息, 获取时会自动刷新路径信息

        :param dst_path: 需要获取的目标路径信息
        :return:
        """
        dst_dir = os.path.dirname(dst_path)
        json_data = {
            'path': dst_dir,
            'password': '',
            'page': 1,
            'per_page': 0,
            'refresh': True,
        }
        res = self.s.post(self._LIST_URL, json=json_data).text
        res = json.loads(res)
        if res.get('code') != 200:  # 上级目录刷新失败，说明不存在上级目录，则刷新再上一级目录
            time.sleep(1)           # 防止递归嵌套频繁请求
            self.getpath(dst_dir)
        json_data = {
            'path': dst_path,
            'password': '',
        }
        res = self.s.post(self._GET_URL, json=json_data).text
        res = json.loads(res)
        return res

    @AlistException(AlistException.MkdirError)
    def mkdir(self, file_path):
        """
        先检查上级目录是否存在，不存在则先创建上级目录
        :param file_path:
        :return:
        """
        file_path = file_path.replace("\\", "/")
        # 检测目录是否存在
        res = self.getpath(file_path)
        if res['code'] == 200:
            return f"目录已存在: {file_path}"

        # 检测上级目录是否存在, 不存在则创建
        last_file_path = os.path.dirname(file_path)
        self.mkdir(last_file_path)

        # 创建目录操作
        json_data = {
            'path': file_path,
        }
        response = self.s.post(self._MKDIR_URL, json=json_data)
        if json.loads(response.text)['code'] == 200:
            log.info(f"已创建alist文件夹: {file_path}")
            time.sleep(3)   # 等待3秒
            return
        else:
            raise AlistException.MkdirError(f"创建目录失败, 响应结果: {response.text}")

    @AlistException(AlistException.DelError)
    def delete(self, file_path):
        """
        删除操作
        :param file_path: 文件路径
        :return:
        """
        file_name = os.path.basename(file_path)
        folder_path = os.path.dirname(file_path)
        with lock:
            # 目标文件是否存在
            file_path_res = self.getpath(file_path)
            if file_path_res['code'] != 200:
                raise AlistException.DelError("目标的文件不存在，请检查目标路径是否正确")
        json_data = {
            'names': [
                file_name,
            ],
            'dir': folder_path,
        }
        res = self.s.post(self._DEL_URL, json=json_data).text
        if json.loads(res)['code'] == 200:
            log.info(f"已删除alist文件: {file_path}")
            return
        else:
            raise AlistException.DelError(f"删除失败, 响应结果: {res}")

    def __local_copy(self, src_path, dst_dir, mkdir_flag=True):
        """
        本地复制，会把文件下载到本地，然后再上传，配置变量LocalDriver后如果移动发生在alist链接目录, 则可免下载上传

        :param src_path: 源文件地址
        :param dst_dir: 目标目录地址
        :param mkdir_flag: 没有文件夹时是否创建文件夹
        :return:
        """
        name = os.path.basename(src_path)

        basedir = src_path[:src_path[1:].find("/") + 1]
        if basedir in self.local_driver:  # 本地存在, 直接对本地进行操作
            local_p = self.local_driver[basedir]
            self.upload(src_path.replace(basedir, local_p), dst_dir, mkdir_flag=mkdir_flag)
            time.sleep(1)
        else:
            self.download_file(src_path, save_path="../cache", mkdir_flag=mkdir_flag)
            self.upload(f"./cache/{name}", dst_dir, mkdir_flag=mkdir_flag)
            time.sleep(1)
            os.remove(f"./cache/{name}")
            log.info(f"已删除临时文件./cache/{name}")
            log.info("跨账号文件复制成功")

    @AlistException(AlistException.MoveError)
    def move(self, src_path, dst_dir, mkdir_flag=True, local_move=True):
        """
        移动文件, 支持跨账号移动

        :param src_path: 源文件地址
        :param dst_dir: 目标目录地址
        :param mkdir_flag: 没有文件夹时是否创建文件夹
        :param local_move: 跨账号移动时是否使用本地移动。(默认True)为True时，此时复制是下载到本地并上传到另一个存储空间。为False时，使用alist的跨盘复制功能
        :return: =1成功，=0失败
        """
        log.info(f"{src_path} --move--> {dst_dir}")
        with lock:
            # 目标路径是否存在
            dst_path_res = self.getpath(dst_dir)
            if dst_path_res['code'] != 200:
                if mkdir_flag is False:
                    raise AlistException.CopyError("目标路径不存在，请检查目标路径是否正确，或选择启用本函数mkdir_flag")
                self.mkdir(dst_dir)
            else:
                if dst_path_res['data']['is_dir'] is False:
                    raise AlistException.CopyError("目标路径实际为文件，请确认输入是否正确")

        src_dir = os.path.dirname(src_path)
        name = os.path.basename(src_path)
        json_data = {
            'src_dir': src_dir,
            'dst_dir': dst_dir,
            'names': [
                name,
            ],
        }
        res = self.s.post(self._MOVE_URL, json=json_data).text
        if json.loads(res)["code"] == 200:  # 跨存储账号移动
            log.info("同账号文件移动操作成功")
            return 1
        elif json.loads(res)["code"] == 500 and "between two storages" in json.loads(res)["message"]:
            log.info("这是跨账号移动")
            if local_move is False:  # 不允许使用本地移动，直接退出，返回移动失败状态数0
                return 0
            self.__local_copy(src_path, dst_dir, mkdir_flag)    # 开始本地移动
            time.sleep(1)
            self.delete(src_path)   # 因为是移动操作，在复制成功后，删除源文件
        else:
            raise AlistException.MoveError(res)

    @AlistException(AlistException.CopyError)
    def copy(self, src_path, dst_dir, mkdir_flag=True, local_copy=False):
        """
        复制文件, 支持跨账号复制

        :param src_path: 源文件地址
        :param dst_dir: 目标目录地址
        :param mkdir_flag: 没有文件夹时是否创建文件夹
        :param local_copy: 跨账号复制时是否使用本地复制。(默认True)为True时，此时复制是下载到本地并上传到另一个存储空间。为False时，使用alist的跨盘复制功能
        :return: =1成功， =0失败
        """
        log.info(f"{src_path} --copy--> {dst_dir}")
        with lock:
            # 目标路径是否存在
            dst_path_res = self.getpath(dst_dir)
            if dst_path_res['code'] != 200:
                if mkdir_flag is False:
                    raise AlistException.CopyError("目标路径不存在，请检查目标路径是否正确，或选择启用本函数mkdir_flag")
                self.mkdir(dst_dir)
            else:
                if dst_path_res['data']['is_dir'] is False:
                    raise AlistException.CopyError("目标路径实际为文件，请确认输入是否正确")

        move_result = self.move(src_path, dst_dir, mkdir_flag, local_move=False)    # 尝试移动，如果是跨账号，则无法移动成功
        if move_result == 1:    # 移动成功，说明是同存储账号，开始还原源目录
            time.sleep(1)   # 等待1秒
            src_dir = os.path.dirname(src_path)
            name = os.path.basename(src_path)
            json_data = {
                'src_dir': dst_dir,
                'dst_dir': src_dir,
                'names': [
                    name,
                ],
            }
            res = self.s.post(self._COPY_URL, json=json_data)
            if res.status_code == 200 and json.loads(res.text)["code"] == 200:
                return 1
            else:
                raise AlistException.CopyError(res.text)
        else:   # 跨账号复制
            if local_copy is False:
                return 0
            self.__local_copy(src_path, dst_dir, mkdir_flag)    # 开始本地复制

    @AlistException(AlistException.DownloadError)
    def download_file(self, file_path: str, save_path: str, mkdir_flag=False, rename=None):
        """
        下载单个文件

        :param file_path: 需要下载的文件路径
        :param save_path: 保存路径
        :param mkdir_flag: 当保存路径不存在时是否创建路径，如果为True则自动创建路径，默认为False
        :param rename: 下载文件是否重命名，默认为None, 不重命名
        :return:
        """
        log.info(f'{file_path} --正在下载--> {save_path}')

        def _download_request(down_url, save_p):
            """
            request的方法下载
            :param down_url: 下载链接
            :param save_p: 保存路径
            :return:
            """
            d = Downloader(down_url, save_p)
            d.start()
            log.info(f"下载完毕, 文件地址: {save_p}")

        # 保存路径正确性检查
        if not os.path.exists(save_path):  # 下载保存的路径
            if mkdir_flag is True:
                os.makedirs(save_path, exist_ok=True)  # 创建保存路径
            else:
                raise AlistException.DownloadError("保存路径不存在，请检查路径是否正确，或选择启用本函数mkdir_flag")
        elif not os.path.isdir(save_path):  # 保存路径不是文件夹
            raise AlistException.DownloadError("保存路径不是文件夹，请检查路径是否正确")
        save_path = os.path.abspath(save_path)  # 强制绝对路径

        # 下载文件链接正确性检查
        res = self.getpath(file_path)
        if res["code"] != 200:
            raise AlistException.DownloadError("输入的文件路径不存在")
        save_file_p = os.path.join(save_path, os.path.basename(file_path) if rename is None else rename)  # 是否重命名
        log.info(f"正在下载文件: {file_path}")
        url = res.get('data').get('raw_url')

        # 开始下载
        log.debug("正在使用request下载")
        _download_request(down_url=url, save_p=save_file_p)

    @AlistException(AlistException.UploadError)
    def upload(self, file_path: str, dst_path: str, mkdir_flag: bool = False):
        """
        上传文件
        :param file_path: 上传的文件路径
        :param dst_path: 目标路径
        :param mkdir_flag: 当目标路径不存在时是否创建路径，如果为True则自动创建路径，默认为False
        :return:
        """

        def random_string_generator(str_size):
            """
            随机字符生成
            :param str_size: 生成字符个数
            :return: 随机字符
            """
            allowed_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
            return ''.join(random.choice(allowed_chars) for _ in range(str_size))

        log.info(f"正在上传: {file_path}")

        # 获取文件名称
        filename = os.path.basename(file_path)
        dst_path = dst_path[:-1] if dst_path[-1] == "/" else dst_path

        # 上传文件是否存在
        if not os.path.exists(file_path):
            raise AlistException.UploadError("需要上传的文件不存在, 请检查上传的文件路径是否正确")

        # 目标路径是否存在
        with lock:
            dst_path_res = self.getpath(dst_path)
            if dst_path_res['code'] != 200:
                if mkdir_flag is False:
                    raise AlistException.CopyError("目标路径不存在，请检查目标路径是否正确，或选择启用本函数mkdir_flag")
                self.mkdir(dst_path)
            else:
                if dst_path_res['data']['is_dir'] is False:
                    raise AlistException.CopyError("目标路径实际为文件，请确认输入是否正确")

        # 构建上传数据
        random_16 = random_string_generator(16)
        headers = deepcopy(self.s.headers)
        headers['Content-Type'] = f'multipart/form-data; boundary=----WebKitFormBoundary{random_16}'
        file_size = os.path.getsize(file_path)
        log.debug(f"文件大小: {file_size}")
        headers['Content-Length'] = f"{file_size}"      # 指定文件大小
        multipart_encoder = MultipartEncoder(
            fields={
                "file": (filename, open(file_path, 'rb'), 'application/octet-stream'),
            },
            boundary=f'----WebKitFormBoundary{random_16}',
            encoding="utf-8"
        )
        headers['File-Path'] = parse.quote(dst_path + "/" + filename, safe="/")
        headers['As-Task'] = 'false'

        # 发送上传请求
        try:
            result = requests.put(self._UPLOAD_URL,
                                  headers=headers,
                                  data=multipart_encoder, timeout=None).text
            res_code = json.loads(result)['code']
        except json.decoder.JSONDecodeError:
            raise AlistException.UploadError(f"json读取异常, result: {result}")
        if res_code == 200:
            log.info(f"上传完毕, 文件地址: {dst_path}/{filename}")
            self.getpath(f'{dst_path}/{filename}')  # 刷新一次
            return
        else:
            # 天翼云盘判定，改非秒传上传
            if "MissingContentLength" not in result:
                raise AlistException.UploadError(result)
            if "Cloud189" not in dst_path:      # 说明是天翼云盘
                raise AlistException.UploadError(result)
            if "Cloud189Sub" in dst_path:       # 说明天翼云盘关闭秒传上传也失败了
                raise AlistException.UploadError(result)
            new_dst_path = dst_path.replace("Cloud189", "Cloud189Sub")
            self.upload(file_path, new_dst_path, mkdir_flag)

    @AlistException(AlistException.SyncError)
    def sync(self, src_path, dst_path_list, rclone_space="alistv3", filter_file=None, auto=False, thread_max_num=None):
        """
        同步命令，需要rclone用webdav绑定alist, 配置变量LocalDriver后如果同步发生在alist链接目录, 则直接调用本地文件资源进行检测
        支持多线程, 通过设置thread_max_num参数启用, 最小设置为2 最大设置为16,

        :param src_path: 源路径
        :param dst_path_list: 目标路径列表(可以同步多个路径，如果只输入1个路径，可以不以列表形式输入)
        :param rclone_space: rclone空间存储符
        :param filter_file: 同步文件过滤器
        :param auto: =True 自动进行，无需确认 默认为False
        :param thread_max_num: 同时进行的最大数量, 默认为None, 不开启多线程, 最小设置为1 最大设置为16
        """
        if thread_max_num is None:
            thread_max_num = 1
        if not (1 <= thread_max_num <= 16):
            raise AlistException.SyncError("你输入的并行数有问题, 最小设置为1, 最大设置为16")

        # 统一dst_path为列表
        if type(dst_path_list) != list:
            dst_path_list = [dst_path_list]

        # 检查源同步目录是否正确
        src_res = self.getpath(src_path)
        if src_res.get('code') != 200:
            raise AlistException.SyncError("输入的文件夹路径不存在，或输入的不是文件夹")

        # 检查目标同步目录是否正确
        err_dst_path_list = []
        for index, dst_path in enumerate(dst_path_list, start=0):
            dst_res = self.getpath(dst_path)
            if dst_res["code"] != 200:
                log.warning(f'此目标路径存在错误: {dst_path}')
                err_dst_path_list.append(index)
        # 删除错误的目标路径
        for err_dst_path in err_dst_path_list:
            dst_path_list.pop(err_dst_path)

        r = RcloneOperation()  # 调用Rclone检测
        src = dst = rclone_space  # 设置为alist存储符

        sync_msg = {
            dst_path: r.check(src_path, dst_path, src=src, dst=dst, filter_file=filter_file)
            for dst_path in dst_path_list
        }
        union_sync = {}

        for dst_path, file_msg_list in sync_msg.items():
            for file_msg in file_msg_list:
                if not union_sync.get(file_msg):
                    union_sync[file_msg] = [dst_path]
                else:
                    union_sync[file_msg].append(dst_path)

        if not union_sync:
            log.info("已同步")
            return

        add_union_sync = {}
        sub_union_sync = {}
        dif_union_sync = {}
        err_union_sync = {}
        for file in union_sync:
            if file[0] == "+":
                add_union_sync[file] = union_sync[file]
            elif file[0] == "-":
                sub_union_sync[file] = union_sync[file]
            elif file[0] == "*":
                dif_union_sync[file] = union_sync[file]
            elif file[0] == "!":
                err_union_sync[file] = union_sync[file]
            else:
                raise AlistException.SyncError(f"差异性文件列表出错: {file}")

        if auto is False:   # 需要输入
            log.info(f"已发现{len(union_sync)}个差异性文件\n"
                     f"{r.SYNC_TIPS}\n"
                     f"+ 文件有{len(add_union_sync)}个, "
                     f"- 文件有{len(sub_union_sync)}个, "
                     f"* 文件有{len(dif_union_sync)}个, "
                     f"! 文件有{len(err_union_sync)}个。\n"
                     f"[+]仅打印+文件, [-][*][!]同理\n"
                     f"[p]打印所有差异性内容\n"
                     f"[+y]将+ 文件从源路径同步内容到目标路径\n"
                     f"[-y]将- 文件从源路径同步内容到目标路径\n"
                     f"[*y]将* 文件从源路径同步内容到目标路径\n"
                     f"[y]从源路径到目标路径同步所有差异性内容\n"
                     f"[n]退出")
            while True:
                flag = input("请输入命令操作: ")
                if flag == "p":
                    for file in union_sync:
                        print(f'{file} -> {union_sync.get(file)}')
                elif flag in ["+", "-", "*", "!"]:
                    for file in union_sync:
                        if file[0] == flag:
                            print(f'{file} -> {union_sync.get(file)}')
                elif flag in ["y", "+y", "-y", "*y"]:
                    break
                elif flag == "n":
                    return
        else:   # 自动进行同步 auto=True
            flag = "y"
            # 打印一次所有要同步的文件
            for file in union_sync:
                print(f'{file} -> {union_sync.get(file)}')

        if flag == "y":
            self.__sync_work(src_path, union_sync, thread_max_num)
        elif flag == "+y":
            self.__sync_work(src_path, add_union_sync, thread_max_num)
        elif flag == "-y":
            self.__sync_work(src_path, sub_union_sync, thread_max_num)
        elif flag == "*y":
            self.__sync_work(src_path, dif_union_sync, thread_max_num)
        else:
            raise AlistException.SyncError(f"操作标识符出错: flag={flag}")

    @AlistException(AlistException.CopyError)
    def __sync_work(self, src_path, union_sync, thread_max_num):
        """
        复制文件, 支持跨账号复制

        :param src_path: 源文件地址
        :param union_sync: 统合的同步信息
        :param thread_max_num: 同时进行的最大数量, 默认为None, 不开启多线程, 最小设置为1 最大设置为16
        """

        # 清除缓存文件
        shutil.rmtree('../cache', ignore_errors=True)
        os.makedirs('../cache', exist_ok=True)

        class _SyncTryAgain:
            """
            同步重试装饰器
            """
            def __init__(self, sync_types, retry_times=3, err_raise=AlistException.SyncError):
                """

                :param retry_times: 重试次数
                :param sync_types: 函数方式
                :param err_raise: 错误报出函数
                """
                self.retry_times = retry_times
                self.sync_types = sync_types
                self.err_raise = err_raise

            def __call__(self, func):
                def wrapper(*args, **kwargs):
                    for n in range(self.retry_times):  # 同步3次
                        try:
                            func(*args, **kwargs)
                            break
                        except Exception as e:
                            log.error(e)
                            if TrackPrintEnable is True:
                                traceback.print_exc()
                            if n+1 < self.retry_times:
                                wait_time = 15 * (n + 1)
                                log.warning(f"第{n + 1}次执行失败, 等到{wait_time}s后尝试执行第{n + 2}次")
                                time.sleep(wait_time)
                            else:
                                log.error(f"失败{self.retry_times}次")
                                raise self.err_raise(f"进行同步操作「{self.sync_types}」时失败, 已重试{self.retry_times}次")
                return wrapper

        @_SyncTryAgain("download")
        def sync_download(src, f):
            """
            下载操作，把临时文件下载到本地

            :param src: 源文件目录
            :param f: 下载的文件，存储到临时文件夹
            """
            down_path = f"{src}/{f[2:]}"
            down_dir = os.path.dirname(down_path)
            basedir = src[:src[1:].find("/") + 1]
            if basedir in self.local_driver:  # 本地存在, 直接对本地进行操作
                local_p = self.local_driver[basedir]
                os.makedirs(f"./cache{down_dir}", exist_ok=True)
                shutil.copy(down_path.replace(basedir, local_p), f"./cache{down_path}")
            else:
                self.download_file(down_path, save_path=f"./cache{down_dir}", mkdir_flag=True)

        @_SyncTryAgain("upload")
        def sync_upload(src, f, dst_dir):
            """
            上传操作

            :param src: 源文件目录
            :param f: 从临时文件夹上传文件
            :param dst_dir: 目标地址
            """
            upload_path = f"{src}/{f[2:]}"
            upload_dir = os.path.dirname(upload_path)
            name = os.path.basename(upload_path)
            self.upload(f"./cache{upload_dir}/{name}", os.path.dirname(dst_dir + '/' + f[2:]), mkdir_flag=True)

        @_SyncTryAgain("clear_cache")
        def sync_clear_cache(src, f):
            """
            清除本地临时文件的缓存

            :param src: 源文件目录
            :param f: 临时文件
            """
            with lock:
                time.sleep(1)   # 等待1秒，确保文件被解除占用。
                cache_path = f"{src}/{f[2:]}"
                os.remove(f'./cache{cache_path}')

        @_SyncTryAgain("delete")
        def sync_delete(f, dst_dir):
            """
            删除操作
            :param f: 需要删除的目标文件
            :param dst_dir: 目标地址
            :return:
            """
            self.delete(f"{dst_dir}/{f[2:]}")
            time.sleep(1)   # 等待1秒

        def sync_func(f, union, sem, count):
            with sem:
                log.info(f"正在执行第{count}/{len(union_sync)}个同步项")
                if f[0] == "+":      # + 型同步
                    sync_download(src_path, f)                 # 下载差异文件
                    for dst in union.get(f):    # 上传差异文件
                        sync_upload(src_path, f, dst)
                    sync_clear_cache(src_path, f)              # 删除下载缓存
                elif f[0] == "-":    # - 型同步
                    for dst in union.get(f):
                        sync_delete(f, dst)                   # 删除差异文件
                elif f[0] == "*":    # * 型同步
                    for dst in union.get(f):
                        sync_delete(f, dst)                   # 删除差异文件
                    sync_download(src_path, f)                 # 下载差异文件
                    for dst in union.get(f):    # 上传差异文件
                        sync_upload(src_path, f, dst)
                    sync_clear_cache(src_path, f)              # 删除下载缓存

        semaphore = threading.Semaphore(thread_max_num)
        for c, file in enumerate(union_sync, start=1):
            t = myThread(sync_func, file, union_sync, semaphore, c)
            t.start()
            if c % 200 == 0:     # 每同步超过200个文件，则休息半小时
                t.join()        # 阻塞
                log.info("已经同步了200个文件了，休息半小时！")
                time.sleep(1800)    # 等待
            # sync_func(file, union_sync, semaphore)


if __name__ == "__main__":
    pass
    # a.sync(
    #     src_path=SRC_PATH,
    #     dst_path_list=DST_PATH_LIST,
    #     auto=True,
    #     thread_max_num=4,
    # )
    # a.upload(r'D:\code\2022\pyprj\pycharm-community-2021.3.2.rar', '/Real/Cloud189-Anime')
    # a.rename('/Local/test/db.sqlite3', "db1.sqlite3")
    # resp = a.getpath("/Local")
    # a.mkdir("/Quark/aa/bb")
    # a.upload(r"Z:\od-acg\OneDrive - soramik\AnimeStorage\Anne Happy\第1季\[10]我们的暑假.mp4", "/Real/Cloud189-Anime")
    # time.sleep(3)
    # a.sync(
    #     src_path="/Real/OneDrive-ACG/",
    #     dst_path_list=[
    #         "/Real/Cloud189-Anime/AnimeStorage",
    #     ],
    #     auto=True,
    #     thread_max_num=4,
    # )
