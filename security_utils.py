"""
安全工具模块
提供输入验证和SQL注入防护功能
"""
import re
import logging
from typing import Any, Union, List, Optional
import html

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("security_utils")

class SecurityValidator:
    """安全验证器类"""
    
    # SQL注入关键词黑名单
    SQL_INJECTION_PATTERNS = [
        r'\b(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|TRUNCATE)\b',
        r'\b(UNION|SELECT|FROM|WHERE|HAVING|GROUP BY|ORDER BY)\b',
        r'[;\'"\\]',
        r'--',
        r'/\*|\*/',
        r'\bOR\s+\d+\s*=\s*\d+',
        r'\bAND\s+\d+\s*=\s*\d+',
        r'\b(EXEC|EXECUTE|sp_|xp_)\b',
        r'\b(SCRIPT|JAVASCRIPT|VBSCRIPT)\b'
    ]
    
    @staticmethod
    def validate_string_input(value: Any, max_length: int = 255, allow_empty: bool = True) -> str:
        """
        验证字符串输入
        
        Args:
            value: 输入值
            max_length: 最大长度
            allow_empty: 是否允许空值
            
        Returns:
            str: 验证后的字符串
            
        Raises:
            ValueError: 输入不合法时抛出异常
        """
        if value is None:
            if allow_empty:
                return ""
            else:
                raise ValueError("输入不能为空")
        
        # 转换为字符串
        if not isinstance(value, str):
            value = str(value)
        
        # 长度检查
        if len(value) > max_length:
            raise ValueError(f"输入长度超出限制，最大长度: {max_length}")
        
        # SQL注入检查
        if SecurityValidator.contains_sql_injection(value):
            logger.warning(f"检测到潜在SQL注入攻击: {value}")
            raise ValueError("输入包含非法字符")
        
        # HTML转义
        value = html.escape(value, quote=True)
        
        return value.strip()
    
    @staticmethod
    def validate_integer_input(value: Any, min_value: int = None, max_value: int = None) -> int:
        """
        验证整数输入
        
        Args:
            value: 输入值
            min_value: 最小值
            max_value: 最大值
            
        Returns:
            int: 验证后的整数
            
        Raises:
            ValueError: 输入不合法时抛出异常
        """
        if value is None:
            raise ValueError("输入不能为空")
        
        # 尝试转换为整数
        try:
            if isinstance(value, str):
                # 检查是否包含非数字字符
                if not value.isdigit() and not (value.startswith('-') and value[1:].isdigit()):
                    raise ValueError("输入不是有效的整数")
            
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValueError("输入不是有效的整数")
        
        # 范围检查
        if min_value is not None and int_value < min_value:
            raise ValueError(f"输入值过小，最小值: {min_value}")
        
        if max_value is not None and int_value > max_value:
            raise ValueError(f"输入值过大，最大值: {max_value}")
        
        return int_value
    
    @staticmethod
    def validate_float_input(value: Any, min_value: float = None, max_value: float = None) -> float:
        """
        验证浮点数输入
        
        Args:
            value: 输入值
            min_value: 最小值
            max_value: 最大值
            
        Returns:
            float: 验证后的浮点数
            
        Raises:
            ValueError: 输入不合法时抛出异常
        """
        if value is None:
            raise ValueError("输入不能为空")
        
        # 尝试转换为浮点数
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValueError("输入不是有效的浮点数")
        
        # 范围检查
        if min_value is not None and float_value < min_value:
            raise ValueError(f"输入值过小，最小值: {min_value}")
        
        if max_value is not None and float_value > max_value:
            raise ValueError(f"输入值过大，最大值: {max_value}")
        
        return float_value
    
    @staticmethod
    def contains_sql_injection(input_str: str) -> bool:
        """
        检查字符串是否包含SQL注入模式
        
        Args:
            input_str: 输入字符串
            
        Returns:
            bool: 如果包含SQL注入模式返回True
        """
        if not input_str:
            return False
        
        input_str = input_str.upper()
        
        for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def sanitize_sql_identifier(identifier: str) -> str:
        """
        清理SQL标识符（表名、列名等）
        
        Args:
            identifier: SQL标识符
            
        Returns:
            str: 清理后的标识符
            
        Raises:
            ValueError: 标识符不合法时抛出异常
        """
        if not identifier:
            raise ValueError("SQL标识符不能为空")
        
        # 只允许字母、数字和下划线
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            raise ValueError("SQL标识符只能包含字母、数字和下划线，且不能以数字开头")
        
        # 检查长度
        if len(identifier) > 63:  # PostgreSQL标识符最大长度
            raise ValueError("SQL标识符长度不能超过63个字符")
        
        return identifier.lower()
    
    @staticmethod
    def validate_sort_order(sort_order: str) -> str:
        """
        验证排序方向
        
        Args:
            sort_order: 排序方向
            
        Returns:
            str: 验证后的排序方向（ASC或DESC）
            
        Raises:
            ValueError: 排序方向不合法时抛出异常
        """
        if not sort_order:
            return "ASC"
        
        sort_order = sort_order.upper()
        
        if sort_order not in ["ASC", "DESC"]:
            raise ValueError("排序方向只能是ASC或DESC")
        
        return sort_order

class SafeQueryBuilder:
    """安全查询构建器"""
    
    @staticmethod
    def build_filter_conditions(filters: dict) -> tuple:
        """
        安全地构建WHERE条件
        
        Args:
            filters: 过滤条件字典
            
        Returns:
            tuple: (conditions_list, params_list)
        """
        conditions = []
        params = []
        
        for key, value in filters.items():
            if value is None:
                continue
            
            # 验证列名
            safe_column = SecurityValidator.sanitize_sql_identifier(key)
            
            # 根据值类型构建条件
            if isinstance(value, dict):
                # 范围查询
                if 'min' in value and value['min'] is not None:
                    conditions.append(f"{safe_column} >= %s")
                    params.append(value['min'])
                
                if 'max' in value and value['max'] is not None:
                    conditions.append(f"{safe_column} <= %s")
                    params.append(value['max'])
            
            elif isinstance(value, list):
                # IN查询
                if value:  # 非空列表
                    placeholders = ', '.join(['%s'] * len(value))
                    conditions.append(f"{safe_column} IN ({placeholders})")
                    params.extend(value)
            
            else:
                # 等值查询
                conditions.append(f"{safe_column} = %s")
                params.append(value)
        
        return conditions, params
    
    @staticmethod
    def build_pagination_clause(limit: int = None, offset: int = None) -> tuple:
        """
        安全地构建分页查询
        
        Args:
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            tuple: (clause, params)
        """
        clause = ""
        params = []
        
        if limit is not None:
            validated_limit = SecurityValidator.validate_integer_input(limit, min_value=1, max_value=10000)
            clause += " LIMIT %s"
            params.append(validated_limit)
        
        if offset is not None:
            validated_offset = SecurityValidator.validate_integer_input(offset, min_value=0)
            clause += " OFFSET %s"
            params.append(validated_offset)
        
        return clause, params
    
    @staticmethod
    def build_order_clause(order_by: str = None, sort_order: str = "ASC") -> str:
        """
        安全地构建ORDER BY子句
        
        Args:
            order_by: 排序字段
            sort_order: 排序方向
            
        Returns:
            str: ORDER BY子句
        """
        if not order_by:
            return ""
        
        safe_column = SecurityValidator.sanitize_sql_identifier(order_by)
        safe_order = SecurityValidator.validate_sort_order(sort_order)
        
        return f" ORDER BY {safe_column} {safe_order}"

# 导出常用的验证函数
def validate_city_name(city: str) -> str:
    """验证城市名称"""
    return SecurityValidator.validate_string_input(city, max_length=50, allow_empty=False)

def validate_district_name(district: str) -> str:
    """验证区域名称"""
    return SecurityValidator.validate_string_input(district, max_length=50, allow_empty=True)

def validate_price_range(min_price: int = None, max_price: int = None) -> tuple:
    """验证价格范围"""
    validated_min = None
    validated_max = None
    
    if min_price is not None:
        validated_min = SecurityValidator.validate_integer_input(min_price, min_value=0, max_value=1000000)
    
    if max_price is not None:
        validated_max = SecurityValidator.validate_integer_input(max_price, min_value=0, max_value=1000000)
    
    # 检查范围合理性
    if validated_min is not None and validated_max is not None and validated_min > validated_max:
        raise ValueError("最小价格不能大于最大价格")
    
    return validated_min, validated_max

def validate_size_range(min_size: float = None, max_size: float = None) -> tuple:
    """验证面积范围"""
    validated_min = None
    validated_max = None
    
    if min_size is not None:
        validated_min = SecurityValidator.validate_float_input(min_size, min_value=0.0, max_value=10000.0)
    
    if max_size is not None:
        validated_max = SecurityValidator.validate_float_input(max_size, min_value=0.0, max_value=10000.0)
    
    # 检查范围合理性
    if validated_min is not None and validated_max is not None and validated_min > validated_max:
        raise ValueError("最小面积不能大于最大面积")
    
    return validated_min, validated_max

def validate_room_count(room_count: int = None) -> int:
    """验证房间数量"""
    if room_count is None:
        return None
    
    return SecurityValidator.validate_integer_input(room_count, min_value=1, max_value=10)

def validate_pagination(limit: int = 20, offset: int = 0) -> tuple:
    """验证分页参数"""
    validated_limit = SecurityValidator.validate_integer_input(limit, min_value=1, max_value=1000)
    validated_offset = SecurityValidator.validate_integer_input(offset, min_value=0)
    
    return validated_limit, validated_offset 