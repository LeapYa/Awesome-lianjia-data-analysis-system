"""
数据库连接配置
分离API和爬虫的数据库连接池，避免资源竞争
"""
import os
import logging
import psycopg2
from psycopg2 import pool

# 确保logs目录存在
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "db_config.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("db_config")

# 数据库连接参数
DB_PARAMS = {
    "user": "postgres",
    "password": "123456",
    "host": "localhost",
    "port": "5432",
    "database": "rental_analysis",
    "client_encoding": "UTF8"
}

# 连接池设置
# API服务连接池（用于处理Web请求）
API_MIN_CONNECTIONS = 5    # 最小连接数
API_MAX_CONNECTIONS = 50   # 最大连接数

# 爬虫连接池（用于爬虫操作）
CRAWLER_MIN_CONNECTIONS = 5  # 最小连接数
CRAWLER_MAX_CONNECTIONS = 30  # 最大连接数

# 认证服务连接池
AUTH_MIN_CONNECTIONS = 3
AUTH_MAX_CONNECTIONS = 15

# 创建通用连接池
def create_pool(min_conn=2, max_conn=10, application_name="rental_app"):
    """
    创建自定义数据库连接池
    
    Args:
        min_conn: 最小连接数，默认2
        max_conn: 最大连接数，默认10
        application_name: 应用名称，用于在数据库中识别连接来源
        
    Returns:
        pool: 数据库连接池对象，如果创建失败则返回None
    """
    try:
        params = DB_PARAMS.copy()
        params['application_name'] = application_name
        
        custom_pool = psycopg2.pool.SimpleConnectionPool(
            min_conn, 
            max_conn,
            **params
        )
        logger.info(f"{application_name}数据库连接池创建成功，连接数范围: {min_conn}-{max_conn}")
        return custom_pool
    except Exception as e:
        logger.error(f"{application_name}数据库连接池创建失败: {str(e)}")
        return None

# 创建API服务连接池
def create_api_pool():
    try:
        api_pool = psycopg2.pool.SimpleConnectionPool(
            API_MIN_CONNECTIONS, 
            API_MAX_CONNECTIONS,
            **DB_PARAMS,
            application_name="rental_api"
        )
        logger.info(f"API服务数据库连接池创建成功，连接数范围: {API_MIN_CONNECTIONS}-{API_MAX_CONNECTIONS}")
        return api_pool
    except Exception as e:
        logger.error(f"API服务数据库连接池创建失败: {str(e)}")
        return None

# 创建爬虫服务连接池
def create_spider_pool():
    try:
        spider_pool = psycopg2.pool.SimpleConnectionPool(
            CRAWLER_MIN_CONNECTIONS, 
            CRAWLER_MAX_CONNECTIONS,
            **DB_PARAMS,
            application_name="rental_spider"
        )
        logger.info(f"爬虫服务数据库连接池创建成功，连接数范围: {CRAWLER_MIN_CONNECTIONS}-{CRAWLER_MAX_CONNECTIONS}")
        return spider_pool
    except Exception as e:
        logger.error(f"爬虫服务数据库连接池创建失败: {str(e)}")
        return None

# 获取数据库连接的辅助函数
def get_connection(connection_pool):
    """从连接池获取数据库连接，确保在使用后正确归还"""
    if not connection_pool:
        logger.error("数据库连接池不可用")
        raise Exception("数据库连接池不可用")
    try:
        conn = connection_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"从连接池获取连接失败: {str(e)}")
        raise

# 归还数据库连接的辅助函数
def release_connection(connection_pool, conn):
    """将连接归还到连接池"""
    if connection_pool and conn:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"归还连接到连接池失败: {str(e)}") 