#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@作者: laity.wang
@创建日期: 2026/2/4 11:50
@文件名: dao.py
@项目名称: python-test-popup
@文件完整绝对路径: D:/LaityTest/python-test-popup/db\dao.py
@文件相对项目路径:   # 可选，不需要可以删掉这行
@描述: 
"""

import pymysql
import json
import logging
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
        logging.info("开始初始化数据库...")
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
            logging.info(f"数据库{DB_CONFIG['db']}创建/验证成功")
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
            logging.info("接口表api_info创建/验证成功")

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
            logging.info("SQL脚本表sql_script创建/验证成功")

            conn.commit()
            cursor.close()
            conn.close()

            # 5. 连接目标数据库
            self.connect_db()
            logging.info("数据库初始化完成")

        except Exception as e:
            err_msg = f"原因：{str(e)}"
            show_error("数据库初始化失败", err_msg)
            logging.error(f"数据库初始化失败：{err_msg}", exc_info=True)

    def connect_db(self):
        """连接数据库"""
        logging.info(f"正在连接数据库：{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['db']}")
        try:
            self.conn = pymysql.connect(**DB_CONFIG)
            self.conn.autocommit(True)
            logging.info("数据库连接成功")
        except Exception as e:
            err_msg = f"原因：{str(e)}"
            show_error("数据库连接失败", err_msg)
            logging.error(f"数据库连接失败：{err_msg}", exc_info=True)
            self.conn = None

    def get_cursor(self):
        """获取游标（自动重连）"""
        if not self.conn or self.conn._closed:
            logging.warning("数据库连接已断开，尝试重连...")
            self.connect_db()
        return self.conn.cursor(pymysql.cursors.DictCursor)

    # ------------------------------ 接口表操作 ------------------------------
    def add_api(self, api_data):
        """添加接口：api_data = {name, url, method, params, headers}"""
        logging.info(f"添加接口：{api_data['name']}")
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
            logging.info(f"接口{api_data['name']}添加成功")
            return True
        except pymysql.IntegrityError:
            err_msg = f"接口名称「{api_data['name']}」已存在！"
            show_error("添加失败", err_msg)
            logging.error(err_msg)
        except Exception as e:
            err_msg = str(e)
            show_error("添加接口失败", err_msg)
            logging.error(f"添加接口失败：{err_msg}", exc_info=True)
        return False

    def get_all_apis(self):
        """查询所有接口"""
        logging.info("查询所有接口")
        try:
            cursor = self.get_cursor()
            cursor.execute("SELECT * FROM api_info ORDER BY update_time DESC")
            result = cursor.fetchall()
            logging.info(f"查询到{len(result)}个接口")
            return result
        except Exception as e:
            err_msg = str(e)
            show_error("查询接口失败", err_msg)
            logging.error(f"查询接口失败：{err_msg}", exc_info=True)
        return []

    def get_api_by_id(self, api_id):
        """根据ID查询接口"""
        logging.info(f"根据ID查询接口：{api_id}")
        try:
            cursor = self.get_cursor()
            cursor.execute("SELECT * FROM api_info WHERE id = %s", (api_id,))
            result = cursor.fetchone()
            logging.info(f"接口ID{api_id}查询结果：{result is not None}")
            return result
        except Exception as e:
            err_msg = str(e)
            show_error("查询接口失败", err_msg)
            logging.error(f"查询接口失败：{err_msg}", exc_info=True)
        return None

    def update_api(self, api_id, api_data):
        """更新接口"""
        logging.info(f"更新接口ID：{api_id}，名称：{api_data['name']}")
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
            rows_affected = cursor.rowcount > 0
            logging.info(f"接口ID{api_id}更新成功：{rows_affected}")
            return rows_affected
        except pymysql.IntegrityError:
            err_msg = f"接口名称「{api_data['name']}」已存在！"
            show_error("更新失败", err_msg)
            logging.error(err_msg)
        except Exception as e:
            err_msg = str(e)
            show_error("更新接口失败", err_msg)
            logging.error(f"更新接口失败：{err_msg}", exc_info=True)
        return False

    def delete_api(self, api_id):
        """删除接口"""
        logging.info(f"删除接口ID：{api_id}")
        try:
            cursor = self.get_cursor()
            cursor.execute("DELETE FROM api_info WHERE id = %s", (api_id,))
            rows_affected = cursor.rowcount > 0
            logging.info(f"接口ID{api_id}删除成功：{rows_affected}")
            return rows_affected
        except Exception as e:
            err_msg = str(e)
            show_error("删除接口失败", err_msg)
            logging.error(f"删除接口失败：{err_msg}", exc_info=True)
        return False

    # ------------------------------ SQL脚本表操作 ------------------------------
    def add_sql_script(self, sql_data):
        """添加SQL脚本：sql_data = {name, description, db_name, table_name, sql_content}"""
        logging.info(f"添加SQL脚本：{sql_data['name']}")
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
            logging.info(f"SQL脚本{sql_data['name']}添加成功")
            return True
        except pymysql.IntegrityError:
            err_msg = f"SQL脚本名称「{sql_data['name']}」已存在！"
            show_error("添加失败", err_msg)
            logging.error(err_msg)
        except Exception as e:
            err_msg = str(e)
            show_error("添加SQL脚本失败", err_msg)
            logging.error(f"添加SQL脚本失败：{err_msg}", exc_info=True)
        return False

    def get_all_sql_scripts(self):
        """查询所有SQL脚本"""
        logging.info("查询所有SQL脚本")
        try:
            cursor = self.get_cursor()
            cursor.execute("SELECT * FROM sql_script ORDER BY update_time DESC")
            result = cursor.fetchall()
            logging.info(f"查询到{len(result)}个SQL脚本")
            return result
        except Exception as e:
            err_msg = str(e)
            show_error("查询SQL脚本失败", err_msg)
            logging.error(f"查询SQL脚本失败：{err_msg}", exc_info=True)
        return []

    def get_sql_script_by_id(self, script_id):
        """根据ID查询SQL脚本"""
        logging.info(f"根据ID查询SQL脚本：{script_id}")
        try:
            cursor = self.get_cursor()
            cursor.execute("SELECT * FROM sql_script WHERE id = %s", (script_id,))
            result = cursor.fetchone()
            logging.info(f"SQL脚本ID{script_id}查询结果：{result is not None}")
            return result
        except Exception as e:
            err_msg = str(e)
            show_error("查询SQL脚本失败", err_msg)
            logging.error(f"查询SQL脚本失败：{err_msg}", exc_info=True)
        return None

    def update_sql_script(self, script_id, sql_data):
        """更新SQL脚本"""
        logging.info(f"更新SQL脚本ID：{script_id}，名称：{sql_data['name']}")
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
            rows_affected = cursor.rowcount > 0
            logging.info(f"SQL脚本ID{script_id}更新成功：{rows_affected}")
            return rows_affected
        except pymysql.IntegrityError:
            err_msg = f"SQL脚本名称「{sql_data['name']}」已存在！"
            show_error("更新失败", err_msg)
            logging.error(err_msg)
        except Exception as e:
            err_msg = str(e)
            show_error("更新SQL脚本失败", err_msg)
            logging.error(f"更新SQL脚本失败：{err_msg}", exc_info=True)
        return False

    def delete_sql_script(self, script_id):
        """删除SQL脚本"""
        logging.info(f"删除SQL脚本ID：{script_id}")
        try:
            cursor = self.get_cursor()
            cursor.execute("DELETE FROM sql_script WHERE id = %s", (script_id,))
            rows_affected = cursor.rowcount > 0
            logging.info(f"SQL脚本ID{script_id}删除成功：{rows_affected}")
            return rows_affected
        except Exception as e:
            err_msg = str(e)
            show_error("删除SQL脚本失败", err_msg)
            logging.error(f"删除SQL脚本失败：{err_msg}", exc_info=True)
        return False

    def execute_sql(self, db_name, sql_content):
        """执行SQL脚本（连接目标库）"""
        logging.info(f"执行SQL脚本，目标库：{db_name}，SQL：{sql_content[:100]}...")
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
                logging.info(f"SQL查询成功，返回{len(result)}行数据")
                return {"type": "query", "columns": columns, "data": result}
            else:
                target_conn.commit()
                logging.info(f"SQL执行成功，影响行数：{cursor.rowcount}")
                return {"type": "execute", "affected_rows": cursor.rowcount}
        except Exception as e:
            if target_conn:
                target_conn.rollback()
            err_msg = str(e)
            show_error("SQL执行失败", err_msg)
            logging.error(f"SQL执行失败：{err_msg}", exc_info=True)
        finally:
            if target_conn:
                target_conn.close()
        return None


# 单例实例
db_dao = DatabaseDAO()