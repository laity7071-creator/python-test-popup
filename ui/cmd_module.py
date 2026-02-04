#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:52
@文件名: cmd_module.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup/ui\cmd_module.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""
# cmd_module.py - Python3.8+PyQt6 兼容，CMD模块（本地执行CMD命令）
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QFont
import subprocess
import sys
import time

# 相对导入通用日志类
from .log_base import LogBaseWidget


# ---------------------- CMD命令执行子线程 ----------------------
class CMDCommandThread(QThread):
    output_signal = pyqtSignal(str, str)
    finish_signal = pyqtSignal(bool)
    _mutex = QMutex()

    def __init__(self, command):
        super().__init__()
        self.command = command
        self._is_running = True
        self._is_paused = False
        self.process = None

    def run(self):
        logging.info(f"开始执行CMD命令：{self.command}")
        try:
            # Windows CMD执行，处理GBK编码（避免中文乱码）
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.process = subprocess.Popen(
                ["cmd", "/c", self.command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                encoding='gbk',
                errors='ignore'
            )

            # 实时读取输出
            while self._is_running and self.process.poll() is None:
                while self._is_paused and self._is_running:
                    time.sleep(0.1)
                    continue

                # 读取标准输出
                if self.process.stdout.readable():
                    line = self.process.stdout.readline()
                    if line and line.strip():
                        self.output_signal.emit(line.strip(), "INFO")

                # 读取标准错误
                if self.process.stderr.readable():
                    err_line = self.process.stderr.readline()
                    if err_line and err_line.strip():
                        self.output_signal.emit(err_line.strip(), "ERROR")

                time.sleep(0.05)

            # 检查退出码
            exit_code = self.process.poll() if self.process else -1
            if exit_code == 0 and self._is_running:
                self.output_signal.emit(f"命令执行完成，退出码：{exit_code}", "SYSTEM")
                logging.info(f"CMD命令执行完成，退出码：{exit_code}")
            else:
                self.output_signal.emit(f"命令执行结束/异常，退出码：{exit_code}", "WARNING")
                logging.warning(f"CMD命令执行异常，退出码：{exit_code}")

        except Exception as e:
            err_msg = f"命令执行异常：{str(e)}"
            self.output_signal.emit(err_msg, "ERROR")
            logging.error(f"CMD命令执行异常：{err_msg}", exc_info=True)

        finally:
            self.finish_signal.emit(self._is_running and (self.process.poll() == 0 if self.process else False))

    def stop(self):
        """停止命令"""
        with QMutexLocker(self._mutex):
            self._is_running = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(1)
                self.output_signal.emit("已强制终止CMD进程", "SYSTEM")
                logging.info("已强制终止CMD进程")
            except Exception as e:
                self.process.kill()
                logging.error(f"终止CMD进程失败：{e}")

    def pause(self):
        """暂停输出"""
        with QMutexLocker(self._mutex):
            self._is_paused = True

    def resume(self):
        """恢复输出"""
        with QMutexLocker(self._mutex):
            self._is_paused = False

    @property
    def is_paused(self):
        return self._is_paused


# ---------------------- CMD主模块 ----------------------
class CMDModule(LogBaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)  # 初始化父类日志组件
        self.cmd_thread = None
        self.cmd_history = []
        self.history_index = -1
        self._init_ui()
        logging.info("CMD模块初始化完成")

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. CMD命令执行区
        self._init_cmd_area()
        # 2. 通用日志区已由父类LogBaseWidget初始化

        # 初始化按钮状态
        self._init_btn_status()

    def _init_cmd_area(self):
        """CMD命令执行区"""
        cmd_group = QGroupBox("📝 CMD命令执行（本地，支持所有CMD命令）")
        self._set_group_style(cmd_group)
        cmd_layout = QVBoxLayout(cmd_group)
        cmd_layout.setContentsMargins(20, 15, 20, 15)
        cmd_layout.setSpacing(15)

        # 命令输入框
        self.cmd_input = QLineEdit()
        self._set_line_style(self.cmd_input)
        self.cmd_input.setPlaceholderText("请输入CMD命令，如：dir 或 ipconfig /all 或 ping 127.0.0.1")
        self.cmd_input.setFont(QFont("Microsoft YaHei", 12))
        cmd_layout.addWidget(self.cmd_input)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.exec_btn = QPushButton("⚡ 执行命令")
        self.stop_btn = QPushButton("🔴 停止命令")
        self.pause_btn = QPushButton("⏸️  暂停输出")
        self.clear_log_btn = QPushButton("🗑️  清空日志")
        btn_list = [self.exec_btn, self.stop_btn, self.pause_btn, self.clear_log_btn]
        for btn in btn_list:
            btn.setFixedSize(120, 36)
            self._set_btn_style(btn)
        btn_layout.addWidget(self.exec_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.clear_log_btn)
        cmd_layout.addLayout(btn_layout)

        # 提示
        tip_label = QLabel("ℹ️  本地执行CMD命令，自动处理GBK中文乱码，支持实时输出！")
        tip_label.setStyleSheet("color: #3b82f6; font-size: 12px;")
        cmd_layout.addWidget(tip_label)

        self.main_layout.addWidget(cmd_group)

        # 绑定信号
        self.exec_btn.clicked.connect(self.exec_cmd)
        self.stop_btn.clicked.connect(self.stop_cmd)
        self.pause_btn.clicked.connect(self.toggle_pause_cmd)
        self.clear_log_btn.clicked.connect(self.clear_all_log)
        self.cmd_input.returnPressed.connect(self.exec_cmd)
        self.cmd_input.installEventFilter(self)

    # ---------------------- 样式封装 ----------------------
    def _set_group_style(self, group):
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px; font-weight: 600; color: #2c3e50;
                border: 1px solid #e2e8f0; border-radius: 6px;
                margin-top: 8px; padding-top: 5px;
                background-color: #f8fafc;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 10px; }
        """)
        group.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        group.setMinimumHeight(150)

    def _set_line_style(self, line):
        line.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e2e8f0; border-radius: 4px;
                padding: 0 12px; height: 36px; font-size: 12px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #3b82f6; outline: none;
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
            }
        """)
        line.setFixedHeight(36)

    def _set_btn_style(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                border: none; border-radius: 4px;
                font-size: 12px; font-weight: 600;
                color: #ffffff;
            }
            QPushButton:hover { opacity: 0.9; }
            QPushButton:pressed { opacity: 0.8; }
            QPushButton:disabled {
                background-color: #cbd5e1;
                color: #94a3b8;
            }
        """)
        if "执行" in btn.text():
            btn.setStyleSheet(btn.styleSheet() + "background-color: #3b82f6;")
        elif "停止" in btn.text():
            btn.setStyleSheet(btn.styleSheet() + "background-color: #ef4444;")
        elif "暂停" in btn.text():
            btn.setStyleSheet(btn.styleSheet() + "background-color: #f59e0b;")
        else:
            btn.setStyleSheet(btn.styleSheet() + "background-color: #6366f1;")

    # ---------------------- 核心功能 ----------------------
    def _init_btn_status(self):
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.exec_btn.setEnabled(True)

    def exec_cmd(self):
        """执行CMD命令"""
        cmd = self.cmd_input.text().strip()
        if not cmd:
            QMessageBox.warning(self, "命令错误", "执行命令不能为空！")
            return

        # 记录历史
        if cmd not in self.cmd_history:
            self.cmd_history.append(cmd)
            if len(self.cmd_history) > 50:
                self.cmd_history.pop(0)
        self.history_index = -1

        # 停止已有命令
        if self.cmd_thread and self.cmd_thread.isRunning():
            self.stop_cmd()

        # 启动线程
        self.cmd_thread = CMDCommandThread(cmd)
        self.cmd_thread.output_signal.connect(self.print_log)
        self.cmd_thread.finish_signal.connect(self._cmd_finish)
        self.cmd_thread.start()

        # 更新按钮
        self.exec_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.print_log(f"开始执行CMD命令：{cmd}", level="SYSTEM")

    def stop_cmd(self):
        """停止命令"""
        if self.cmd_thread and self.cmd_thread.isRunning():
            self.cmd_thread.stop()
            self.cmd_thread.wait(1000)
            self._cmd_finish(False)

    def toggle_pause_cmd(self):
        """暂停/恢复"""
        if not self.cmd_thread or not self.cmd_thread.isRunning():
            self.print_log("⚠️  无正在执行的请求，无法暂停", level="WARNING")
            return

        if self.cmd_thread.is_paused:
            self.cmd_thread.resume()
            self.pause_btn.setText("⏸️  暂停输出")
            self.print_log("🟢 已恢复响应结果输出", level="SYSTEM")
        else:
            self.cmd_thread.pause()
            self.pause_btn.setText("▶️  继续输出")
            self.print_log("🟡 已暂停响应结果输出", level="SYSTEM")

    def _cmd_finish(self, is_normal):
        """命令完成"""
        if is_normal:
            self.print_log("CMD命令执行完成，无异常", level="SYSTEM")
            logging.info("CMD命令执行完成")
        else:
            self.print_log("CMD命令执行被中断/异常", level="WARNING")
            logging.warning("CMD命令执行被中断/异常")

        self.exec_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸️  暂停输出")
        self.cmd_thread = None

    def eventFilter(self, obj, event):
        """上下键历史"""
        if obj == self.cmd_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                if self.cmd_history and self.history_index < len(self.cmd_history) - 1:
                    self.history_index += 1
                    self.cmd_input.setText(self.cmd_history[-(self.history_index + 1)])
                    self.cmd_input.setCursorPosition(len(self.cmd_input.text()))
                return True
            elif event.key() == Qt.Key.Key_Down:
                if self.cmd_history and self.history_index >= 0:
                    self.history_index -= 1
                    if self.history_index < 0:
                        self.cmd_input.clear()
                    else:
                        self.cmd_input.setText(self.cmd_history[-(self.history_index + 1)])
                        self.cmd_input.setCursorPosition(len(self.cmd_input.text()))
                return True
        return super().eventFilter(obj, event)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow
    # 初始化日志
    from utils.log_utils import init_logger

    init_logger()

    app = QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle("CMD模块 - 优化版")
    win.setGeometry(100, 100, 1600, 900)
    win.setCentralWidget(CMDModule())
    win.show()
    sys.exit(app.exec())