# -*- coding: UTF-8 -*-
"""
@Project  : sync 
@File     : rclone.py
@Author   : Sorami
@GitHub   : https://github.com/Soramik
"""
import os
import subprocess as sbp
import traceback
from common.log import log
from config import RCLONE_PATH


class RcloneOperation:
    _RCLONE_PATH = None
    _WORKSPACE = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/")
    _SYNC_CACHE_LOG = os.path.abspath(f"{_WORKSPACE}/log.txt")
    _CONFIG_FILE = f"{_WORKSPACE}/config/rclone.conf"

    SYNC_TIPS = "- 表示源上缺少路径，因此仅在目标中 \n" \
                "+ 表示目标上缺少路径，因此仅在源中 \n" \
                "* 意味着路径存在于源和目标中，但二者不同 \n" \
                "! 表示读取源或目标时出错"

    class _Exp:
        """
        RcloneOperation的错误处理类型
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
                except self.BaseError as e:        # 属于Exp类的异常
                    raise self.exp(e)
                except Exception:
                    # 未知异常
                    traceback.print_exc()  # 打印异常
                    raise self.exp
            return wrapper

        class BaseError(Exception):
            """
            基础错误类型
            """
            def __init__(self):
                self.err_msg = ""
                self.err_msg_detail = ""

        class RclonePathError(BaseError):
            def __init__(self, err_msg=None):
                if err_msg is None:
                    err_msg = "未知错误"
                self.err_msg = "Rclone路径出错"
                self.err_msg_detail = err_msg
                Exception.__init__(self, self.err_msg, self.err_msg_detail)

        class InitError(BaseError):
            def __init__(self, err_msg=None):
                if err_msg is None:
                    err_msg = "未知错误"
                self.err_msg = "初始化出错"
                self.err_msg_detail = err_msg
                Exception.__init__(self, self.err_msg, self.err_msg_detail)

        class CheckError(BaseError):
            def __init__(self, err_msg=None):
                if err_msg is None:
                    err_msg = "未知错误"
                self.err_msg = "同步检查出错"
                self.err_msg_detail = err_msg
                Exception.__init__(self, self.err_msg, self.err_msg_detail)

    @_Exp(_Exp.RclonePathError)
    def _setRclonePath(self):
        """
        设置Rclone路径
        :return:
        """
        if not RCLONE_PATH:
            raise self._Exp.InitError("没有设置Rclone路径")
        if RCLONE_PATH == "rclone":
            log.debug("rclone已加入环境变量")
        elif not os.path.exists(RCLONE_PATH):
            raise self._Exp.InitError("Rclone路径设置错误")
        self._RCLONE_PATH = RCLONE_PATH

    @_Exp(_Exp.InitError)
    def __init__(self, transfers=4):
        """
        Rclone操作类初始化
        :param transfers: 最大并行数, 默认为4
        """
        self.transfers = transfers
        self._setRclonePath()

    @_Exp(_Exp.CheckError)
    def check(self, src_path: str, dst_path: str, src=None, dst=None, filter_file=None) -> list:
        """
        检查同步某一文件夹
        :param filter_file: 排除目录文件
        :param src_path: 源目录，同步时不变
        :param dst_path: 目标目录，会根据目标目录增删改等
        :param src: 源存储符，可以是本地盘符，可留空
        :param dst: 目标存储符，可以是本地盘符，可留空
        :return:
        """
        # 设置存储符
        if src is not None:
            src_path = f"{src}:{src_path}"
        if dst is not None:
            dst_path = f"{dst}:{dst_path}"
        # 绝对路径化filter_file
        if filter_file is not None:
            filter_file = os.path.abspath(filter_file)
            check_cmd = f'{self._RCLONE_PATH} check "{src_path}" "{dst_path}" --size-only --combined={self._SYNC_CACHE_LOG} --filter-from="{filter_file}"'
        else:
            check_cmd = f'{self._RCLONE_PATH} check "{src_path}" "{dst_path}" --size-only --combined={self._SYNC_CACHE_LOG}'
        # 检查不同的文件
        try:
            log.info(check_cmd)
            sbp.call(
                check_cmd,
                # stdout=sbp.PIPE, stderr=sbp.PIPE,
                shell=True)
        except Exception as e:
            log.error(e)
            # traceback.print_exc()
            raise self._Exp.CheckError("rclone检查差异性文件时出现错误")

        with open(self._SYNC_CACHE_LOG, 'r', encoding='utf-8') as f:
            ck_msg_str = f.read()
        os.remove(self._SYNC_CACHE_LOG)
        ck_msg_list = ck_msg_str.split("\n")
        diff_file_list = []  # 不同文件信息的列表
        for ck_msg in ck_msg_list:
            if ck_msg == "":
                continue
            if ck_msg[0] != "=":
                diff_file_list.append(ck_msg)
        if not diff_file_list:  # 如果没找到需要同步的文件，则退出
            return []
        return diff_file_list
