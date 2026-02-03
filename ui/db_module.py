from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                             QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QTextEdit,
                             QTabWidget, QSplitter, QTextBrowser, QMessageBox, QLabel)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from db.dao import db_dao
from utils.common_utils import copy_to_clipboard, validate_required_fields

class SqlDialog(QDialog):
    """SQL脚本新建/编辑对话框"""
    def __init__(self, parent=None, sql_data=None):
        super().__init__(parent)
        self.sql_data = sql_data
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑SQL脚本" if self.sql_data else "新建SQL脚本")
        self.setMinimumSize(600, 450)
        layout = QVBoxLayout()

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(20, 20, 20, 20)

        # 脚本名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入SQL脚本名称（唯一）")
        form_layout.addRow("脚本名称*", self.name_edit)

        # 描述
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("请输入脚本描述（可选）")
        form_layout.addRow("描述", self.desc_edit)

        # 目标库名
        self.db_name_edit = QLineEdit()
        self.db_name_edit.setPlaceholderText("例如：test_db")
        form_layout.addRow("目标库名*", self.db_name_edit)

        # 目标表名
        self.table_name_edit = QLineEdit()
        self.table_name_edit.setPlaceholderText("例如：user_info（可选）")
        form_layout.addRow("目标表名", self.table_name_edit)

        # SQL内容
        self.sql_edit = QTextEdit()
        self.sql_edit.setPlaceholderText("请输入SQL语句（支持多语句）")
        self.sql_edit.setMinimumHeight(150)
        form_layout.addRow("SQL内容*", self.sql_edit)

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
        if self.sql_data:
            self.name_edit.setText(self.sql_data["name"])
            self.desc_edit.setText(self.sql_data.get("description", ""))
            self.db_name_edit.setText(self.sql_data["db_name"])
            self.table_name_edit.setText(self.sql_data.get("table_name", ""))
            self.sql_edit.setText(self.sql_data["sql_content"])

    def get_data(self):
        """获取表单数据"""
        return {
            "name": self.name_edit.text().strip(),
            "description": self.desc_edit.text().strip(),
            "db_name": self.db_name_edit.text().strip(),
            "table_name": self.table_name_edit.text().strip(),
            "sql_content": self.sql_edit.toPlainText().strip()
        }

    def accept(self):
        """保存前验证"""
        data = self.get_data()
        if validate_required_fields({
            "脚本名称": data["name"],
            "目标库名": data["db_name"],
            "SQL内容": data["sql_content"]
        }):
            super().accept()

class SqlExampleWidget(QWidget):
    """SQL书写示例页面"""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("<h3>常用SQL示例</h3>")
        layout.addWidget(title)

        # 示例列表
        examples = [
            ("1. 单表查询", "SELECT * FROM table_name WHERE condition LIMIT 10;", "查询表中前10条符合条件的数据"),
            ("2. 插入数据", "INSERT INTO table_name (col1, col2) VALUES ('val1', 'val2');", "向表中插入一条数据"),
            ("3. 更新数据", "UPDATE table_name SET col1 = 'new_val' WHERE condition;", "更新符合条件的数据"),
            ("4. 删除数据", "DELETE FROM table_name WHERE condition;", "删除符合条件的数据"),
            ("5. 联表查询", "SELECT a.*, b.* FROM table_a a JOIN table_b b ON a.id = b.a_id;", "两表关联查询"),
            ("6. 统计计数", "SELECT COUNT(*) AS total FROM table_name WHERE condition;", "统计符合条件的记录数"),
            ("7. 分组统计", "SELECT col1, COUNT(*) FROM table_name GROUP BY col1;", "按字段分组统计")
        ]

        for title, sql, desc in examples:
            # 示例标题
            example_title = QLabel(f"<strong>{title}</strong>")
            layout.addWidget(example_title)
            # 描述
            desc_label = QLabel(f"描述：{desc}")
            desc_label.setStyleSheet("color: #666;")
            layout.addWidget(desc_label)
            # SQL内容（可复制）
            sql_browser = QTextBrowser()
            sql_browser.setText(sql)
            sql_browser.setMinimumHeight(60)
            layout.addWidget(sql_browser)
            # 复制按钮
            copy_btn = QPushButton(f"复制「{title.split(' ')[1]}」SQL")
            copy_btn.clicked.connect(lambda _, s=sql: copy_to_clipboard(s))
            layout.addWidget(copy_btn)
            # 分隔线
            line = QLabel("")
            line.setStyleSheet("background-color: #eee; height: 1px; margin: 15px 0;")
            layout.addWidget(line)

        layout.addStretch()
        self.setLayout(layout)

class SqlScriptWidget(QWidget):
    """SQL脚本录入与管理页面"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_sql_list()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 顶部按钮区域
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("新建SQL脚本")
        self.refresh_btn = QPushButton("刷新列表")
        self.add_btn.clicked.connect(self.add_sql)
        self.refresh_btn.clicked.connect(self.load_sql_list)
        self.add_btn.setIcon(QIcon.fromTheme("list-add"))
        self.refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 分割器（列表 + 结果区域）
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(5)

        # SQL列表表格
        self.sql_table = QTableWidget()
        self.sql_table.setColumnCount(7)
        self.sql_table.setHorizontalHeaderLabels(["ID", "脚本名称", "目标库", "目标表", "描述", "更新时间", "操作"])
        self.sql_table.horizontalHeader().setStretchLastSection(True)
        self.sql_table.setMinimumHeight(300)
        splitter.addWidget(self.sql_table)

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
        splitter.setSizes([300, 200])

        layout.addWidget(splitter)
        self.setLayout(layout)

    def load_sql_list(self):
        """加载SQL脚本列表"""
        self.sql_table.setRowCount(0)
        scripts = db_dao.get_all_sql_scripts()
        for script in scripts:
            row = self.sql_table.rowCount()
            self.sql_table.insertRow(row)
            # 填充数据
            self.sql_table.setItem(row, 0, QTableWidgetItem(str(script["id"])))
            self.sql_table.setItem(row, 1, QTableWidgetItem(script["name"]))
            self.sql_table.setItem(row, 2, QTableWidgetItem(script["db_name"]))
            self.sql_table.setItem(row, 3, QTableWidgetItem(script.get("table_name", "")))
            self.sql_table.setItem(row, 4, QTableWidgetItem(script.get("description", "")))
            self.sql_table.setItem(row, 5, QTableWidgetItem(script["update_time"].strftime("%Y-%m-%d %H:%M:%S")))
            # 操作按钮
            btn_layout = QHBoxLayout()
            view_btn = QPushButton("查看")
            edit_btn = QPushButton("编辑")
            delete_btn = QPushButton("删除")
            run_btn = QPushButton("执行")
            view_btn.clicked.connect(lambda _, s=script: self.view_sql(s))
            edit_btn.clicked.connect(lambda _, s=script: self.edit_sql(s))
            delete_btn.clicked.connect(lambda _, s=script: self.delete_sql(s["id"]))
            run_btn.clicked.connect(lambda _, s=script: self.run_sql(s))
            # 按钮大小
            view_btn.setFixedSize(QSize(60, 25))
            edit_btn.setFixedSize(QSize(60, 25))
            delete_btn.setFixedSize(QSize(60, 25))
            run_btn.setFixedSize(QSize(60, 25))
            btn_layout.addWidget(view_btn)
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            btn_layout.addWidget(run_btn)
            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.sql_table.setCellWidget(row, 6, btn_widget)
        # 自适应列宽
        for col in range(6):
            self.sql_table.horizontalHeader().setSectionResizeMode(col, self.sql_table.horizontalHeader().sectionResizeMode.Interactive)

    def add_sql(self):
        """新建SQL脚本"""
        dialog = SqlDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if db_dao.add_sql_script(data):
                self.load_sql_list()
                copy_to_clipboard("SQL脚本添加成功！")

    def edit_sql(self, sql_data):
        """编辑SQL脚本"""
        dialog = SqlDialog(self, sql_data)
        if dialog.exec():
            data = dialog.get_data()
            if db_dao.update_sql_script(sql_data["id"], data):
                self.load_sql_list()
                copy_to_clipboard("SQL脚本更新成功！")

    def delete_sql(self, script_id):
        """删除SQL脚本"""
        if QMessageBox.question(self, "确认删除", "是否删除该SQL脚本？",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if db_dao.delete_sql_script(script_id):
                self.load_sql_list()
                copy_to_clipboard("SQL脚本删除成功！")

    def view_sql(self, sql_data):
        """查看SQL脚本"""
        self.result_browser.clear()
        self.result_browser.append(f"=== SQL脚本详情 ===")
        self.result_browser.append(f"名称：{sql_data['name']}")
        self.result_browser.append(f"描述：{sql_data.get('description', '无')}")
        self.result_browser.append(f"目标库：{sql_data['db_name']}")
        self.result_browser.append(f"目标表：{sql_data.get('table_name', '无')}")
        self.result_browser.append(f"更新时间：{sql_data['update_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        self.result_browser.append("--- SQL内容 ---")
        self.result_browser.append(sql_data["sql_content"])
        self.copy_btn.setEnabled(True)

    def run_sql(self, sql_data):
        """执行SQL脚本"""
        self.result_browser.clear()
        self.result_browser.append(f"=== 开始执行SQL脚本：{sql_data['name']} ===")
        self.result_browser.append(f"目标库：{sql_data['db_name']}")
        self.result_browser.append(f"SQL内容：{sql_data['sql_content']}")
        self.result_browser.append("--- 执行结果 ---")

        # 执行SQL
        result = db_dao.execute_sql(sql_data["db_name"], sql_data["sql_content"])
        if result:
            if result["type"] == "query":
                self.result_browser.append(f"查询成功，共 {len(result['data'])} 条数据：")
                # 显示列名
                self.result_browser.append("\t".join(result["columns"]))
                # 显示数据
                for row in result["data"]:
                    self.result_browser.append("\t".join(str(val) for val in row.values()))
            else:
                self.result_browser.append(f"执行成功，影响行数：{result['affected_rows']}")
        self.result_browser.append("=== 执行结束 ===")
        self.copy_btn.setEnabled(True)

    def copy_result(self):
        """复制结果"""
        copy_to_clipboard(self.result_browser.toPlainText())

    def clear_result(self):
        """清空结果"""
        self.result_browser.clear()
        self.copy_btn.setEnabled(False)

class DbModule(QWidget):
    """数据库模块主页面（包含2个子标签）"""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("数据库管理")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 标签页
        self.tab_widget = QTabWidget()
        self.example_tab = SqlExampleWidget()
        self.script_tab = SqlScriptWidget()
        self.tab_widget.addTab(self.example_tab, "SQL书写示例")
        self.tab_widget.addTab(self.script_tab, "SQL录入与管理")
        layout.addWidget(self.tab_widget)

        self.setLayout(layout)