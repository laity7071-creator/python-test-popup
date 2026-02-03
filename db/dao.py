import pymysql
import json
from datetime import datetime
from config import DB_CONFIG
from utils.common_utils import show_error

class DatabaseDAO:
    _instance = None  # 单例模式

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conn = None
            cls._instance.init_db()
        return cls._instance

    def init_db(self):
        """初始化数据库（创建库、表）"""
        try:
            # 1. 连接MySQL服务器（不指定数据库）
            conn = pymysql.connect(
                host=DB_CONFIG["host"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                port=DB_CONFIG["port"],
                charset=DB_CONFIG["charset"]
            )
            cursor = conn.cursor()

            # 2. 创建数据库（如果不存在）
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['db']} DEFAULT CHARACTER SET utf8mb4")
            conn.select_db(DB_CONFIG["db"])

            # 3. 创建接口表
            create_api_table_sql = """
            CREATE TABLE IF NOT EXISTS api_info (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL COMMENT '接口名称',
                url VARCHAR(500) NOT NULL COMMENT '接口URL',
                method VARCHAR(20) NOT NULL COMMENT '请求方法（GET/POST等）',
                params TEXT COMMENT '请求参数（JSON字符串）',
                headers TEXT COMMENT '请求头（JSON字符串）',
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='接口配置表';
            """
            cursor.execute(create_api_table_sql)

            # 4. 创建SQL脚本表
            create_sql_table_sql = """
            CREATE TABLE IF NOT EXISTS sql_script (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL COMMENT '脚本名称',
                description VARCHAR(500) COMMENT '描述',
                db_name VARCHAR(100) NOT NULL COMMENT '目标库名',
                table_name VARCHAR(100) COMMENT '目标表名',
                sql_content TEXT NOT NULL COMMENT 'SQL内容',
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='SQL脚本表';
            """
            cursor.execute(create_sql_table_sql)

            conn.commit()
            cursor.close()
            conn.close()

            # 5. 连接目标数据库
            self.connect_db()
        except Exception as e:
            show_error("数据库初始化失败", f"原因：{str(e)}")

    def connect_db(self):
        """连接数据库"""
        try:
            self.conn = pymysql.connect(**DB_CONFIG)
            self.conn.autocommit(True)
        except Exception as e:
            show_error("数据库连接失败", f"原因：{str(e)}")
            self.conn = None

    def get_cursor(self):
        """获取游标（自动重连）"""
        if not self.conn or self.conn._closed:
            self.connect_db()
        return self.conn.cursor(pymysql.cursors.DictCursor)

    # ------------------------------ 接口表操作 ------------------------------
    def add_api(self, api_data):
        """添加接口：api_data = {name, url, method, params, headers}"""
        try:
            cursor = self.get_cursor()
            sql = """
            INSERT INTO api_info (name, url, method, params, headers)
            VALUES (%s, %s, %s, %s, %s)
            """
            # 转换字典为JSON字符串
            params_str = json.dumps(api_data.get("params", {}), ensure_ascii=False)
            headers_str = json.dumps(api_data.get("headers", {}), ensure_ascii=False)
            cursor.execute(
                sql,
                (api_data["name"], api_data["url"], api_data["method"], params_str, headers_str)
            )
            return True
        except pymysql.IntegrityError:
            show_error("添加失败", f"接口名称「{api_data['name']}」已存在！")
        except Exception as e:
            show_error("添加接口失败", str(e))
        return False

    def get_all_apis(self):
        """查询所有接口"""
        try:
            cursor = self.get_cursor()
            cursor.execute("SELECT * FROM api_info ORDER BY update_time DESC")
            return cursor.fetchall()
        except Exception as e:
            show_error("查询接口失败", str(e))
        return []

    def get_api_by_id(self, api_id):
        """根据ID查询接口"""
        try:
            cursor = self.get_cursor()
            cursor.execute("SELECT * FROM api_info WHERE id = %s", (api_id,))
            return cursor.fetchone()
        except Exception as e:
            show_error("查询接口失败", str(e))
        return None

    def update_api(self, api_id, api_data):
        """更新接口"""
        try:
            cursor = self.get_cursor()
            sql = """
            UPDATE api_info SET name = %s, url = %s, method = %s, params = %s, headers = %s
            WHERE id = %s
            """
            params_str = json.dumps(api_data.get("params", {}), ensure_ascii=False)
            headers_str = json.dumps(api_data.get("headers", {}), ensure_ascii=False)
            cursor.execute(
                sql,
                (api_data["name"], api_data["url"], api_data["method"], params_str, headers_str, api_id)
            )
            return cursor.rowcount > 0
        except pymysql.IntegrityError:
            show_error("更新失败", f"接口名称「{api_data['name']}」已存在！")
        except Exception as e:
            show_error("更新接口失败", str(e))
        return False

    def delete_api(self, api_id):
        """删除接口"""
        try:
            cursor = self.get_cursor()
            cursor.execute("DELETE FROM api_info WHERE id = %s", (api_id,))
            return cursor.rowcount > 0
        except Exception as e:
            show_error("删除接口失败", str(e))
        return False

    # ------------------------------ SQL脚本表操作 ------------------------------
    def add_sql_script(self, sql_data):
        """添加SQL脚本：sql_data = {name, description, db_name, table_name, sql_content}"""
        try:
            cursor = self.get_cursor()
            sql = """
            INSERT INTO sql_script (name, description, db_name, table_name, sql_content)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(
                sql,
                (sql_data["name"], sql_data["description"], sql_data["db_name"],
                 sql_data["table_name"], sql_data["sql_content"])
            )
            return True
        except pymysql.IntegrityError:
            show_error("添加失败", f"SQL脚本名称「{sql_data['name']}」已存在！")
        except Exception as e:
            show_error("添加SQL脚本失败", str(e))
        return False

    def get_all_sql_scripts(self):
        """查询所有SQL脚本"""
        try:
            cursor = self.get_cursor()
            cursor.execute("SELECT * FROM sql_script ORDER BY update_time DESC")
            return cursor.fetchall()
        except Exception as e:
            show_error("查询SQL脚本失败", str(e))
        return []

    def get_sql_script_by_id(self, script_id):
        """根据ID查询SQL脚本"""
        try:
            cursor = self.get_cursor()
            cursor.execute("SELECT * FROM sql_script WHERE id = %s", (script_id,))
            return cursor.fetchone()
        except Exception as e:
            show_error("查询SQL脚本失败", str(e))
        return None

    def update_sql_script(self, script_id, sql_data):
        """更新SQL脚本"""
        try:
            cursor = self.get_cursor()
            sql = """
            UPDATE sql_script SET name = %s, description = %s, db_name = %s, table_name = %s, sql_content = %s
            WHERE id = %s
            """
            cursor.execute(
                sql,
                (sql_data["name"], sql_data["description"], sql_data["db_name"],
                 sql_data["table_name"], sql_data["sql_content"], script_id)
            )
            return cursor.rowcount > 0
        except pymysql.IntegrityError:
            show_error("更新失败", f"SQL脚本名称「{sql_data['name']}」已存在！")
        except Exception as e:
            show_error("更新SQL脚本失败", str(e))
        return False

    def delete_sql_script(self, script_id):
        """删除SQL脚本"""
        try:
            cursor = self.get_cursor()
            cursor.execute("DELETE FROM sql_script WHERE id = %s", (script_id,))
            return cursor.rowcount > 0
        except Exception as e:
            show_error("删除SQL脚本失败", str(e))
        return False

    def execute_sql(self, db_name, sql_content):
        """执行SQL脚本（连接目标库）"""
        target_conn = None
        try:
            # 连接目标数据库
            target_conn = pymysql.connect(
                host=DB_CONFIG["host"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                port=DB_CONFIG["port"],
                db=db_name,
                charset=DB_CONFIG["charset"]
            )
            cursor = target_conn.cursor(pymysql.cursors.DictCursor)
            # 执行SQL（支持多语句）
            cursor.execute(sql_content)
            # 获取结果（查询返回数据，其他返回影响行数）
            if sql_content.strip().upper().startswith("SELECT"):
                result = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return {"type": "query", "columns": columns, "data": result}
            else:
                target_conn.commit()
                return {"type": "execute", "affected_rows": cursor.rowcount}
        except Exception as e:
            if target_conn:
                target_conn.rollback()
            show_error("SQL执行失败", str(e))
        finally:
            if target_conn:
                target_conn.close()
        return None

# 单例实例
db_dao = DatabaseDAO()