# -*- coding: UTF-8 -*-
"""
@Project  : SonepDown
@File     : log.py
@Author   : Sorami
@GitHub   : https://github.com/Soramik
"""

import logging
import os
import platform
from datetime import datetime
from logging.handlers import RotatingFileHandler

import colorlog

# 日志设置(只影响终端, 不影响日志文件)
if platform.system() == 'Windows':
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO


class BaseLog:
    cur_path = os.path.dirname(os.path.realpath(__file__))  # 当前项目路径
    if platform.system() == 'Windows':
        log_path = os.path.join(os.path.dirname(cur_path), 'logs')  # log_path为存放日志的路径
    else:
        log_path = "/home/john/logs"  # log_path为存放日志的路径
    try:
        if not os.path.exists(log_path):
            os.mkdir(log_path)  # 若不存在logs文件夹，则自动创建
    except FileNotFoundError:
        log_path = os.path.join(os.path.dirname(cur_path), 'logs')  # log_path为存放日志的路径
        if not os.path.exists(log_path):
            os.mkdir(log_path)  # 若不存在logs文件夹，则自动创建
    log_colors_config = {
        # 终端输出日志颜色配置
        'DEBUG': 'white',
        'INFO': 'cyan',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
    default_formats = {
        # 终端输出格式
        'color_format': '%(log_color)s%(asctime)s[%(name)s][%(filename)s][line:%(lineno)d]-%(levelname)s: %(message)s',
        # 日志输出格式
        'log_format': '%(asctime)s[%(name)s][%(filename)s][line:%(lineno)d]-%(levelname)s: %(message)s'
    }

    def __init__(self):
        self._logger = logging.getLogger()  # 创建日志记录器
        self._logger.setLevel(logging.DEBUG)  # 设置日志记录器记录级别

    @staticmethod
    def _init_logger_handler(log_path):
        """
        创建日志记录器handler，用于收集日志
        :param log_path: 日志文件路径
        :return: 日志记录器
        """
        # 写入文件，如果文件超过1M大小时，切割日志文件，仅保留3个文件
        logger_handler = RotatingFileHandler(filename=log_path, maxBytes=1 * 1024 * 1024, backupCount=3,
                                             encoding='utf-8')
        return logger_handler

    @staticmethod
    def _init_console_handle():
        """创建终端日志记录器handler，用于输出到控制台"""
        console_handle = colorlog.StreamHandler()
        return console_handle

    def _set_log_formatter(self, file_handler, datefmt='%a, %d %b %Y %H:%M:%S'):
        """
        设置日志输出格式-日志文件
        :param file_handler: 日志记录器
        """
        formatter = logging.Formatter(self.default_formats["log_format"], datefmt=datefmt)
        file_handler.setFormatter(formatter)

    def _set_color_formatter(self, console_handle, color_config):
        """
        设置输出格式-控制台
        :param console_handle: 终端日志记录器
        :param color_config: 控制台打印颜色配置信息
        :return:
        """
        formatter = colorlog.ColoredFormatter(self.default_formats["color_format"], log_colors=color_config)
        console_handle.setFormatter(formatter)

    def _set_log_handler(self, logger_handler, level=None):
        """
        设置handler级别并添加到logger收集器
        :param logger_handler: 日志记录器
        :param level: 日志记录器级别
        """
        if level is None:
            level = logging.DEBUG
        logger_handler.setLevel(level=level)
        self._logger.addHandler(logger_handler)

    def _set_color_handle(self, console_handle, level=None):
        """
        设置handler级别并添加到终端logger收集器
        :param console_handle: 终端日志记录器
        :param level: 日志记录器级别
        """
        if level is None:
            level = logging.DEBUG
        console_handle.setLevel(level)
        self._logger.addHandler(console_handle)

    @staticmethod
    def _close_handler(file_handler):
        """
        关闭handler
        :param file_handler: 日志记录器
        """
        file_handler.close()


class MainLog(BaseLog):
    """
    先创建日志记录器（logging.getLogger），然后再设置日志级别（logger.setLevel），
    接着再创建日志文件，也就是日志保存的地方（logging.FileHandler），然后再设置日志格式（logging.Formatter），
    最后再将日志处理程序记录到记录器（addHandler）
    """
    default_formats = {
        # 终端输出格式
        'color_format': '%(log_color)s%(asctime)s[%(name)s][%(filename)s][line:%(lineno)d]-%(levelname)s: %(message)s',
        # 日志输出格式
        'log_format': '%(asctime)s[%(name)s][%(filename)s][line:%(lineno)d]-%(levelname)s: %(message)s'
    }

    def __init__(self, loglevel=None):
        if loglevel is None:
            loglevel = logging.DEBUG
        super().__init__()
        self.__now_time = datetime.now().strftime('%Y-%m-%d')  # 当前日期格式化
        self.__all_log_path = os.path.join(self.log_path, self.__now_time + "-all" + ".log")  # 收集所有日志信息文件
        self.__error_log_path = os.path.join(self.log_path, self.__now_time + "-error" + ".log")  # 收集错误日志信息文件
        self.LOG_LEVEL = loglevel

    def __console(self, level, message):
        """构造日志收集器"""
        # 创建日志文件
        all_logger_handler = self._init_logger_handler(self.__all_log_path)  # 收集所有日志文件
        error_logger_handler = self._init_logger_handler(self.__error_log_path)  # 收集错误日志信息文件
        console_handle = self._init_console_handle()

        # 设置日志文件格式
        self._set_log_formatter(all_logger_handler)
        self._set_log_formatter(error_logger_handler)
        self._set_color_formatter(console_handle, self.log_colors_config)

        self._set_log_handler(all_logger_handler)  # 设置handler级别并添加到logger收集器
        self._set_log_handler(error_logger_handler, level=logging.ERROR)
        self._set_color_handle(console_handle)

        if level == 'info':
            self._logger.info(message)
        elif level == 'debug':
            self._logger.debug(message)
        elif level == 'warning':
            self._logger.warning(message)
        elif level == 'error':
            self._logger.error(message, exc_info=True, stack_info=True)
            # exc_info=True, stack_info=True 用于在日志中记录堆栈信息，方便查看日志进行调试
        elif level == 'critical':
            self._logger.critical(message, exc_info=True, stack_info=True)
            # exc_info=True, stack_info=True 用于在日志中记录堆栈信息，方便查看日志进行调试

        self._logger.removeHandler(all_logger_handler)  # 避免日志输出重复问题
        self._logger.removeHandler(error_logger_handler)
        self._logger.removeHandler(console_handle)

        self._close_handler(all_logger_handler)  # 关闭handler
        self._close_handler(error_logger_handler)

    def debug(self, message):
        self.__console('debug', message)

    def info(self, message):
        self.__console('info', message)

    def warning(self, message):
        self.__console('warning', message)

    def error(self, message):
        self.__console('error', message)

    def critical(self, message):
        self.__console('critical', message)

    def __call__(self):
        """构造日志收集器"""
        # 创建日志文件
        all_logger_handler = self._init_logger_handler(self.__all_log_path)
        error_logger_handler = self._init_logger_handler(self.__error_log_path)
        console_handle = self._init_console_handle()

        # 设置日志格式
        self._set_log_formatter(all_logger_handler)
        self._set_log_formatter(error_logger_handler)
        self._set_color_formatter(console_handle, self.log_colors_config)

        # 设置handler级别并添加到logger收集器
        self._set_log_handler(all_logger_handler, level=logging.DEBUG)
        self._set_log_handler(error_logger_handler, level=logging.ERROR)
        self._set_color_handle(console_handle, level=self.LOG_LEVEL)

        return self._logger


# 主log
main_log_obj = MainLog(LOG_LEVEL)
log = main_log_obj()


if __name__ == '__main__':
    for i in range(2):
        log.info(f"这是日志信息")
        log.debug("这是debug信息")
        log.warning("这是警告信息")
        log.error("这是错误日志信息")
        log.critical("这是严重级别信息")
