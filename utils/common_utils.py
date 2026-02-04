#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:49
@文件名: common_utils.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup/utils\common_utils.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""

import json
import logging
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
        err_msg = f"JSON格式化失败：{str(e)}"
        logging.error(err_msg)
        return err_msg

def copy_to_clipboard(text):
    """复制文本到剪贴板"""
    clipboard = QApplication.clipboard()
    clipboard.setText(text)
    show_info("提示", "已复制到剪贴板！")
    logging.info("文本已复制到剪贴板")

def show_info(title, content):
    """显示信息提示框（同时记录日志）"""
    QMessageBox.information(None, title, content, QMessageBox.StandardButton.Ok)
    logging.info(f"[{title}] {content}")

def show_error(title, content):
    """显示错误提示框（同时记录日志）"""
    QMessageBox.critical(None, title, content, QMessageBox.StandardButton.Ok)
    logging.error(f"[{title}] {content}")

def validate_required_fields(fields):
    """验证必填字段（{字段名: 字段值}）"""
    for field_name, field_value in fields.items():
        if not field_value or str(field_value).strip() == "":
            show_error("验证失败", f"{field_name}不能为空！")
            return False
    return True