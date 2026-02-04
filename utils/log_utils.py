#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:47
@文件名: log_utils.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup/utils\log_utils.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from config import LOG_CONFIG


def init_logger():
    """初始化日志配置：同时输出到文件和控制台，支持调试/打包模式"""
    # 创建日志文件夹
    log_dir = LOG_CONFIG["LOG_DIR"]
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 日志文件路径
    log_file = os.path.join(log_dir, LOG_CONFIG["LOG_FILENAME"])

    # 配置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))

    # 文件处理器（按大小轮转）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_CONFIG["MAX_LOG_SIZE"],
        backupCount=LOG_CONFIG["BACKUP_COUNT"],
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(log_format, date_format))

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_CONFIG["LOG_LEVEL"])
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 屏蔽不需要的第三方日志
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("PyQt6").setLevel(logging.WARNING)