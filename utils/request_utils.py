import requests
from config import REQUEST_TIMEOUT
from utils.common_utils import show_error


def send_request(url, method, params=None, headers=None):
    """发送HTTP请求"""
    try:
        # 处理参数格式
        params = params if params else {}
        headers = headers if headers else {}

        # 转换参数（如果是JSON字符串则解析）
        try:
            params = json.loads(params) if isinstance(params, str) else params
        except:
            pass
        try:
            headers = json.loads(headers) if isinstance(headers, str) else headers
        except:
            pass

        method = method.upper()
        response = None

        if method == "GET":
            response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        elif method == "POST":
            # 自动判断参数类型（JSON优先）
            if isinstance(params, dict) and "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
                response = requests.post(url, json=params, headers=headers, timeout=REQUEST_TIMEOUT)
            else:
                response = requests.post(url, data=params, headers=headers, timeout=REQUEST_TIMEOUT)
        elif method in ["PUT", "DELETE", "PATCH"]:
            response = requests.request(
                method, url, json=params, headers=headers, timeout=REQUEST_TIMEOUT
            )
        else:
            raise ValueError(f"不支持的请求方法：{method}")

        # 构建响应结果
        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "text": response.text,
            "encoding": response.encoding
        }
        return result
    except requests.exceptions.Timeout:
        show_error("请求失败", "请求超时！")
    except requests.exceptions.ConnectionError:
        show_error("请求失败", "连接错误，请检查URL是否正确！")
    except Exception as e:
        show_error("请求失败", f"异常：{str(e)}")
    return None