import time
import random
import re
import logging
import datetime
import traceback
import os
import json
import psycopg2
from psycopg2 import pool
from psycopg2 import errors as psycopg2_errors
from urllib.parse import urlparse
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import threading
import concurrent.futures  # 导入并行处理模块
import ip_manager  # 导入IP管理模块
# 导入数据库配置
import db_config
# 导入数据库工具
import db_utils
# 导入数据分析模块
import data_processor

# 导入DrissionPage
from DrissionPage import ChromiumPage
from DrissionPage.errors import ElementNotFoundError
from DrissionPage._configs.chromium_options import ChromiumOptions
import cv2
import numpy as np
# 导入验证管理器
import verification_manager

# 确保logs目录存在
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "selenium_spider.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("rental_selenium_spider")

# 调整日志级别，减少不必要的输出
file_handler = logging.FileHandler(os.path.join(logs_dir, "selenium_spider_detail.log"), encoding="utf-8")
file_handler.setLevel(logging.ERROR)
# 控制台只显示重要信息
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
# 重新配置logger处理器
logger.handlers = [file_handler, console_handler]

# 创建爬虫专用的数据库连接池
connection_pool = db_config.create_spider_pool()
if not connection_pool:
    logger.error("无法创建爬虫数据库连接池，程序可能无法正常工作")

# 获取数据库连接的辅助函数
def get_db_connection():
    """从连接池获取数据库连接，并确保使用后正确归还"""
    return db_config.get_connection(connection_pool)

# 创建装饰器实例，专用于爬虫连接池
with_db_connection = db_utils.with_db_connection(connection_pool)

# 存储线程ID到WebDriver的映射
_thread_driver_map = {}

# 初始默认值，会在setup_driver中更新为实际值
BROWSER_WINDOW_WIDTH = 1920
BROWSER_WINDOW_HEIGHT = 1080

def register_driver(driver):
    """注册当前线程的WebDriver对象"""
    thread_id = threading.current_thread().ident
    _thread_driver_map[thread_id] = driver
    logger.info(f"已注册线程 {thread_id} 的WebDriver对象")
    return thread_id

def get_current_driver(thread_id=None):
    """获取当前线程或指定线程的WebDriver对象"""
    if thread_id is None:
        thread_id = threading.current_thread().ident
    
    driver = _thread_driver_map.get(thread_id)
    if driver:
        logger.info(f"已找到线程 {thread_id} 的WebDriver对象")
    else:
        logger.warning(f"未找到线程 {thread_id} 的WebDriver对象")
    
    return driver

def unregister_driver():
    """注销当前线程的WebDriver对象"""
    thread_id = threading.current_thread().ident
    if thread_id in _thread_driver_map:
        del _thread_driver_map[thread_id]
        logger.info(f"已注销线程 {thread_id} 的WebDriver对象")

def get_house_id_from_url(url):
    """从URL中提取房源ID"""
    try:
        if not url:
            logger.warning("尝试从空URL提取house_id")
            return None
            
        # 记录正在处理的URL
        logger.info(f"正在从URL提取house_id: {url}")
        
        # 例如从 https://nj.zu.ke.com/zufang/ZHANJIANG2032311205850251264.html 提取ID
        match = re.search(r'zufang/(\w+)\.html', url)
        if match:
            house_id = match.group(1)
            logger.info(f"从zufang类型URL提取到house_id: {house_id}")
            return house_id
        
        # 处理公寓类型URL: https://sh.zu.ke.com/apartment/74943.html
        apartment_match = re.search(r'apartment/(\d+)\.html', url)
        if apartment_match:
            # 添加前缀以区分公寓类型ID
            house_id = f"APT{apartment_match.group(1)}"
            logger.info(f"从apartment类型URL提取到house_id: {house_id}")
            return house_id
            
        # 处理其他可能的格式: 例如https://sh.zu.ke.com/details/12345.html
        details_match = re.search(r'details/(\w+)\.html', url)
        if details_match:
            house_id = f"DTL{details_match.group(1)}"
            logger.info(f"从details类型URL提取到house_id: {house_id}")
            return house_id
            
        # 如果没有匹配的格式，从整个URL生成一个唯一ID
        logger.warning(f"未能匹配URL格式: {url}，将生成哈希ID")
        import hashlib
        hash_id = "URL" + hashlib.md5(url.encode()).hexdigest()[:20]
        logger.info(f"为未知格式URL生成哈希ID: {hash_id}")
        return hash_id
    except Exception as e:
        logger.error(f"从URL提取house_id时出错: {str(e)}，URL: {url}")
        # 出错时也生成一个基于URL的唯一ID
        import hashlib
        return "ERR" + hashlib.md5(url.encode()).hexdigest()[:20]

def parse_room_info(room_text):
    """解析户型信息，提取房间数、厅数和卫生间数"""
    try:
        room_count = hall_count = bath_count = 0
        room_match = re.search(r'(\d+)室', room_text)
        hall_match = re.search(r'(\d+)厅', room_text)
        bath_match = re.search(r'(\d+)卫', room_text)
        
        if room_match:
            room_count = int(room_match.group(1))
        if hall_match:
            hall_count = int(hall_match.group(1))
        if bath_match:
            bath_count = int(bath_match.group(1))
            
        return room_count, hall_count, bath_count
    except:
        return 0, 0, 0

def parse_layout_to_components(layout_str):
    """
    解析户型布局字符串（如"2室1厅1卫"、"开间"等）为组件
    
    Returns:
        tuple: (room_description, room_count, hall_count, bath_count)
    """
    if not layout_str:
        return "", 0, 0, 0
        
    layout_str = layout_str.strip()
    
    # 特殊情况：开间通常是1室0厅1卫
    if layout_str == "开间":
        return "开间", 1, 0, 1
        
    # 使用已有函数解析
    room_count, hall_count, bath_count = parse_room_info(layout_str)
    
    # 如果没有找到卫生间数量但有卧室，默认为1卫
    if bath_count == 0 and room_count > 0:
        bath_count = 1
        
    return layout_str, room_count, hall_count, bath_count

def start_crawl_task(city, city_code):
    """开始一个新的爬虫任务"""
    if not connection_pool:
        logger.error("数据库连接池不可用，无法创建爬虫任务")
        return None
    
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        # 插入新任务记录
        cursor.execute(
            "INSERT INTO crawl_task (city, city_code, start_time, status) VALUES (%s, %s, %s, %s) RETURNING id",
            (city, city_code, datetime.datetime.now(), "In Progress")
        )
        task_id = cursor.fetchone()[0]
        conn.commit()
        logger.info(f"创建爬虫任务成功，任务ID: {task_id}")
        return task_id
    except Exception as e:
        logger.error(f"创建爬虫任务失败: {str(e)}")
        return None
    finally:
        if conn:
            connection_pool.putconn(conn)

@with_db_connection
def update_crawl_task(conn, task_id, status, success_items=None, success_pages=None, 
                   failed_pages=None, end_time=None, error=None, total_pages=None, expected_items=None):
    """
    更新爬虫任务状态
    """
    try:
        cursor = conn.cursor()
        
        set_clauses = ["status = %s"]
        params = [status]
        
        # 添加可选参数到更新语句中
        if success_items is not None:
            set_clauses.append("success_items = %s")
            params.append(success_items)
        
        if success_pages is not None:
            set_clauses.append("success_pages = %s")
            params.append(success_pages)
            
        if failed_pages is not None:
            set_clauses.append("failed_pages = %s")
            params.append(failed_pages)
        
        if total_pages is not None:
            set_clauses.append("total_pages = %s")
            params.append(total_pages)
            
        if expected_items is not None:
            set_clauses.append("total_items = %s")
            params.append(expected_items)
            
        if end_time is not None:
            set_clauses.append("end_time = %s")
            params.append(end_time)
            
        if error is not None:
            set_clauses.append("error_message = %s")
            params.append(error)
            
        # 构建SQL更新语句
        query = f"UPDATE crawl_task SET {', '.join(set_clauses)} WHERE id = %s"
        params.append(task_id)
        
        # 执行更新
        cursor.execute(query, params)
        conn.commit()
        
        logger.info(f"更新爬虫任务成功，任务ID: {task_id}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"更新爬虫任务失败: {str(e)}")
        return False

@with_db_connection
def save_house_info(conn, house_info):
    """
    保存房源信息到数据库，添加重试机制
    数据库在house_info字典中对应的字段名
    id: ID/主键
    house_id -> house_id: 房源ID
    task_id -> task_id: 任务ID
    title -> title: 房源标题
    price -> price: 价格
    district -> location_qu: 位置（区）
    community -> location_big: 位置（大区域/商圈）
    # location_small: 位置（小区域/街道）
    area -> size: 面积/大小
    direction -> direction: 朝向
    features -> room: 房型描述
    floor -> floor: 楼层
    image_url -> image: 图片
    url -> link: 链接
    # unit_price: 单位价格/每平米价格
    room_count: 卧室数量(需要从layout中解析)
    hall_count: 客厅数量(需要从layout中解析)
    bath_count: 卫生间数量(需要从layout中解析)
    layout -> layout: 户型布局
    city_code -> city_code: 城市代码
    publish_date -> publish_date: 发布日期
    features -> features: 特色标签
    created_at -> created_at: 创建时间
    last_updated -> last_updated: 最后更新时间
    """
    max_retries = 3
    retry_count = 0
    retry_delay = 2  # 初始延迟2秒
    
    while retry_count < max_retries:
        try:
            cursor = conn.cursor()
            
            # 确保有house_id，从URL提取
            if 'house_id' not in house_info or not house_info['house_id']:
                house_info['house_id'] = get_house_id_from_url(house_info['url'])
                
                # 如果获取失败，使用备用方法生成ID
                if not house_info['house_id']:
                    logger.warning(f"无法从URL提取house_id: {house_info['url']}")
                    import hashlib
                    house_info['house_id'] = "HASH" + hashlib.md5(house_info['url'].encode()).hexdigest()[:20]
                    logger.info(f"生成备用house_id: {house_info['house_id']}")
            
            # 解析户型字段，提取房间、厅和卫生间数量
            layout_str = house_info.get('layout', '')
            room_description, room_count, hall_count, bath_count = parse_layout_to_components(layout_str)
            
            # 计算单价
            unit_price = 0
            try:
                price = float(house_info.get('price', 0))
                area = float(house_info.get('area', 0))
                if price > 0 and area > 0:
                    unit_price = round(price / area, 2)
            except (ValueError, TypeError):
                logger.warning(f"计算单价失败: price={house_info.get('price')}, area={house_info.get('area')}")
            
            logger.info(f"准备保存房源，house_id: {house_info.get('house_id', '空')}, URL: {house_info.get('url', '空')}")
            
            # 记录所有将要保存的字段
            log_fields = {k: v for k, v in house_info.items() if k != 'features'}
            logger.info(f"房源信息字段: {log_fields}")
            
            # 首先检查是否已存在相同的house_id
            cursor.execute(
                "SELECT id FROM house_info WHERE house_id = %s",
                (house_info['house_id'],)
            )
            existing_by_id = cursor.fetchone()
            
            if existing_by_id:
                logger.info(f"更新已存在的房源(根据house_id): {existing_by_id[0]}")
                # 如果house_id存在，则更新
                try:
                    cursor.execute("""
                    UPDATE house_info SET
                        title = %s,
                        price = %s,
                        layout = %s,
                        size = %s,
                        floor = %s,
                        direction = %s,
                        subway = %s,
                        location_qu = %s,
                        location_big = %s,
                        publish_date = %s,
                        features = %s,
                        image = %s,
                        link = %s,
                        city_code = %s,
                        room = %s,
                        room_count = %s,
                        hall_count = %s,
                        bath_count = %s,
                        unit_price = %s,
                        last_updated = %s
                    WHERE house_id = %s
                    """, (
                        house_info['title'],
                        house_info['price'],
                        house_info['layout'],
                        house_info['area'],
                        house_info['floor'],
                        house_info['direction'],
                        house_info['subway'],
                        house_info['district'],
                        house_info['community'],
                        house_info['publish_date'],
                        json.dumps(house_info['features'], ensure_ascii=False),
                        house_info.get('image_url', ''),
                        house_info['url'],
                        house_info['city_code'],
                        room_description,
                        room_count,
                        hall_count,
                        bath_count,
                        unit_price,
                        datetime.datetime.now(),
                        house_info['house_id']
                    ))
                except Exception as update_err:
                    logger.error(f"执行UPDATE语句失败: {str(update_err)}")
                    logger.error(f"UPDATE参数: {house_info}")
                    raise update_err
            else:
                # 检查是否已存在相同的URL和城市代码
                cursor.execute(
                    "SELECT id FROM house_info WHERE link = %s AND city_code = %s",
                    (house_info['url'], house_info['city_code'])
                )
                existing_by_url = cursor.fetchone()
                
                if existing_by_url:
                    logger.info(f"更新已存在的房源(根据URL): {existing_by_url[0]}")
                    # 如果URL和城市代码存在，则更新
                    try:
                        cursor.execute("""
                        UPDATE house_info SET
                            title = %s,
                            price = %s,
                            layout = %s,
                            size = %s,
                            floor = %s,
                            direction = %s,
                            subway = %s,
                            location_qu = %s,
                            location_big = %s,
                            publish_date = %s,
                            features = %s,
                            image = %s,
                            house_id = %s,
                            room = %s,
                            room_count = %s,
                            hall_count = %s,
                            bath_count = %s,
                            unit_price = %s,
                            last_updated = %s
                        WHERE link = %s AND city_code = %s
                        """, (
                            house_info['title'],
                            house_info['price'],
                            house_info['layout'],
                            house_info['area'],
                            house_info['floor'],
                            house_info['direction'],
                            house_info['subway'],
                            house_info['district'],
                            house_info['community'],
                            house_info['publish_date'],
                            json.dumps(house_info['features'], ensure_ascii=False),
                            house_info.get('image_url', ''),
                            house_info['house_id'],
                            room_description,
                            room_count,
                            hall_count,
                            bath_count,
                            unit_price,
                            datetime.datetime.now(),
                            house_info['url'],
                            house_info['city_code']
                        ))
                    except Exception as update_err:
                        logger.error(f"执行UPDATE语句失败: {str(update_err)}")
                        logger.error(f"UPDATE参数: {house_info}")
                        raise update_err
                else:
                    logger.info(f"插入新房源: {house_info['house_id']}")
                    # 如果不存在，则插入
                    try:
                        cursor.execute("""
                        INSERT INTO house_info (
                            link, title, price, layout, size, floor, direction,
                            subway, location_qu, location_big, city_code, publish_date, 
                            features, image, created_at, last_updated, task_id, house_id,
                            room, room_count, hall_count, bath_count, unit_price
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        )
                        """, (
                            house_info['url'],
                            house_info['title'],
                            house_info['price'],
                            house_info['layout'],
                            house_info['area'],
                            house_info['floor'],
                            house_info['direction'],
                            house_info['subway'],
                            house_info['district'],
                            house_info['community'],
                            house_info['city_code'],
                            house_info['publish_date'],
                            json.dumps(house_info['features'], ensure_ascii=False),
                            house_info.get('image_url', ''),
                            datetime.datetime.now(),
                            datetime.datetime.now(),
                            house_info.get('task_id'),
                            house_info['house_id'],
                            room_description,
                            room_count,
                            hall_count,
                            bath_count,
                            unit_price
                        ))
                    except Exception as insert_err:
                        logger.error(f"执行INSERT语句失败: {str(insert_err)}")
                        logger.error(f"INSERT参数: {house_info}")
                        raise insert_err
            
            conn.commit()
            logger.info(f"保存房源成功: {house_info['house_id']}")
            return True
            
        except psycopg2.pool.PoolError as e:
            # 连接池满错误，进行重试
            retry_count += 1
            logger.warning(f"保存房源数据时连接池满，正在进行第{retry_count}次重试. 错误: {str(e)}")
            
            if retry_count < max_retries:
                # 随机增加延迟，避免所有失败请求同时重试
                time.sleep(retry_delay + random.uniform(0, 2))
                retry_delay *= 2  # 指数退避
            else:
                logger.error(f"保存房源信息失败，已超过最大重试次数: {str(e)}")
                return False
                
        except Exception as e:
            # 其他错误
            conn.rollback()
            logger.error(f"保存房源信息失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False
            
    return False  # 所有重试都失败

def get_city_url(city_code, page=1):
    """获取城市租房URL"""
    return f'https://{city_code}.zu.ke.com/zufang/pg{page}'

def is_captcha_page(driver):
    """检测是否是验证码页面"""
    try:
        # 检查页面中是否包含验证码相关元素
        try:
            # DrissionPage的查找元素方法
            captcha_elements = driver.eles('xpath://*[contains(text(), "验证码") or contains(text(), "人机验证") or contains(text(), "安全验证") or contains(@id, "captcha")]')
            if captcha_elements:
                logger.warning("检测到验证码页面")
                return True
        except ElementNotFoundError:
            pass
            
        # 检查页面标题是否包含验证相关字样
        title = driver.title
        if "验证" in title or "captcha" in title.lower():
            logger.warning(f"检测到验证页面，标题: {title}")
            return True
            
        return False
    except Exception as e:
        logger.error(f"检查验证码页面时出错: {str(e)}")
        return False

# 使用直接像素差分法识别滑块缺口
def detect_gap_position(bg_bytes):
    """使用直接像素差分法识别滑块缺口位置"""
    try:
        # 将二进制图像转换为OpenCV格式
        bg_img = cv2.imdecode(np.frombuffer(bg_bytes, np.uint8), cv2.IMREAD_COLOR)
        
        # 保存原始图片用于调试
        cv2.imwrite('debug_original.png', bg_img)
        
        # 获取图像尺寸
        height, width = bg_img.shape[:2]
        
        # 1. 将图像转为灰度图
        gray = cv2.cvtColor(bg_img, cv2.COLOR_BGR2GRAY)
        
        # 2. 对图像进行平滑处理
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 3. 直接计算每一列的像素变化率
        diff_cols = []
        # 搜索范围限制 - 缺口通常在中间偏右位置，非常靠边的位置不太可能
        search_start = int(width * 0.2)  # 从20%处开始搜索
        search_end = int(width * 0.8)    # 搜索到80%
        
        # 这里我们计算每一列的相邻像素差分总和，突变处差分值较大
        for i in range(search_start, search_end):
            # 计算列内相邻像素的差异
            col = blur[:, i]
            next_col = blur[:, i+1]
            # 计算差分绝对值的和
            diff = np.sum(np.abs(col.astype(float) - next_col.astype(float)))
            diff_cols.append((i, diff))
        
        # 制作差分可视化图像
        diff_img = bg_img.copy()
        diff_vals = [d[1] for d in diff_cols]
        max_diff = max(diff_vals) if diff_vals else 1
        
        for i, diff_val in enumerate(diff_vals):
            normalized = int((diff_val / max_diff) * 200)  # 归一化到0-200的范围，作为线的高度
            x_pos = diff_cols[i][0]
            # 绘制线条，差异越大，线条越高
            cv2.line(diff_img, (x_pos, height), (x_pos, height - normalized), (0, 0, 255), 1)
        
        # # 保存差分可视化图像
        # cv2.imwrite('debug_diff.png', diff_img)
        
        # 4. 找出差异最大的几个点
        # 对差分值进行排序
        sorted_diffs = sorted(diff_cols, key=lambda x: x[1], reverse=True)
        
        # 取前10个点，这些点很可能是缺口位置
        top_points = sorted_diffs[:10]
        
        # 5. 对这些点进行聚类，过滤掉孤立点
        # 首先按x坐标排序
        top_points.sort(key=lambda x: x[0])
        
        # 找到相邻点的簇
        clusters = []
        current_cluster = [top_points[0]]
        
        for i in range(1, len(top_points)):
            # 如果当前点与上一点距离较近，加入同一簇
            if top_points[i][0] - top_points[i-1][0] < 10:  # 10像素内认为是同一簇
                current_cluster.append(top_points[i])
            else:
                # 否则开始新的簇
                clusters.append(current_cluster)
                current_cluster = [top_points[i]]
        
        # 添加最后一个簇
        if current_cluster:
            clusters.append(current_cluster)
        
        # 6. 选取最大的簇
        best_cluster = max(clusters, key=lambda c: sum(p[1] for p in c)) if clusters else []
        
        if best_cluster:
            # 计算簇的中心点位置
            cluster_x = int(sum(p[0] for p in best_cluster) / len(best_cluster))
            
            # 7. 创建最终可视化结果
            result_img = bg_img.copy()
            
            # 在所有可能的点上画上红点
            for x, _ in top_points:
                cv2.circle(result_img, (x, height//2), 3, (0, 0, 255), -1)
            
            # 在选中的簇中心点画一条垂直线
            cv2.line(result_img, (cluster_x, 0), (cluster_x, height), (0, 0, 255), 2)
            
            # 不再缩放距离，直接使用检测到的原始位置
            slide_distance = cluster_x
            
            # 添加位置信息文本
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(result_img, f"Detected: {cluster_x}px", (10, 30), font, 0.7, (0, 0, 255), 2)
            cv2.putText(result_img, f"Slide: {slide_distance}px", (10, 60), font, 0.7, (0, 0, 255), 2)
            
            # 保存最终结果图像
            cv2.imwrite('debug_final_detection.png', result_img)
            
            logger.info(f"像素差分法检测到缺口位置: x={cluster_x}")
            
            return slide_distance
        else:
            logger.warning("未能检测到明显的缺口")
            # 如果没有找到明显缺口，提供一个中等默认值
            return 80
    
    except Exception as e:
        logger.error(f"缺口识别失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        # 使用固定默认距离，而不是动态调整
        dis = 80
        logger.info(f"使用默认距离: {dis}px")
        return dis

# 处理滑块验证码
def solve_slider_captcha(page, session_id=None):
    """
    使用DrissionPage解决滑块验证码，无限尝试直到成功
    
    Args:
        page: DrissionPage实例
        session_id: 会话ID，用于记录日志
        
    Returns:
        Dict: 处理结果
    """
    attempt = 0
    logger.info(f"开始处理滑块验证码 [尝试 {attempt}], 会话ID: {session_id}")
    
    # 1. 点击开始验证按钮
    try:
        # 查找开始验证按钮
        verify_btns = page.eles('xpath://div/div[@aria-label]')
        if verify_btns:
            logger.info(f"找到开始验证按钮，准备点击")
            verify_btns[0].click()
        else:
            logger.info("未找到开始验证按钮，尝试直接操作当前验证内容")
    except Exception as e:
        logger.warning(f"点击开始验证按钮失败: {str(e)}")
        
    # 2. 休眠等待验证码加载
    time.sleep(2)
    while True:  # 无限循环尝试
        attempt += 1
        # 3. 获取滑块验证码有缺口的图片
        logger.info("获取背景图片")
        bg_src = page.run_js('return window.getComputedStyle(document.getElementsByClassName("geetest_bg")[0]).backgroundImage.slice(5, -2)')
        response = requests.get(bg_src)
        response.raise_for_status()
        bg_bytes = response.content  # 保存原始字节用于处理
        
        if not bg_src:
            logger.error("无法获取背景图片")
            continue  # 尝试下一次
        
        # 4. 获取要滑动的图片 (仅记录，不使用)
        logger.info("获取滑块图片")
        full_src = page.run_js('return window.getComputedStyle(document.getElementsByClassName("geetest_slice_bg")[0]).backgroundImage.slice(5, -2)')
        
        # 5. 缺口识别 - 使用像素差分法
        logger.info("使用像素差分法识别缺口位置")
        try:
            # 使用像素差分法识别
            dis = detect_gap_position(bg_bytes)
            logger.info(f"像素差分法识别的缺口位置: x={dis}")
            
            # 不再限制距离范围
                
        except Exception as e:
            logger.error(f"缺口识别失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            # 使用默认距离
            dis = 80
            logger.info(f"使用默认距离: {dis}px")
        
        # 6. 拖动滑块
        logger.info(f"开始拖动滑块，距离: {dis}px")
        try:
            # 查找滑块按钮
            slide_btn = page.ele('xpath://div[contains(@class,"geetest_track")]/div[contains(@class, "geetest_btn")]')
            
            # 如果未找到滑块按钮，尝试查找滑块元素
            if not slide_btn:
                logger.warning("未找到滑块按钮，尝试查找滑块元素")
                slide_btn = page.ele_at_point(20, 200)  # 估计位置
                if slide_btn:
                    logger.info(f"在估计位置找到元素: {slide_btn.tag}")
            
            if not slide_btn:
                logger.error("无法找到滑块按钮")
                continue  # 尝试下一次
            
            # 获取动作链对象
            actions = page.actions
            
            # 使用简单平滑的滑动方式
            # 鼠标移动到滑块按钮
            actions.move_to(slide_btn)
            
            # 按下鼠标左键
            actions.m_hold(slide_btn)
            time.sleep(0.2)
            
            # 缓慢平滑移动
            actions.move(dis - 10, 0)
            time.sleep(0.8)
            actions.move(10, 0)
            time.sleep(1.4)
            actions.move(-10, 0)
            time.sleep(0.5)
            try:
                # 松开鼠标左键
                actions.m_release(slide_btn)
            except Exception as e:
                logger.error(f"松开鼠标左键失败: {str(e)}")
            
            logger.info("滑块拖动完成")
            
            # 等待验证结果
            time.sleep(5)
            verification_success = False
            
            # 简化验证结果检测
            # 获取页面文本内容
            current_url = page.url
            logger.info(f"当前URL: {current_url}")

            if "zu.ke.com/zufang" in current_url and "captcha" not in current_url:
                verification_success = True
                logger.info(f"已经成功跳转到租房列表页面: {current_url}")
            
            # # 判断是否通过验证
            # verification_success = "验证成功" in page_text or "captcha success" in page_text.lower()
            
            # # 检查是否还存在验证码相关内容（如果不存在则认为验证通过）
            # has_captcha = "验证" in page_text or "captcha" in page_text.lower() or "geetest" in page_text.lower()
            
            # # 如果页面上不再包含验证码相关内容，也可能是验证通过了
            # if not has_captcha:
            #     verification_success = True
            #     logger.info("页面不再包含验证码相关内容，验证可能已通过")
            
            # 如果验证成功，返回结果
            if verification_success:
                logger.info(f"验证成功 [尝试 {attempt}]")
                logger.info(f"成功的滑动距离: {dis}px")
                screenshot = page.get_screenshot()
                return {
                    "success": True,
                    "message": "验证成功",
                    "method": "pixel_diff",
                    "distance": dis,
                    "screenshot": screenshot is not None,
                    "attempts": attempt
                }
            
            # 验证失败，继续循环
            logger.warning(f"验证失败 [尝试 {attempt}]")
            # 等待一小段时间后继续下一次尝试
            logger.info(f"等待后进行下一次尝试 [{attempt}]")
            time.sleep(2)
                    
        except Exception as e:
            logger.error(f"拖动滑块失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            # 失败后继续尝试

def handle_captcha_with_manager(driver, task_id, city_code, page_url):
    """使用验证码代理系统处理验证码页面"""
    try:
        logger.info(f"开始处理验证码，任务ID: {task_id}, 城市代码: {city_code}, 页面URL: {page_url}")
        
        # 记录处理验证码的开始时间
        captcha_start_time = datetime.datetime.now()
        
        # 先确保当前线程的driver已注册
        thread_id = register_driver(driver)
        logger.info(f"已注册线程ID: {thread_id} 的DrissionPage实例")
        
        # ===尝试自动解决验证码===
        logger.info("尝试自动解决验证码...")
        # 等待一段时间让页面完全加载
        time.sleep(5)
        
        result = solve_slider_captcha(driver)
        captcha_success = False
        
        if result['success']:
            logger.info("自动解决验证码成功!")
            captcha_success = True
        else:
            logger.warning("自动解决验证码失败")
            
            # 提示用户手动处理
            logger.info("=========================================================================")
            logger.info("自动解决验证码失败！请手动处理验证码")
            logger.info("=========================================================================")
            
            # 等待用户手动处理
            input("请手动完成验证，完成后按Enter键继续...")
            captcha_success = True
            
        # 计算处理验证码所用的时间（分钟）
        if captcha_success:
            captcha_end_time = datetime.datetime.now()
            captcha_duration = (captcha_end_time - captcha_start_time).total_seconds() / 60.0
            captcha_minutes = int(captcha_duration) + 1  # 向上取整，确保有足够时间
            
            logger.info(f"处理验证码用时 {captcha_duration:.2f} 分钟，将延长锁超时时间 {captcha_minutes} 分钟")
            
            # 延长锁的超时时间
            if extend_crawler_lock(task_id, captcha_minutes):
                logger.info(f"成功延长爬虫锁超时时间 {captcha_minutes} 分钟")
            else:
                logger.warning("延长爬虫锁超时时间失败，可能会导致爬虫过早释放锁")
        
        return captcha_success
            
    except Exception as e:
        logger.error(f"处理验证码时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def setup_driver():
    """设置并返回DrissionPage对象，替代原Selenium WebDriver"""
    try:
        logger.info("初始化DrissionPage替代Selenium WebDriver")
        
        # 初始化DrissionPage对象前，检查是否存在代理可用
        proxy_config = None
        proxy = ip_manager.get_random_proxy()
        if proxy:
            proxy_url = proxy["http"]
            logger.info(f"使用代理: {proxy_url}")
            
            # 从代理URL中提取信息
            if '@' in proxy_url:
                # 有用户名密码的情况: http://username:password@ip:port
                credentials, address = proxy_url.split('@')
                scheme, auth = credentials.split('://')
                username, password = auth.split(':')
                ip, port = address.split(':')
                
                # 为DrissionPage添加代理设置
                proxy_config = {
                    'http': {
                        'server': f'{ip}:{port}',
                        'username': username,
                        'password': password
                    },
                    'https': {
                        'server': f'{ip}:{port}',
                        'username': username,
                        'password': password
                    }
                }
            else:
                # 无用户名密码的情况: http://ip:port
                scheme, ip_port = proxy_url.split('://')
                ip, port = ip_port.split(':')
                
                # 为DrissionPage添加代理设置
                proxy_config = {
                    'http': {'server': f'{ip}:{port}'},
                    'https': {'server': f'{ip}:{port}'}
                }
        
        # 根据是否有代理信息，创建DrissionPage对象
        # 检查环境变量决定是否使用headless模式
        use_headless = os.getenv('CHROME_HEADLESS', 'false').lower() == 'true'
        logger.info(f"Chrome headless模式: {use_headless}")
        
        if proxy_config:
            # 设置代理相关配置
            co = ChromiumOptions()
            # 根据环境变量配置headless模式
            co.headless(use_headless)
            # 添加Docker环境所需的配置
            co.add_argument('--no-sandbox')
            co.add_argument('--disable-dev-shm-usage')
            co.add_argument('--disable-gpu')
            co.add_argument('--remote-debugging-port=9222')
            co.set_proxy(proxy_config)
            page = ChromiumPage(co)
            mode_text = "headless" if use_headless else "界面"
            logger.info(f"DrissionPage已配置代理和{mode_text}模式")
        else:
            # 默认配置
            co = ChromiumOptions()
            # 根据环境变量配置headless模式
            co.headless(use_headless)
            # 添加Docker环境所需的配置
            co.add_argument('--no-sandbox')
            co.add_argument('--disable-dev-shm-usage')
            co.add_argument('--disable-gpu')
            co.add_argument('--remote-debugging-port=9222')
            page = ChromiumPage(co)
            mode_text = "headless" if use_headless else "界面"
            logger.info(f"DrissionPage已配置{mode_text}模式")
        
        # 设置窗口大小
        page.set.window.size(1920, 1080)
        
        # 使用execute_script保持与selenium API的兼容性
        page.run_js("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 获取当前实际窗口尺寸
        window_size = page.run_js("""
            return {
                width: window.outerWidth,
                height: window.outerHeight
            };
        """)
        window_width = window_size['width']
        window_height = window_size['height']
        
        # 记录实际窗口大小
        logger.info(f"浏览器窗口大小: {window_width}x{window_height}")
        
        # 获取实际视口大小
        viewport_size = page.run_js("""
            return {
                width: window.innerWidth,
                height: window.innerHeight
            };
        """)
        viewport_width = viewport_size['width']
        viewport_height = viewport_size['height']
        logger.info(f"浏览器视口大小: {viewport_width}x{viewport_height}")
        
        # 保存实际分辨率到全局变量，以便后续使用
        global BROWSER_WINDOW_WIDTH, BROWSER_WINDOW_HEIGHT
        BROWSER_WINDOW_WIDTH = window_width
        BROWSER_WINDOW_HEIGHT = window_height
        
        logger.info(f"已设置浏览器窗口大小为 {window_width}x{window_height} 用于坐标映射")
        
        return page
    except Exception as e:
        logger.error(f"设置DrissionPage对象时出错: {str(e)}")
        return None

def get_total_pages(driver, base_url=None):
    """获取总页数"""
    try:
        # 如果提供了base_url，先访问该URL
        if base_url:
            logger.info(f"访问URL获取总页数: {base_url}")
            driver.get(base_url)
            time.sleep(random.uniform(2, 4))
            
        # 检查是否出现验证码
        if is_captcha_page(driver):
            logger.warning("获取总页数时遇到验证码页面，返回默认值")
            return 1
            
        # 查找分页元素
        try:
            # 等待页面加载完成
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.content__list--item'))
            )
            
            # 尝试获取分页信息
            pagination = driver.find_elements(By.CSS_SELECTOR, '.content__pg')
            if pagination:
                # 获取最后一个页码按钮
                page_links = pagination[0].find_elements(By.CSS_SELECTOR, 'a')
                if page_links:
                    # 通常倒数第二个是最后一页
                    last_page_text = page_links[-2].text
                    if last_page_text.isdigit():
                        return int(last_page_text)
        except Exception as e:
            logger.warning(f"获取分页信息出错: {str(e)}")
            
        # 如果上面的方法失败，尝试从div.content__pg中获取data-totalpage属性
        try:
            pagination_div = driver.find_element(By.CSS_SELECTOR, 'div.content__pg')
            total_pages_attr = pagination_div.get_attribute('data-totalpage')
            if total_pages_attr and total_pages_attr.isdigit():
                return int(total_pages_attr)
        except:
            pass
            
        # 所有方法都失败，返回默认值
        logger.warning("无法获取总页数，使用默认值1")
        return 1
    except Exception as e:
        logger.error(f"获取总页数时出现错误: {str(e)}")
        return 1

def extract_house_info(house_element, city_code, task_id=None):
    """
    从房源元素中提取信息
    返回提取到的房源数据字典
    """
    try:
        # 提取标题 - 使用DrissionPage的API
        title_element = house_element.ele('css:.content__list--item--title a')
        title = title_element.text.strip()
        url = title_element.attr('href')
        
        # 提取图片URL
        image_url = ""
        try:
            # 尝试通过XPath获取图片
            img_element = house_element.ele('css:.content__list--item--aside img')
            if img_element:
                image_url = img_element.attr('src')
            else:
                logger.warning("提取图片URL时出错: 没有找到图片元素")
        except Exception as img_error:
            logger.warning(f"提取图片URL时出错: {str(img_error)}")
        
        # 提取价格
        price_element = house_element.ele('css:.content__list--item-price')
        price_text = price_element.text.strip()
        # print(price_text)
        price = int(re.search(r'\d+', price_text).group()) if re.search(r'\d+', price_text) else 0
        
        # 提取户型、面积等信息
        desc_elements = house_element.eles('css:.content__list--item--des')
        # print(desc_elements.text)
        # 初始化变量
        layout = ""
        area = 0
        floor = ""
        direction = ""
        district = ""
        community = ""
        subway = ""

        desc_text = desc_elements[0].text
        # 用 / 或 \n 分割成若干部分
        desc_parts = [part.strip() for part in re.split(r'[\/\n]', desc_text) if part.strip()]
        for part in desc_parts:
            # print(f"🧩 part: {part}")

            # 区域和小区（如：浦东-张江-玫瑰湾(别墅)）
            if "-" in part and not district:
                location_parts = part.split("-")
                if len(location_parts) >= 2:
                    district = location_parts[0]
                    community = location_parts[-1]

            # 面积
            elif "㎡" in part and not area:
                area_match = re.search(r'(\d+(\.\d+)?)', part)
                if area_match:
                    area = float(area_match.group(1))

            # 户型
            elif "室" in part and "厅" in part and not layout:
                layout = part

            # 楼层
            elif "楼层" in part and not floor:
                floor = part

            # 朝向（只判断方向的汉字）
            elif any(d in part for d in ["东", "南", "西", "北"]) and not direction:
                direction = part

            # 地铁
            elif "号线" in part and not subway:
                subway = part
        
        publish_date = datetime.datetime.now().strftime("%Y-%m-%d")
        publish_elements = house_element.eles('css:.content__list--item--time')

        if publish_elements:
            publish_text = publish_elements[0].text.strip()

            # 1. 格式：3天前维护
            match_before = re.search(r'(\d+)天前', publish_text)
            if match_before:
                days = int(match_before.group(1))
                publish_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')

            # 3. 格式：今天维护
            elif "今天维护" in publish_text:
                publish_date = datetime.datetime.now().strftime('%Y-%m-%d')

            # 4. 格式：05.12发布
            else:
                date_match = re.search(r'(\d{2})\.(\d{2})', publish_text)
                if date_match:
                    year = datetime.datetime.now().year
                    month, day = date_match.groups()
                    publish_date = f"{year}-{month}-{day}"
        else:
            publish_date = None
        
        # 提取特色标签
        # features = []
        tag_elements = house_element.eles('css:.content__list--item--bottom i')
        features = [el.text.strip() for el in tag_elements]
        print({
            'url': url,
            'title': title,
            'price': price,
            'layout': layout,
            'area': area,
            'floor': floor,
            'direction': direction,
            'subway': subway,
            'district': district,
            'community': community,
            'city_code': city_code,
            'publish_date': publish_date,
            'features': features,
            'task_id': task_id,
            'image_url': image_url  # 添加图片URL
        })
        # 构建并返回房源信息字典
        return {
            'url': url,
            'title': title,
            'price': price,
            'layout': layout,
            'area': area,
            'floor': floor,
            'direction': direction,
            'subway': subway,
            'district': district,
            'community': community,
            'city_code': city_code,
            'publish_date': publish_date,
            'features': features,
            'task_id': task_id,
            'image_url': image_url  # 添加图片URL
        }
    
    except Exception as e:
        logger.error(f"提取房源信息时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return None

def crawl_city_with_selenium(city_name, city_code, max_pages=5, task_id=None):
    """使用DrissionPage爬取指定城市的房源信息，可以从已有任务继续
    
    Args:
        city_name: 城市名称
        city_code: 城市代码
        max_pages: 最大爬取页数
        task_id: 已有任务ID，如果提供则继续该任务
    """
    # 重试配置
    MAX_RETRIES = 3
    
    try:
        logger.info(f"开始使用DrissionPage爬取 {city_name}({city_code}) 的房源信息，最大页数: {max_pages}")
        
        if task_id:
            # 如果提供了任务ID，则验证它是否存在
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crawl_task WHERE id = %s", (task_id,))
            existing_task = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if existing_task:
                logger.info(f"继续已有任务 ID: {task_id}")
            else:
                logger.warning(f"提供的任务ID {task_id} 不存在，将创建新任务")
                task_id = None
                
        if not task_id:
            # 创建新任务
            task_id = start_crawl_task(city_name, city_code)
            logger.info(f"创建新的爬取任务 ID: {task_id}")
        # 由爬虫进程补全计划字段
        update_crawl_task(
            task_id=task_id,
            status="In Progress",
            total_pages=max_pages,
            expected_items=max_pages * 30
        )
        
        # 初始化浏览器
        driver = setup_driver()
        
        try:
            # 注册当前线程的WebDriver对象
            register_driver(driver)
            
            # 设置基础URL
            base_url = f"https://{city_code}.zu.ke.com/zufang/"
            
            # 直接使用用户指定的页数，不再尝试获取网站的总页数
            pages_to_crawl = max_pages
            logger.info(f"计划爬取: {pages_to_crawl} 页")
            
            # 获取已成功爬取的页面，用于断点续传
            crawled_pages = get_crawled_pages(task_id)
            logger.info(f"检测到已成功爬取的页面: {crawled_pages}" if crawled_pages else "未检测到已爬取页面，将从第1页开始爬取")
            
            for page in range(1, pages_to_crawl + 1):
                # 如果页面已经成功爬取过，则跳过
                if page in crawled_pages:
                    logger.info(f"第 {page} 页已成功爬取，跳过")
                    continue
                
                page_url = f"{base_url}pg{page}/"
                logger.info(f"开始爬取第 {page} 页: {page_url}")
                
                # 重试机制
                retry_count = 0
                success = False
                last_error = None
                
                while retry_count < MAX_RETRIES and not success:
                    if retry_count > 0:
                        logger.warning(f"第 {page} 页爬取失败，进行第 {retry_count} 次重试")
                        # 每次重试增加等待时间
                        time.sleep(5 * retry_count)
                    
                    try:
                        # 访问页面
                        driver.get(page_url)
                        time.sleep(random.uniform(2, 5))  # 随机等待
                        
                        # 检查是否出现验证码
                        if is_captcha_page(driver):
                            logger.warning(f"第 {page} 页出现验证码，开始处理")
                            
                            # 使用验证码代理系统处理验证码
                            if handle_captcha_with_manager(driver, task_id, city_code, page_url):
                                logger.info("验证码处理成功，继续爬取")
                                # 重新加载页面
                                driver.get(page_url)
                                time.sleep(random.uniform(2, 5))
                            else:
                                raise Exception("验证码处理失败")
                        
                        # 等待房源列表加载 (通过sleep替代WebDriverWait，因为DrissionPage没有WebDriverWait)
                        time.sleep(3)
                        
                        # 处理该页的所有房源
                        success_count, total_count = process_house_items(driver, task_id)
                        logger.info(f"第 {page} 页成功保存 {success_count}/{total_count} 个房源")
                        
                        # 标记为成功
                        success = success_count > 0
                        
                        # 记录该页爬取的成功房源数 - 修复连接管理问题
                        try:
                            # 获取统计信息 - 这个函数内部会管理自己的连接
                            stats = get_crawl_statistics(task_id)
                            logger.info(f"目前已成功爬取 {stats['task_items']} 条房源信息（总数据库记录：{stats['total_items']}条）")
                            
                            # 更新任务状态 - 这个函数使用装饰器管理连接
                            update_crawl_task(
                                task_id=task_id, 
                                status="In Progress", 
                                success_items=stats['task_items'],
                                success_pages=stats['success_pages']
                            )
                        except Exception as e:
                            logger.error(f"更新爬取进度时出错: {str(e)}")
                        # 移除多余的异常处理和连接管理代码，避免尝试归还不存在的连接
                        
                    except Exception as e:
                        last_error = str(e)
                        logger.error(f"爬取第 {page} 页时出错 (尝试 {retry_count+1}/{MAX_RETRIES}): {last_error}")
                    
                    retry_count += 1
                
                # 记录页面爬取状态
                record_page_crawl(
                    task_id, 
                    page, 
                    page_url, 
                    success=success, 
                    retry_count=retry_count-1, 
                    error_message=None if success else last_error
                )
                
                if not success:
                    logger.error(f"第 {page} 页爬取失败，已达到最大重试次数 {MAX_RETRIES}")
                
                # 随机等待，避免被封
                time.sleep(random.uniform(5, 10))
            
            logger.info(f"完成 {city_name} 的爬取任务，共计划爬取 {pages_to_crawl} 页")
            
            # 查询已成功爬取的页面数
            successful_pages = get_crawled_pages(task_id)
            logger.info(f"共成功爬取 {len(successful_pages)}/{pages_to_crawl} 页")
            
            # 如果全部页面都爬取成功，标记任务为完成
            if len(successful_pages) == pages_to_crawl:
                # 计算总成功爬取的房源数
                try:
                    stats = get_crawl_statistics(task_id)
                    logger.info(f"任务 {task_id} 共成功爬取 {stats['task_items']} 条房源信息")
                    
                    # 更新任务状态，包括成功爬取的房源数量
                    update_crawl_task(
                        task_id=task_id, 
                        status="Completed", 
                        success_items=stats['task_items'],
                        success_pages=len(successful_pages),
                        total_pages=pages_to_crawl
                    )
                    
                    # 爬虫任务完成后自动执行数据分析
                    logger.info(f"爬虫任务完成，准备执行数据分析...")
                    # 在新线程中执行数据分析，避免阻塞主线程
                    analysis_thread = threading.Thread(
                        target=run_data_analysis,
                        args=(task_id, city_name, city_code),
                        daemon=True
                    )
                    analysis_thread.start()
                    logger.info(f"数据分析任务已在后台启动")
                except Exception as e:
                    logger.error(f"计算爬取房源数时出错: {str(e)}")
                    update_crawl_task(task_id=task_id, status="Completed")
            else:
                # 任务未完全完成，但暂时结束
                try:
                    stats = get_crawl_statistics(task_id)
                    logger.info(f"任务 {task_id} 部分完成，共爬取 {stats['task_items']} 条房源信息")
                    
                    # 更新任务状态，包括成功爬取的房源数量
                    update_crawl_task(
                        task_id=task_id, 
                        status="Incomplete", 
                        success_items=stats['task_items'],
                        success_pages=len(successful_pages),
                        total_pages=pages_to_crawl,
                        error_message=f"部分页面爬取失败，已成功爬取 {len(successful_pages)}/{pages_to_crawl} 页"
                    )
                except Exception as e:
                    logger.error(f"计算爬取房源数时出错: {str(e)}")
                    update_crawl_task(
                        task_id=task_id, 
                        status="Incomplete", 
                        error_message=f"部分页面爬取失败，已成功爬取 {len(successful_pages)}/{pages_to_crawl} 页"
                    )
            
        finally:
            # 关闭浏览器
            unregister_driver()
            # 使用DrissionPage的关闭方法
            driver.quit()
            
    except Exception as e:
        logger.error(f"DrissionPage爬取过程中出现错误: {str(e)}")
        if task_id:
            try:
                conn = connection_pool.getconn()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM house_info WHERE task_id = %s",
                    (task_id,)
                )
                success_items_count = cursor.fetchone()[0]
                logger.info(f"任务 {task_id} 失败，但已爬取 {success_items_count} 条房源信息")
                
                # 更新任务状态，包括成功爬取的房源数量
                update_crawl_task(task_id, "Failed", 
                                success_items=success_items_count,
                                error_message=str(e))
                
                # 确保连接正确关闭
                connection_pool.putconn(conn)
            except Exception as count_error:
                logger.error(f"计算爬取房源数时出错: {str(count_error)}")
                update_crawl_task(task_id, "Failed", error_message=str(e))
        
    return task_id

def save_browser_cookies(driver, session_id):
    """保存浏览器cookies到验证会话"""
    try:
        cookies = driver.get_cookies()
        verification_manager.save_verification_cookies(session_id, cookies)
        logger.info(f"保存浏览器cookies到验证会话 {session_id} 成功")
        return True
    except Exception as e:
        logger.error(f"保存浏览器cookies失败: {str(e)}")
        return False

def export_to_csv(houses, filename="rental_data.csv"):
    """将房源数据导出为CSV文件"""
    if not houses:
        logger.warning("没有数据可导出")
        return False
    
    try:
        df = pd.DataFrame(houses)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"数据已导出到 {filename}")
        return True
    except Exception as e:
        logger.error(f"导出数据失败: {str(e)}")
        return False

def get_city_code(city_name):
    """
    根据城市名称获取城市代码
    
    Args:
        city_name (str): 城市名称，如"北京"、"上海"等
        
    Returns:
        str: 城市代码，如"bj"、"sh"等；如果城市不支持，返回None
    """
    cities = get_supported_cities()
    return cities.get(city_name)

def get_supported_cities():
    """获取支持的城市列表"""
    return {
        "北京": "bj",
        "上海": "sh",
        "广州": "gz",
        "深圳": "sz",
        "杭州": "hz",
        "南京": "nj",
        "成都": "cd",
        "武汉": "wh",
        "天津": "tj",
        "西安": "xa",
        "重庆": "cq",
        "苏州": "su",
        "郑州": "zz",
        "长沙": "cs",
        "合肥": "hf",
        "宁波": "nb",
        "青岛": "qd",
        "大连": "dl",
        "厦门": "xm",
        "福州": "fz",
        "济南": "jn",
        "南昌": "nc",
        "昆明": "km",
        "沈阳": "sy",
        "长春": "cc",
        "哈尔滨": "hrb",
        "石家庄": "sjz",
        "太原": "ty",
        "南宁": "nn",
        "无锡": "wx",
        "湖州": "huzhou",
        "常州": "cz",
        "嘉兴": "jx",
        "海口": "hk",
        "贵阳": "gy",
        "三亚": "sanya",
        "兰州": "lz",
        "廊坊": "lf",
        "保定": "bd",
        "佛山": "fs",
        "东莞": "dg",
        "中山": "zs",
        "珠海": "zh",
        "湛江": "zhanjiang"
    }

def record_page_crawl(task_id, page_number, page_url, success=True, retry_count=0, error_message=None):
    """记录页面爬取状态，用于断点续传
    
    Args:
        task_id: 爬虫任务ID
        page_number: 页码
        page_url: 页面URL
        success: 是否成功爬取
        retry_count: 重试次数
        error_message: 错误信息
    """
    if not connection_pool:
        logger.error("数据库连接池不可用，无法记录页面爬取状态")
        return False
    
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        # 检查是否已有记录
        cursor.execute(
            "SELECT id FROM crawled_pages WHERE task_id = %s AND page_number = %s",
            (task_id, page_number)
        )
        exists = cursor.fetchone()
        
        current_time = datetime.datetime.now()
        
        if exists:
            # 更新已有记录
            cursor.execute(
                """
                UPDATE crawled_pages 
                SET success = %s, retry_count = %s, error_message = %s, crawl_time = %s 
                WHERE task_id = %s AND page_number = %s
                """,
                (success, retry_count, error_message, current_time, task_id, page_number)
            )
        else:
            # 插入新记录
            cursor.execute(
                """
                INSERT INTO crawled_pages 
                (task_id, page_number, page_url, crawl_time, success, retry_count, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (task_id, page_number, page_url, current_time, success, retry_count, error_message)
            )
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"记录页面爬取状态失败: {str(e)}")
        return False
    finally:
        if conn:
            connection_pool.putconn(conn)

def is_page_crawled_successfully(task_id, page_number):
    """检查页面是否已成功爬取，用于断点续传
    
    Args:
        task_id: 爬虫任务ID
        page_number: 页码
    
    Returns:
        bool: 是否已成功爬取
    """
    if not connection_pool:
        logger.error("数据库连接池不可用，无法检查页面爬取状态")
        return False
    
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT success FROM crawled_pages WHERE task_id = %s AND page_number = %s",
            (task_id, page_number)
        )
        result = cursor.fetchone()
        
        return result is not None and result[0] == True
    except Exception as e:
        logger.error(f"检查页面爬取状态失败: {str(e)}")
        return False
    finally:
        if conn:
            connection_pool.putconn(conn)

def get_crawled_pages(task_id):
    """获取任务已爬取的页面列表
    
    Args:
        task_id: 爬虫任务ID
    
    Returns:
        list: 已成功爬取的页码列表
    """
    if not connection_pool:
        logger.error("数据库连接池不可用，无法获取已爬取页面")
        return []
    
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        try:
            # 先检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'crawled_pages'
                )
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                logger.warning("crawled_pages表不存在，尝试创建...")
                # 创建表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS crawled_pages (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER REFERENCES crawl_task(id),
                    page_number INTEGER NOT NULL,
                    page_url TEXT NOT NULL,
                    crawl_time TIMESTAMP NOT NULL,
                    success BOOLEAN NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    UNIQUE (task_id, page_number)
                )
                ''')
                conn.commit()
                logger.info("crawled_pages表创建成功")
                return []  # 新表中没有数据，返回空列表
        
            cursor.execute(
                "SELECT page_number FROM crawled_pages WHERE task_id = %s AND success = true",
                (task_id,)
            )
            results = cursor.fetchall()
            
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"获取已爬取页面失败: {str(e)}")
            # 尝试运行数据库初始化脚本
            try:
                # 先关闭当前连接
                cursor.close()
                connection_pool.putconn(conn)
                
                # 再次尝试获取
                conn = connection_pool.getconn()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT page_number FROM crawled_pages WHERE task_id = %s AND success = true",
                    (task_id,)
                )
                results = cursor.fetchall()
                
                return [row[0] for row in results]
            except Exception as init_error:
                logger.error(f"重试创建表并获取数据失败: {str(init_error)}")
                return []
    finally:
        if 'conn' in locals() and conn:
            connection_pool.putconn(conn)

def get_browser_dimensions():
    """获取浏览器实际尺寸"""
    return {
        'width': BROWSER_WINDOW_WIDTH,
        'height': BROWSER_WINDOW_HEIGHT
    }

def acquire_crawler_lock(task_id, max_pages=5, lock_timeout_minutes=None):
    """
    尝试获取爬虫锁，如果成功返回True，否则返回False
    
    Args:
        task_id: 爬虫任务ID
        max_pages: 计划爬取的最大页数，用于计算超时时间
        lock_timeout_minutes: 锁超时时间（分钟），如果不提供则根据页数动态计算
    
    Returns:
        bool: 是否成功获取锁
    """
    if not connection_pool:
        logger.error("数据库连接池不可用，无法获取爬虫锁")
        return False
    
    # 如果没有提供超时时间，则根据页数动态计算
    if lock_timeout_minutes is None:
        # 基本算法：
        # 1. 每页基本爬取时间：2.5分钟（页面加载、提取信息等）
        # 2. 初始验证码时间预留：每4页预留15分钟（验证码通常不会每页都出现）
        # 3. 额外增加50%的缓冲时间用于处理网络延迟等意外情况
        # 4. 再加上15分钟的基础缓冲时间用于初始化和其他操作
        # 注意：后续每次实际处理验证码时会动态延长锁时间
        base_time_per_page = 2.5  # 基本爬取时间（分钟/页）
        captcha_time_allocation = max(15, (max_pages // 4) * 15)  # 初始预留的验证码处理时间（分钟）
        buffer_ratio = 1.5  # 缓冲比例
        base_buffer = 15  # 基础缓冲时间（分钟）
        
        # 计算总的锁超时时间（分钟）
        lock_timeout_minutes = int(base_time_per_page * max_pages * buffer_ratio) + captcha_time_allocation + base_buffer
        logger.info(f"根据爬取页数 {max_pages} 动态计算锁超时时间为 {lock_timeout_minutes} 分钟，包含验证码预留时间 {captcha_time_allocation} 分钟")
        
        # 如果页数过多，确保有足够的时间（最多24小时）
        if lock_timeout_minutes > 24 * 60:
            lock_timeout_minutes = 24 * 60
            logger.info(f"超时时间超过24小时，已限制为 {lock_timeout_minutes} 分钟")
            
        # 如果页数很少，确保有最低的超时时间
        if lock_timeout_minutes < 30:
            lock_timeout_minutes = 30
            logger.info(f"超时时间过短，已设置为最低值 {lock_timeout_minutes} 分钟")
    
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        # 开始事务
        conn.autocommit = False
        
        # 获取锁的当前状态（使用FOR UPDATE锁定行）
        cursor.execute(
            "SELECT is_locked, locked_by, locked_at, expires_at FROM crawler_lock WHERE lock_name = %s FOR UPDATE",
            ('main_crawler_lock',)
        )
        lock_info = cursor.fetchone()
        
        if not lock_info:
            logger.error("爬虫锁记录不存在")
            conn.rollback()
            return False
        
        is_locked, locked_by, locked_at, expires_at = lock_info
        current_time = datetime.datetime.now()
        
        # 检查锁是否已被获取，并且没有过期
        if is_locked and expires_at and current_time < expires_at:
            # 计算剩余时间
            remaining_minutes = (expires_at - current_time).total_seconds() / 60
            logger.info(f"爬虫锁已被任务 {locked_by} 持有，剩余 {remaining_minutes:.1f} 分钟，获取失败")
            # 提交事务
            conn.commit()
            return False
        
        # 计算过期时间
        expiration_time = current_time + datetime.timedelta(minutes=lock_timeout_minutes)
        
        # 获取锁
        cursor.execute(
            """
            UPDATE crawler_lock
            SET is_locked = %s, locked_by = %s, locked_at = %s, expires_at = %s
            WHERE lock_name = %s
            """,
            (True, task_id, current_time, expiration_time, 'main_crawler_lock')
        )
        
        # 同时更新任务的预计结束时间
        cursor.execute(
            """
            UPDATE crawl_task
            SET expected_end_time = %s
            WHERE id = %s
            """,
            (expiration_time, task_id)
        )
        
        # 提交事务
        conn.commit()
        logger.info(f"任务 {task_id} 成功获取爬虫锁，超时时间为 {lock_timeout_minutes} 分钟，过期时间 {expiration_time}")
        return True
    except Exception as e:
        logger.error(f"获取爬虫锁失败: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.autocommit = True
            connection_pool.putconn(conn)

def release_crawler_lock(task_id):
    """
    释放爬虫锁，如果锁由当前任务持有
    
    Args:
        task_id: 爬虫任务ID
    
    Returns:
        bool: 是否成功释放锁
    """
    if not connection_pool:
        logger.error("数据库连接池不可用，无法释放爬虫锁")
        return False
    
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        # 开始事务
        conn.autocommit = False
        
        # 获取锁的当前状态（使用FOR UPDATE锁定行）
        cursor.execute(
            "SELECT is_locked, locked_by FROM crawler_lock WHERE lock_name = %s FOR UPDATE",
            ('main_crawler_lock',)
        )
        lock_info = cursor.fetchone()
        
        if not lock_info:
            logger.error("爬虫锁记录不存在")
            conn.rollback()
            return False
        
        is_locked, locked_by = lock_info
        
        # 检查锁是否由当前任务持有
        if is_locked and locked_by == task_id:
            # 释放锁
            cursor.execute(
                """
                UPDATE crawler_lock
                SET is_locked = %s, locked_by = NULL, locked_at = NULL, expires_at = NULL
                WHERE lock_name = %s
                """,
                (False, 'main_crawler_lock')
            )
            
            # 提交事务
            conn.commit()
            logger.info(f"任务 {task_id} 成功释放爬虫锁")
            
            # 尝试启动队列中的下一个任务
            start_next_queued_task()
            
            return True
        else:
            logger.warning(f"任务 {task_id} 尝试释放不属于它的锁")
            conn.rollback()
            return False
    except Exception as e:
        logger.error(f"释放爬虫锁失败: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.autocommit = True
            connection_pool.putconn(conn)

def extend_crawler_lock(task_id, additional_minutes):
    """
    延长爬虫锁的超时时间
    
    Args:
        task_id: 爬虫任务ID
        additional_minutes: 要额外增加的分钟数
    
    Returns:
        bool: 是否成功延长锁的超时时间
    """
    if not connection_pool:
        logger.error("数据库连接池不可用，无法延长爬虫锁超时时间")
        return False
    
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        # 开始事务
        conn.autocommit = False
        
        # 获取锁的当前状态（使用FOR UPDATE锁定行）
        cursor.execute(
            "SELECT is_locked, locked_by, expires_at FROM crawler_lock WHERE lock_name = %s FOR UPDATE",
            ('main_crawler_lock',)
        )
        lock_info = cursor.fetchone()
        
        if not lock_info:
            logger.error("爬虫锁记录不存在")
            conn.rollback()
            return False
        
        is_locked, locked_by, current_expires_at = lock_info
        
        # 检查锁是否由当前任务持有
        if is_locked and locked_by == task_id:
            # 计算新的过期时间
            if current_expires_at:
                new_expires_at = current_expires_at + datetime.timedelta(minutes=additional_minutes)
                
                # 更新过期时间
                cursor.execute(
                    """
                    UPDATE crawler_lock
                    SET expires_at = %s
                    WHERE lock_name = %s
                    """,
                    (new_expires_at, 'main_crawler_lock')
                )
                
                # 同时更新任务的预计结束时间
                cursor.execute(
                    """
                    UPDATE crawl_task
                    SET expected_end_time = %s
                    WHERE id = %s
                    """,
                    (new_expires_at, task_id)
                )
                
                # 提交事务
                conn.commit()
                logger.info(f"任务 {task_id} 成功延长爬虫锁超时时间 {additional_minutes} 分钟，新的过期时间: {new_expires_at}")
                return True
            else:
                logger.warning(f"任务 {task_id} 的爬虫锁没有过期时间，无法延长")
                conn.rollback()
                return False
        else:
            logger.warning(f"任务 {task_id} 尝试延长不属于它的锁")
            conn.rollback()
            return False
    except Exception as e:
        logger.error(f"延长爬虫锁超时时间失败: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.autocommit = True
            connection_pool.putconn(conn)

def is_crawler_locked():
    """
    检查爬虫锁是否被占用
    
    Returns:
        tuple: (是否锁定, 锁定的任务ID) 如果未锁定则任务ID为None
    """
    if not connection_pool:
        logger.error("数据库连接池不可用，无法检查爬虫锁状态")
        return (True, None)  # 如果无法检查，假设已锁定
    
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT is_locked, locked_by, expires_at FROM crawler_lock WHERE lock_name = %s",
            ('main_crawler_lock',)
        )
        lock_info = cursor.fetchone()
        
        if not lock_info:
            logger.error("爬虫锁记录不存在")
            return (True, None)
        
        is_locked, locked_by, expires_at = lock_info
        current_time = datetime.datetime.now()
        
        # 检查锁是否已过期
        if is_locked and expires_at and current_time > expires_at:
            logger.info("爬虫锁已过期，将自动释放")
            
            # 释放过期的锁
            cursor.execute(
                """
                UPDATE crawler_lock
                SET is_locked = %s, locked_by = NULL, locked_at = NULL, expires_at = NULL
                WHERE lock_name = %s
                """,
                (False, 'main_crawler_lock')
            )
            conn.commit()
            
            return (False, None)
        
        return (is_locked, locked_by)
    except Exception as e:
        logger.error(f"检查爬虫锁状态失败: {str(e)}")
        return (True, None)  # 如果发生错误，假设已锁定
    finally:
        if 'conn' in locals() and conn:
            connection_pool.putconn(conn)

def queue_crawl_task(task_id):
    """
    将爬虫任务添加到队列中等待执行
    
    Args:
        task_id: 爬虫任务ID
    
    Returns:
        bool: 是否成功添加到队列
    """
    if not connection_pool:
        logger.error("数据库连接池不可用，无法将任务添加到队列")
        return False
    
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        # 获取当前最大队列位置
        cursor.execute("SELECT MAX(queue_position) FROM crawl_task WHERE status = 'Queued'")
        max_position = cursor.fetchone()[0]
        
        if max_position is None:
            max_position = 0
        
        next_position = max_position + 1
        
        # 更新任务状态为队列中
        cursor.execute(
            """
            UPDATE crawl_task
            SET status = %s, queue_position = %s
            WHERE id = %s
            """,
            ('Queued', next_position, task_id)
        )
        
        conn.commit()
        logger.info(f"任务 {task_id} 已添加到队列，位置 {next_position}")
        return True
    except Exception as e:
        logger.error(f"将任务添加到队列失败: {str(e)}")
        return False
    finally:
        if 'conn' in locals() and conn:
            connection_pool.putconn(conn)

def start_next_queued_task():
    """
    启动队列中的下一个爬虫任务
    
    Returns:
        bool: 是否成功启动下一个任务
    """
    if not connection_pool:
        logger.error("数据库连接池不可用，无法启动下一个任务")
        return False
    
    try:
        # 检查锁是否可用
        is_locked, _ = is_crawler_locked()
        if is_locked:
            logger.info("爬虫锁仍在使用中，无法启动下一个任务")
            return False
        
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        # 获取队列中的下一个任务
        cursor.execute(
            """
            SELECT id, city, city_code
            FROM crawl_task
            WHERE status = 'Queued'
            ORDER BY queue_position ASC
            LIMIT 1
            """
        )
        next_task = cursor.fetchone()
        
        if not next_task:
            logger.info("队列中没有等待的任务")
            return False
        
        task_id, city, city_code = next_task
        logger.info(f"准备启动队列中的下一个任务: {task_id} - {city}")
        
        # 更新任务状态为进行中
        cursor.execute(
            """
            UPDATE crawl_task
            SET status = %s, queue_position = 0
            WHERE id = %s
            """,
            ('In Progress', task_id)
        )
        conn.commit()
        
        # 启动爬虫任务（异步方式）
        import threading
        thread = threading.Thread(
            target=start_queued_crawler_task, 
            args=(task_id, city, city_code),
            daemon=True
        )
        thread.start()
        
        logger.info(f"已启动队列中的下一个任务: {task_id}")
        return True
    except Exception as e:
        logger.error(f"启动下一个任务失败: {str(e)}")
        return False
    finally:
        if 'conn' in locals() and conn:
            connection_pool.putconn(conn)

def start_queued_crawler_task(task_id, city, city_code, max_pages=5):
    """
    启动队列中的爬虫任务
    
    Args:
        task_id: 爬虫任务ID
        city: 城市名称
        city_code: 城市代码
        max_pages: 最大爬取页数
    """
    try:
        logger.info(f"开始执行队列中的任务: {task_id} - {city}")
        
        # 获取爬虫锁
        if not acquire_crawler_lock(task_id, max_pages):
            logger.error(f"无法获取爬虫锁，取消执行任务 {task_id}")
            return
        
        try:
            # 执行爬虫任务
            crawl_city_with_selenium(city, city_code, max_pages, task_id)
            
            # 任务完成后，检查状态并执行数据分析
            conn = connection_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status FROM crawl_task WHERE id = %s",
                (task_id,)
            )
            task_status = cursor.fetchone()
            connection_pool.putconn(conn)
            
            if task_status and task_status[0] == "Completed":
                logger.info(f"队列任务 {task_id} 已完成，启动数据分析...")
                # 在新线程中执行数据分析，避免阻塞主线程
                analysis_thread = threading.Thread(
                    target=run_data_analysis,
                    args=(task_id, city, city_code),
                    daemon=True
                )
                analysis_thread.start()
                logger.info(f"数据分析任务已在后台启动")
        finally:
            # 确保任务完成后释放锁
            release_crawler_lock(task_id)
            
    except Exception as e:
        logger.error(f"执行队列中的任务时出错: {str(e)}")
        try:
            update_crawl_task(task_id, "Failed", error_message=f"执行队列任务时出错: {str(e)}")
        except:
            pass
        
        # 确保无论如何都释放锁
        try:
            release_crawler_lock(task_id)
        except:
            pass

# 添加一个处理单个房源的函数，用于多线程调用
def process_single_house(house_item, city_code, task_id, index, total):
    """
    处理单个房源项目，不直接保存数据库
    
    Args:
        house_item: 房源元素
        city_code: 城市代码
        task_id: 任务ID
        index: 房源索引
        total: 总房源数
    
    Returns:
        dict: 处理后的房源信息，失败则返回None
    """
    try:
        logger.info(f"开始处理第 {index+1}/{total} 个房源")
        # 提取房源信息
        house_info = extract_house_info(house_item, city_code, task_id)
        
        if house_info:
            logger.info(f"成功提取房源信息: {house_info.get('title', '无标题')}")
            
            # 生成唯一的house_id (如果URL中包含)
            if house_info.get('url'):
                house_id = get_house_id_from_url(house_info['url'])
                logger.info(f"从URL提取的house_id: {house_id}")
                house_info['house_id'] = house_id
            else:
                logger.warning(f"房源信息中不包含URL")
                # 生成一个随机ID
                import uuid
                house_info['house_id'] = f"RAND{str(uuid.uuid4())[:20]}"
                logger.info(f"生成随机house_id: {house_info['house_id']}")
            
            # 返回处理好的房源信息，不立即保存
            return house_info
        else:
            logger.warning(f"房源信息提取失败，跳过此项")
            return None
    except Exception as item_err:
        logger.error(f"处理第 {index+1} 个房源时出错: {str(item_err)}")
        return None

# 添加一个处理整个页面房源的函数
def process_house_items(driver, task_id):
    """
    处理页面上的所有房源项目，使用批量保存减少数据库连接消耗
    
    Args:
        driver: DrissionPage对象
        task_id: 任务ID
    
    Returns:
        tuple: (成功保存的房源数, 总房源数)
    """
    try:
        # 获取城市代码，从URL中提取
        current_url = driver.url
        city_code = current_url.split(".")[0].split("//")[1]
        logger.info(f"当前页面URL: {current_url}, 提取城市代码: {city_code}")
        
        # 获取所有房源元素
        house_items = driver.eles('css:div.content__list--item')
        logger.info(f"在页面上找到 {len(house_items)} 个房源项目")
        
        # 使用线程池并行处理房源信息提取
        max_workers = min(10, len(house_items))  # 设置最大线程数，避免创建过多线程
        logger.info(f"创建线程池，最大线程数: {max_workers}")
        
        # 初始化房源信息集合
        valid_house_info_list = []
        
        # 使用线程池执行器并行处理房源
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有房源处理任务
            future_to_house = {
                executor.submit(
                    process_single_house, 
                    house_item, 
                    city_code, 
                    task_id, 
                    i, 
                    len(house_items)
                ): i for i, house_item in enumerate(house_items)
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_house):
                house_index = future_to_house[future]
                try:
                    house_info = future.result()
                    if house_info:
                        # 收集有效的房源信息
                        valid_house_info_list.append(house_info)
                except Exception as e:
                    logger.error(f"处理房源 {house_index+1} 时发生异常: {str(e)}")
        
        # 对收集到的房源信息进行批量保存
        logger.info(f"开始批量保存 {len(valid_house_info_list)} 个房源信息")
        
        if valid_house_info_list:
            # 批量保存到数据库
            save_result = batch_save_house_info(valid_house_info_list)
            success_count = save_result['success']
            failed_count = save_result['failed']
        else:
            success_count = 0
            failed_count = 0
        
        logger.info(f"页面处理完成，成功保存: {success_count}, 失败: {failed_count}, 总数: {len(house_items)}")
        return success_count, len(house_items)
    
    except Exception as e:
        logger.error(f"处理房源列表时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return 0, 0

# 在爬取完成后添加更详细的统计代码，放在process_house_items后面调用
def get_crawl_statistics(task_id):
    """获取当前爬取任务的统计信息"""
    if not connection_pool:
        return {"task_items": 0, "total_items": 0, "success_pages": 0}
    
    conn = None
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        # 统计与当前任务关联的房源数
        cursor.execute(
            "SELECT COUNT(*) FROM house_info WHERE task_id = %s",
            (task_id,)
        )
        task_items_count = cursor.fetchone()[0]
        
        # 统计总房源数
        cursor.execute("SELECT COUNT(*) FROM house_info")
        total_items_count = cursor.fetchone()[0]
        
        # 统计当前任务的成功页面数
        cursor.execute(
            "SELECT COUNT(*) FROM crawled_pages WHERE task_id = %s AND success = true",
            (task_id,)
        )
        success_pages_count = cursor.fetchone()[0]
        
        return {
            "task_items": task_items_count,
            "total_items": total_items_count,
            "success_pages": success_pages_count
        }
    except Exception as e:
        logger.error(f"获取爬取统计信息失败: {str(e)}")
        return {"task_items": 0, "total_items": 0, "success_pages": 0}
    finally:
        # 确保在所有情况下都正确归还连接
        if conn:
            try:
                connection_pool.putconn(conn)
            except Exception as conn_err:
                logger.error(f"归还数据库连接时出错: {str(conn_err)}")
                # 连接归还错误不应影响函数返回

@with_db_connection
def batch_save_house_info(conn, house_info_list):
    """批量保存多个房源信息到数据库，减少数据库连接次数
    
    Args:
        conn: 数据库连接
        house_info_list: 房源信息列表
        
    Returns:
        dict: 包含成功和失败的房源数量
    """
    if not house_info_list:
        logger.warning("没有房源信息可保存")
        return {"success": 0, "failed": 0}
    
    try:
        cursor = conn.cursor()
        success_count = 0
        failed_count = 0
        
        # 开始事务
        try:
            conn.autocommit = False
        except Exception as e:
            logger.warning(f"设置autocommit=False失败: {str(e)}，将尝试继续执行")
        
        # 为每个房源生成house_id并尝试保存
        for house_info in house_info_list:
            try:
                # 确保有house_id
                if 'house_id' not in house_info or not house_info['house_id']:
                    house_info['house_id'] = get_house_id_from_url(house_info['url'])
                    if not house_info['house_id']:
                        import hashlib
                        house_info['house_id'] = "HASH" + hashlib.md5(house_info['url'].encode()).hexdigest()[:20]
                
                # 解析户型字段，提取房间、厅和卫生间数量
                layout_str = house_info.get('layout', '')
                room_description, room_count, hall_count, bath_count = parse_layout_to_components(layout_str)
                
                # 计算单价
                unit_price = 0
                try:
                    price = float(house_info.get('price', 0))
                    area = float(house_info.get('area', 0))
                    if price > 0 and area > 0:
                        unit_price = round(price / area, 2)
                except (ValueError, TypeError):
                    logger.warning(f"计算单价失败: price={house_info.get('price')}, area={house_info.get('area')}")
                
                # 检查是否已存在相同的house_id
                cursor.execute(
                    "SELECT id FROM house_info WHERE house_id = %s",
                    (house_info['house_id'],)
                )
                existing_by_id = cursor.fetchone()
                
                if existing_by_id:
                    # 更新已存在的记录
                    cursor.execute("""
                    UPDATE house_info SET
                        title = %s,
                        price = %s,
                        layout = %s,
                        size = %s,
                        floor = %s,
                        direction = %s,
                        subway = %s,
                        location_qu = %s,
                        location_big = %s,
                        publish_date = %s,
                        features = %s,
                        image = %s,
                        link = %s,
                        city_code = %s,
                        room = %s,
                        room_count = %s,
                        hall_count = %s,
                        bath_count = %s,
                        unit_price = %s,
                        last_updated = %s
                    WHERE house_id = %s
                    """, (
                        house_info['title'],
                        house_info['price'],
                        house_info['layout'],
                        house_info['area'],
                        house_info['floor'],
                        house_info['direction'],
                        house_info['subway'],
                        house_info['district'],
                        house_info['community'],
                        house_info['publish_date'],
                        json.dumps(house_info['features'], ensure_ascii=False),
                        house_info.get('image_url', ''),
                        house_info['url'],
                        house_info['city_code'],
                        room_description,
                        room_count,
                        hall_count,
                        bath_count,
                        unit_price,
                        datetime.datetime.now(),
                        house_info['house_id']
                    ))
                    success_count += 1
                else:
                    # 检查是否已存在相同的URL和城市代码
                    cursor.execute(
                        "SELECT id FROM house_info WHERE link = %s AND city_code = %s",
                        (house_info['url'], house_info['city_code'])
                    )
                    existing_by_url = cursor.fetchone()
                    
                    if existing_by_url:
                        # 更新已存在记录
                        cursor.execute("""
                        UPDATE house_info SET
                            title = %s,
                            price = %s,
                            layout = %s,
                            size = %s,
                            floor = %s,
                            direction = %s,
                            subway = %s,
                            location_qu = %s,
                            location_big = %s,
                            publish_date = %s,
                            features = %s,
                            image = %s,
                            house_id = %s,
                            room = %s,
                            room_count = %s,
                            hall_count = %s,
                            bath_count = %s,
                            unit_price = %s,
                            last_updated = %s
                        WHERE link = %s AND city_code = %s
                        """, (
                            house_info['title'],
                            house_info['price'],
                            house_info['layout'],
                            house_info['area'],
                            house_info['floor'],
                            house_info['direction'],
                            house_info['subway'],
                            house_info['district'],
                            house_info['community'],
                            house_info['publish_date'],
                            json.dumps(house_info['features'], ensure_ascii=False),
                            house_info.get('image_url', ''),
                            house_info['house_id'],
                            room_description,
                            room_count,
                            hall_count,
                            bath_count,
                            unit_price,
                            datetime.datetime.now(),
                            house_info['url'],
                            house_info['city_code']
                        ))
                        success_count += 1
                    else:
                        # 插入新记录
                        cursor.execute("""
                        INSERT INTO house_info (
                            link, title, price, layout, size, floor, direction,
                            subway, location_qu, location_big, city_code, publish_date, 
                            features, image, created_at, last_updated, task_id, house_id,
                            room, room_count, hall_count, bath_count, unit_price
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        )
                        """, (
                            house_info['url'],
                            house_info['title'],
                            house_info['price'],
                            house_info['layout'],
                            house_info['area'],
                            house_info['floor'],
                            house_info['direction'],
                            house_info['subway'],
                            house_info['district'],
                            house_info['community'],
                            house_info['city_code'],
                            house_info['publish_date'],
                            json.dumps(house_info['features'], ensure_ascii=False),
                            house_info.get('image_url', ''),
                            datetime.datetime.now(),
                            datetime.datetime.now(),
                            house_info.get('task_id'),
                            house_info['house_id'],
                            room_description,
                            room_count,
                            hall_count,
                            bath_count,
                            unit_price
                        ))
                        success_count += 1
            except Exception as e:
                logger.error(f"保存房源 {house_info.get('house_id', '未知')} 失败: {str(e)}")
                failed_count += 1
                # 继续处理下一个房源，而不是整体失败
                continue
        
        # 所有操作成功，提交事务
        try:
            conn.commit()
            logger.info(f"批量保存房源完成，成功: {success_count}，失败: {failed_count}")
        except Exception as commit_err:
            logger.error(f"提交事务失败: {str(commit_err)}")
            try:
                conn.rollback()
            except:
                pass
            return {"success": 0, "failed": len(house_info_list)}
            
        return {"success": success_count, "failed": failed_count}
    
    except Exception as e:
        logger.error(f"批量保存房源失败: {str(e)}")
        try:
            conn.rollback()
        except Exception as rollback_err:
            logger.error(f"回滚事务失败: {str(rollback_err)}")
        return {"success": 0, "failed": len(house_info_list)}
    finally:
        # 确保恢复autocommit状态
        try:
            conn.autocommit = True
        except Exception as ac_err:
            logger.warning(f"恢复autocommit状态失败: {str(ac_err)}")

def run_data_analysis(task_id, city, city_code):
    """
    在爬虫任务完成后执行数据分析
    
    Args:
        task_id: 爬虫任务ID
        city: 城市名称
        city_code: 城市代码
    """
    try:
        logger.info(f"爬虫任务 {task_id} 完成，开始执行数据分析...")
        
        # 创建RentalDataProcessor实例
        processor = data_processor.RentalDataProcessor()
        
        try:
            # 加载当前任务的数据
            logger.info(f"正在加载任务 {task_id} 的数据...")
            df = processor.load_data_from_db(city=city, task_id=task_id)
            
            if df:
                # 执行所有分析
                logger.info(f"开始为城市 {city} 执行数据分析...")
                processor.run_all_analysis(df, city=city)
                logger.info(f"数据分析完成，结果已保存到数据库")
            else:
                logger.warning(f"未找到任务 {task_id} 的有效数据，跳过分析")
        finally:
            # 确保关闭Spark会话
            processor.close()
            
    except Exception as e:
        logger.error(f"执行数据分析时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

# 如果直接运行此文件，则初始化验证管理器
if __name__ == '__main__':
    # 初始化验证管理器
    verification_manager.init()
    
    # 检查是否有未完成的任务
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, city, city_code, start_time, status 
            FROM crawl_task 
            WHERE status IN ('In Progress', 'Incomplete', 'Queued') 
            ORDER BY start_time DESC
            LIMIT 5
            """
        )
        unfinished_tasks = cursor.fetchall()
        
        # 检查爬虫锁状态
        is_locked, locked_task_id = is_crawler_locked()
        if is_locked:
            print("\n⚠️ 警告: 爬虫正在运行中，任务ID:", locked_task_id)
            print("新任务将被添加到队列中等待执行")
        
        if unfinished_tasks:
            print("\n===== 检测到未完成的爬取任务 =====")
            print("ID\t城市\t城市代码\t开始时间\t\t\t状态")
            print("-" * 70)
            
            for task in unfinished_tasks:
                task_id, city, city_code, start_time, status = task
                print(f"{task_id}\t{city}\t{city_code}\t\t{start_time}\t{status}")
            
            print("-" * 70)
            continue_task = input("是否要继续一个未完成的任务？(y/n，默认为n): ").strip().lower()
            
            if continue_task == 'y':
                task_id = input("请输入要继续的任务ID: ")
                try:
                    task_id = int(task_id)
                    
                    # 获取任务信息
                    cursor.execute(
                        "SELECT city, city_code, status FROM crawl_task WHERE id = %s",
                        (task_id,)
                    )
                    task_info = cursor.fetchone()
                    
                    if task_info:
                        city, city_code, status = task_info
                        print(f"将继续爬取任务 ID: {task_id}, 城市: {city}({city_code})")
                        
                        # 获取已爬取页数
                        crawled_pages = get_crawled_pages(task_id)
                        print(f"已成功爬取 {len(crawled_pages)} 页")
                        
                        max_pages = input(f"请输入要爬取的最大页数 (已爬取页面会自动跳过，默认: 5): ")
                        try:
                            max_pages = int(max_pages)
                        except:
                            max_pages = 5
                        
                        print(f"继续爬取 {city}({city_code}) 的租房信息，最大页数: {max_pages}")
                        
                        # 检查爬虫锁状态
                        is_locked, locked_task_id = is_crawler_locked()
                        if is_locked and locked_task_id != task_id:
                            print(f"\n⚠️ 爬虫正在运行中，任务将被添加到队列等待执行")
                            update_crawl_task(task_id, "Queued")
                            queue_crawl_task(task_id)
                            print(f"任务 {task_id} 已添加到队列，当前爬虫完成后将自动执行")
                        else:
                            # 开始爬取
                            if is_locked and locked_task_id == task_id:
                                print(f"当前任务已经在执行中")
                            else:
                                # 获取爬虫锁
                                if acquire_crawler_lock(task_id, max_pages):
                                    try:
                                        # 开始爬取
                                        task_id = crawl_city_with_selenium(city, city_code, max_pages, task_id)
                                        
                                        # 导出数据
                                        if task_id:
                                            houses, _ = extract_house_info(None, task_id)
                                            export_to_csv(houses, f"{city}_rental_data_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv")
                                        
                                        # 程序结束
                                        print("爬取任务完成")
                                        
                                        # 检查任务状态，如果成功完成则运行数据分析
                                        conn = connection_pool.getconn()
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            "SELECT status FROM crawl_task WHERE id = %s",
                                            (task_id,)
                                        )
                                        task_status = cursor.fetchone()
                                        connection_pool.putconn(conn)
                                        
                                        if task_status and task_status[0] == "Completed":
                                            print("爬虫任务完成，开始执行数据分析...")
                                            # 直接调用分析函数，而不是开新线程（因为是主程序的最后阶段）
                                            run_data_analysis(task_id, city, city_code)
                                            print("数据分析完成")
                                    finally:
                                        # 确保释放锁
                                        release_crawler_lock(task_id)
                                else:
                                    print("无法获取爬虫锁，可能另一个爬虫正在运行")
                                    # 将任务添加到队列
                                    update_crawl_task(task_id, "Queued")
                                    queue_crawl_task(task_id)
                                    print(f"任务 {task_id} 已添加到队列，当前爬虫完成后将自动执行")
                        
                        exit(0)
                    else:
                        print(f"未找到任务 ID: {task_id}")
                except ValueError:
                    print("无效的任务ID，请输入数字")
                except Exception as e:
                    print(f"处理任务时出错: {str(e)}")
    except Exception as e:
        print(f"查询未完成任务时出错: {str(e)}")
    finally:
        if 'conn' in locals() and conn:
            connection_pool.putconn(conn)
    
    # 获取支持的城市列表
    cities = get_supported_cities()
    print("\n支持的城市列表:")
    for city, code in cities.items():
        print(f"{city}: {code}")
    
    # 选择要爬取的城市
    city_name = input("\n请输入要爬取的城市名称 (默认: 湛江): ") or "湛江"
    city_code = cities.get(city_name)
    
    if not city_code:
        print(f"不支持的城市: {city_name}，将使用默认城市代码: zhanjiang")
        city_code = "zhanjiang"
    
    # 设置爬取页数
    max_pages = input("请输入要爬取的最大页数 (默认: 5): ")
    try:
        max_pages = int(max_pages)
    except:
        max_pages = 5
    
    print(f"开始爬取 {city_name}({city_code}) 的租房信息，最大页数: {max_pages}")
    print("这将使用DrissionPage，请确保已安装Chrome浏览器和WebDriver")
    print("如果遇到人机验证，程序会自动创建验证会话，请查看控制台获取验证URL")
    
    # 创建新的爬取任务
    task_id = start_crawl_task(city_name, city_code)
    
    if task_id:
        # 检查爬虫锁状态
        is_locked, locked_task_id = is_crawler_locked()
        if is_locked:
            print(f"\n⚠️ 爬虫正在运行中，任务将被添加到队列等待执行")
            update_crawl_task(task_id, "Queued")
            queue_crawl_task(task_id)
            print(f"任务 {task_id} 已添加到队列，当前爬虫完成后将自动执行")
        else:
            # 获取爬虫锁
            if acquire_crawler_lock(task_id, max_pages):
                try:
                    # 开始爬取
                    task_id = crawl_city_with_selenium(city_name, city_code, max_pages, task_id)
                    
                    # 导出数据
                    if task_id:
                        houses, _ = extract_house_info(None, task_id)
                        export_to_csv(houses, f"{city_name}_rental_data_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv")
                        
                        # 检查任务状态，如果成功完成则运行数据分析
                        conn = connection_pool.getconn()
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT status FROM crawl_task WHERE id = %s",
                            (task_id,)
                        )
                        task_status = cursor.fetchone()
                        connection_pool.putconn(conn)
                        
                        if task_status and task_status[0] == "Completed":
                            print("爬虫任务完成，开始执行数据分析...")
                            # 直接调用分析函数，而不是开新线程（因为是主程序的最后阶段）
                            run_data_analysis(task_id, city_name, city_code)
                            print("数据分析完成")
                finally:
                    # 确保释放锁
                    release_crawler_lock(task_id)