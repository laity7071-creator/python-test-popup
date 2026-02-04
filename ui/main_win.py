#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:51
@文件名: main_win.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup/ui\main_win.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""
# main_win.py - 主窗口（整合所有模块）- Python3.8+PyQt6 兼容
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
import sys

# 导入所有模块
from .ssh_module import SSHModule
from .ps1_module import PS1Module
from .cmd_module import CMDModule
from .db_module import DBModule
from .api_module import APIModule


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._init_main_ui()
        logging.info("主窗口初始化完成")

    def _init_main_ui(self):
        """初始化主窗口：标签页整合所有模块"""
        # 窗口基础配置
        self.setWindowTitle("全能运维工具集 - SSH/PS1/CMD/DB/API（Python3.8+PyQt6）")
        self.setGeometry(50, 50, 1600, 900)  # 初始大小：宽1600，高900
        self.setMinimumSize(1200, 800)  # 最小窗口大小，避免挤压

        # 中心部件 + 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 标签页：整合SSH/PS1/CMD/DB/API
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget { font-size: 14px; }
            QTabBar { font-family: Microsoft YaHei; font-size: 14px; height: 40px; }
            QTabBar::tab { 
                padding: 0 30px; margin: 0 2px; 
                border-radius: 6px 6px 0 0; 
            }
            QTabBar::tab:selected { 
                background-color: #ffffff; 
                border: 1px solid #e2e8f0; 
                border-bottom: none;
                color: #3b82f6; font-weight: 600;
            }
            QTabBar::tab:!selected { 
                background-color: #f8fafc; 
                color: #64748b;
            }
            QTabWidget::pane { 
                border: 1px solid #e2e8f0; 
                border-radius: 0 6px 6px 6px;
                background-color: #ffffff;
            }
        """)
        # 设置标签页可关闭（可选，右键也可关闭）
        self.tab_widget.setTabsClosable(False)
        # 标签页切换方式：鼠标点击/滚轮
        self.tab_widget.setMouseTracking(True)

        # 添加所有模块到标签页
        self.tab_widget.addTab(SSHModule(), "🖥️ SSH远程连接")
        self.tab_widget.addTab(PS1Module(), "⚙️ PowerShell")
        self.tab_widget.addTab(CMDModule(), "🖨️ CMD命令")
        self.tab_widget.addTab(DBModule(), "🗄️ 数据库操作")
        self.tab_widget.addTab(APIModule(), "🌐 API请求")

        # 加入主布局
        main_layout.addWidget(self.tab_widget)

        # 全局字体：统一为微软雅黑，避免乱码
        app.setFont(QFont("Microsoft YaHei", 12))
