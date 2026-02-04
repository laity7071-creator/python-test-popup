#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:53
@文件名: db_module.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup/ui\db_module.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""
# db_module.py - Python3.8+PyQt6 兼容，数据库模块（支持MySQL/PG/SQLite）
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QMessageBox, QComboBox, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QFont
import time

# 相对导入通用日志类
from .log_base import LogBaseWidget

# 动态导入数据库驱动（使用前需安装：pip install pymysql psycopg2-binary sqlite3）
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError as e:
    logging.warning(f"MySQL驱动导入失败：{e}，MySQL功能不可用")
try:
    import psycopg2
except ImportError as e:
    logging.warning(f"PostgreSQL驱动导入失败：{e}，PostgreSQL功能不可用")
import sqlite3
import traceback


# ---------------------- 数据库查询子线程 ----------------------
class DBQueryThread(QThread):
    output_signal = pyqtSignal(str, str)
    finish_signal = pyqtSignal(bool)
    _mutex = QMutex()

    def __init__(self, db_type, conn, sql):
        super().__init__()
        self.db_type = db_type
        self.conn = conn
        self.sql = sql
        self._is_running = True
        self._is_paused = False
        self.cursor = None

    def run(self):
        logging.info(f"开始执行{self.db_type}SQL：{self.sql[:100]}...")
        try:
            if not self.conn or (hasattr(self.conn, 'closed') and self.conn.closed):
                self.output_signal.emit("数据库连接已断开，无法执行查询", "ERROR")
                self.finish_signal.emit(False)
                return

            self.cursor = self.conn.cursor()
            self.output_signal.emit(
                f"开始执行SQL语句：{self.sql[:100]}..." if len(self.sql) > 100 else f"开始执行SQL语句：{self.sql}",
                level="SYSTEM"
            )
            start_time = time.time()

            # 执行SQL
            self.cursor.execute(self.sql)
            self.conn.commit()

            # 获取结果（查询语句返回结果，增删改返回影响行数）
            if self.sql.strip().upper().startswith(("SELECT", "SHOW", "DESC", "EXPLAIN")):
                results = self.cursor.fetchall()
                fields = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
                # 输出字段
                self.output_signal.emit(f"查询结果字段：{', '.join(fields)}", level="INFO")
                # 输出结果行数
                self.output_signal.emit(f"查询结果共 {len(results)} 行", level="INFO")
                logging.info(f"{self.db_type}SQL查询成功，返回{len(results)}行数据")
                # 输出前50行（避免大数据量卡顿）
                show_rows = min(50, len(results))
                for i in range(show_rows):
                    while self._is_paused and self._is_running:
                        time.sleep(0.1)
                        continue
                    if not self._is_running:
                        break
                    self.output_signal.emit(f"第{i + 1}行：{results[i]}", level="INFO")
                if len(results) > 50:
                    self.output_signal.emit(f"结果超过50行，仅显示前50行", level="SYSTEM")
            else:
                affect_rows = self.cursor.rowcount
                self.output_signal.emit(f"SQL执行成功，影响行数：{affect_rows}", level="INFO")
                logging.info(f"{self.db_type}SQL执行成功，影响行数：{affect_rows}")

            # 执行耗时
            cost_time = round(time.time() - start_time, 3)
            self.output_signal.emit(f"SQL执行完成，耗时：{cost_time} 秒", level="SYSTEM")

        except Exception as e:
            self.conn.rollback()
            err_info = f"SQL执行异常：{str(e)}\n{traceback.format_exc()[:500]}"
            self.output_signal.emit(err_info, "ERROR")
            logging.error(f"{self.db_type}SQL执行异常：{err_info}", exc_info=True)
        finally:
            try:
                if self.cursor:
                    self.cursor.close()
            except:
                pass
            self.finish_signal.emit(self._is_running and (not hasattr(self.conn, 'closed') or not self.conn.closed))

    def stop(self):
        """停止查询"""
        with QMutexLocker(self._mutex):
            self._is_running = False
        self.output_signal.emit("已强制停止SQL查询", "SYSTEM")
        logging.warning("已强制停止SQL查询")

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


# ---------------------- 数据库主模块 ----------------------
class DBModule(LogBaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)  # 初始化父类日志组件
        self.db_type = None
        self.conn = None
        self.query_thread = None
        self._init_ui()
        logging.info("数据库模块初始化完成")

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. 数据库连接配置区
        self._init_db_config_area()
        # 2. SQL查询区
        self._init_sql_query_area()
        # 3. 通用日志区已由父类LogBaseWidget初始化

        # 初始化按钮状态
        self._init_btn_status()

    def _init_db_config_area(self):
        """数据库连接配置区：类型选择 + 连接信息 + 连接/断开按钮"""
        conn_group = QGroupBox("🗄️  数据库连接配置（*为必填）")
        self._set_group_style(conn_group)
        conn_layout = QVBoxLayout(conn_group)
        conn_layout.setContentsMargins(20, 15, 20, 15)
        conn_layout.setSpacing(15)

        # 行1：数据库类型选择
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("*数据库类型：", font=QFont("Microsoft YaHei", 12)))
        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["MySQL", "PostgreSQL", "SQLite"])
        self.db_type_combo.setFixedWidth(150)
        self.db_type_combo.setStyleSheet("""
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
        row1.addWidget(self.db_type_combo)
        # 类型切换信号
        self.db_type_combo.currentTextChanged.connect(self._db_type_change)
        conn_layout.addLayout(row1)

        # 行2：主机/IP + 端口
        row2 = QHBoxLayout()
        self.host_label = QLabel("*主机IP：", font=QFont("Microsoft YaHei", 12))
        self.host_input = QLineEdit()
        self._set_line_style(self.host_input)
        self.host_input.setPlaceholderText("MySQL/PG填IP，如127.0.0.1；SQLite填文件路径")
        row2.addWidget(self.host_label)
        row2.addWidget(self.host_input, stretch=2)
        self.port_label = QLabel("*端口：", font=QFont("Microsoft YaHei", 12))
        self.port_input = QLineEdit()
        self._set_line_style(self.port_input)
        self.port_input.setPlaceholderText("MySQL默认3306，PG默认5432，SQLite留空")
        self.port_input.setFixedWidth(100)
        row2.addWidget(self.port_label)
        row2.addWidget(self.port_input)
        conn_layout.addLayout(row2)

        # 行3：数据库名 + 用户名
        row3 = QHBoxLayout()
        self.db_name_label = QLabel("*数据库名：", font=QFont("Microsoft YaHei", 12))
        self.db_name_input = QLineEdit()
        self._set_line_style(self.db_name_input)
        self.db_name_input.setPlaceholderText("MySQL/PG填数据库名，SQLite留空")
        row3.addWidget(self.db_name_label)
        row3.addWidget(self.db_name_input, stretch=2)
        self.user_label = QLabel("*用户名：", font=QFont("Microsoft YaHei", 12))
        self.user_input = QLineEdit()
        self._set_line_style(self.user_input)
        self.user_input.setPlaceholderText("MySQL/PG填用户名，SQLite留空")
        row3.addWidget(self.user_label)
        row3.addWidget(self.user_input, stretch=2)
        conn_layout.addLayout(row3)

        # 行4：密码
        row4 = QHBoxLayout()
        self.pwd_label = QLabel("*密码：", font=QFont("Microsoft YaHei", 12))
        self.pwd_input = QLineEdit()
        self._set_line_style(self.pwd_input)
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText("MySQL/PG填密码，SQLite留空")
        row4.addWidget(self.pwd_label)
        row4.addWidget(self.pwd_input, stretch=2)
        conn_layout.addLayout(row4)

        # 行5：连接/断开按钮
        row5 = QHBoxLayout()
        self.connect_btn = QPushButton("🔌 连接数据库")
        self.disconnect_btn = QPushButton("❌ 断开数据库")
        self.default_btn = QPushButton("🔄 填充默认配置")
        for btn in [self.connect_btn, self.disconnect_btn, self.default_btn]:
            btn.setFixedSize(120, 36)
            self._set_btn_style(btn)
        row5.addWidget(self.default_btn)
        row5.addWidget(self.connect_btn)
        row5.addWidget(self.disconnect_btn)
        conn_layout.addLayout(row5)

        self.main_layout.addWidget(conn_group)

        # 绑定信号
        self.connect_btn.clicked.connect(self.db_connect)
        self.disconnect_btn.clicked.connect(self.db_disconnect)
        self.default_btn.clicked.connect(self.fill_default_config)

        # 初始类型为MySQL
        self._db_type_change("MySQL")

    def _init_sql_query_area(self):
        """SQL查询区：SQL编辑框 + 执行/停止/暂停/清空日志按钮"""
        sql_group = QGroupBox("📝 SQL语句执行（支持查询/增删改，自动提交事务）")
        self._set_group_style(sql_group)
        sql_layout = QVBoxLayout(sql_group)
        sql_layout.setContentsMargins(20, 15, 20, 15)
        sql_layout.setSpacing(15)

        # SQL编辑框（多行）
        self.sql_edit = QTextEdit()
        self.sql_edit.setPlaceholderText(
            "请输入SQL语句，如：SELECT * FROM table LIMIT 10; 或 INSERT INTO table (id) VALUES (1);")
        self.sql_edit.setFont(QFont("Consolas", 12))
        self.sql_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e2e8f0; border-radius: 4px;
                padding: 8px; font-size: 12px;
                background-color: #ffffff;
            }
            QTextEdit:focus {
                border-color: #3b82f6; outline: none;
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
            }
        """)
        sql_layout.addWidget(self.sql_edit, stretch=1)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.exec_sql_btn = QPushButton("⚡ 执行SQL")
        self.stop_sql_btn = QPushButton("🔴 停止执行")
        self.pause_sql_btn = QPushButton("⏸️  暂停输出")
        self.clear_log_btn = QPushButton("🗑️  清空日志")
        btn_list = [self.exec_sql_btn, self.stop_sql_btn, self.pause_sql_btn, self.clear_log_btn]
        for btn in btn_list:
            btn.setFixedSize(120, 36)
            self._set_btn_style(btn)
        btn_layout.addWidget(self.exec_sql_btn)
        btn_layout.addWidget(self.stop_sql_btn)
        btn_layout.addWidget(self.pause_sql_btn)
        btn_layout.addWidget(self.clear_log_btn)
        sql_layout.addLayout(btn_layout)

        # 提示
        tip_label = QLabel("ℹ️  查询语句仅显示前50行结果，增删改自动提交事务，异常自动回滚！")
        tip_label.setStyleSheet("color: #3b82f6; font-size: 12px;")
        sql_layout.addWidget(tip_label)

        self.main_layout.addWidget(sql_group)

        # 绑定信号
        self.exec_sql_btn.clicked.connect(self.exec_sql)
        self.stop_sql_btn.clicked.connect(self.stop_sql)
        self.pause_sql_btn.clicked.connect(self.toggle_pause_sql)
        self.clear_log_btn.clicked.connect(self.clear_all_log)

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

    # ---------------------- 数据库类型切换适配 ----------------------
    def _db_type_change(self, db_type):
        """数据库类型切换，适配输入框提示和必填项"""
        self.db_type = db_type
        if db_type == "MySQL":
            self.host_label.setText("*主机IP：")
            self.port_label.setText("*端口：")
            self.db_name_label.setText("*数据库名：")
            self.user_label.setText("*用户名：")
            self.pwd_label.setText("*密码：")
            self.host_input.setPlaceholderText("请输入MySQL主机IP，如：127.0.0.1")
            self.port_input.setPlaceholderText("默认3306")
            self.db_name_input.setPlaceholderText("请输入MySQL数据库名，如：test")
            self.user_input.setPlaceholderText("请输入MySQL用户名，如：root")
            self.pwd_input.setPlaceholderText("请输入MySQL密码")
            # 显示所有输入框
            for w in [self.host_label, self.host_input, self.port_label, self.port_input,
                      self.db_name_label, self.db_name_input, self.user_label, self.user_input,
                      self.pwd_label, self.pwd_input]:
                w.show()
        elif db_type == "PostgreSQL":
            self.host_label.setText("*主机IP：")
            self.port_label.setText("*端口：")
            self.db_name_label.setText("*数据库名：")
            self.user_label.setText("*用户名：")
            self.pwd_label.setText("*密码：")
            self.host_input.setPlaceholderText("请输入PG主机IP，如：127.0.0.1")
            self.port_input.setPlaceholderText("默认5432")
            self.db_name_input.setPlaceholderText("请输入PG数据库名，如：postgres")
            self.user_input.setPlaceholderText("请输入PG用户名，如：postgres")
            self.pwd_input.setPlaceholderText("请输入PG密码")
            # 显示所有输入框
            for w in [self.host_label, self.host_input, self.port_label, self.port_input,
                      self.db_name_label, self.db_name_input, self.user_label, self.user_input,
                      self.pwd_label, self.pwd_input]:
                w.show()
        elif db_type == "SQLite":
            self.host_label.setText("*SQLite文件路径：")
            self.port_label.setText("端口：")
            self.db_name_label.setText("数据库名：")
            self.user_label.setText("用户名：")
            self.pwd_label.setText("密码：")
            self.host_input.setPlaceholderText("请输入SQLite文件绝对路径，如：D:/test.db（不存在则自动创建）")
            self.port_input.setPlaceholderText("留空")
            self.db_name_input.setPlaceholderText("留空")
            self.user_input.setPlaceholderText("留空")
            self.pwd_input.setPlaceholderText("留空")
            # 隐藏无用输入框
            for w in [self.port_label, self.port_input, self.db_name_label, self.db_name_input,
                      self.user_label, self.user_input, self.pwd_label, self.pwd_input]:
                w.hide()

        self.fill_default_config()

    # ---------------------- 核心功能 ----------------------
    def _init_btn_status(self):
        """初始化按钮状态：未连接时仅连接/默认/类型选择可用"""
        self.disconnect_btn.setEnabled(False)
        self.exec_sql_btn.setEnabled(False)
        self.stop_sql_btn.setEnabled(False)
        self.pause_sql_btn.setEnabled(False)
        self.connect_btn.setEnabled(True)
        self.default_btn.setEnabled(True)

    def fill_default_config(self):
        """填充各数据库默认配置"""
        if self.db_type == "MySQL":
            self.host_input.setText("127.0.0.1")
            self.port_input.setText("3306")
            self.db_name_input.setText("test")
            self.user_input.setText("root")
            self.pwd_input.setText("root")
        elif self.db_type == "PostgreSQL":
            self.host_input.setText("127.0.0.1")
            self.port_input.setText("5432")
            self.db_name_input.setText("postgres")
            self.user_input.setText("postgres")
            self.pwd_input.setText("postgres")
        elif self.db_type == "SQLite":
            self.host_input.setText("D:/sqlite_test.db")
            self.port_input.setText("")
            self.db_name_input.setText("")
            self.user_input.setText("")
            self.pwd_input.setText("")

        self.print_log(f"已填充{self.db_type}默认配置", level="SYSTEM")
        logging.info(f"已填充{self.db_type}默认配置")
        self.host_input.setFocus()

    def db_connect(self):
        """数据库连接"""
        try:
            # 获取配置
            host = self.host_input.text().strip()
            port = self.port_input.text().strip()
            db_name = self.db_name_input.text().strip()
            user = self.user_input.text().strip()
            pwd = self.pwd_input.text().strip()

            # 校验配置
            if self.db_type in ["MySQL", "PostgreSQL"]:
                if not host:
                    QMessageBox.warning(self, "配置错误", "主机IP为必填项！")
                    return
                if not db_name:
                    QMessageBox.warning(self, "配置错误", "数据库名为必填项！")
                    return
                if not user:
                    QMessageBox.warning(self, "配置错误", "用户名为必填项！")
                    return
                # 端口默认值
                port = int(port) if port else (3306 if self.db_type == "MySQL" else 5432)
            elif self.db_type == "SQLite":
                if not host:
                    QMessageBox.warning(self, "配置错误", "SQLite文件路径为必填项！")
                    return

            self.print_log(f"正在连接{self.db_type}数据库...", level="SYSTEM")
            logging.info(f"正在连接{self.db_type}数据库：{host}:{port if self.db_type != 'SQLite' else ''}")

            # 连接数据库
            if self.db_type == "MySQL":
                self.conn = pymysql.connect(
                    host=host, port=port, user=user, password=pwd, database=db_name,
                    charset="utf8mb4", connect_timeout=10
                )
            elif self.db_type == "PostgreSQL":
                self.conn = psycopg2.connect(
                    host=host, port=port, user=user, password=pwd, dbname=db_name,
                    connect_timeout=10
                )
            elif self.db_type == "SQLite":
                self.conn = sqlite3.connect(host, timeout=10)
                self.conn.row_factory = sqlite3.Row  # 支持按字段名获取

            # 连接成功
            self.print_log(f"{self.db_type}数据库连接成功！", level="INFO")
            logging.info(f"{self.db_type}数据库连接成功")
            self._init_btn_status()
            self.disconnect_btn.setEnabled(True)
            self.exec_sql_btn.setEnabled(True)
            self.connect_btn.setEnabled(False)
            self.sql_edit.setFocus()

        except Exception as e:
            err_info = f"{self.db_type}数据库连接失败：{str(e)}"
            self.print_log(err_info, level="ERROR")
            logging.error(err_info, exc_info=True)
            QMessageBox.critical(self, "连接失败", err_info)

    def db_disconnect(self):
        """数据库断开"""
        if self.query_thread and self.query_thread.isRunning():
            self.stop_sql()

        if self.conn and (not hasattr(self.conn, 'closed') or not self.conn.closed):
            try:
                self.conn.close()
                self.print_log(f"{self.db_type}数据库已安全断开", level="SYSTEM")
                logging.info(f"{self.db_type}数据库已安全断开")
            except Exception as e:
                logging.error(f"断开{self.db_type}数据库失败：{e}")

        self._init_btn_status()
        self.connect_btn.setEnabled(True)

    def exec_sql(self):
        """执行SQL语句"""
        sql = self.sql_edit.toPlainText().strip()
        if not sql:
            QMessageBox.warning(self, "SQL错误", "SQL语句不能为空！")
            return

        if not self.conn or (hasattr(self.conn, 'closed') and self.conn.closed):
            QMessageBox.warning(self, "连接错误", "数据库未连接，请先连接！")
            return

        # 停止已有查询
        if self.query_thread and self.query_thread.isRunning():
            self.stop_sql()

        # 启动查询线程
        self.query_thread = DBQueryThread(self.db_type, self.conn, sql)
        self.query_thread.output_signal.connect(self.print_log)
        self.query_thread.finish_signal.connect(self._sql_finish)
        self.query_thread.start()

        # 更新按钮状态
        self.exec_sql_btn.setEnabled(False)
        self.stop_sql_btn.setEnabled(True)
        self.pause_sql_btn.setEnabled(True)

    def stop_sql(self):
        """停止SQL执行"""
        if self.query_thread and self.query_thread.isRunning():
            self.query_thread.stop()
            self.query_thread.wait(1000)
            self._sql_finish(False)

    def toggle_pause_sql(self):
        """暂停/恢复SQL输出"""
        if not self.query_thread or not self.query_thread.isRunning():
            return

        if self.query_thread.is_paused:
            self.query_thread.resume()
            self.pause_sql_btn.setText("⏸️  暂停输出")
            self.print_log("恢复SQL结果输出", level="SYSTEM")
        else:
            self.query_thread.pause()
            self.pause_sql_btn.setText("▶️  继续输出")
            self.print_log("暂停SQL结果输出", level="SYSTEM")

    def _sql_finish(self, is_normal):
        """SQL执行完成回调"""
        if is_normal:
            self.print_log("SQL执行完成，无异常", level="SYSTEM")
            logging.info("SQL执行完成，无异常")
        else:
            self.print_log("SQL执行被中断/异常", level="WARNING")
            logging.warning("SQL执行被中断/异常")

        # 恢复按钮状态
        self.exec_sql_btn.setEnabled(True)
        self.stop_sql_btn.setEnabled(False)
        self.pause_sql_btn.setEnabled(False)
        self.pause_sql_btn.setText("⏸️  暂停输出")
        self.query_thread = None


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow
    # 初始化日志
    from utils.log_utils import init_logger

    init_logger()

    app = QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle("数据库模块 - 优化版")
    win.setGeometry(100, 100, 1600, 900)
    win.setCentralWidget(DBModule())
    win.show()
    sys.exit(app.exec())