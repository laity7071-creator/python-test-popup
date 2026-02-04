#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:48
@文件名: main.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup\main.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""
import sys
import os
from pathlib import Path
# 先初始化日志配置
from utils.log_utils import init_logger

init_logger()

import logging
from ui.main_win import MainWindow
from PyQt6.QtWidgets import QApplication

if __name__ == "__main__":
    logging.info("=" * 50)
    logging.info("开始启动全能运维工具集")
    logging.info(f"运行环境：{'打包模式' if getattr(sys, 'frozen', False) else '调试模式'}")
    logging.info(f"程序路径：{Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent}")

    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { font-family: Microsoft YaHei; }")

    win = MainWindow()
    win.show()

    # 窗口居中
    qr = win.frameGeometry()
    cp = app.primaryScreen().availableGeometry().center()
    qr.moveCenter(cp)
    win.move(qr.topLeft())

    logging.info("工具启动成功")
    sys.exit(app.exec())
