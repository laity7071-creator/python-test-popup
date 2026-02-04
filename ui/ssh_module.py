#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:51
@文件名: ssh_module.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup/ui\ssh_module.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""
# -*- coding: utf-8 -*-
# ssh_module.py - SSH远程连接模块（优化版）
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTextEdit, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QFont
import paramiko
from paramiko.ssh_exception import SSHException, NoValidConnectionsError, ChannelException
import time

# 相对导入通用日志类
from .log_base import LogBaseWidget


# ---------------------- 1. 先定义子线程类（必须在SSHModule前面） ----------------------
class SSHCommandThread(QThread):
    output_signal = pyqtSignal(str, str)  # 内容，级别
    finish_signal = pyqtSignal(bool)
    _mutex = QMutex()

    def __init__(self, ssh_client, command):
        super().__init__()
        self.ssh_client = ssh_client
        self.command = command
        self._is_running = True
        self._is_paused = False
        self.cmd_channel = None

    def run(self):
        try:
            if not self.ssh_client or not self.ssh_client.get_transport().is_active():
                self.output_signal.emit("SSH连接已断开，无法执行命令", "ERROR")
                self.finish_signal.emit(False)
                return

            stdin, stdout, stderr = self.ssh_client.exec_command(self.command)
            self.cmd_channel = stdout.channel

            while self._is_running and self.cmd_channel.active:
                while self._is_paused and self._is_running:
                    time.sleep(0.1)
                    continue

                if stdout.channel.recv_ready():
                    line = stdout.readline()
                    if line and line.strip():
                        line = line.strip() if isinstance(line, str) else line.strip().decode('utf-8', errors='ignore')
                        self.output_signal.emit(line, "INFO")

                if stderr.channel.recv_stderr_ready():
                    err_line = stderr.readline()
                    if err_line and err_line.strip():
                        err_line = err_line.strip() if isinstance(err_line, str) else err_line.strip().decode('utf-8',
                                                                                                              errors='ignore')
                        self.output_signal.emit(err_line, "ERROR")

                time.sleep(0.05)

            self.output_signal.emit("命令执行结束/已手动停止", "SYSTEM")

        except Exception as e:
            err_msg = f"命令执行异常：{str(e)}"
            self.output_signal.emit(err_msg, "WARNING")
            logging.error(err_msg, exc_info=True)

        finally:
            try:
                if hasattr(self, 'cmd_channel') and self.cmd_channel:
                    self.cmd_channel.close()
                stdin.close()
                stdout.close()
                stderr.close()
            except:
                pass
            self.finish_signal.emit(self._is_running)

    def stop(self):
        with QMutexLocker(self._mutex):
            self._is_running = False
        if hasattr(self, 'cmd_channel') and self.cmd_channel:
            try:
                self.cmd_channel.close()
                self.output_signal.emit("已强制关闭远程命令通道", "SYSTEM")
                logging.info("已强制关闭远程命令通道")
            except Exception as e:
                logging.error(f"关闭命令通道失败：{e}")

    def pause(self):
        with QMutexLocker(self._mutex):
            self._is_paused = True

    def resume(self):
        with QMutexLocker(self._mutex):
            self._is_paused = False

    @property
    def is_paused(self):
        return self._is_paused


# ---------------------- 2. 再定义主模块类（继承通用日志类） ----------------------
class SSHModule(LogBaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)  # 必须调用父类构造，初始化log_widget
        self.ssh_client = None
        self.cmd_thread = None
        self.cmd_history = []
        self.history_index = -1
        self.DANGER_COMMANDS = ['rm -rf', 'drop database', 'format', 'mkfs']
        self._init_ui()
        logging.info("SSH模块初始化完成")

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. SSH连接配置区
        self._init_ssh_config_area()
        # 2. SSH命令执行区
        self._init_ssh_cmd_area()
        # 3. 通用日志区已由父类LogBaseWidget初始化，无需重复创建

        self._init_btn_status()

    def _init_ssh_config_area(self):
        conn_group = QGroupBox("🖥️ SSH远程连接配置（*为必填）")
        self._set_group_style(conn_group)
        conn_layout = QVBoxLayout(conn_group)
        conn_layout.setContentsMargins(20, 15, 20, 15)
        conn_layout.setSpacing(15)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("*主机IP：", font=QFont("Microsoft YaHei", 12)))
        self.host_input = QLineEdit()
        self._set_line_style(self.host_input)
        self.host_input.setPlaceholderText("请输入远程主机IP，如：192.168.1.100")
        row1.addWidget(self.host_input, stretch=2)
        row1.addWidget(QLabel("*端口：", font=QFont("Microsoft YaHei", 12)))
        self.port_input = QLineEdit()
        self._set_line_style(self.port_input)
        self.port_input.setPlaceholderText("默认22")
        self.port_input.setFixedWidth(100)
        row1.addWidget(self.port_input)
        conn_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("*用户名：", font=QFont("Microsoft YaHei", 12)))
        self.user_input = QLineEdit()
        self._set_line_style(self.user_input)
        self.user_input.setPlaceholderText("请输入SSH用户名，如：root")
        row2.addWidget(self.user_input, stretch=2)
        row2.addWidget(QLabel("*密码：", font=QFont("Microsoft YaHei", 12)))
        self.pwd_input = QLineEdit()
        self._set_line_style(self.pwd_input)
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText("请输入SSH密码")
        row2.addWidget(self.pwd_input, stretch=2)
        conn_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.connect_btn = QPushButton("🔌 连接SSH")
        self.disconnect_btn = QPushButton("❌ 断开SSH")
        self.default_btn = QPushButton("🔄 填充默认配置")
        for btn in [self.connect_btn, self.disconnect_btn, self.default_btn]:
            btn.setFixedSize(120, 36)
            self._set_btn_style(btn)
        row3.addWidget(self.default_btn)
        row3.addWidget(self.connect_btn)
        row3.addWidget(self.disconnect_btn)
        conn_layout.addLayout(row3)

        self.main_layout.addWidget(conn_group)

        self.connect_btn.clicked.connect(self.ssh_connect)
        self.disconnect_btn.clicked.connect(self.ssh_disconnect)
        self.default_btn.clicked.connect(self.fill_default_config)

    def _init_ssh_cmd_area(self):
        cmd_group = QGroupBox("📝 SSH命令执行（支持tail -f/ls/grep等）")
        self._set_group_style(cmd_group)
        cmd_layout = QVBoxLayout(cmd_group)
        cmd_layout.setContentsMargins(20, 15, 20, 15)
        cmd_layout.setSpacing(15)

        self.cmd_input = QLineEdit()
        self._set_line_style(self.cmd_input)
        self.cmd_input.setPlaceholderText("请输入SSH命令，如：tail -f /var/log/messages")
        self.cmd_input.setFont(QFont("Microsoft YaHei", 12))
        cmd_layout.addWidget(self.cmd_input)

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

        tip_label = QLabel("⚠️  禁止执行rm -rf/drop database等高危命令，已做拦截！")
        tip_label.setStyleSheet("color: #ff4d4f; font-size: 12px;")
        cmd_layout.addWidget(tip_label)

        self.main_layout.addWidget(cmd_group)

        self.exec_btn.clicked.connect(self.exec_ssh_cmd)
        self.stop_btn.clicked.connect(self.stop_ssh_cmd)
        self.pause_btn.clicked.connect(self.toggle_pause_cmd)
        self.clear_log_btn.clicked.connect(self.clear_all_log)
        self.cmd_input.returnPressed.connect(self.exec_ssh_cmd)
        self.cmd_input.installEventFilter(self)

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
        group.setMinimumHeight(200)

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
        if "连接" in btn.text():
            btn.setStyleSheet(btn.styleSheet() + "background-color: #10b981;")
        elif "断开" in btn.text() or "停止" in btn.text():
            btn.setStyleSheet(btn.styleSheet() + "background-color: #ef4444;")
        elif "执行" in btn.text():
            btn.setStyleSheet(btn.styleSheet() + "background-color: #3b82f6;")
        elif "暂停" in btn.text():
            btn.setStyleSheet(btn.styleSheet() + "background-color: #f59e0b;")
        else:
            btn.setStyleSheet(btn.styleSheet() + "background-color: #6366f1;")

    def _init_btn_status(self):
        self.disconnect_btn.setEnabled(False)
        self.exec_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.connect_btn.setEnabled(True)
        self.default_btn.setEnabled(True)

    def fill_default_config(self):
        self.host_input.setText("")
        self.port_input.setText("22")
        self.user_input.setText("root")
        self.pwd_input.setText("")
        self.print_log("已填充默认配置：端口22，用户名root", "SYSTEM")

    def ssh_connect(self):
        try:
            host = self.host_input.text().strip()
            port = self.port_input.text().strip() or 22
            user = self.user_input.text().strip()
            pwd = self.pwd_input.text().strip()

            if not all([host, user, pwd]):
                QMessageBox.warning(self, "配置错误", "IP、用户名、密码为必填项！")
                return

            if not str(port).isdigit() or not 1 <= int(port) <= 65535:
                QMessageBox.warning(self, "配置错误", "端口必须是1-65535的数字！")
                return
            port = int(port)

            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.print_log(f"正在连接 {user}@{host}:{port}...", "SYSTEM")

            self.ssh_client.connect(
                hostname=host, port=port, username=user, password=pwd,
                timeout=10, look_for_keys=False, allow_agent=False
            )

            self.print_log(f"SSH连接成功：{user}@{host}:{port}", "INFO")
            self._init_btn_status()
            self.disconnect_btn.setEnabled(True)
            self.exec_btn.setEnabled(True)
            self.connect_btn.setEnabled(False)
            self.cmd_input.setFocus()

        except NoValidConnectionsError:
            self.print_log("连接失败：主机不可达/端口未开/SSH服务未启动", "ERROR")
        except SSHException as e:
            if "Authentication failed" in str(e):
                self.print_log("连接失败：用户名/密码错误", "ERROR")
            else:
                self.print_log(f"SSH异常：{str(e)}", "ERROR")
        except Exception as e:
            self.print_log(f"连接失败：{str(e)}", "ERROR")
            logging.error(f"SSH连接失败：{e}", exc_info=True)

    def ssh_disconnect(self):
        if self.cmd_thread and self.cmd_thread.isRunning():
            self.stop_ssh_cmd()

        if self.ssh_client and self.ssh_client.get_transport().is_active():
            self.ssh_client.close()
            self.print_log("SSH已安全断开", "SYSTEM")
            logging.info("SSH已安全断开")

        self._init_btn_status()
        self.connect_btn.setEnabled(True)

    def _check_danger_cmd(self, cmd):
        cmd_lower = cmd.strip().lower()
        for danger_cmd in self.DANGER_COMMANDS:
            if danger_cmd in cmd_lower:
                return True, danger_cmd
        return False, None

    def exec_ssh_cmd(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            QMessageBox.warning(self, "命令错误", "执行命令不能为空！")
            return

        is_danger, danger_cmd = self._check_danger_cmd(cmd)
        if is_danger:
            QMessageBox.warning(self, "高危命令拦截", f"禁止执行高危命令「{danger_cmd}」，避免数据丢失！")
            logging.warning(f"用户尝试执行高危命令：{cmd}")
            return

        # 记录命令历史
        if cmd not in self.cmd_history:
            self.cmd_history.append(cmd)
            if len(self.cmd_history) > 50:
                self.cmd_history.pop(0)
        self.history_index = -1

        # 停止已有命令
        if self.cmd_thread and self.cmd_thread.isRunning():
            self.stop_ssh_cmd()

        # 启动命令线程
        self.cmd_thread = SSHCommandThread(self.ssh_client, cmd)
        self.cmd_thread.output_signal.connect(self.print_log)
        self.cmd_thread.finish_signal.connect(self._cmd_finish)
        self.cmd_thread.start()

        self.exec_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.print_log(f"开始执行命令：{cmd}", "SYSTEM")

    def stop_ssh_cmd(self):
        if self.cmd_thread and self.cmd_thread.isRunning():
            self.cmd_thread.stop()
            self.cmd_thread.wait(1000)
            self._cmd_finish(False)

    def toggle_pause_cmd(self):
        if not self.cmd_thread or not self.cmd_thread.isRunning():
            return

        if self.cmd_thread.is_paused:
            self.cmd_thread.resume()
            self.pause_btn.setText("⏸️  暂停输出")
            self.print_log("恢复日志输出", "SYSTEM")
        else:
            self.cmd_thread.pause()
            self.pause_btn.setText("▶️  继续输出")
            self.print_log("暂停日志输出", "SYSTEM")

    def _cmd_finish(self, is_normal):
        if is_normal:
            self.print_log("命令执行完成，无异常", "SYSTEM")
        else:
            self.print_log("命令执行被中断（停止/断连）", "SYSTEM")

        self.exec_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸️  暂停输出")
        self.cmd_thread = None

    def eventFilter(self, obj, event):
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
