import os
import json
import logging
import threading
import time
import datetime
from typing import Dict, Any, Optional, List, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

# 导入数据库配置和工具
import db_config
import db_utils

# 确保logs目录存在
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)
    
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "verification.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("verification_manager")

# 验证状态常量
VERIFICATION_STATUS = {
    "NONE": "none",              # 无需验证
    "PENDING": "pending",        # 等待验证
    "IN_PROGRESS": "in_progress", # 正在验证中
    "COMPLETED": "completed",    # 验证完成
    "FAILED": "failed"           # 验证失败
}

# 验证会话存储目录
COOKIES_DIR = "verification_cookies"
os.makedirs(COOKIES_DIR, exist_ok=True)

# 创建验证管理器专用的数据库连接池
try:
    verification_pool = db_config.create_pool(
        min_conn=1, 
        max_conn=5, 
        application_name="verification_manager"
    )
    logger.info("验证管理器数据库连接池创建成功")
except Exception as e:
    logger.error(f"验证管理器数据库连接池创建失败: {str(e)}")
    verification_pool = None

# 创建装饰器实例
with_db_connection = db_utils.with_db_connection(verification_pool)

@with_db_connection
def create_verification_session(conn, task_id: int, city_code: str, page_url: str) -> int:
    """创建新的验证会话，返回会话ID"""
    try:
        cursor = conn.cursor()
        
        # 检查是否已存在会话
        cursor.execute(
            "SELECT id FROM verification_session WHERE task_id = %s AND status = %s",
            (task_id, VERIFICATION_STATUS["PENDING"])
        )
        existing = cursor.fetchone()
        
        if existing:
            return existing[0]
        
        # 创建新会话
        cursor.execute(
            "INSERT INTO verification_session (task_id, city_code, status, page_url) VALUES (%s, %s, %s, %s) RETURNING id",
            (task_id, city_code, VERIFICATION_STATUS["PENDING"], page_url)
        )
        session_id = cursor.fetchone()[0]
        
        # 生成验证URL
        verification_url = f"/verify/{session_id}"
        
        # 更新会话URL
        cursor.execute(
            "UPDATE verification_session SET verification_url = %s WHERE id = %s",
            (verification_url, session_id)
        )
        
        conn.commit()
        logger.info(f"创建验证会话成功，会话ID: {session_id}, 任务ID: {task_id}")
        return session_id
    except Exception as e:
        logger.error(f"创建验证会话失败: {str(e)}")
        return None

@with_db_connection
def get_verification_session(conn, session_id: int) -> Dict[str, Any]:
    """获取验证会话信息"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM verification_session WHERE id = %s", (session_id,))
        session = cursor.fetchone()
        
        return dict(session) if session else None
    except Exception as e:
        logger.error(f"获取验证会话失败: {str(e)}")
        return None

@with_db_connection
def update_verification_status(conn, session_id: int, status: str, error_message: str = None) -> bool:
    """更新验证会话状态"""
    try:
        cursor = conn.cursor()
        
        update_fields = ["status = %s", "updated_at = NOW()"]
        params = [status]
        
        if error_message:
            update_fields.append("error_message = %s")
            params.append(error_message)
        
        query = f"UPDATE verification_session SET {', '.join(update_fields)} WHERE id = %s"
        params.append(session_id)
        
        cursor.execute(query, params)
        conn.commit()
        
        logger.info(f"更新验证会话状态成功，会话ID: {session_id}, 状态: {status}")
        return True
    except Exception as e:
        logger.error(f"更新验证会话状态失败: {str(e)}")
        return False

@with_db_connection
def save_verification_cookies(conn, session_id: int, cookies: List[Dict]) -> bool:
    """保存验证完成后的cookie"""
    try:
        # 确保目录存在
        os.makedirs(COOKIES_DIR, exist_ok=True)
        
        # 生成cookie文件路径
        cookies_path = os.path.join(COOKIES_DIR, f"session_{session_id}.json")
        
        # 保存cookie到文件
        with open(cookies_path, 'w') as f:
            json.dump(cookies, f)
        
        # 更新数据库中的cookie路径
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE verification_session SET cookies_path = %s, status = %s, updated_at = NOW() WHERE id = %s",
            (cookies_path, VERIFICATION_STATUS["COMPLETED"], session_id)
        )
        
        conn.commit()
        logger.info(f"保存验证cookie成功，会话ID: {session_id}")
        return True
    except Exception as e:
        logger.error(f"保存验证cookie失败: {str(e)}")
        return False

@with_db_connection
def load_verification_cookies(conn, session_id: int) -> List[Dict]:
    """加载已保存的cookie"""
    try:
        # 从数据库获取cookie路径
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT cookies_path FROM verification_session WHERE id = %s",
            (session_id,)
        )
        
        result = cursor.fetchone()
        
        if not result or not result[0]:
            logger.warning(f"未找到会话 {session_id} 的cookie路径")
            return None
        
        cookies_path = result[0]
        
        # 检查文件是否存在
        if not os.path.exists(cookies_path):
            logger.warning(f"验证cookie文件不存在: {cookies_path}")
            return None
        
        # 从文件加载cookie
        with open(cookies_path, 'r') as f:
            cookies = json.load(f)
        
        if not cookies:
            logger.warning(f"验证cookie文件为空: {cookies_path}")
            return None
        
        logger.info(f"加载验证cookie成功，会话ID: {session_id}，找到 {len(cookies)} 个cookie")
        
        # 打印前3个cookie的关键信息进行调试
        for i, cookie in enumerate(cookies[:3]):
            logger.info(f"Cookie {i+1}: name={cookie.get('name')}, domain={cookie.get('domain')}, path={cookie.get('path')}")
        
        return cookies
    except Exception as e:
        logger.error(f"加载验证cookie失败: {str(e)}")
        return None

@with_db_connection
def get_latest_verification_session_for_task(conn, task_id: int) -> Dict[str, Any]:
    """获取任务的最新验证会话"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT * FROM verification_session WHERE task_id = %s ORDER BY updated_at DESC LIMIT 1",
            (task_id,)
        )
        
        session = cursor.fetchone()
        return dict(session) if session else None
    except Exception as e:
        logger.error(f"获取任务验证会话失败: {str(e)}")
        return None

@with_db_connection
def get_pending_verification_sessions(conn) -> List[Dict[str, Any]]:
    """获取所有待处理的验证会话"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT * FROM verification_session WHERE status = %s ORDER BY created_at",
            (VERIFICATION_STATUS["PENDING"],)
        )
        
        sessions = cursor.fetchall()
        return [dict(session) for session in sessions]
    except Exception as e:
        logger.error(f"获取待处理验证会话失败: {str(e)}")
        return []

# 验证会话监控
def verification_monitor(interval=30):
    """定期监控验证会话状态"""
    while True:
        try:
            # 检查超时的会话
            if verification_pool:
                conn = db_config.get_connection(verification_pool)
                try:
                    cursor = conn.cursor()
                    
                    # 获取超过30分钟未更新的待处理会话
                    timeout_threshold = datetime.datetime.now() - datetime.timedelta(minutes=30)
                    
                    cursor.execute(
                        "SELECT id FROM verification_session WHERE status = %s AND updated_at < %s",
                        (VERIFICATION_STATUS["PENDING"], timeout_threshold)
                    )
                    
                    timeout_sessions = cursor.fetchall()
                    
                    # 将超时会话标记为失败
                    for session in timeout_sessions:
                        session_id = session[0]
                        cursor.execute(
                            "UPDATE verification_session SET status = %s, error_message = %s, updated_at = NOW() WHERE id = %s",
                            (VERIFICATION_STATUS["FAILED"], "验证会话超时", session_id)
                        )
                        logger.warning(f"验证会话 {session_id} 已超时，标记为失败")
                    
                    conn.commit()
                finally:
                    db_config.release_connection(verification_pool, conn)
            
        except Exception as e:
            logger.error(f"验证监控错误: {str(e)}")
        
        time.sleep(interval)

# 启动监控线程
def start_monitoring():
    """启动验证会话监控线程"""
    monitor_thread = threading.Thread(target=verification_monitor, daemon=True)
    monitor_thread.start()
    logger.info("验证会话监控线程已启动")

# 初始化
if __name__ == "__main__":
    start_monitoring() 