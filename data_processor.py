# -*- coding: utf-8 -*-
import os
import logging
import datetime
import pandas as pd
import numpy as np
import psycopg2
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, round as spark_round, avg, count, min, max, stddev, expr, when, regexp_extract, lag, date_format, explode, array_contains, from_json, lit
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, TimestampType, ArrayType
import traceback
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number

# 确保logs目录存在
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "data_processor.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("data_processor")

class RentalDataProcessor:
    def __init__(self, db_config=None):
        """
        初始化数据处理器
        :param db_config: 数据库配置信息，默认为本地PostgreSQL
        """
        # 默认数据库配置
        self.db_config = db_config or {
            "user": "postgres",
            "password": "123456",
            "host": "localhost",
            "port": "5432",
            "database": "rental_analysis"
        }
        
        # 初始化Spark会话
        self.spark = self._create_spark_session()
        
        # 定义数据库表结构
        self.house_schema = StructType([
            StructField("id", IntegerType(), True),
            StructField("house_id", StringType(), True),
            StructField("title", StringType(), True),
            StructField("price", IntegerType(), True),
            StructField("location_qu", StringType(), True),
            StructField("location_big", StringType(), True),
            StructField("location_small", StringType(), True),
            StructField("size", FloatType(), True),
            StructField("direction", StringType(), True),
            StructField("room", StringType(), True),
            StructField("floor", StringType(), True),
            StructField("image", StringType(), True),
            StructField("link", StringType(), True),
            StructField("unit_price", FloatType(), True),
            StructField("room_count", IntegerType(), True),
            StructField("hall_count", IntegerType(), True),
            StructField("bath_count", IntegerType(), True),
            StructField("crawl_time", TimestampType(), True),
            StructField("task_id", IntegerType(), True)
        ])
    
    def _create_spark_session(self):
        """创建Spark会话"""
        try:
            # 获取当前工作目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            workspace_dir = os.path.abspath(os.getcwd())
            
            # 查找PostgreSQL驱动
            jar_path = os.path.join(workspace_dir, "postgresql-42.3.1.jar")
            if not os.path.exists(jar_path):
                jar_path = os.path.join(current_dir, "postgresql-42.3.1.jar")
                if not os.path.exists(jar_path):
                    # 如果在上述位置找不到，尝试在当前脚本所在目录查找
                    jar_path = "postgresql-42.3.1.jar"
            
            logger.info(f"使用PostgreSQL JDBC驱动: {jar_path}")
            
            # 针对Windows环境的Hadoop配置
            os.environ['HADOOP_HOME'] = workspace_dir
            
            # 创建Hive Metastore数据库连接字符串
            metastore_jdbc_url = f"jdbc:postgresql://{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            metastore_jdbc_driver = "org.postgresql.Driver"
            metastore_username = self.db_config['user']
            metastore_password = self.db_config['password']
            
            # 配置参数，增加网络超时和资源设置
            hadoop_conf = {
                "spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version": "2",
                "spark.jars": jar_path,
                "spark.driver.extraClassPath": jar_path,
                "spark.executor.extraClassPath": jar_path,
                
                # 配置使用外部Hive Metastore (PostgreSQL)
                "spark.sql.catalogImplementation": "hive",
                "spark.sql.warehouse.dir": os.path.join(workspace_dir, "spark-warehouse"),
                "spark.hadoop.javax.jdo.option.ConnectionURL": metastore_jdbc_url,
                "spark.hadoop.javax.jdo.option.ConnectionDriverName": metastore_jdbc_driver,
                "spark.hadoop.javax.jdo.option.ConnectionUserName": metastore_username,
                "spark.hadoop.javax.jdo.option.ConnectionPassword": metastore_password,
                "spark.hadoop.datanucleus.autoCreateSchema": "true",
                "spark.hadoop.datanucleus.autoCreateTables": "true",
                "spark.hadoop.hive.metastore.schema.verification": "false",
                
                # 增加内存配置
                "spark.executor.memory": "3g",
                "spark.driver.memory": "3g",
                "spark.sql.crossJoin.enabled": "true",
                # 绕过Windows Hadoop依赖
                "spark.hadoop.fs.file.impl": "org.apache.hadoop.fs.LocalFileSystem",
                "spark.sql.adaptive.enabled": "true",
                # 在本地模式下运行，减少并行度以匹配资源
                "spark.master": "local[2]",
                # 增加网络超时设置
                "spark.network.timeout": "1200s",
                "spark.executor.heartbeatInterval": "240s",
                "spark.storage.blockManagerSlaveTimeoutMs": "1200000",
                "spark.rpc.askTimeout": "1200s",
                "spark.rpc.lookupTimeout": "1200s",
                # 增加SQL查询超时
                "spark.sql.broadcastTimeout": "2400s",
                # 优化内存使用
                "spark.memory.fraction": "0.7",
                "spark.memory.storageFraction": "0.3",
                # 优化序列化
                "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
                # 减少分区数量，防止创建过多小任务
                "spark.sql.shuffle.partitions": "4",
                "spark.default.parallelism": "4",
                # 添加Python worker超时设置
                "spark.python.worker.timeout": "1200s",
                "spark.python.task.maxFailures": "3",
                "spark.python.worker.reuse": "true",
                "spark.python.worker.memory": "1g"
            }
            
            # 创建Spark会话
            spark_builder = SparkSession.builder.appName("RentalDataAnalysis").enableHiveSupport()
            
            # 添加所有配置
            for key, value in hadoop_conf.items():
                spark_builder = spark_builder.config(key, value)
            
            spark = spark_builder.getOrCreate()
            
            # 设置日志级别
            spark.sparkContext.setLogLevel("WARN")
            
            logger.info("Spark会话创建成功，使用PostgreSQL作为Hive Metastore")
            return spark
        except Exception as e:
            logger.error(f"创建Spark会话失败: {str(e)}")
            raise
    
    def load_data_from_db(self, city=None, task_id=None, limit=None):
        """
        从数据库加载数据
        :param city: 城市名称
        :param task_id: 任务ID
        :param limit: 限制记录数
        :return: Spark DataFrame
        """
        try:
            # 构建JDBC URL
            jdbc_url = f"jdbc:postgresql://{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            
            # 构建查询条件
            query = "SELECT h.* FROM house_info h"
            
            if city or task_id:
                query += " JOIN crawl_task t ON h.task_id = t.id WHERE "
                conditions = []
                
                if city:
                    conditions.append(f"t.city = '{city}'")
                
                if task_id:
                    conditions.append(f"t.id = {task_id}")
                
                query += " AND ".join(conditions)
            
            if limit:
                query += f" LIMIT {limit}"
            
            logger.info(f"执行SQL查询: {query}")
            logger.info(f"JDBC URL: {jdbc_url}")
            
            # 设置JDBC连接属性，优化连接池参数
            jdbc_properties = {
                "url": jdbc_url,
                "dbtable": f"({query}) as house_data",
                "user": self.db_config["user"],
                "password": self.db_config["password"],
                "driver": "org.postgresql.Driver",
                # 添加连接池配置
                "fetchsize": "1000",  # 每批次获取的行数
                "partitionColumn": "id",  # 分区列
                "numPartitions": "4",  # 并行度
                "lowerBound": "1",  # ID最小值
                "upperBound": "1000000"  # ID最大值估计
            }
            
            # 设置重试逻辑
            max_retries = 3
            retry_wait = 2  # 初始等待时间（秒）
            
            # 重试循环
            last_exception = None
            for retry in range(max_retries):
                try:
                    # 从数据库加载数据
                    df = self.spark.read.format("jdbc").options(**jdbc_properties).load()
                    
                    # 显示数据统计
                    count = df.count()
                    logger.info(f"从数据库加载了 {count} 条房源记录")
                    
                    # 确保features字段正确解析为数组
                    if "features" in df.columns:
                        try:
                            # 尝试解析features列，假设它是JSON字符串数组
                            df = df.withColumn("features", from_json(col("features"), ArrayType(StringType())))
                            logger.info("成功将features字段解析为数组类型")
                        except Exception as parse_err:
                            logger.warning(f"解析features字段失败: {str(parse_err)}，将尝试保持原样")
                    else:
                        logger.warning("数据中不包含features字段")
                    
                    # 检查数据有效性
                    if count > 0:
                        # 添加缓存以提高后续处理性能
                        df.cache()
                        return df
                    else:
                        logger.warning("查询结果为空，请检查筛选条件")
                        return None
                        
                except Exception as e:
                    last_exception = e
                    logger.warning(f"从数据库加载数据失败 (尝试 {retry+1}/{max_retries}): {str(e)}")
                    
                    # 如果还有重试机会，等待后重试
                    if retry < max_retries - 1:
                        wait_time = retry_wait * (2 ** retry)  # 指数退避
                        logger.info(f"等待 {wait_time} 秒后重试...")
                        import time
                        time.sleep(wait_time)
                        
                        # 在重试前进行垃圾回收
                        import gc
                        gc.collect()
            
            # 如果所有重试都失败，尝试进行一个简单的数据库连接测试
            logger.error(f"从数据库加载数据失败，已重试 {max_retries} 次: {str(last_exception)}")
            conn = None
            cursor = None
            try:
                logger.info("尝试测试数据库连接...")
                conn = psycopg2.connect(
                    user=self.db_config["user"],
                    password=self.db_config["password"],
                    host=self.db_config["host"],
                    port=self.db_config["port"],
                    database=self.db_config["database"],
                    connect_timeout=5  # 设置连接超时
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                logger.info("数据库连接测试成功")
            except Exception as conn_error:
                logger.error(f"数据库连接测试失败: {str(conn_error)}")
            finally:
                # 确保关闭cursor和连接
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
            
            # 如果尝试了所有重试后仍失败，则抛出异常
            raise last_exception or Exception("从数据库加载数据失败，原因未知")
            
        except Exception as e:
            logger.error(f"从数据库加载数据失败: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return None
    
    def load_data_from_csv(self, file_path):
        """
        从CSV文件加载数据
        :param file_path: CSV文件路径
        :return: Spark DataFrame
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            # 从CSV加载数据
            df = self.spark.read \
                .option("header", "true") \
                .option("inferSchema", "true") \
                .csv(file_path)
            
            # 显示数据统计
            count = df.count()
            logger.info(f"从CSV文件加载了 {count} 条房源记录")
            
            return df
        except Exception as e:
            logger.error(f"从CSV文件加载数据失败: {str(e)}")
            return None
    
    def clean_data(self, df):
        """
        数据清洗
        :param df: 输入的DataFrame
        :return: 清洗后的DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要清洗")
                return None
            
            # 记录初始数据量
            original_count = df.count()
            logger.info(f"开始清洗数据，原始记录数: {original_count}")
            
            # 检查缺失的字段并创建诊断信息
            for column in df.columns:
                null_count = df.filter(col(column).isNull()).count()
                null_percentage = (null_count / original_count) * 100
                logger.info(f"字段 {column}: 缺失值数量 {null_count}/{original_count} ({null_percentage:.2f}%)")
            
            # 数据转换和基本清洗 - 放宽条件，允许部分字段为空
            cleaned_df = df \
                .filter(col("price").isNotNull()) \
                .filter(col("price") > 0)
                
            # 如果size字段存在且大于0，保留它，否则尝试使用默认值
            if "size" in df.columns:
                cleaned_df = cleaned_df.filter(col("size").isNotNull()) \
                               .filter(col("size") > 0)
                # 在此添加单价计算，如果size大于0
                cleaned_df = cleaned_df.withColumn("unit_price", 
                                     when(col("size") > 0, spark_round(col("price") / col("size"), 2))
                                     .otherwise(None))
            
            # 记录基本清洗后的数据量
            after_clean_count = cleaned_df.count()
            logger.info(f"基本清洗后记录数: {after_clean_count}，移除了 {original_count - after_clean_count} 条无效记录")
            
            # 数据去重：按house_id分组，保留最新的记录
            if "house_id" in cleaned_df.columns:
                # 定义窗口函数，按house_id分组，按crawl_time降序排序
                window_spec = Window.partitionBy("house_id").orderBy(col("crawl_time").desc())
                
                # 使用窗口函数为每条记录分配序号，相同house_id中最新的记录序号为1
                deduped_df = cleaned_df.withColumn("row_num", row_number().over(window_spec))
                
                # 只保留每个house_id的最新记录（row_num=1）
                deduped_df = deduped_df.filter(col("row_num") == 1).drop("row_num")
                
                # 记录去重后的数据量
                after_dedup_count = deduped_df.count()
                logger.info(f"去重后记录数: {after_dedup_count}，移除了 {after_clean_count - after_dedup_count} 条重复记录")
                
                cleaned_df = deduped_df
            else:
                logger.warning("数据中没有house_id字段，无法进行去重操作")
            
            # 显示清洗结果
            final_count = cleaned_df.count()
            removed_count = original_count - final_count
            
            logger.info(f"数据清洗完成: 总记录数 {original_count}，有效记录数 {final_count}，已移除 {removed_count} 条无效/重复记录")
            
            return cleaned_df
        except Exception as e:
            logger.error(f"数据清洗失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return df
    
    def analyze_by_district(self, df):
        """
        按区域分析租金
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 按区域分组统计
            district_stats = df.groupBy("location_qu") \
                .agg(
                    count("*").alias("house_count"),
                    avg("price").alias("avg_price"),
                    min("price").alias("min_price"),
                    max("price").alias("max_price"),
                    stddev("price").alias("stddev_price"),
                    avg("unit_price").alias("avg_unit_price"),
                    avg("size").alias("avg_size")
                ) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_unit_price", spark_round(col("avg_unit_price"), 2)) \
                .withColumn("avg_size", spark_round(col("avg_size"), 2)) \
                .withColumn("stddev_price", spark_round(col("stddev_price"), 2)) \
                .orderBy(col("avg_price").desc())
            
            logger.info("区域租金分析完成")
            return district_stats
        except Exception as e:
            logger.error(f"区域租金分析失败: {str(e)}")
            return None
    
    def analyze_by_room_type(self, df):
        """
        按户型分析租金
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 按户型分组统计
            room_type_stats = df.groupBy("room_count", "hall_count") \
                .agg(
                    count("*").alias("house_count"),
                    avg("price").alias("avg_price"),
                    min("price").alias("min_price"),
                    max("price").alias("max_price"),
                    avg("unit_price").alias("avg_unit_price"),
                    avg("size").alias("avg_size")
                ) \
                .withColumn("room_type", expr("concat(room_count, '室', hall_count, '厅')")) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_unit_price", spark_round(col("avg_unit_price"), 2)) \
                .withColumn("avg_size", spark_round(col("avg_size"), 2)) \
                .orderBy(col("house_count").desc())
            
            logger.info("户型租金分析完成")
            return room_type_stats
        except Exception as e:
            logger.error(f"户型租金分析失败: {str(e)}")
            return None
    
    def analyze_by_direction(self, df):
        """
        按朝向分析租金
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 按朝向分组统计
            direction_stats = df.groupBy("direction") \
                .agg(
                    count("*").alias("house_count"),
                    avg("price").alias("avg_price"),
                    min("price").alias("min_price"),
                    max("price").alias("max_price"),
                    avg("unit_price").alias("avg_unit_price")
                ) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_unit_price", spark_round(col("avg_unit_price"), 2)) \
                .orderBy(col("house_count").desc())
            
            logger.info("朝向租金分析完成")
            return direction_stats
        except Exception as e:
            logger.error(f"朝向租金分析失败: {str(e)}")
            return None
    
    def analyze_by_floor(self, df):
        """
        按楼层分析租金
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 提取楼层类型
            floor_df = df.withColumn(
                "floor_type",
                when(col("floor").contains("低"), "低楼层")
                .when(col("floor").contains("中"), "中楼层")
                .when(col("floor").contains("高"), "高楼层")
                .otherwise("其他")
            )
            
            # 按楼层类型分组统计
            floor_stats = floor_df.groupBy("floor_type") \
                .agg(
                    count("*").alias("house_count"),
                    avg("price").alias("avg_price"),
                    min("price").alias("min_price"),
                    max("price").alias("max_price"),
                    avg("unit_price").alias("avg_unit_price")
                ) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_unit_price", spark_round(col("avg_unit_price"), 2)) \
                .orderBy(col("floor_type"))
            
            logger.info("楼层租金分析完成")
            return floor_stats
        except Exception as e:
            logger.error(f"楼层租金分析失败: {str(e)}")
            return None
    
    def analyze_price_distribution(self, df):
        """
        分析租金价格分布
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 定义租金区间
            price_ranges = [
                (0, 1000, "1000元以下"),
                (1000, 1500, "1000-1500元"),
                (1500, 2000, "1500-2000元"),
                (2000, 2500, "2000-2500元"),
                (2500, 3000, "2500-3000元"),
                (3000, 4000, "3000-4000元"),
                (4000, 5000, "4000-5000元"),
                (5000, 10000, "5000-10000元"),
                (10000, float('inf'), "10000元以上")
            ]
            
            # 使用when链创建租金区间列
            from pyspark.sql.functions import lit
            price_range_column = None
            
            for min_price, max_price, label in price_ranges:
                if price_range_column is None:
                    price_range_column = when((col("price") >= min_price) & (col("price") < max_price), label)
                else:
                    price_range_column = price_range_column.when((col("price") >= min_price) & (col("price") < max_price), label)
            
            # 对于不属于任何区间的值，赋予默认值
            price_range_column = price_range_column.otherwise("其他")
            
            # 创建带有租金区间的新DataFrame
            df_with_range = df.withColumn("price_range", price_range_column)
            
            # 按租金区间分组统计
            price_distribution = df_with_range.groupBy("price_range") \
                .agg(count("*").alias("house_count")) \
                .orderBy("price_range")
            
            logger.info("租金价格分布分析完成")
            return price_distribution
        except Exception as e:
            logger.error(f"租金价格分布分析失败: {str(e)}")
            return None
    
    def analyze_size_price_correlation(self, df):
        """
        分析面积与租金的相关性
        :param df: 输入的DataFrame
        :return: 相关系数
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 转换为Pandas DataFrame进行相关性分析
            pandas_df = df.select("size", "price").toPandas()
            correlation = pandas_df.corr().iloc[0, 1]
            
            logger.info(f"面积与租金的相关系数: {correlation:.4f}")
            return correlation
        except Exception as e:
            logger.error(f"相关性分析失败: {str(e)}")
            return None
    
    def analyze_by_community(self, df, top_n=20):
        """
        分析小区租金情况
        :param df: 输入的DataFrame
        :param top_n: 返回的小区数量
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 按小区分组统计
            community_stats = df.groupBy("location_small") \
                .agg(
                    count("*").alias("house_count"),
                    avg("price").alias("avg_price"),
                    min("price").alias("min_price"),
                    max("price").alias("max_price"),
                    avg("unit_price").alias("avg_unit_price"),
                    avg("size").alias("avg_size")
                ) \
                .filter(col("house_count") >= 3) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_unit_price", spark_round(col("avg_unit_price"), 2)) \
                .withColumn("avg_size", spark_round(col("avg_size"), 2)) \
                .orderBy(col("avg_price").desc()) \
                .limit(top_n)
            
            logger.info(f"小区租金分析完成，返回前 {top_n} 个小区")
            return community_stats
        except Exception as e:
            logger.error(f"小区租金分析失败: {str(e)}")
            return None
    
    def save_analysis_to_db(self, analysis_df, analysis_type, city=None):
        """
        将分析结果保存到数据库
        :param analysis_df: 分析结果DataFrame
        :param analysis_type: 分析类型
        :param city: 城市名称
        :return: 是否成功
        """
        conn = None
        cursor = None
        try:
            if analysis_df is None or analysis_df.count() == 0:
                logger.warning("没有分析结果需要保存")
                return False
            
            # 准备数据库连接
            conn = psycopg2.connect(
                user=self.db_config["user"],
                password=self.db_config["password"],
                host=self.db_config["host"],
                port=self.db_config["port"],
                database=self.db_config["database"],
                client_encoding='UTF8'  # 使用UTF8编码以支持中文
            )
            cursor = conn.cursor()
            
            # 将分析结果转换为JSON字符串
            pandas_df = analysis_df.toPandas()
            result_json = pandas_df.to_json(orient="records")
            
            # 插入分析结果
            cursor.execute(
                "INSERT INTO analysis_result (analysis_type, city, analysis_time, result_data) VALUES (%s, %s, %s, %s)",
                (analysis_type, city, datetime.datetime.now(), result_json)
            )
            
            conn.commit()
            logger.info(f"分析结果已保存到数据库，类型: {analysis_type}, 城市: {city}")
            return True
        except Exception as e:
            logger.error(f"保存分析结果到数据库失败: {str(e)}")
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"回滚事务失败: {str(rollback_error)}")
            return False
        finally:
            # 确保关闭cursor和连接
            if cursor:
                try:
                    cursor.close()
                except Exception as cursor_error:
                    logger.error(f"关闭cursor失败: {str(cursor_error)}")
            if conn:
                try:
                    conn.close()
                    logger.debug("数据库连接已关闭")
                except Exception as conn_error:
                    logger.error(f"关闭数据库连接失败: {str(conn_error)}")
    
    def export_analysis_to_csv(self, analysis_df, filename):
        """
        将分析结果导出为CSV文件
        :param analysis_df: 分析结果DataFrame
        :param filename: 文件名
        :return: 是否成功
        """
        try:
            if analysis_df is None or analysis_df.count() == 0:
                logger.warning("没有分析结果需要导出")
                return False
            
            # 转换为Pandas DataFrame并导出
            pandas_df = analysis_df.toPandas()
            pandas_df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            logger.info(f"分析结果已导出到 {filename}")
            return True
        except Exception as e:
            logger.error(f"导出分析结果失败: {str(e)}")
            return False
    
    def analyze_price_trend(self, df):
        """
        分析租金价格随时间变化趋势
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 增加日期列
            from pyspark.sql.functions import date_format, to_date
            df_with_date = df.withColumn("crawl_date", date_format(col("crawl_time"), "yyyy-MM-dd"))
            
            # 按日期和区域分组统计
            trend_stats = df_with_date.groupBy("crawl_date", "location_qu") \
                .agg(
                    count("*").alias("house_count"),
                    avg("price").alias("avg_price"),
                    avg("unit_price").alias("avg_unit_price")
                ) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_unit_price", spark_round(col("avg_unit_price"), 2)) \
                .orderBy("crawl_date", "location_qu")
            
            logger.info("租金价格趋势分析完成")
            return trend_stats
        except Exception as e:
            logger.error(f"租金价格趋势分析失败: {str(e)}")
            return None
    
    def analyze_price_stats_by_district(self, df):
        """
        按区域进行价格统计分析，包括均值、中位数、四分位数等
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            logger.info("开始区域价格统计分析，使用优化的内存管理")
            
            # 使用纯Spark SQL方式处理，避免转换为Pandas造成的内存问题
            # 注册临时视图
            df.createOrReplaceTempView("house_data")
            
            # 使用Spark SQL进行数据分析
            result_df = self.spark.sql("""
                SELECT 
                    location_qu,
                    COUNT(*) as price_count,
                    ROUND(AVG(price), 2) as price_mean,
                    ROUND(PERCENTILE_APPROX(price, 0.5), 2) as price_median,
                    ROUND(MIN(price), 2) as price_min,
                    ROUND(MAX(price), 2) as price_max,
                    ROUND(STDDEV(price), 2) as price_std,
                    ROUND(PERCENTILE_APPROX(price, 0.25), 2) as price_25th,
                    ROUND(PERCENTILE_APPROX(price, 0.75), 2) as price_75th,
                    ROUND(AVG(unit_price), 2) as unit_price_mean,
                    ROUND(PERCENTILE_APPROX(unit_price, 0.5), 2) as unit_price_median,
                    ROUND(MIN(unit_price), 2) as unit_price_min,
                    ROUND(MAX(unit_price), 2) as unit_price_max,
                    ROUND(STDDEV(unit_price), 2) as unit_price_std,
                    ROUND(AVG(size), 2) as size_mean,
                    ROUND(PERCENTILE_APPROX(size, 0.5), 2) as size_median,
                    ROUND(MIN(size), 2) as size_min,
                    ROUND(MAX(size), 2) as size_max,
                    ROUND(STDDEV(size), 2) as size_std
                FROM house_data
                WHERE location_qu IS NOT NULL AND price > 0 AND size > 0
                GROUP BY location_qu
                ORDER BY price_count DESC
            """)
            
            # 清理内存
            self.spark.catalog.dropTempView("house_data")
            
            # 强制执行
            row_count = result_df.count()
            logger.info(f"区域价格统计分析完成，共 {row_count} 个区域")
            
            # 如果行数少于5个，记录详细信息以便调试
            if row_count < 5:
                logger.info(f"区域统计详细信息: {result_df.collect()}")
            
            return result_df
            
        except Exception as e:
            logger.error(f"区域价格统计分析失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            
            # 尝试备用方案 - 简化版本，只计算基本统计数据
            try:
                logger.info("尝试使用简化方法执行区域价格统计分析")
                
                # 使用简单的聚合函数，避免复杂计算
                simple_stats = df.filter(col("location_qu").isNotNull()) \
                    .filter(col("price") > 0) \
                    .groupBy("location_qu") \
                    .agg(
                        count("*").alias("price_count"),
                        avg("price").alias("price_mean"),
                        min("price").alias("price_min"),
                        max("price").alias("price_max"),
                        avg("unit_price").alias("unit_price_mean"),
                        avg("size").alias("size_mean")
                    ) \
                    .withColumn("price_mean", spark_round(col("price_mean"), 2)) \
                    .withColumn("unit_price_mean", spark_round(col("unit_price_mean"), 2)) \
                    .withColumn("size_mean", spark_round(col("size_mean"), 2)) \
                    .orderBy(col("price_count").desc())
                
                logger.info("简化版区域价格统计分析完成")
                return simple_stats
                
            except Exception as backup_error:
                logger.error(f"备用分析方法也失败: {str(backup_error)}")
                return None
    
    def analyze_district_heatmap(self, df):
        """
        生成区域热力图数据，分析不同区域的房源密度和价格水平
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 按区域和小区分组统计
            heatmap_data = df.groupBy("location_qu", "location_small") \
                .agg(
                    count("*").alias("house_count"),
                    avg("price").alias("avg_price"),
                    avg("unit_price").alias("avg_unit_price")
                ) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_unit_price", spark_round(col("avg_unit_price"), 2)) \
                .orderBy(col("house_count").desc())
            
            logger.info("区域热力图数据生成完成")
            return heatmap_data
        except Exception as e:
            logger.error(f"区域热力图数据生成失败: {str(e)}")
            return None
    
    def analyze_room_price_cross(self, df):
        """
        户型与价格的交叉分析，分析不同户型在不同价格区间的分布
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 定义价格区间
            price_ranges = [
                (0, 2000, "2000元以下"),
                (2000, 3000, "2000-3000元"),
                (3000, 5000, "3000-5000元"),
                (5000, 10000, "5000-10000元"),
                (10000, float('inf'), "10000元以上")
            ]
            
            # 使用when链创建租金区间列
            from pyspark.sql.functions import lit
            price_range_column = None
            
            for min_price, max_price, label in price_ranges:
                if price_range_column is None:
                    price_range_column = when((col("price") >= min_price) & (col("price") < max_price), label)
                else:
                    price_range_column = price_range_column.when((col("price") >= min_price) & (col("price") < max_price), label)
            
            # 对于不属于任何区间的值，赋予默认值
            price_range_column = price_range_column.otherwise("其他")
            
            # 户型分类
            room_df = df.withColumn(
                "room_type", 
                expr("concat(room_count, '室', hall_count, '厅')")
            ).withColumn(
                "price_range", 
                price_range_column
            )
            
            # 按户型和价格区间交叉分析
            cross_stats = room_df.groupBy("room_type", "price_range") \
                .agg(
                    count("*").alias("house_count"),
                    avg("price").alias("avg_price"),
                    avg("size").alias("avg_size")
                ) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_size", spark_round(col("avg_size"), 2)) \
                .orderBy("room_type", "price_range")
            
            logger.info("户型与价格交叉分析完成")
            return cross_stats
        except Exception as e:
            logger.error(f"户型与价格交叉分析失败: {str(e)}")
            return None
    
    def analyze_rental_efficiency(self, df):
        """
        分析租金效率，即每平方米租金与面积的关系
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 按面积区间统计
            size_ranges = [
                (0, 30, "30㎡以下"),
                (30, 50, "30-50㎡"),
                (50, 70, "50-70㎡"),
                (70, 90, "70-90㎡"),
                (90, 120, "90-120㎡"),
                (120, float('inf'), "120㎡以上")
            ]
            
            # 使用when链创建面积区间列
            size_range_column = None
            
            for min_size, max_size, label in size_ranges:
                if size_range_column is None:
                    size_range_column = when((col("size") >= min_size) & (col("size") < max_size), label)
                else:
                    size_range_column = size_range_column.when((col("size") >= min_size) & (col("size") < max_size), label)
            
            # 对于不属于任何区间的值，赋予默认值
            size_range_column = size_range_column.otherwise("其他")
            
            # 创建带有面积区间的新DataFrame
            df_with_range = df.withColumn("size_range", size_range_column)
            
            # 分析租金效率
            efficiency_stats = df_with_range.groupBy("size_range") \
                .agg(
                    count("*").alias("house_count"),
                    avg("unit_price").alias("avg_unit_price"),
                    min("unit_price").alias("min_unit_price"),
                    max("unit_price").alias("max_unit_price"),
                    stddev("unit_price").alias("stddev_unit_price"),
                    avg("price").alias("avg_price"),
                    avg("size").alias("avg_size")
                ) \
                .withColumn("avg_unit_price", spark_round(col("avg_unit_price"), 2)) \
                .withColumn("min_unit_price", spark_round(col("min_unit_price"), 2)) \
                .withColumn("max_unit_price", spark_round(col("max_unit_price"), 2)) \
                .withColumn("stddev_unit_price", spark_round(col("stddev_unit_price"), 2)) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_size", spark_round(col("avg_size"), 2)) \
                .orderBy("size_range")
            
            logger.info("租金效率分析完成")
            return efficiency_stats
        except Exception as e:
            logger.error(f"租金效率分析失败: {str(e)}")
            return None
    
    def analyze_price_changes(self, df):
        """
        分析同一房源在不同时间点的价格变化
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析")
                return None
            
            # 检查是否有足够的时间跨度数据
            distinct_dates = df.select(date_format(col("crawl_time"), "yyyy-MM-dd")).distinct().count()
            if distinct_dates <= 1:
                logger.warning("没有足够的时间点数据来分析价格变化，至少需要两个不同的爬取日期")
                return None
            
            logger.info(f"开始分析房源价格变化，发现 {distinct_dates} 个不同的爬取日期")
            
            # 使用窗口函数，为每个house_id按时间排序
            window_spec = Window.partitionBy("house_id").orderBy("crawl_time")
            window_spec_desc = Window.partitionBy("house_id").orderBy(col("crawl_time").desc())
            
            # 计算每个房源的前一次价格和当前价格
            price_changes_df = df.withColumn("row_num", row_number().over(window_spec))
            price_changes_df = price_changes_df.withColumn(
                "prev_price", 
                lag("price", 1).over(window_spec)
            ).withColumn(
                "is_latest", 
                row_number().over(window_spec_desc) == 1
            ).withColumn(
                "date", 
                date_format(col("crawl_time"), "yyyy-MM-dd")
            ).withColumn(
                "prev_date", 
                lag("date", 1).over(window_spec)
            )
            
            # 过滤出有价格变化记录的房源
            price_changes_df = price_changes_df.filter(col("prev_price").isNotNull())
            
            # 计算价格变化和变化率
            price_changes_df = price_changes_df.withColumn(
                "price_change", 
                col("price") - col("prev_price")
            ).withColumn(
                "price_change_percent", 
                when(col("prev_price") > 0, 
                     spark_round((col("price") - col("prev_price")) / col("prev_price") * 100, 2)
                ).otherwise(None)
            ).withColumn(
                "price_change_category", 
                when(col("price_change") > 0, "上涨")
                .when(col("price_change") < 0, "下跌")
                .otherwise("不变")
            )
            
            # 选择需要的列
            result_df = price_changes_df.select(
                "house_id", "title", "location_qu", "location_small",
                "prev_date", "date", "prev_price", "price",
                "price_change", "price_change_percent", "price_change_category",
                "is_latest"
            )
            
            # 计算汇总统计信息
            count_total = result_df.count()
            if count_total == 0:
                logger.warning("没有找到价格变化记录")
                return None
                
            # 只分析最新的价格变化
            latest_changes = result_df.filter(col("is_latest") == True)
            
            # 区域价格变化统计
            district_changes = latest_changes.groupBy("location_qu", "price_change_category").count() \
                .withColumnRenamed("count", "house_count")
            
            # 整体价格变化趋势
            increase_count = latest_changes.filter(col("price_change") > 0).count()
            decrease_count = latest_changes.filter(col("price_change") < 0).count()
            unchanged_count = latest_changes.filter(col("price_change") == 0).count()
            
            avg_increase = latest_changes.filter(col("price_change") > 0).agg(
                avg("price_change").alias("avg_increase"),
                avg("price_change_percent").alias("avg_increase_percent")
            ).collect()
            
            avg_decrease = latest_changes.filter(col("price_change") < 0).agg(
                avg("price_change").alias("avg_decrease"),
                avg("price_change_percent").alias("avg_decrease_percent")
            ).collect()
            
            # 记录分析结果
            total_changed = increase_count + decrease_count
            logger.info(f"价格变化分析完成，共分析 {count_total} 条价格变化记录")
            logger.info(f"其中 {increase_count} 套房源价格上涨，{decrease_count} 套房源价格下跌，{unchanged_count} 套房源价格不变")
            
            if increase_count > 0:
                avg_inc = avg_increase[0]["avg_increase"]
                avg_inc_pct = avg_increase[0]["avg_increase_percent"]
                logger.info(f"价格上涨房源平均上涨 {avg_inc:.2f} 元，平均涨幅 {avg_inc_pct:.2f}%")
            
            if decrease_count > 0:
                avg_dec = avg_decrease[0]["avg_decrease"]
                avg_dec_pct = avg_decrease[0]["avg_decrease_percent"]
                logger.info(f"价格下跌房源平均下跌 {abs(avg_dec):.2f} 元，平均跌幅 {abs(avg_dec_pct):.2f}%")
            
            # 构造结果DataFrame: 1. 详细变化记录
            detailed_changes = result_df.orderBy(col("price_change_percent").desc())
            
            # 2. 按区域统计价格变化情况
            district_summary = latest_changes.groupBy("location_qu").agg(
                count(when(col("price_change") > 0, 1)).alias("increase_count"),
                count(when(col("price_change") < 0, 1)).alias("decrease_count"),
                count(when(col("price_change") == 0, 1)).alias("unchanged_count"),
                avg(when(col("price_change") > 0, col("price_change"))).alias("avg_increase"),
                avg(when(col("price_change") < 0, col("price_change"))).alias("avg_decrease"),
                avg(when(col("price_change") > 0, col("price_change_percent"))).alias("avg_increase_percent"),
                avg(when(col("price_change") < 0, col("price_change_percent"))).alias("avg_decrease_percent"),
                count("*").alias("total_count")
            ).orderBy(col("increase_count").desc())
            
            # 3. 按涨跌幅度区间统计
            percent_ranges = [
                (-float('inf'), -10, "跌幅超过10%"),
                (-10, -5, "跌幅5%-10%"),
                (-5, 0, "跌幅小于5%"),
                (0, 0, "价格不变"),
                (0, 5, "涨幅小于5%"),
                (5, 10, "涨幅5%-10%"),
                (10, float('inf'), "涨幅超过10%")
            ]
            
            # 使用when链创建涨跌幅区间列
            range_column = None
            for min_pct, max_pct, label in percent_ranges:
                if range_column is None:
                    range_column = when((col("price_change_percent") > min_pct) & (col("price_change_percent") <= max_pct), label)
                else:
                    range_column = range_column.when((col("price_change_percent") > min_pct) & (col("price_change_percent") <= max_pct), label)
            
            range_column = range_column.otherwise("其他")
            
            # 统计不同涨跌幅区间的房源数量
            percent_distribution = latest_changes.withColumn("change_range", range_column) \
                .groupBy("change_range").count() \
                .withColumnRenamed("count", "house_count") \
                .orderBy("change_range")
            
            # 合并所有分析结果
            return {
                "detailed_changes": detailed_changes,
                "district_summary": district_summary,
                "percent_distribution": percent_distribution,
                "district_changes": district_changes
            }
        except Exception as e:
            logger.error(f"分析房源价格变化失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return None
            
    def save_price_changes_to_db(self, analysis_results, city=None):
        """
        将价格变化分析结果保存到数据库
        :param analysis_results: 分析结果字典
        :param city: 城市名称
        :return: 是否成功
        """
        conn = None
        cursor = None
        try:
            if analysis_results is None:
                logger.warning("没有价格变化分析结果需要保存")
                return False
                
            # 准备数据库连接
            conn = psycopg2.connect(
                user=self.db_config["user"],
                password=self.db_config["password"],
                host=self.db_config["host"],
                port=self.db_config["port"],
                database=self.db_config["database"],
                client_encoding='UTF8'  # 使用UTF8编码以支持中文
            )
            cursor = conn.cursor()
            
            # 保存结果到相应的表中
            for result_type, result_df in analysis_results.items():
                if result_df is None or result_df.count() == 0:
                    continue
                    
                # 将分析结果转换为JSON字符串
                pandas_df = result_df.toPandas()
                result_json = pandas_df.to_json(orient="records")
                
                # 插入分析结果
                analysis_type = f"price_changes_{result_type}"
                cursor.execute(
                    "INSERT INTO analysis_result (analysis_type, city, analysis_time, result_data) VALUES (%s, %s, %s, %s)",
                    (analysis_type, city, datetime.datetime.now(), result_json)
                )
            
            conn.commit()
            logger.info(f"价格变化分析结果已保存到数据库，城市: {city}")
            return True
        except Exception as e:
            logger.error(f"保存价格变化分析结果到数据库失败: {str(e)}")
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"回滚事务失败: {str(rollback_error)}")
            return False
        finally:
            # 确保关闭cursor和连接
            if cursor:
                try:
                    cursor.close()
                except Exception as cursor_error:
                    logger.error(f"关闭cursor失败: {str(cursor_error)}")
            if conn:
                try:
                    conn.close()
                    logger.debug("数据库连接已关闭")
                except Exception as conn_error:
                    logger.error(f"关闭数据库连接失败: {str(conn_error)}")
    
    def analyze_features(self, df):
        """
        分析房源特征标签
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析features")
                return None
            
            # 确保features字段存在
            if "features" not in df.columns:
                logger.warning("数据中不包含features字段")
                return None
            
            # 检查features字段的类型
            features_type = df.select("features").schema[0].dataType
            logger.info(f"features字段的数据类型是: {features_type}")
            
            try:
                # 过滤出features不为空的记录
                non_empty_features_df = df.filter(col("features").isNotNull())
                # 获取features非空的记录数
                non_empty_count = non_empty_features_df.count()
                logger.info(f"features非空的记录数: {non_empty_count}")
                
                if non_empty_count == 0:
                    logger.warning("所有features字段都为空")
                    return None
                
                # 尝试explode前先做一次类型转换，只有当字段是字符串类型时才进行转换
                if isinstance(features_type, StringType):
                    try:
                        non_empty_features_df = non_empty_features_df.withColumn(
                            "features", 
                            from_json(col("features"), ArrayType(StringType()))
                        )
                        logger.info("成功将features字段从字符串转换为数组类型")
                    except Exception as e:
                        logger.error(f"转换features从字符串到数组类型失败: {str(e)}")
                        logger.error("将尝试直接使用原始features字段")
                else:
                    logger.info("features字段已经是数组类型，无需转换")
                
                # 展开features数组，每个标签生成一行
                exploded_df = non_empty_features_df.select("*", explode(col("features")).alias("feature"))
                
                # 按标签分组统计
                feature_stats = exploded_df.groupBy("feature") \
                    .agg(
                        count("*").alias("count"),
                        avg("price").alias("avg_price"),
                        stddev("price").alias("stddev_price"),
                        avg("size").alias("avg_size")
                    ) \
                    .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                    .withColumn("avg_size", spark_round(col("avg_size"), 2)) \
                    .withColumn("percentage", spark_round(col("count") * 100 / non_empty_count, 2)) \
                    .orderBy(col("count").desc())
                
                logger.info("特征标签分析完成")
                return feature_stats
            
            except Exception as inner_e:
                logger.error(f"展开和分析features数组失败: {str(inner_e)}")
                logger.error(f"错误详情: {traceback.format_exc()}")
                
                # 尝试一种替代方法，直接分析没有展开的features
                logger.info("尝试直接分析features字段，不展开数组")
                feature_counts = df.filter(col("features").isNotNull()) \
                    .groupBy("features") \
                    .agg(
                        count("*").alias("count"),
                        avg("price").alias("avg_price")
                    ) \
                    .orderBy(col("count").desc())
                
                return feature_counts
            
        except Exception as e:
            logger.error(f"特征标签分析失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return None
    
    def analyze_feature_combinations(self, df, top_n=20):
        """
        分析常见的特征组合及其影响
        :param df: 输入的DataFrame
        :param top_n: 返回的最常见组合数量
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析特征组合")
                return None
            
            # 确保features字段存在
            if "features" not in df.columns:
                logger.warning("数据中不包含features字段")
                return None
            
            # 过滤出features不为空的记录
            non_empty_features_df = df.filter(col("features").isNotNull())
            
            # 按特征组合分组统计
            combinations = non_empty_features_df.groupBy("features") \
                .agg(
                    count("*").alias("count"),
                    avg("price").alias("avg_price"),
                    avg("size").alias("avg_size"),
                    min("price").alias("min_price"),
                    max("price").alias("max_price")
                ) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_size", spark_round(col("avg_size"), 2)) \
                .withColumn("percentage", spark_round(col("count") * 100 / non_empty_features_df.count(), 2)) \
                .orderBy(col("count").desc()) \
                .limit(top_n)
            
            logger.info(f"特征组合分析完成，显示前 {top_n} 个最常见组合")
            return combinations
        
        except Exception as e:
            logger.error(f"特征组合分析失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return None
    
    def analyze_metro_price_impact(self, df):
        """
        分析地铁对房价的影响
        :param df: 输入的DataFrame
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析地铁影响")
                return None
            
            # 确保必要的字段存在
            if "features" not in df.columns or "location_qu" not in df.columns:
                logger.warning("数据中缺少features或location_qu字段")
                return None
            
            # 过滤出features不为空的记录
            non_empty_features_df = df.filter(col("features").isNotNull())
            
            # 创建是否靠近地铁的标志列
            df_with_metro = non_empty_features_df.withColumn(
                "near_metro", 
                array_contains(col("features"), "近地铁")
            )
            
            # 按区域和靠近地铁分组
            metro_impact = df_with_metro.groupBy("location_qu", "near_metro") \
                .agg(
                    count("*").alias("house_count"),
                    avg("price").alias("avg_price"),
                    avg("size").alias("avg_size"),
                    min("price").alias("min_price"),
                    max("price").alias("max_price")
                ) \
                .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                .withColumn("avg_size", spark_round(col("avg_size"), 2)) \
                .withColumn("percentage", spark_round(col("house_count") * 100 / df_with_metro.count(), 2)) \
                .orderBy("location_qu", "near_metro")
            
            logger.info("地铁影响分析完成")
            return metro_impact
        
        except Exception as e:
            logger.error(f"地铁影响分析失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return None
    
    def analyze_popular_features_price(self, df, top_features=5):
        """
        分析最热门特征对房价的影响
        :param df: 输入的DataFrame
        :param top_features: 要分析的热门特征数量
        :return: 分析结果DataFrame
        """
        try:
            if df is None or df.count() == 0:
                logger.warning("没有数据需要分析热门特征")
                return None
            
            # 确保features字段存在
            if "features" not in df.columns:
                logger.warning("数据中不包含features字段")
                return None
            
            # 过滤出features不为空的记录
            non_empty_features_df = df.filter(col("features").isNotNull())
            
            # 缓存这个DataFrame以提高性能
            non_empty_features_df.cache()
            total_count = non_empty_features_df.count()
            
            if total_count == 0:
                logger.warning("所有features字段都为空")
                non_empty_features_df.unpersist()
                return None
                
            logger.info(f"处理 {total_count} 条具有features的记录")
            
            # 将特征计数和特征影响分析分为两个步骤，减少单步复杂度
            
            # 步骤1: 计算并获取最热门特征
            try:
                # 展开特征并计数 - 这一步较轻量
                exploded_features = non_empty_features_df.select(
                    explode(col("features")).alias("feature")
                )
                
                # 计算特征频率
                feature_counts = exploded_features.groupBy("feature").count()
                
                # 获取前N个热门特征
                popular_features = feature_counts.orderBy(col("count").desc()) \
                    .limit(top_features) \
                    .select("feature") \
                    .collect()
                
                # 将结果转换为列表
                popular_feature_list = [row['feature'] for row in popular_features]
                
                logger.info(f"找到最热门的 {len(popular_feature_list)} 个特征: {popular_feature_list}")
                
                if not popular_feature_list:
                    logger.warning("未找到任何特征")
                    non_empty_features_df.unpersist()
                    return None
                    
            except Exception as e:
                logger.error(f"计算热门特征失败: {str(e)}")
                logger.error(f"错误详情: {traceback.format_exc()}")
                non_empty_features_df.unpersist()
                return None
                
            # 步骤2: 分析每个热门特征对房价的影响
            results = []
            
            for feature in popular_feature_list:
                try:
                    # 添加特征标志列
                    df_with_feature = non_empty_features_df.withColumn(
                        "has_feature", 
                        array_contains(col("features"), feature)
                    )
                    
                    # 按特征标志分组统计
                    feature_impact = df_with_feature.groupBy("has_feature") \
                        .agg(
                            count("*").alias("house_count"),
                            avg("price").alias("avg_price"),
                            min("price").alias("min_price"),
                            max("price").alias("max_price"),
                            avg("size").alias("avg_size")
                        ) \
                        .withColumn("feature", lit(feature)) \
                        .withColumn("avg_price", spark_round(col("avg_price"), 2)) \
                        .withColumn("avg_size", spark_round(col("avg_size"), 2)) \
                        .withColumn("percentage", spark_round(col("house_count") * 100 / df_with_feature.count(), 2))
                        
                    results.append(feature_impact)
                except Exception as fe:
                    logger.error(f"分析特征 '{feature}' 失败: {str(fe)}")
                    # 继续处理下一个特征
            
            # 释放缓存
            non_empty_features_df.unpersist()
            
            if not results:
                logger.warning("没有成功分析任何特征对房价的影响")
                return None
            
            # 合并所有结果
            from functools import reduce
            from pyspark.sql import DataFrame
            
            # 使用一个安全的方式合并结果
            try:
                combined_results = reduce(DataFrame.unionAll, results)
                ordered_results = combined_results.orderBy("feature", "has_feature")
                
                logger.info("热门特征对房价影响分析完成")
                return ordered_results
            except Exception as ue:
                logger.error(f"合并特征分析结果失败: {str(ue)}")
                
                # 如果合并失败，至少返回第一个结果
                if results:
                    logger.info("返回第一个特征的分析结果")
                    return results[0]
                return None
        
        except Exception as e:
            logger.error(f"热门特征分析失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return None
    
    def run_all_analysis(self, df, city=None, export_path=None):
        """
        运行所有分析并保存结果
        :param df: 输入的DataFrame
        :param city: 城市名称
        :param export_path: 导出路径，如果提供则导出为CSV
        :return: 分析结果字典
        """
        if df is None or df.count() == 0:
            logger.warning("没有数据需要分析")
            return {}
        
        # 清洗数据
        try:
            cleaned_df = self.clean_data(df)
            if cleaned_df is None or cleaned_df.count() == 0:
                logger.warning("清洗后没有有效数据进行分析")
                return {}
                
            # 缓存清洗后的数据以提高性能
            cleaned_df.cache()
        except Exception as e:
            logger.error(f"数据清洗失败: {str(e)}")
            return {}
        
        # 运行各项分析
        results = {}
        
        # 定义辅助函数处理单个分析任务，包含错误处理和重试逻辑
        def run_analysis_task(analysis_func, analysis_name, *args, **kwargs):
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"开始执行{analysis_name}分析 (尝试 {attempt+1}/{max_retries+1})")
                    
                    # 运行分析
                    analysis_result = analysis_func(cleaned_df, *args, **kwargs)
                    
                    # 如果分析成功，保存结果
                    if analysis_result is not None:
                        results[analysis_name] = analysis_result
                        
                        # 对于价格变化分析，使用专门的保存方法
                        if analysis_name == "price_changes":
                            try:
                                self.save_price_changes_to_db(analysis_result, city)
                                logger.info(f"{analysis_name}分析结果已使用专用方法保存到数据库")
                            except Exception as db_error:
                                logger.error(f"保存{analysis_name}分析结果到数据库失败: {str(db_error)}")
                        else:
                            # 保存到数据库
                            try:
                                self.save_analysis_to_db(analysis_result, analysis_name, city)
                                logger.info(f"{analysis_name}分析结果已保存到数据库")
                            except Exception as db_error:
                                logger.error(f"保存{analysis_name}分析结果到数据库失败: {str(db_error)}")
                        
                        # 导出CSV（如果需要）
                        if export_path:
                            try:
                                export_file = os.path.join(export_path, f"{analysis_name}.csv")
                                self.export_analysis_to_csv(analysis_result, export_file)
                                logger.info(f"{analysis_name}分析结果已导出至 {export_file}")
                            except Exception as export_error:
                                logger.error(f"导出{analysis_name}分析结果失败: {str(export_error)}")
                    
                    # 分析成功，跳出重试循环
                    return True
                    
                except Exception as e:
                    logger.error(f"{analysis_name}分析失败 (尝试 {attempt+1}/{max_retries+1}): {str(e)}")
                    
                    # 如果还有重试机会，继续尝试
                    if attempt < max_retries:
                        wait_time = 5 * (attempt + 1)  # 逐次增加等待时间
                        logger.info(f"等待{wait_time}秒后重试{analysis_name}分析...")
                        import time
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{analysis_name}分析最终失败，跳过此项分析")
                        return False
        
        # 运行所有分析任务，错误处理确保单个任务失败不会影响其他任务
        
        # 1. 区域分析
        run_analysis_task(self.analyze_by_district, "district_analysis")
        
        # 2. 户型分析
        run_analysis_task(self.analyze_by_room_type, "room_type_analysis")
        
        # 3. 朝向分析
        run_analysis_task(self.analyze_by_direction, "direction_analysis")
        
        # 4. 楼层分析
        run_analysis_task(self.analyze_by_floor, "floor_analysis")
        
        # 5. 租金分布分析
        run_analysis_task(self.analyze_price_distribution, "price_distribution")
        
        # 6. 小区分析
        run_analysis_task(self.analyze_by_community, "community_analysis")
        
        # 7. 特征标签分析（新添加）
        run_analysis_task(self.analyze_features, "features_analysis")
        
        # 8. 特征组合分析（新添加）
        run_analysis_task(self.analyze_feature_combinations, "feature_combinations")
        
        # 9. 地铁影响分析（新添加）
        run_analysis_task(self.analyze_metro_price_impact, "metro_price_impact")
        
        # 10. 热门特征价格影响分析（新添加）
        run_analysis_task(self.analyze_popular_features_price, "popular_features_price")
        
        # 11. 价格区间详细统计
        run_analysis_task(self.analyze_price_stats_by_district, "price_stats")
        
        # 12. 区域热力图数据
        run_analysis_task(self.analyze_district_heatmap, "district_heatmap")
        
        # 13. 户型与价格交叉分析
        run_analysis_task(self.analyze_room_price_cross, "room_price_cross")
        
        # 14. 租金效率分析
        run_analysis_task(self.analyze_rental_efficiency, "rental_efficiency")
        
        # 15. 尝试分析价格趋势（需要足够的数据）
        try:
            if cleaned_df.select("crawl_time").distinct().count() > 1:
                run_analysis_task(self.analyze_price_trend, "price_trend")
        except Exception as e:
            logger.error(f"检查价格趋势数据失败: {str(e)}")
        
        # 16. 分析价格变化
        run_analysis_task(self.analyze_price_changes, "price_changes")
        
        # 清理缓存
        try:
            cleaned_df.unpersist()
        except:
            pass
            
        logger.info(f"所有分析已完成，成功完成 {len(results)} 个分析任务")
        return results
    
    def close(self):
        """关闭Spark会话和清理资源"""
        try:
            logger.info("开始清理数据处理器资源...")
            
            # 清理可能的缓存数据
            try:
                for df_name in self.spark.catalog.listTables("default"):
                    logger.info(f"删除临时表: {df_name.name}")
                    self.spark.catalog.dropTempView(df_name.name)
            except Exception as cache_err:
                logger.warning(f"清理临时表失败: {str(cache_err)}")
            
            # 手动触发垃圾回收
            import gc
            gc.collect()
            
            # 关闭Spark会话
            if self.spark:
                try:
                    # 尝试取消所有正在运行的作业
                    try:
                        spark_context = self.spark.sparkContext
                        running_jobs = spark_context.statusTracker().getActiveJobsIds()
                        for job_id in running_jobs:
                            logger.info(f"取消Spark作业: {job_id}")
                            spark_context.cancelJob(job_id)
                    except Exception as job_err:
                        logger.warning(f"取消Spark作业失败: {str(job_err)}")
                    
                    # 关闭Spark会话
                    self.spark.stop()
                    logger.info("Spark会话已成功关闭")
                except Exception as spark_err:
                    logger.error(f"关闭Spark会话时发生错误: {str(spark_err)}")
            
            # 释放可能的其他资源
            for attr_name in list(self.__dict__.keys()):
                if attr_name != 'db_config' and attr_name != 'house_schema':
                    try:
                        delattr(self, attr_name)
                        logger.debug(f"已释放属性: {attr_name}")
                    except:
                        pass
            
            # 再次触发垃圾回收
            gc.collect()
            logger.info("数据处理器资源清理完成")
        
        except Exception as e:
            logger.error(f"清理资源时发生错误: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")

if __name__ == "__main__":
    # 示例用法
    processor = RentalDataProcessor()
    
    # 从数据库加载数据
    df = processor.load_data_from_db(city="湛江")
    
    if df is not None:
        # 运行所有分析
        results = processor.run_all_analysis(df, city="湛江", export_path="./analysis_results")
        
        # 显示一些分析结果
        if "district_analysis" in results and results["district_analysis"] is not None:
            print("\n区域租金分析结果:")
            results["district_analysis"].show(truncate=False)
        
        if "room_type_analysis" in results and results["room_type_analysis"] is not None:
            print("\n户型租金分析结果:")
            results["room_type_analysis"].show(truncate=False)
    
    # 关闭Spark会话
    processor.close() 