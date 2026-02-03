from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QListWidget, QListWidgetItem, QStackedWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont
from ui.api_module import ApiModule
from ui.db_module import DbModule
from ui.ps1_module import Ps1Module
from ui.cmd_module import CmdModule
from config import QSS_PATH

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_style()

    def init_ui(self):
        self.setWindowTitle("多功能工具平台")
        self.setMinimumSize(1000, 700)
        self.setWindowIcon(QIcon("resources/icon/app.ico"))  # 替换为实际图标路径

        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧导航栏
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setStyleSheet("QListWidget::item { height: 50px; }")
        # 导航项字体
        font = QFont()
        font.setPointSize(12)

        # 添加导航项
        self.add_nav_item("接口管理", "icon-api", ApiModule())
        self.add_nav_item("数据库管理", "icon-db", DbModule())
        self.add_nav_item("PS1脚本管理", "icon-ps1", Ps1Module())
        self.add_nav_item("CMD脚本管理", "icon-cmd", CmdModule())

        # 右侧内容区域
        self.stack_widget = QStackedWidget()
        layout.addWidget(self.nav_list)
        layout.addWidget(self.stack_widget)

        # 导航项点击事件
        self.nav_list.currentItemChanged.connect(self.switch_page)

    def add_nav_item(self, text, icon_name, widget):
        """添加导航项"""
        item = QListWidgetItem(text)
        item.setIcon(QIcon.fromTheme(icon_name))  # 替换为实际图标
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        item.setFont(font)
        self.nav_list.addItem(item)
        self.stack_widget.addWidget(widget)

    def switch_page(self, current_item, previous_item):
        """切换页面"""
        if current_item:
            index = self.nav_list.row(current_item)
            self.stack_widget.setCurrentIndex(index)

    def load_style(self):
        """加载样式表"""
        try:
            with open(QSS_PATH, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"加载样式表失败：{e}")
            # 备用样式
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f7fa;
                }
                QListWidget {
                    background-color: #2d3748;
                    color: white;
                    border: none;
                }
                QListWidget::item:selected {
                    background-color: #4a5568;
                    border-left: 4px solid #4299e1;
                }
                QPushButton {
                    background-color: #4299e1;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #3182ce;
                }
                QTableWidget {
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                }
                QTableWidget::item:selected {
                    background-color: #e8f4f8;
                    color: #2d3748;
                }
                QTextBrowser, QTextEdit, QLineEdit, QComboBox {
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 6px;
                }
                QTabWidget::pane {
                    border: 1px solid #dee2e6;
                }
                QTabBar::tab {
                    padding: 8px 16px;
                    margin-right: 4px;
                }
                QTabBar::tab:selected {
                    background-color: #4299e1;
                    color: white;
                    border-radius: 4px 4px 0 0;
                }
            """)