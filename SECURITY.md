# 租房数据分析系统 - 安全部署指南

## 目录
1. [环境变量配置](#环境变量配置)
2. [网络安全配置](#网络安全配置)  
3. [数据库安全](#数据库安全)
4. [容器安全](#容器安全)
5. [文件权限](#文件权限)
6. [SQL注入防护](#SQL注入防护) 
7. [监控和日志](#监控和日志)
8. [备份和恢复](#备份和恢复)
9. [安全事件响应](#安全事件响应)
10. [定期安全检查](#定期安全检查)
11. [推荐安全工具](#推荐安全工具)

## 🔒 安全配置清单

### 1. 环境变量配置

在部署前，请务必配置以下环境变量：

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件
nano .env
```

**必须修改的变量：**

- `DB_PASSWORD`: 数据库密码（至少12位，包含大小写字母、数字、特殊字符）
- `JWT_SECRET_KEY`: JWT密钥（至少32位随机字符串）
- `EMAIL_ENCRYPTION_KEY`: 邮件加密密钥

### 2. 网络安全配置

**生产环境CORS设置：**

```python
# 在 api.py 中修改 allow_origins
allow_origins=[
    "https://yourdomain.com",      # 你的生产域名
    "https://www.yourdomain.com",  # 带www的域名
]
```

**防火墙设置：**

- 只开放必要端口（80, 443）
- 禁止直接访问数据库端口（5432）
- 禁止直接访问后端API端口（8000）

### 3. 数据库安全

**强密码要求：**

- 至少12位字符
- 包含大小写字母、数字、特殊字符
- 定期轮换密码

**访问控制：**

- 数据库只在内部网络访问
- 不暴露到公网
- 定期备份

### 4. 容器安全

**镜像安全：**

- 使用官方基础镜像
- 定期更新镜像版本
- 扫描镜像漏洞

**运行时安全：**

- 使用非root用户运行
- 限制容器权限
- 禁用不必要的功能

### 5. 文件权限

**目录权限设置：**

```bash
# 应用目录
chmod 755 /app

# 日志目录
chmod 755 /app/logs

# 数据目录
chmod 750 /app/data
```

### 6. SQL注入防护

#### 已实施的安全措施

##### 1. 参数化查询
- 所有用户输入都使用参数化查询（占位符 `%s`）
- 禁止字符串拼接构建SQL语句
- 示例：
```python
# 安全的方式
cursor.execute("SELECT * FROM houses WHERE city = %s", (city,))

# 危险的方式（已修复）
# cursor.execute(f"SELECT * FROM houses WHERE city = '{city}'")
```

##### 2. 输入验证
- 集成 `security_utils` 模块进行严格的输入验证
- 检查SQL注入攻击模式
- 验证数据类型和范围
```python
# 字符串验证
validated_city = security_utils.validate_city_name(city)

# 数值验证
validated_price = security_utils.validate_price_range(min_price, max_price)
```

##### 3. SQL关键词检测
系统会检测并阻止以下SQL注入模式：
- SQL命令关键词：`DROP`, `DELETE`, `INSERT`, `UPDATE`, `CREATE`, `ALTER`, `TRUNCATE`
- 查询关键词：`UNION`, `SELECT`, `FROM`, `WHERE`, `HAVING`, `GROUP BY`, `ORDER BY`
- 特殊字符：`;`, `'`, `"`, `\`, `--`, `/*`, `*/`
- 条件注入：`OR 1=1`, `AND 1=1`
- 存储过程：`EXEC`, `EXECUTE`, `sp_`, `xp_`
- 脚本注入：`SCRIPT`, `JAVASCRIPT`, `VBSCRIPT`

##### 4. 数据类型验证
- 整数输入：验证范围和类型
- 浮点数输入：验证精度和范围
- 字符串输入：长度限制和字符过滤
- HTML转义：防止XSS攻击

##### 5. 数据库权限最小化
- 应用程序使用专用数据库用户
- 仅授予必要的操作权限
- 禁用不必要的数据库功能

#### 安全配置验证
定期运行以下命令检查SQL注入防护：
```bash
# 检查参数化查询使用情况
grep -r "cursor.execute.*%s" *.py

# 检查是否存在字符串拼接SQL
grep -r "cursor.execute.*\+\|cursor.execute.*f['\"]" *.py

# 验证输入验证模块
python -c "import security_utils; print('安全模块加载成功')"
```

### 7. 监控和日志

**安全监控：**

- 启用访问日志记录
- 监控异常登录尝试
- 设置安全警报

**日志管理：**

- 定期轮转日志文件
- 安全存储敏感日志
- 避免记录敏感信息

### 8. 备份和恢复

**数据备份：**

- 定期自动备份数据库
- 加密备份文件
- 测试恢复流程

**灾难恢复：**

- 制定恢复计划
- 定期演练
- 多地备份

## 🚨 安全事件响应

### 发现安全问题时：

1. **立即停止服务**

```bash
docker-compose down
```

2. **检查日志**

```bash
docker-compose logs backend
docker-compose logs postgres
```

3. **更新密码**

```bash
# 生成新的强密码
openssl rand -base64 32
```

4. **重新部署**

```bash
docker-compose up -d --build
```

## 📋 定期安全检查

### 每月检查：

- [ ] 更新依赖包版本
- [ ] 检查访问日志异常
- [ ] 验证备份完整性
- [ ] 更新安全补丁

### 每季度检查：

- [ ] 轮换所有密码
- [ ] 安全渗透测试
- [ ] 权限审计
- [ ] 应急响应演练

## 🔧 安全工具推荐

### 容器安全扫描：

```bash
# 使用 trivy 扫描镜像漏洞
trivy image your-image-name
```

### 依赖漏洞检查：

```bash
# Python 依赖漏洞扫描
pip-audit
```

### 网络安全测试：

```bash
# 使用 nmap 检查开放端口
nmap -sT -p 1-65535 your-server-ip
```

---

**重要提醒：** 安全是一个持续的过程，请定期更新此指南并根据最新的安全威胁调整配置。
