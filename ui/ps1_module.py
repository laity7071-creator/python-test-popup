# ps1_module.py - Python3.10+PyQt6 兼容，PS1模块（本地执行PowerShell）
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QFont
import subprocess
import sys
import time
# 先确保顶部有这个相对导入（没有就加上）
from .log_base import LogBaseWidget

# 1. 类定义：把继承QWidget改成继承LogBaseWidget
class PS1Module(LogBaseWidget):  # 原代码是class PS1Module(QWidget):
    log_signal = pyqtSignal(str, str)
    exec_finish_signal = pyqtSignal()

    # 2. __init__方法：第一行调用父类构造函数
    def __init__(self, parent=None):
        super().__init__(parent)  # 必须加这行！初始化log_widget
        self.ps1_thread = None
        self.is_executing = False
        self._init_ui()  # 原有代码保留

    def clear_all_log(self):
        """新增清空日志方法，解决属性缺失报错"""
        self.log_widget.clear()  # 清空日志显示框
        # 打印日志（和父类逻辑一致，可选）
        import time
        log_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.log_widget.insertPlainText(f"[{log_time}] [SYSTEM] 日志已清空\n")

    def run(self):
        try:
            # Windows PowerShell执行命令，处理编码（避免中文乱码）
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.process = subprocess.Popen(
                ["powershell", "-Command", self.command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                encoding='utf-8',
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
            if self.process.poll() == 0 and self._is_running:
                self.output_signal.emit("命令执行完成，退出码：0", "SYSTEM")
            else:
                self.output_signal.emit(f"命令执行结束/异常，退出码：{self.process.poll()}", "WARNING")

        except Exception as e:
            self.output_signal.emit(f"命令执行异常：{str(e)}", "ERROR")
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
                self.output_signal.emit("已强制终止PowerShell进程", "SYSTEM")
            except:
                self.process.kill()

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

# ---------------------- PS1主模块 ----------------------
class PS1Module(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cmd_thread = None
        self.cmd_history = []
        self.history_index = -1
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. PS1命令执行区
        self._init_ps1_cmd_area()

        # 2. 通用日志区
        self.log_widget = LogBaseWidget(self)
        self.main_layout.addWidget(self.log_widget, stretch=1)

        # 初始化按钮状态
        self._init_btn_status()

    def _init_ps1_cmd_area(self):
        """PS1命令执行区"""
        cmd_group = QGroupBox("📝 PowerShell命令执行（本地，支持所有PS1命令）")
        self._set_group_style(cmd_group)
        cmd_layout = QVBoxLayout(cmd_group)
        cmd_layout.setContentsMargins(20, 15, 20, 15)
        cmd_layout.setSpacing(15)

        # 命令输入框
        self.cmd_input = QLineEdit()
        self._set_line_style(self.cmd_input)
        self.cmd_input.setPlaceholderText("请输入PowerShell命令，如：Get-ChildItem 或 ipconfig")
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
        tip_label = QLabel("ℹ️  本地执行PowerShell命令，自动处理中文乱码，支持实时输出！")
        tip_label.setStyleSheet("color: #3b82f6; font-size: 12px;")
        cmd_layout.addWidget(tip_label)

        self.main_layout.addWidget(cmd_group)

        # 绑定信号
        self.exec_btn.clicked.connect(self.exec_ps1_cmd)
        self.stop_btn.clicked.connect(self.stop_ps1_cmd)
        self.pause_btn.clicked.connect(self.toggle_pause_cmd)
        self.clear_log_btn.clicked.connect(self.clear_all_log)
        self.cmd_input.returnPressed.connect(self.exec_ps1_cmd)
        self.cmd_input.installEventFilter(self)

    # ---------------------- 样式封装（和SSH一致） ----------------------
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

    def exec_ps1_cmd(self):
        """执行PS1命令"""
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
            self.stop_ps1_cmd()

        # 启动线程
        self.cmd_thread = PS1CommandThread(cmd)
        self.cmd_thread.output_signal.connect(self.log_widget.print_log)
        self.cmd_thread.finish_signal.connect(self._cmd_finish)
        self.cmd_thread.start()

        # 更新按钮
        self.exec_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.log_widget.print_log(f"开始执行PowerShell命令：{cmd}", level="SYSTEM")

    def stop_ps1_cmd(self):
        """停止命令"""
        if self.cmd_thread and self.cmd_thread.isRunning():
            self.cmd_thread.stop()
            self.cmd_thread.wait(1000)
            self._cmd_finish(False)

    def toggle_pause_cmd(self):
        """暂停/恢复"""
        if not self.cmd_thread or not self.cmd_thread.isRunning():
            return
        if self.cmd_thread.is_paused:
            self.cmd_thread.resume()
            self.pause_btn.setText("⏸️  暂停输出")
            self.log_widget.print_log("恢复日志输出", level="SYSTEM")
        else:
            self.cmd_thread.pause()
            self.pause_btn.setText("▶️  继续输出")
            self.log_widget.print_log("暂停日志输出", level="SYSTEM")

    def _cmd_finish(self, is_normal):
        """命令完成"""
        if is_normal:
            self.log_widget.print_log("PowerShell命令执行完成，无异常", level="SYSTEM")
        else:
            self.log_widget.print_log("PowerShell命令执行被中断/异常", level="WARNING")
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
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle("PowerShell模块 - 优化版")
    win.setGeometry(100, 100, 1600, 900)
    win.setCentralWidget(PS1Module())
    win.show()
    sys.exit(app.exec())