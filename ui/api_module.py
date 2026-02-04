#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:53
@文件名: api_module.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup/ui\api_module.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""
# api_module.py - Python3.8+PyQt6 兼容，API请求模块（支持GET/POST，Form/JSON/请求头/URL参数）
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QMessageBox, QComboBox, QTextEdit, QTabWidget,
    QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QFont
import requests
import json
import time
import traceback

# 相对导入通用日志类
from .log_base import LogBaseWidget

# 关闭requests SSL警告
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# ---------------------- API请求子线程 ----------------------
class APIRequestThread(QThread):
    output_signal = pyqtSignal(str, str)
    finish_signal = pyqtSignal(bool)
    _mutex = QMutex()

    def __init__(self, method, url, headers, params, data_type, data, timeout=30, verify_ssl=False):
        super().__init__()
        self.method = method
        self.url = url
        self.headers = headers if headers else {}
        self.params = params if params else {}
        self.data_type = data_type
        self.data = data if data else {}
        self.timeout = int(timeout) if timeout else 30
        self.verify_ssl = verify_ssl
        self._is_running = True
        self._is_paused = False

    def run(self):
        logging.info(f"开始{self.method}请求：{self.url}")
        logging.info(f"请求参数：{self.params}，请求体：{self.data}，请求头：{self.headers}")
        try:
            if not self.url.startswith(("http://", "https://")):
                self.output_signal.emit("请求URL格式错误，必须以http://或https://开头", "ERROR")
                self.finish_signal.emit(False)
                return

            self.output_signal.emit(f"开始{self.method}请求：{self.url}", level="SYSTEM")
            self.output_signal.emit(f"超时时间：{self.timeout}秒 | SSL验证：{self.verify_ssl}", level="SYSTEM")
            start_time = time.time()

            # 输出请求信息（格式化）
            if self.headers:
                self.output_signal.emit("📌 请求头：", level="INFO")
                for k, v in self.headers.items():
                    self.output_signal.emit(f"  {k}: {v}", level="INFO")
            if self.params:
                self.output_signal.emit("📌 URL参数：", level="INFO")
                for k, v in self.params.items():
                    self.output_signal.emit(f"  {k}: {v}", level="INFO")
            if self.data:
                self.output_signal.emit(f"📌 {self.data_type}请求体：", level="INFO")
                self.output_signal.emit(json.dumps(self.data, ensure_ascii=False, indent=2), level="INFO")

            # 发送核心请求
            response = None
            if self.method == "GET":
                response = requests.get(
                    url=self.url, params=self.params, headers=self.headers,
                    timeout=self.timeout, verify=self.verify_ssl
                )
            elif self.method == "POST":
                if self.data_type == "Form":
                    self.headers.setdefault("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
                    response = requests.post(
                        url=self.url, params=self.params, headers=self.headers, data=self.data,
                        timeout=self.timeout, verify=self.verify_ssl
                    )
                else:  # JSON
                    self.headers.setdefault("Content-Type", "application/json;charset=utf-8")
                    response = requests.post(
                        url=self.url, params=self.params, headers=self.headers, json=self.data,
                        timeout=self.timeout, verify=self.verify_ssl
                    )

            # 处理响应结果
            cost_time = round(time.time() - start_time, 3)
            self.output_signal.emit(f"✅ 请求完成 | 耗时：{cost_time}秒 | 状态码：{response.status_code}", level="INFO")
            logging.info(f"API请求完成：状态码{response.status_code}，耗时{cost_time}秒")

            self.output_signal.emit("📌 响应头：", level="INFO")
            for k, v in response.headers.items():
                self.output_signal.emit(f"  {k}: {v}", level="INFO")

            # 格式化响应体（兼容JSON/文本，分段输出避免卡顿）
            self.output_signal.emit("📌 响应体（格式化）：", level="INFO")
            try:
                resp_json = response.json()
                resp_str = json.dumps(resp_json, ensure_ascii=False, indent=2)
                logging.info(f"API响应体（JSON）：{resp_str[:1000]}...")
            except:
                resp_str = response.text if len(
                    response.text) <= 5000 else f"{response.text[:5000]}...[响应体过长，仅显示前5000字符]"
                logging.info(f"API响应体（文本）：{resp_str[:1000]}...")

            # 分段输出响应体
            for line in resp_str.split("\n"):
                while self._is_paused and self._is_running:
                    time.sleep(0.1)
                    continue
                if not self._is_running:
                    break
                self.output_signal.emit(line.strip(), level="INFO")

        except Exception as e:
            err_info = f"❌ 请求异常：{str(e)}\n{traceback.format_exc()[:600]}"
            self.output_signal.emit(err_info, "ERROR")
            logging.error(f"API请求异常：{err_info}", exc_info=True)
        finally:
            self.finish_signal.emit(self._is_running)

    def stop(self):
        """强制停止请求"""
        with QMutexLocker(self._mutex):
            self._is_running = False
        self.output_signal.emit("🔴 已强制停止API请求", "SYSTEM")
        logging.warning("已强制停止API请求")

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


# ---------------------- API主模块（继承通用日志类） ----------------------
class APIModule(LogBaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)  # 初始化父类日志组件
        self.request_thread = None
        self._init_ui()
        logging.info("API模块初始化完成")

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. API基础配置区（请求方式/URL/超时/SSL）
        self._init_api_base_config()
        # 2. API参数配置区（标签页：请求头/URL参数/请求体）
        self._init_api_param_area()
        # 3. 通用日志区已由父类LogBaseWidget初始化

        # 初始化按钮状态
        self._init_btn_status()

    def _init_api_base_config(self):
        """API基础配置：请求方式/URL/超时时间/SSL验证 + 操作按钮"""
        base_group = QGroupBox("🌐 API基础请求配置（*为必填）")
        self._set_group_style(base_group)
        base_layout = QVBoxLayout(base_group)
        base_layout.setContentsMargins(20, 15, 20, 15)
        base_layout.setSpacing(15)

        # 行1：请求方式 + 目标URL
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("*请求方式：", font=QFont("Microsoft YaHei", 12)))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST"])
        self.method_combo.setFixedWidth(80)
        self._set_combo_style(self.method_combo)
        row1.addWidget(self.method_combo)
        row1.addWidget(QLabel("*请求URL：", font=QFont("Microsoft YaHei", 12)))
        self.url_input = QLineEdit()
        self._set_line_style(self.url_input)
        self.url_input.setPlaceholderText("请输入完整URL，如：http://127.0.0.1:8080/api/test 或 https://www.xxx.com/api")
        row1.addWidget(self.url_input, stretch=1)
        base_layout.addLayout(row1)

        # 行2：超时时间 + SSL验证复选框
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("超时时间（秒）：", font=QFont("Microsoft YaHei", 12)))
        self.timeout_input = QLineEdit()
        self._set_line_style(self.timeout_input)
        self.timeout_input.setPlaceholderText("默认30秒")
        self.timeout_input.setFixedWidth(100)
        self.timeout_input.setText("30")
        row2.addWidget(self.timeout_input)
        self.ssl_check = QCheckBox("启用SSL证书验证（默认关闭，忽略不安全警告）")
        self.ssl_check.setFont(QFont("Microsoft YaHei", 11))
        self.ssl_check.setStyleSheet("QCheckBox { color: #2c3e50; }")
        row2.addWidget(self.ssl_check)
        row2.addStretch(1)
        base_layout.addLayout(row2)

        # 行3：操作按钮（发送/停止/暂停/清空日志）
        row3 = QHBoxLayout()
        self.send_btn = QPushButton("⚡ 发送请求")
        self.stop_btn = QPushButton("🔴 停止请求")
        self.pause_btn = QPushButton("⏸️  暂停输出")
        self.clear_log_btn = QPushButton("🗑️  清空日志")
        btn_list = [self.send_btn, self.stop_btn, self.pause_btn, self.clear_log_btn]
        for btn in btn_list:
            btn.setFixedSize(120, 36)
            self._set_btn_style(btn)
        row3.addWidget(self.send_btn)
        row3.addWidget(self.stop_btn)
        row3.addWidget(self.pause_btn)
        row3.addWidget(self.clear_log_btn)
        row3.addStretch(1)
        base_layout.addLayout(row3)

        self.main_layout.addWidget(base_group)

        # 绑定基础信号
        self.send_btn.clicked.connect(self.send_api_request)
        self.stop_btn.clicked.connect(self.stop_api_request)
        self.pause_btn.clicked.connect(self.toggle_pause_output)
        self.clear_log_btn.clicked.connect(self.clear_all_log)

    def _init_api_param_area(self):
        """API参数配置：标签页（请求头/URL参数/请求体）+ 请求体类型选择"""
        param_group = QGroupBox("📋 API请求参数配置（JSON格式，键值对）")
        self._set_group_style(param_group)
        param_layout = QVBoxLayout(param_group)
        param_layout.setContentsMargins(20, 15, 20, 15)
        param_layout.setSpacing(15)

        # 行1：请求体类型（Form/JSON）- 仅POST生效
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["JSON", "Form"])
        self.data_type_combo.setFixedWidth(100)
        self._set_combo_style(self.data_type_combo)
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("请求体类型（POST）：", font=QFont("Microsoft YaHei", 12)))
        type_layout.addWidget(self.data_type_combo)
        type_layout.addStretch(1)
        type_layout.addWidget(
            QLabel("提示：所有参数均为JSON格式，空则留{}", font=QFont("Microsoft YaHei", 10, QFont.Weight.Light)))
        type_layout.labelWidget().setStyleSheet("color: #64748b;")
        param_layout.addLayout(type_layout)

        # 标签页：请求头 / URL参数 / 请求体
        self.param_tab = QTabWidget()
        self.param_tab.setStyleSheet("""
            QTabWidget { font-size: 12px; }
            QTabBar::tab { padding: 6px 20px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #e2e8f0; border-radius: 4px 4px 0 0; }
        """)

        # 标签1：请求头（JSON）
        self.header_edit = QTextEdit()
        self._set_textedit_style(self.header_edit)
        self.header_edit.setPlaceholderText('{"Content-Type":"application/json;charset=utf-8", "Token":"your_token"}')
        self.header_edit.setText("{}")
        self.param_tab.addTab(self.header_edit, "请求头")

        # 标签2：URL参数（JSON）- GET/POST均生效
        self.param_edit = QTextEdit()
        self._set_textedit_style(self.param_edit)
        self.param_edit.setPlaceholderText('{"page":1, "size":10, "keyword":"test"}')
        self.param_edit.setText("{}")
        self.param_tab.addTab(self.param_edit, "URL参数")

        # 标签3：请求体（JSON）- 仅POST生效
        self.body_edit = QTextEdit()
        self._set_textedit_style(self.body_edit)
        self.body_edit.setPlaceholderText('{"name":"test", "age":20, "data":[1,2,3]}')
        self.body_edit.setText("{}")
        self.param_tab.addTab(self.body_edit, "请求体")

        param_layout.addWidget(self.param_tab, stretch=1)
        self.main_layout.addWidget(param_group)

    # ---------------------- 样式封装（和SSH/DB等模块完全统一） ----------------------
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
        group.setMinimumHeight(180)

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

    def _set_combo_style(self, combo):
        combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #e2e8f0; border-radius: 4px;
                padding: 0 12px; height: 36px; font-size: 12px;
                background-color: #ffffff;
            }
            QComboBox:focus {
                border-color: #3b82f6; outline: none;
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
            }
        """)
        combo.setFixedHeight(36)

    def _set_textedit_style(self, edit):
        edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e2e8f0; border-radius: 4px;
                padding: 8px; font-size: 12px; line-height: 1.6;
                background-color: #ffffff; font-family: Consolas;
            }
            QTextEdit:focus {
                border-color: #3b82f6; outline: none;
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
            }
        """)
        edit.setFont(QFont("Consolas", 12))

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
        if "发送" in btn.text():
            btn.setStyleSheet(btn.styleSheet() + "background-color: #3b82f6;")
        elif "停止" in btn.text():
            btn.setStyleSheet(btn.styleSheet() + "background-color: #ef4444;")
        elif "暂停" in btn.text():
            btn.setStyleSheet(btn.styleSheet() + "background-color: #f59e0b;")
        else:
            btn.setStyleSheet(btn.styleSheet() + "background-color: #6366f1;")

    # ---------------------- 核心功能实现（和其他模块逻辑一致） ----------------------
    def _init_btn_status(self):
        """初始化按钮状态：仅发送/清空日志可用"""
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.send_btn.setEnabled(True)
        self.clear_log_btn.setEnabled(True)

    def _parse_json(self, text, tip):
        """通用JSON解析方法，带异常处理"""
        try:
            if not text.strip():
                return {}
            return json.loads(text.strip())
        except Exception as e:
            err_msg = f"{tip}JSON格式解析失败：{str(e)}"
            self.print_log(err_msg, level="ERROR")
            logging.error(err_msg)
            QMessageBox.warning(self, "格式错误", f"{tip}必须为合法JSON格式！\n{e}")
            return None

    def send_api_request(self):
        """发送API请求：解析参数+校验+启动子线程"""
        # 1. 基础参数获取
        method = self.method_combo.currentText()
        url = self.url_input.text().strip()
        timeout = self.timeout_input.text().strip() or 30
        verify_ssl = self.ssl_check.isChecked()
        data_type = self.data_type_combo.currentText()

        # 2. 基础校验
        if not url:
            QMessageBox.warning(self, "参数错误", "请求URL不能为空！")
            return
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "参数错误", "请求URL必须以http://或https://开头！")
            return

        # 3. 解析JSON参数（请求头/URL参数/请求体）
        headers = self._parse_json(self.header_edit.toPlainText(), "请求头")
        params = self._parse_json(self.param_edit.toPlainText(), "URL参数")
        body = self._parse_json(self.body_edit.toPlainText(), "请求体")
        if any(x is None for x in [headers, params, body]):
            return

        # 4. POST请求体空值处理
        if method == "POST" and not body:
            self.print_log("⚠️  POST请求体为空，将发送空数据", level="WARNING")
            logging.warning("POST请求体为空，将发送空数据")

        # 5. 停止已有请求
        if self.request_thread and self.request_thread.isRunning():
            self.stop_api_request()

        # 6. 启动请求线程
        self.request_thread = APIRequestThread(
            method=method, url=url, headers=headers, params=params,
            data_type=data_type, data=body, timeout=timeout, verify_ssl=verify_ssl
        )
        self.request_thread.output_signal.connect(self.print_log)
        self.request_thread.finish_signal.connect(self._request_finish)
        self.request_thread.start()

        # 7. 更新按钮状态
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.print_log(f"🚀 已启动{method}请求，目标URL：{url}", level="SYSTEM")

    def stop_api_request(self):
        """强制停止API请求"""
        if self.request_thread and self.request_thread.isRunning():
            self.request_thread.stop()
            self.request_thread.wait(1000)
            self._request_finish(False)

    def toggle_pause_output(self):
        """暂停/恢复日志输出"""
        if not self.request_thread or not self.request_thread.isRunning():
            self.print_log("⚠️  无正在执行的请求，无法暂停", level="WARNING")
            return

        if self.request_thread.is_paused:
            self.request_thread.resume()
            self.pause_btn.setText("⏸️  暂停输出")
            self.print_log("🟢 已恢复响应结果输出", level="SYSTEM")
        else:
            self.request_thread.pause()
            self.pause_btn.setText("▶️  继续输出")
            self.print_log("🟡 已暂停响应结果输出", level="SYSTEM")

        def _request_finish(self, is_normal):
            """请求完成回调：恢复按钮状态"""
            if is_normal:
                self.print_log("✅ API请求流程执行完成", level="SYSTEM")
                logging.info("API请求流程执行完成")
            else:
                self.print_log("🔴 API请求被中断/执行异常", level="WARNING")
                logging.warning("API请求被中断/执行异常")

            self.send_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸️  暂停输出")
            self.request_thread = None

    if __name__ == "__main__":
        import sys
        from PyQt6.QtWidgets import QApplication, QMainWindow
        # 初始化日志
        from utils.log_utils import init_logger
        init_logger()

        app = QApplication(sys.argv)
        win = QMainWindow()
        win.setWindowTitle("API请求模块 - 优化版")
        win.setGeometry(100, 100, 1600, 900)
        win.setCentralWidget(APIModule())  # 保持不变，新增下面2行
        # 解决PyCharm未解析提示（实际运行不影响，仅IDE提示）
        from __main__ import APIModule
        win.setCentralWidget(APIModule())
        win.show()
        sys.exit(app.exec())