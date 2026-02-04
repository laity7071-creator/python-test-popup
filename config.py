#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:48
@文件名: config.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup\config.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""# 全局配置文件
import sys  # 新增：解决未解析sys
import time  # 新增：解决未解析time
from pathlib import Path

# 项目根路径（自动适配调试/打包模式）
if getattr(sys, 'frozen', False):
    # 打包后（exe所在目录）
    BASE_DIR = Path(sys.executable).parent
else:
    # 调试模式（项目根目录）
    BASE_DIR = Path(__file__).parent

# 日志配置
LOG_CONFIG = {
    "LOG_DIR": BASE_DIR / "logs",  # 日志文件夹路径
    "LOG_FILENAME": "ops_tool_{}.log".format(time.strftime("%Y-%m-%d")),  # 按日期命名
    "LOG_LEVEL": "INFO",  # 日志级别：DEBUG/INFO/WARNING/ERROR
    "MAX_LOG_SIZE": 10 * 1024 * 1024,  # 单日志文件最大10MB
    "BACKUP_COUNT": 5  # 保留5个备份日志
}

# 数据库配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "root",
    "port": 3306,
    "db": "tool_platform",
    "charset": "utf8mb4"
}

# 接口请求超时时间（秒）
REQUEST_TIMEOUT = 10

# 样式表路径（如需使用）
QSS_PATH = BASE_DIR / "resources" / "qss" / "style.qss"