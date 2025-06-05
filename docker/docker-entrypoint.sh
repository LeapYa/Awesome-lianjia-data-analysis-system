#!/bin/bash
set -e

echo "Starting backend services..."

# 启动虚拟显示服务（用于无头浏览器）
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 -ac &

# 等待PostgreSQL服务准备就绪
echo "Waiting for PostgreSQL..."
until PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c '\q'; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

# 初始化数据库（如果未初始化）
echo "Checking if database is initialized..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1 FROM pg_tables WHERE tablename = 'users'" | grep -q 1 || {
  echo "Database tables not found, initializing database..."
  # 运行初始化脚本
  PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f init.sql
}

# 确保目录权限正确
echo "设置目录权限..."
chmod -R 755 /app/logs
chmod -R 755 /app/screenshots
chmod -R 755 /app/verification_sessions
chmod -R 755 /app/verification_cookies
chmod -R 755 /app/captcha_data

echo "Backend is ready!"

# 执行传入的命令
exec "$@" 