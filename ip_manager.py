# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
import requests
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import ipaddress
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, validator
import threading
import time
import random

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
        logging.FileHandler(os.path.join(logs_dir, "ip_manager.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ip_manager")

# 创建IP管理器专用的数据库连接池
try:
    ip_manager_pool = db_config.create_pool(
        min_conn=1, 
        max_conn=5, 
        application_name="ip_manager"
    )
    logger.info("IP管理器数据库连接池创建成功")
except Exception as e:
    logger.error(f"IP管理器数据库连接池创建失败: {str(e)}")
    ip_manager_pool = None

# 创建装饰器实例
with_db_connection = db_utils.with_db_connection(ip_manager_pool)

# 定义模型
class ProxyInfo(BaseModel):
    id: Optional[int] = None
    ip: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    location: Optional[str] = None
    status: str = "inactive"  # active, inactive, error
    latency: Optional[int] = None
    last_used: Optional[datetime.datetime] = None
    last_checked: Optional[datetime.datetime] = None
    
    @validator('ip')
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError("无效的IP地址格式")
    
    @validator('port')
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError("端口号必须在1-65535范围内")
        return v

class IpSettings(BaseModel):
    rotation_strategy: str = "manual"  # manual, time, failure, request
    rotation_interval: int = 30  # 分钟
    max_failures: int = 3
    auto_add_proxies: bool = False
    last_updated: datetime.datetime = datetime.datetime.now()

class CurrentIpInfo(BaseModel):
    ip: str
    location: str
    isp: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    last_changed: Optional[datetime.datetime] = None

# 获取当前IP信息
@with_db_connection
def get_current_ip(conn) -> CurrentIpInfo:
    """
    获取当前IP信息，始终从API获取最新状态，确保IP变化能够被实时检测到
    """
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 始终通过API获取最新IP信息
        try:
            response = requests.get('https://ipinfo.io/json', timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                ip = data.get('ip', '')
                location = f"{data.get('city', '')} {data.get('region', '')} {data.get('country', '')}"
                isp = data.get('org', '')
                country = data.get('country', '')
                region = data.get('region', '')
                city = data.get('city', '')
                
                # 检查IP是否变化（与最近一条记录比较）
                cursor.execute("SELECT ip FROM current_ip ORDER BY id DESC LIMIT 1")
                last_record = cursor.fetchone()
                ip_changed = True
                
                if last_record and last_record['ip'] == ip:
                    # IP没有变化，不更新数据库
                    ip_changed = False
                    logger.info(f"当前IP未变化: {ip}")
                else:
                    # IP发生变化，保存到数据库
                    logger.info(f"检测到IP变化，新IP: {ip}")
                    cursor.execute('''
                    INSERT INTO current_ip (ip, location, isp, country, region, city)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (ip, location, isp, country, region, city))
                    conn.commit()
                
                return CurrentIpInfo(
                    ip=ip,
                    location=location,
                    isp=isp,
                    country=country,
                    region=region,
                    city=city,
                    last_changed=datetime.datetime.now() if ip_changed else None
                )
        except Exception as e:
            logger.error(f"通过API获取IP信息失败: {str(e)}")
            
            # 如果API获取失败，尝试从数据库获取最近一条记录
            cursor.execute("SELECT * FROM current_ip ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            
            if result:
                logger.warning("API获取失败，使用数据库中的最后记录")
                return CurrentIpInfo(
                    ip=result['ip'],
                    location=result['location'] or '',
                    isp=result['isp'],
                    country=result['country'],
                    region=result['region'],
                    city=result['city'],
                    last_changed=result['last_changed']
                )
        
        # 如果API获取失败且数据库中没有记录，返回一个默认值
        return CurrentIpInfo(ip="未知", location="未知")
    except Exception as e:
        logger.error(f"获取当前IP信息失败: {str(e)}")
        return CurrentIpInfo(ip="未知", location="未知")

# 刷新IP
@with_db_connection
def refresh_ip(conn) -> bool:
    """
    刷新当前IP，可以通过更换代理或直接获取当前真实IP实现
    返回是否成功刷新
    """
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # 从代理池中选择一个可用的代理
        cursor.execute("SELECT * FROM proxies WHERE status = 'active' ORDER BY RANDOM() LIMIT 1")
        proxy = cursor.fetchone()
        
        if proxy:
            # 使用该代理
            new_ip = proxy['ip']
            new_location = proxy['location'] or "未知"
            
            # 更新当前IP信息
            cursor.execute('''
            INSERT INTO current_ip (ip, location, last_changed)
            VALUES (%s, %s, %s)
            ''', (new_ip, new_location, datetime.datetime.now()))
            
            # 更新代理的使用时间
            cursor.execute('''
            UPDATE proxies SET last_used = %s WHERE id = %s
            ''', (datetime.datetime.now(), proxy['id']))
            
            conn.commit()
            
            logger.info(f"已从代理池刷新IP: {new_ip}")
            return True
        else:
            # 没有可用的代理，尝试获取当前真实IP
            logger.info("没有可用的代理，尝试刷新当前真实IP")
            
            try:
                # 获取当前IP信息
                response = requests.get('https://ipinfo.io/json', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    
                    ip = data.get('ip', '')
                    location = f"{data.get('city', '')} {data.get('region', '')} {data.get('country', '')}"
                    isp = data.get('org', '')
                    country = data.get('country', '')
                    region = data.get('region', '')
                    city = data.get('city', '')
                    
                    # 检查IP是否与最后一次记录相同
                    cursor.execute("SELECT ip FROM current_ip ORDER BY id DESC LIMIT 1")
                    last_record = cursor.fetchone()
                    
                    if last_record and last_record['ip'] == ip:
                        logger.info(f"IP未变化: {ip}")
                        # IP未变化但我们仍然更新时间戳，表示刷新操作已完成
                        cursor.execute('''
                        INSERT INTO current_ip (ip, location, isp, country, region, city)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (ip, location, isp, country, region, city))
                        conn.commit()
                    else:
                        logger.info(f"检测到IP变化，新IP: {ip}")
                        # 保存新的IP信息
                        cursor.execute('''
                        INSERT INTO current_ip (ip, location, isp, country, region, city)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (ip, location, isp, country, region, city))
                        conn.commit()
                    
                    return True
                else:
                    logger.warning(f"获取IP信息失败，HTTP状态码: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"刷新真实IP失败: {str(e)}")
                return False
    except Exception as e:
        conn.rollback()
        logger.error(f"刷新IP失败: {str(e)}")
        return False

# 获取代理列表
@with_db_connection
def get_proxy_list(conn) -> List[ProxyInfo]:
    """获取所有代理信息"""
    proxies = []
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM proxies ORDER BY status DESC, last_used DESC")
        for row in cursor.fetchall():
            proxies.append(ProxyInfo(
                id=row['id'],
                ip=row['ip'],
                port=row['port'],
                username=row['username'],
                password=row['password'],
                location=row['location'],
                status=row['status'],
                latency=row['latency'],
                last_used=row['last_used'],
                last_checked=row['last_checked']
            ))
        logger.info(f"获取到 {len(proxies)} 个代理")
    except Exception as e:
        logger.error(f"获取代理列表失败: {str(e)}")
    
    return proxies

# 添加代理
@with_db_connection
def add_proxy(conn, proxy: ProxyInfo) -> bool:
    """添加一个新代理"""
    try:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO proxies (ip, port, username, password, status, last_checked)
        VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            proxy.ip,
            proxy.port,
            proxy.username,
            proxy.password,
            'inactive',
            datetime.datetime.now()
        ))
        conn.commit()
        logger.info(f"已添加代理: {proxy.ip}:{proxy.port}")
        return True
    except psycopg2.IntegrityError:
        conn.rollback()
        logger.warning(f"代理已存在: {proxy.ip}:{proxy.port}")
        return False
    except Exception as e:
        conn.rollback()
        logger.error(f"添加代理失败: {str(e)}")
        return False

# 删除代理
@with_db_connection
def delete_proxy(conn, proxy_id: int) -> bool:
    """删除一个代理"""
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proxies WHERE id = %s", (proxy_id,))
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"已删除代理ID: {proxy_id}")
            return True
        else:
            logger.warning(f"代理不存在，ID: {proxy_id}")
            return False
    except Exception as e:
        conn.rollback()
        logger.error(f"删除代理失败: {str(e)}")
        return False

# 测试代理
@with_db_connection
def test_proxy(conn, proxy_id: int) -> bool:
    """
    测试代理是否可用
    返回测试结果(成功/失败)和延迟(毫秒)
    """
    latency = None
    status = 'error'
    
    try:
        # 获取代理信息
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM proxies WHERE id = %s", (proxy_id,))
        proxy = cursor.fetchone()
        
        if not proxy:
            logger.warning(f"代理不存在，ID: {proxy_id}")
            return False
    
        # 构建代理URL
        proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
        if proxy['username'] and proxy['password']:
            proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
        
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        # 测试连接
        start_time = time.time()
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            if 'origin' in data:
                latency = int((end_time - start_time) * 1000)  # 毫秒
                status = 'active'
                logger.info(f"代理测试成功，ID: {proxy_id}, 延迟: {latency}ms")
        
    except requests.exceptions.RequestException:
        status = 'error'
        logger.warning(f"代理测试失败，ID: {proxy_id}")
    except Exception as e:
        status = 'error'
        logger.error(f"代理测试发生错误: {str(e)}")
    
    # 更新代理状态
    try:
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE proxies SET status = %s, latency = %s, last_checked = %s WHERE id = %s
        ''', (status, latency, datetime.datetime.now(), proxy_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"更新代理状态失败: {str(e)}")
        return False
    
    return status == 'active'

# 获取IP设置
@with_db_connection
def get_ip_settings(conn) -> IpSettings:
    """获取IP设置"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM ip_settings ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            return IpSettings(
                rotation_strategy=result['rotation_strategy'],
                rotation_interval=result['rotation_interval'],
                max_failures=result['max_failures'],
                auto_add_proxies=result['auto_add_proxies'],
                last_updated=result['last_updated']
            )
    except Exception as e:
        logger.error(f"获取IP设置失败: {str(e)}")
    
    # 返回默认设置
    return IpSettings()

# 保存IP设置
@with_db_connection
def save_ip_settings(conn, settings: IpSettings) -> bool:
    """保存IP设置"""
    try:
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE ip_settings SET
        rotation_strategy = %s,
        rotation_interval = %s,
        max_failures = %s,
        auto_add_proxies = %s,
        last_updated = %s
        WHERE id = 1
        ''', (
            settings.rotation_strategy,
            settings.rotation_interval,
            settings.max_failures,
            settings.auto_add_proxies,
            datetime.datetime.now()
        ))
        
        if cursor.rowcount == 0:
            # 如果没有更新任何记录，说明之前没有设置记录，需要插入
            cursor.execute('''
            INSERT INTO ip_settings (
                id, rotation_strategy, rotation_interval, max_failures, auto_add_proxies, last_updated
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                1,
                settings.rotation_strategy,
                settings.rotation_interval,
                settings.max_failures,
                settings.auto_add_proxies,
                datetime.datetime.now()
            ))
        
        conn.commit()
        logger.info("IP设置已保存")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"保存IP设置失败: {str(e)}")
        return False

# 获取位置信息服务
def get_location(ip: str) -> str:
    """获取IP的地理位置信息"""
    try:
        response = requests.get(f'https://ipinfo.io/{ip}/json')
        if response.status_code == 200:
            data = response.json()
            location = f"{data.get('city', '')} {data.get('region', '')} {data.get('country', '')}"
            isp = data.get('org', '')
            return f"{location.strip()} {isp}"
    except Exception as e:
        logger.error(f"获取位置信息失败: {str(e)}")
    
    return "未知"

# 获取随机可用代理
@with_db_connection
def get_random_proxy(conn) -> Optional[Dict[str, str]]:
    """
    获取一个随机可用的代理，供爬虫使用
    返回格式: {'http': 'http://user:pass@ip:port', 'https': 'http://user:pass@ip:port'} 或 None
    """
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM proxies WHERE status = 'active' ORDER BY RANDOM() LIMIT 1")
        proxy = cursor.fetchone()
        
        if not proxy:
            logger.warning("没有找到可用的代理")
            return None
        
        # 构建代理URL
        proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
        if proxy['username'] and proxy['password']:
            proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
        
        # 更新代理的使用时间
        cursor.execute('''
        UPDATE proxies SET last_used = %s WHERE id = %s
        ''', (datetime.datetime.now(), proxy['id']))
        conn.commit()
        
        logger.info(f"获取代理成功: {proxy['ip']}:{proxy['port']}")
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"获取代理失败: {str(e)}")
        return None

# 初始化
def initialize():
    """初始化IP管理模块"""
    logger.info("IP管理模块已初始化")

# 当作为独立模块运行时初始化数据库
if __name__ == "__main__":
    initialize() 