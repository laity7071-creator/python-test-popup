from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                             QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QTextEdit,
                             QComboBox, QSplitter, QTextBrowser, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from db.dao import db_dao
from utils.request_utils import send_request
from utils.common_utils import format_json, copy_to_clipboard, validate_required_fields

class ApiDialog(QDialog):
    """接口新建/编辑对话框"""
    def __init__(self, parent=None, api_data=None):
        super().__init__(parent)
        self.api_data = api_data  # 编辑时传入已有数据
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑接口" if self.api_data else "新建接口")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout()

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(20, 20, 20, 20)

        # 接口名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入接口名称（唯一）")
        form_layout.addRow("接口名称*", self.name_edit)

        # 接口URL
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("例如：https://api.example.com/getData")
        form_layout.addRow("接口URL*", self.url_edit)

        # 请求方法
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH"])
        form_layout.addRow("请求方法*", self.method_combo)

        # 请求参数（JSON格式）
        self.params_edit = QTextEdit()
        self.params_edit.setPlaceholderText('{"key1": "value1", "key2": "value2"}（无参数留空）')
        self.params_edit.setMinimumHeight(80)
        form_layout.addRow("请求参数", self.params_edit)

        # 请求头（JSON格式）
        self.headers_edit = QTextEdit()
        self.headers_edit.setPlaceholderText('{"Content-Type": "application/json"}（无请求头留空）')
        self.headers_edit.setMinimumHeight(80)
        form_layout.addRow("请求头", self.headers_edit)

        layout.addLayout(form_layout)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 0, 20, 20)
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 编辑时填充数据
        if self.api_data:
            self.name_edit.setText(self.api_data["name"])
            self.url_edit.setText(self.api_data["url"])
            self.method_combo.setCurrentText(self.api_data["method"])
            self.params_edit.setText(format_json(self.api_data["params"]))
            self.headers_edit.setText(format_json(self.api_data["headers"]))

    def get_data(self):
        """获取表单数据"""
        return {
            "name": self.name_edit.text().strip(),
            "url": self.url_edit.text().strip(),
            "method": self.method_combo.currentText(),
            "params": self.params_edit.toPlainText().strip() or "{}",
            "headers": self.headers_edit.toPlainText().strip() or "{}"
        }

    def accept(self):
        """保存前验证"""
        data = self.get_data()
        if validate_required_fields({
            "接口名称": data["name"],
            "接口URL": data["url"],
            "请求方法": data["method"]
        }):
            super().accept()

class ApiModule(QWidget):
    """接口模块主页面"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_api_list()

    def init_ui(self):
        self.setWindowTitle("接口管理")
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 顶部按钮区域
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("新建接口")
        self.refresh_btn = QPushButton("刷新列表")
        self.add_btn.clicked.connect(self.add_api)
        self.refresh_btn.clicked.connect(self.load_api_list)
        # 按钮样式（通过QSS美化，这里只设置图标占位）
        self.add_btn.setIcon(QIcon.fromTheme("list-add"))
        self.refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 分割器（列表 + 结果区域）
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(5)

        # 接口列表表格
        self.api_table = QTableWidget()
        self.api_table.setColumnCount(6)
        self.api_table.setHorizontalHeaderLabels(["ID", "接口名称", "URL", "请求方法", "更新时间", "操作"])
        self.api_table.horizontalHeader().setStretchLastSection(True)
        self.api_table.setMinimumHeight(300)
        splitter.addWidget(self.api_table)

        # 结果显示区域
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)

        # 结果顶部按钮
        result_btn_layout = QHBoxLayout()
        self.copy_btn = QPushButton("复制结果")
        self.clear_btn = QPushButton("清空结果")
        self.copy_btn.clicked.connect(self.copy_result)
        self.clear_btn.clicked.connect(self.clear_result)
        self.copy_btn.setEnabled(False)
        result_btn_layout.addWidget(self.copy_btn)
        result_btn_layout.addWidget(self.clear_btn)
        result_btn_layout.addStretch()
        result_layout.addLayout(result_btn_layout)

        # 结果显示文本框
        self.result_browser = QTextBrowser()
        self.result_browser.setReadOnly(True)
        result_layout.addWidget(self.result_browser)
        splitter.addWidget(result_widget)
        splitter.setSizes([300, 200])  # 初始高度比例

        layout.addWidget(splitter)
        self.setLayout(layout)

    def load_api_list(self):
        """加载接口列表"""
        self.api_table.setRowCount(0)
        apis = db_dao.get_all_apis()
        for api in apis:
            row = self.api_table.rowCount()
            self.api_table.insertRow(row)
            # 填充数据
            self.api_table.setItem(row, 0, QTableWidgetItem(str(api["id"])))
            self.api_table.setItem(row, 1, QTableWidgetItem(api["name"]))
            self.api_table.setItem(row, 2, QTableWidgetItem(api["url"]))
            self.api_table.setItem(row, 3, QTableWidgetItem(api["method"]))
            self.api_table.setItem(row, 4, QTableWidgetItem(api["update_time"].strftime("%Y-%m-%d %H:%M:%S")))
            # 操作按钮
            btn_layout = QHBoxLayout()
            run_btn = QPushButton("运行")
            edit_btn = QPushButton("编辑")
            delete_btn = QPushButton("删除")
            run_btn.clicked.connect(lambda _, a=api: self.run_api(a))
            edit_btn.clicked.connect(lambda _, a=api: self.edit_api(a))
            delete_btn.clicked.connect(lambda _, a=api: self.delete_api(a["id"]))
            # 按钮大小
            run_btn.setFixedSize(QSize(60, 25))
            edit_btn.setFixedSize(QSize(60, 25))
            delete_btn.setFixedSize(QSize(60, 25))
            btn_layout.addWidget(run_btn)
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.api_table.setCellWidget(row, 5, btn_widget)
        # 自适应列宽
        for col in range(5):
            self.api_table.horizontalHeader().setSectionResizeMode(col, self.api_table.horizontalHeader().sectionResizeMode.Interactive)

    def add_api(self):
        """新建接口"""
        dialog = ApiDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if db_dao.add_api(data):
                self.load_api_list()
                copy_to_clipboard("接口添加成功！")

    def edit_api(self, api_data):
        """编辑接口"""
        dialog = ApiDialog(self, api_data)
        if dialog.exec():
            data = dialog.get_data()
            if db_dao.update_api(api_data["id"], data):
                self.load_api_list()
                copy_to_clipboard("接口更新成功！")

    def delete_api(self, api_id):
        """删除接口"""
        if QMessageBox.question(self, "确认删除", "是否删除该接口？",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if db_dao.delete_api(api_id):
                self.load_api_list()
                copy_to_clipboard("接口删除成功！")

    def run_api(self, api_data):
        """运行接口"""
        self.result_browser.clear()
        self.result_browser.append(f"=== 开始请求接口：{api_data['name']} ===")
        self.result_browser.append(f"URL：{api_data['url']}")
        self.result_browser.append(f"方法：{api_data['method']}")
        self.result_browser.append(f"参数：{format_json(api_data['params'])}")
        self.result_browser.append(f"请求头：{format_json(api_data['headers'])}")
        self.result_browser.append("--- 响应结果 ---")

        # 发送请求
        result = send_request(
            url=api_data["url"],
            method=api_data["method"],
            params=api_data["params"],
            headers=api_data["headers"]
        )

        if result:
            self.result_browser.append(f"状态码：{result['status_code']}")
            self.result_browser.append(f"响应头：{format_json(result['headers'])}")
            self.result_browser.append(f"响应体：{format_json(result['text'])}")
        self.result_browser.append("=== 请求结束 ===")
        self.copy_btn.setEnabled(True)

    def copy_result(self):
        """复制结果"""
        copy_to_clipboard(self.result_browser.toPlainText())

    def clear_result(self):
        """清空结果"""
        self.result_browser.clear()
        self.copy_btn.setEnabled(False)