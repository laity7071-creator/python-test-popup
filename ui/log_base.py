# -*- coding: utf-8 -*-
# log_base.py - 通用日志父类（所有业务模块继承，实现log_widget核心功能）
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor, QColor

class LogBaseWidget(QWidget):
    # 定义日志信号（可选，子类可复用）
    log_signal = pyqtSignal(str, str)  # 日志内容，日志级别(INFO/ERROR/WARNING/SYSTEM)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 初始化核心日志组件：log_widget（所有子类直接使用）
        self._init_log_widget()
        # 绑定日志信号
        self.log_signal.connect(self.print_log)

    def _init_log_widget(self):
        """初始化日志显示组件：log_widget + 清空按钮（子类直接用self.log_widget）"""
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(0, 10, 0, 0)
        log_layout.setSpacing(8)

        # 日志显示框：核心属性self.log_widget，子类直接引用
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)  # 只读，禁止编辑
        self.log_widget.setFont(QFont("Consolas", 11))  # 等宽字体，适合日志
        self.log_widget.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px;
                background-color: #fdfdfd;
                color: #2c3e50;
                line-height: 1.6;
            }
        """)
        # 设置日志框最小高度
        self.log_widget.setMinimumHeight(300)

        # 日志操作按钮（清空日志）
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.clear_log_btn = QPushButton("🗑️  清空日志")
        self.clear_log_btn.setFixedSize(120, 36)
        self.clear_log_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 4px;
                background-color: #6366f1;
                color: white;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { opacity: 0.9; }
            QPushButton:pressed { opacity: 0.8; }
            QPushButton:disabled {
                background-color: #cbd5e1;
                color: #94a3b8;
            }
        """)
        # 绑定清空日志方法到按钮
        self.clear_log_btn.clicked.connect(self.clear_all_log)
        btn_layout.addWidget(self.clear_log_btn)

        # 组装日志布局
        log_layout.addLayout(btn_layout)
        log_layout.addWidget(self.log_widget)

        # 把日志布局添加到父类的主布局（子类的主布局会自动包含这个日志区）
        self.setLayout(log_layout)

    def print_log(self, content, level="INFO"):
        """通用日志打印方法（子类直接调用：self.log_widget.print_log("内容", "级别")）"""
        # 根据级别设置字体颜色
        color_map = {
            "INFO": QColor(34, 197, 94),    # 绿色
            "ERROR": QColor(239, 68, 68),   # 红色
            "WARNING": QColor(245, 158, 11),# 黄色
            "SYSTEM": QColor(99, 102, 241)  # 紫色
        }
        color = color_map.get(level, QColor(44, 62, 80))  # 默认黑色

        # 移动光标到末尾，避免覆盖原有日志
        self.log_widget.moveCursor(QTextCursor.MoveOperation.End)
        # 设置字体颜色
        self.log_widget.setTextColor(color)
        # 插入日志内容（带时间，可选）
        import time
        log_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.log_widget.insertPlainText(f"[{log_time}] [{level}] {content}\n")
        # 滚动到日志末尾
        self.log_widget.ensureCursorVisible()

    def clear_all_log(self):
        """清空日志方法（绑定到按钮，子类也可直接调用：self.log_widget.clear_all_log()）"""
        self.log_widget.clear()
        self.print_log("日志已清空", "SYSTEM")