#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:50
@文件名: request_utils.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup/utils\request_utils.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""
import requests
import json
import logging
from config import REQUEST_TIMEOUT
from utils.common_utils import show_error


def send_request(url, method, params=None, headers=None):
    """发送HTTP请求（添加日志记录）"""
    logging.info(f"开始发送{method}请求：{url}")
    logging.info(f"请求参数：{params}")
    logging.info(f"请求头：{headers}")

    try:
        # 处理参数格式
        params = params if params else {}
        headers = headers if headers else {}

        # 转换参数（如果是JSON字符串则解析）
        try:
            params = json.loads(params) if isinstance(params, str) else params
        except Exception as e:
            logging.warning(f"参数JSON解析失败，使用原始参数：{e}")
        try:
            headers = json.loads(headers) if isinstance(headers, str) else headers
        except Exception as e:
            logging.warning(f"请求头JSON解析失败，使用原始请求头：{e}")

        method = method.upper()
        response = None

        if method == "GET":
            response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT, verify=False)
        elif method == "POST":
            # 自动判断参数类型（JSON优先）
            if isinstance(params, dict) and "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
                response = requests.post(url, json=params, headers=headers, timeout=REQUEST_TIMEOUT, verify=False)
            else:
                response = requests.post(url, data=params, headers=headers, timeout=REQUEST_TIMEOUT, verify=False)
        elif method in ["PUT", "DELETE", "PATCH"]:
            response = requests.request(
                method, url, json=params, headers=headers, timeout=REQUEST_TIMEOUT, verify=False
            )
        else:
            raise ValueError(f"不支持的请求方法：{method}")

        # 记录响应信息
        logging.info(f"请求成功，状态码：{response.status_code}")
        logging.info(f"响应头：{dict(response.headers)}")
        logging.info(f"响应体：{response.text[:1000]}...")  # 只记录前1000字符

        # 构建响应结果
        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "text": response.text,
            "encoding": response.encoding
        }
        return result

    except requests.exceptions.Timeout:
        err_msg = "请求超时！"
        show_error("请求失败", err_msg)
        logging.error(err_msg)
    except requests.exceptions.ConnectionError:
        err_msg = "连接错误，请检查URL是否正确！"
        show_error("请求失败", err_msg)
        logging.error(err_msg)
    except Exception as e:
        err_msg = f"异常：{str(e)}"
        show_error("请求失败", err_msg)
        logging.error(err_msg, exc_info=True)

    return None