import json
from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import Qt

def format_json(data):
    """格式化JSON字符串"""
    try:
        if isinstance(data, dict):
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif isinstance(data, str):
            return json.dumps(json.loads(data), ensure_ascii=False, indent=2)
        else:
            return str(data)
    except Exception as e:
        return f"JSON格式化失败：{str(e)}"

def copy_to_clipboard(text):
    """复制文本到剪贴板"""
    clipboard = QApplication.clipboard()
    clipboard.setText(text)
    show_info("提示", "已复制到剪贴板！")

def show_info(title, content):
    """显示信息提示框"""
    QMessageBox.information(None, title, content, QMessageBox.StandardButton.Ok)

def show_error(title, content):
    """显示错误提示框"""
    QMessageBox.critical(None, title, content, QMessageBox.StandardButton.Ok)

def validate_required_fields(fields):
    """验证必填字段（{字段名: 字段值}）"""
    for field_name, field_value in fields.items():
        if not field_value or str(field_value).strip() == "":
            show_error("验证失败", f"{field_name}不能为空！")
            return False
    return True