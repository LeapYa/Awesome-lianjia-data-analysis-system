"""
数据库工具函数
提供数据库连接和操作的通用功能，避免代码重复
"""
import os
import logging
import db_config
from psycopg2.extras import RealDictCursor

# 确保logs目录存在
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "db_utils.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("db_utils")

EMAIL_ENCRYPTION_KEY = os.getenv("EMAIL_ENCRYPTION_KEY", "very_secure_encryption_key_change_me")

def get_db_connection():
    """获取通用数据库连接"""
    try:
        # 创建通用连接池
        if not hasattr(get_db_connection, 'pool'):
            get_db_connection.pool = db_config.create_pool(
                min_conn=1, 
                max_conn=5, 
                application_name="db_utils"
            )
        
        conn = db_config.get_connection(get_db_connection.pool)
        conn.cursor_factory = RealDictCursor
        return conn
    except Exception as e:
        logger.error(f"获取数据库连接失败: {str(e)}")
        raise

def release_db_connection(conn):
    """释放数据库连接"""
    try:
        if hasattr(get_db_connection, 'pool') and get_db_connection.pool:
            db_config.release_connection(get_db_connection.pool, conn)
    except Exception as e:
        logger.error(f"释放数据库连接失败: {str(e)}")

def store_email(email: str) -> str:
    """直接返回邮箱明文"""
    return email

def get_email(stored_email: str) -> str:
    """直接返回存储的邮箱"""
    return stored_email

def with_db_connection(connection_pool):
    """
    装饰器工厂函数，返回一个确保数据库连接在使用后被正确归还到连接池的装饰器
    
    Args:
        connection_pool: 使用的数据库连接池
        
    Returns:
        decorator: 用于装饰数据库操作函数的装饰器
    """
    def decorator(func):
        """
        装饰器函数，确保数据库连接在使用后被正确归还到连接池
        无论函数执行是否出现异常，都会确保连接被归还
        
        Args:
            func: 被装饰的函数，第一个参数必须是数据库连接
            
        Returns:
            wrapper: 包装后的函数
        """
        def wrapper(*args, **kwargs):
            conn = None
            try:
                conn = db_config.get_connection(connection_pool)
                # 将连接作为第一个参数传递给被装饰的函数
                return func(conn, *args, **kwargs)
            except Exception as e:
                logger.error(f"数据库操作出错: {str(e)}")
                raise
            finally:
                if conn is not None:
                    db_config.release_connection(connection_pool, conn)
                    logger.debug("数据库连接已归还到连接池")
        return wrapper
    return decorator

def execute_query(conn, query, params=None, fetch=True):
    """
    执行数据库查询并返回结果
    
    Args:
        conn: 数据库连接
        query: SQL查询语句
        params: 查询参数，默认为None
        fetch: 是否获取结果，默认为True
        
    Returns:
        results: 查询结果，如果fetch为False则返回None
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        if fetch:
            return cursor.fetchall()
        return None
    finally:
        cursor.close()

def execute_query_single(conn, query, params=None):
    """
    执行数据库查询并返回单个结果
    
    Args:
        conn: 数据库连接
        query: SQL查询语句
        params: 查询参数，默认为None
        
    Returns:
        result: 查询的第一行结果，如果没有结果则返回None
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        return cursor.fetchone()
    finally:
        cursor.close()

def execute_update(conn, query, params=None, commit=True):
    """
    执行数据库更新操作
    
    Args:
        conn: 数据库连接
        query: SQL更新语句
        params: 更新参数，默认为None
        commit: 是否提交事务，默认为True
        
    Returns:
        affected_rows: 受影响的行数
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        affected_rows = cursor.rowcount
        if commit:
            conn.commit()
        return affected_rows
    except Exception as e:
        if commit:
            conn.rollback()
        raise e
    finally:
        cursor.close() 