# -*- coding: utf-8 -*-
import os
import logging
import datetime
import secrets
import string
import json
import shutil
import base64
from typing import Optional, Dict, Any, List
import jwt
from jwt.exceptions import PyJWTError
from fastapi import Depends, HTTPException, status, APIRouter, Request, File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt

# 导入数据库配置和工具
import db_config
import db_utils

def get_email_utils():
    """动态导入邮件工具，避免循环导入"""
    from email_utils import email_sender, verification_manager
    return email_sender, verification_manager

# 确保logs目录存在
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "auth.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("auth")

# 创建认证系统专用的数据库连接池
try:
    auth_pool = db_config.create_pool(
        min_conn=2, 
        max_conn=10, 
        application_name="auth_service"
    )
    logger.info("认证系统数据库连接池创建成功")
except Exception as e:
    logger.error(f"认证系统数据库连接池创建失败: {str(e)}")
    auth_pool = None

# 创建装饰器实例
with_db_connection = db_utils.with_db_connection(auth_pool)

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "rental_data_analysis_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# 邮箱加密密钥
EMAIL_ENCRYPTION_KEY = os.getenv("EMAIL_ENCRYPTION_KEY", "very_secure_encryption_key_change_me")

# 创建API路由
router = APIRouter(prefix="/auth", tags=["认证"])

# OAuth2 密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# 定义模型
class Token(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_at: int

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime.datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    verification_code: str
    language: Optional[str] = 'zh-CN'  # 添加语言参数

class UserLogin(BaseModel):
    username: str
    password: str

class PasswordReset(BaseModel):
    email: EmailStr
    language: Optional[str] = 'zh-CN'  # 添加语言参数

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str
    password: str

class UserProfile(BaseModel):
    username: str
    email: EmailStr
    is_admin: bool
    created_at: datetime.datetime
    last_login: Optional[datetime.datetime] = None

class UserSettings(BaseModel):
    emailNotifications: bool = True
    taskCompletionNotifications: bool = True
    theme: str = "light"
    dataSharing: bool = True
    language: str = "zh-CN"  # 添加语言偏好字段

class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    currentPassword: Optional[str] = None
    password: Optional[str] = None

class AvatarUpdate(BaseModel):
    avatar_data: str  # Base64编码的图像数据

class VerificationCodeRequest(BaseModel):
    email: EmailStr
    code_type: str = "email_verification"  # email_verification, password_reset
    language: Optional[str] = 'zh-CN'  # 添加语言参数

class VerificationCodeVerify(BaseModel):
    email: EmailStr
    code: str
    code_type: str = "email_verification"

# 计算邮箱哈希，用于查找
def hash_email_for_lookup(email: str) -> str:
    """使用SHA256对邮箱进行哈希，用于查找目的"""
    import hashlib
    return hashlib.sha256(email.lower().encode('utf-8')).hexdigest()

# 移除邮箱加密解密函数，直接使用明文
def store_email(email: str) -> str:
    """直接返回邮箱明文"""
    return email

def get_email(stored_email: str) -> str:
    """直接返回存储的邮箱"""
    return stored_email

# 验证用户
@with_db_connection
def authenticate_user(conn, username: str, password: str) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 增加日志
        logger.info(f"尝试验证用户: {username}")
        
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if not user:
            logger.warning(f"用户不存在: {username}")
            return None
        
        # 增加更多日志来调试密码验证问题
        logger.info(f"找到用户: {username}, ID: {user['id']}")
        
        # 检查密码哈希
        password_valid = verify_password(password, user["password_hash"])
        logger.info(f"密码验证结果: {password_valid}")
        
        if not password_valid:
            logger.warning(f"密码验证失败: {username}")
            return None
        
        # 更新最后登录时间
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
            (user["id"],)
        )
        conn.commit()
        
        
        return user
    except Exception as e:
        logger.error(f"用户验证失败: {str(e)}")
        return None

# 创建访问令牌
@with_db_connection
def create_access_token(conn, data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    # 存储令牌到数据库
    cursor = conn.cursor()
    
    try:
        # 确保使用正确的键名获取user_id
        user_id = data.get("user_id")
        if user_id:
            cursor.execute(
                "INSERT INTO user_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (user_id, encoded_jwt, expire)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"令牌存储失败: {str(e)}")
        # 添加详细错误信息
        logger.error(f"令牌数据: {data}, 错误详情: {str(e)}")
    
    return encoded_jwt, int(expire.timestamp())

# 从令牌获取当前用户
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证已过期或无效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("user_id")
        
        if username is None or user_id is None:
            raise credentials_exception
        
        token_data = TokenData(username=username, user_id=user_id)
    except PyJWTError:
        raise credentials_exception
    
    conn = None
    try:
        conn = db_config.get_connection(auth_pool)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM users WHERE id = %s", (token_data.user_id,))
        user = cursor.fetchone()
        
        if user is None:
            raise credentials_exception
    
        return user
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误") 
    finally:
        if conn:
            db_config.release_connection(auth_pool, conn)

# 散列密码
def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

# 验证密码
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"密码验证错误: {str(e)}")
        return False

# 生成随机令牌
def generate_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# API 路由

@router.post("/login", response_model=Dict[str, Any])
async def login(form_data: UserLogin):
    """用户登录"""
    try:
        # 增加日志
        logger.info(f"登录尝试: 用户名={form_data.username}")
        
        user = authenticate_user(form_data.username, form_data.password)
        
        if not user:
            logger.warning(f"登录失败: 用户名={form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user["is_active"]:
            logger.warning(f"禁用账户尝试登录: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用"
            )
        
        # 确保user_id正确传递
        access_token, expires_at = create_access_token(
            data={"sub": user["username"], "user_id": user["id"]}
        )
        
        logger.info(f"登录成功: {form_data.username}")
        
        return {
            "token": access_token,
            "token_type": "bearer",
            "expires_at": expires_at,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "is_admin": user["is_admin"]
            }
        }
    except Exception as e:
        logger.error(f"登录过程异常: {str(e)}")
        raise

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=Dict[str, str])
async def register(user_data: UserCreate):
    """用户注册"""
    conn = db_config.get_connection(auth_pool)
    try:
        # 先验证验证码
        _, verification_manager = get_email_utils()
        is_valid = verification_manager.verify_code(
            user_data.email,
            user_data.verification_code,
            'email_verification'
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期"
            )
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM users WHERE username = %s", (user_data.username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 检查邮箱是否已存在（通过邮箱哈希）
        email_hash = hash_email_for_lookup(user_data.email)
        cursor.execute("SELECT id FROM users WHERE email_hash = %s", (email_hash,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
        
        password_hash = get_password_hash(user_data.password)
        
        cursor.execute(
            """
            INSERT INTO users (username, email, email_hash, password_hash) 
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (user_data.username, user_data.email, email_hash, password_hash)
        )
        
        user_id = cursor.fetchone()["id"]
        conn.commit()
        
        logger.info(f"新用户注册成功: {user_data.username} (ID: {user_id})")
        
        # 发送欢迎邮件
        try:
            email_sender, _ = get_email_utils()
            email_sender.send_welcome_email(user_data.email, user_data.username, user_data.language)
            logger.info(f"欢迎邮件发送成功: {user_data.email}")
        except Exception as e:
            logger.error(f"发送欢迎邮件失败: {e}")
            # 不影响注册流程
        
        return {"message": "注册成功，欢迎邮件已发送"}
    
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )
    finally:
        db_config.release_connection(auth_pool, conn)

@router.post("/forgot-password", response_model=Dict[str, str])
async def forgot_password(reset_data: PasswordReset):
    """忘记密码 - 发送验证码"""
    try:
        # 发送密码重置验证码（无论用户是否存在都发送，为了安全）
        _, verification_manager = get_email_utils()
        success = verification_manager.send_verification_code(
            reset_data.email, 
            'password_reset',
            reset_data.language
        )
        
        if success:
            logger.info(f"密码重置验证码已发送到: {reset_data.email}")
            return {"message": "密码重置验证码已发送，请查收邮件"}
        else:
            logger.error(f"发送密码重置验证码失败: {reset_data.email}")
            # 为了安全，即使失败也返回成功消息
            return {"message": "如果该邮箱已注册，密码重置验证码已发送"}
    except Exception as e:
        logger.error(f"忘记密码处理失败: {str(e)}")
        # 为了安全，即使出错也返回成功消息
        return {"message": "如果该邮箱已注册，密码重置验证码已发送"}

@router.post("/reset-password", response_model=Dict[str, str])
async def reset_password(reset_data: PasswordResetConfirm):
    """重置密码 - 使用验证码"""
    conn = db_config.get_connection(auth_pool)
    try:
        # 先验证验证码
        _, verification_manager = get_email_utils()
        is_valid = verification_manager.verify_code(
            reset_data.email,
            reset_data.code,
            'password_reset'
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期"
            )
        
        # 验证码正确，检查用户是否存在
        email_hash = hash_email_for_lookup(reset_data.email)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id FROM users WHERE email_hash = %s", (email_hash,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户不存在"
            )
        
        # 更新用户密码
        password_hash = get_password_hash(reset_data.password)
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE email_hash = %s",
            (password_hash, email_hash)
        )
        
        conn.commit()
        logger.info(f"用户 (邮箱哈希:{email_hash}) 成功重置了密码")
        
        return {"message": "密码重置成功"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"密码重置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="处理请求时出错"
        )
    finally:
        db_config.release_connection(auth_pool, conn)

@router.post("/logout", response_model=Dict[str, str])
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """用户登出"""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        
        conn = db_config.get_connection(auth_pool)
        try:
            # 从数据库中删除令牌
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_tokens WHERE token = %s", (token,))
            conn.commit()
        except Exception as e:
            logger.error(f"登出失败: {str(e)}")
        finally:
            db_config.release_connection(auth_pool, conn)
    
    return {"message": "登出成功"}

@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """获取当前用户的个人资料"""
    try:
        # 将用户信息转换为UserProfile模型格式
        profile = {
            "username": current_user["username"],
            "email": current_user["email"],
            "is_admin": current_user.get("is_admin", False),
            "created_at": current_user["created_at"],
            "last_login": current_user.get("last_login")
        }
        
        # 添加头像URL
        if "avatar" in current_user and current_user["avatar"]:
            profile["avatar"] = current_user["avatar"]
        
        return profile
    except Exception as e:
        logger.error(f"获取用户资料失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户资料失败")

@router.put("/profile", response_model=Dict[str, str])
async def update_user_profile(
    profile_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """更新当前用户的个人资料"""
    conn = db_config.get_connection(auth_pool)
    try:
        # 记录初始操作
        user_id = current_user["id"]
        logger.info(f"用户 {current_user['username']} (ID: {user_id}) 请求更新个人资料")
        logger.info(f"更新内容: {profile_data}")
        
        # 准备更新项
        updates = []
        params = []
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 处理邮箱更新
        if "email" in profile_data and profile_data["email"] != current_user["email"]:
            # 验证新邮箱是否已被使用
            email_hash = hash_email_for_lookup(profile_data["email"])
            cursor.execute(
                "SELECT id FROM users WHERE email_hash = %s AND id != %s",
                (email_hash, user_id)
            )
            
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="该邮箱已被使用")
            
            # 添加到更新项
            updates.append("email = %s, email_hash = %s")
            params.extend([profile_data["email"], email_hash])
            logger.info(f"用户 {current_user['username']} 更新了邮箱")
        
        # 处理密码更新
        if "password" in profile_data and "currentPassword" in profile_data:
            # 验证当前密码
            if not verify_password(profile_data["currentPassword"], current_user["password_hash"]):
                raise HTTPException(status_code=400, detail="当前密码不正确")
            
            # 生成新密码哈希
            password_hash = get_password_hash(profile_data["password"])
            
            # 添加到更新项
            updates.append("password_hash = %s")
            params.append(password_hash)
            logger.info(f"用户 {current_user['username']} 更新了密码")
        
        # 如果没有要更新的内容，返回成功
        if not updates:
            return {"message": "个人资料未更改"}
        
        # 构建和执行SQL更新
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
        params.append(user_id)
        
        cursor.execute(sql, params)
        conn.commit()
        
        return {"message": "个人资料更新成功"}
    except HTTPException as e:
        # 传递HTTP异常
        raise e
    except Exception as e:
        conn.rollback()
        logger.error(f"更新用户资料失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新用户资料失败")
    finally:
        db_config.release_connection(auth_pool, conn)

@router.get("/check", response_model=Dict[str, bool])
async def check_auth_status(current_user: dict = Depends(get_current_user)):
    """检查认证状态"""
    return {"authenticated": True}

@router.delete("/account", response_model=Dict[str, str])
async def delete_account(
    request: Request,
    password: str,
    current_user: dict = Depends(get_current_user)
):
    """删除用户账户"""
    conn = db_config.get_connection(auth_pool)
    try:
        # 验证密码
        if not verify_password(password, current_user["password_hash"]):
            raise HTTPException(status_code=400, detail="密码不正确")
        
        user_id = current_user["id"]
        username = current_user["username"]
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 从用户设置表中删除数据
        cursor.execute("DELETE FROM user_settings WHERE user_id = %s", (user_id,))
        
        # 从用户令牌表中删除数据
        cursor.execute("DELETE FROM user_tokens WHERE user_id = %s", (user_id,))
        
        # 从用户表中删除数据
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        conn.commit()
        logger.info(f"用户 {username} (ID: {user_id}) 已删除其账户")
        
        # 清除当前令牌
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # 这里不需要查询数据库，因为我们已经删除了所有令牌
        
        return {"message": "账户已成功删除"}
    except HTTPException as e:
        conn.rollback()
        raise e
    except Exception as e:
        conn.rollback()
        logger.error(f"删除账户失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除账户失败")
    finally:
        db_config.release_connection(auth_pool, conn)

@router.get("/settings", response_model=UserSettings)
async def get_user_settings(current_user: dict = Depends(get_current_user)):
    """获取用户设置"""
    conn = db_config.get_connection(auth_pool)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT settings FROM user_settings WHERE user_id = %s",
            (current_user["id"],)
        )
        result = cursor.fetchone()
        
        # 如果用户没有设置记录，返回默认设置
        if not result:
            default_settings = UserSettings().dict()
            
            # 创建默认设置记录
            cursor.execute(
                "INSERT INTO user_settings (user_id, settings) VALUES (%s, %s)",
                (current_user["id"], json.dumps(default_settings))
            )
            conn.commit()
            
            return UserSettings()
        
        # 将存储的JSON转换为模型
        settings = result["settings"]
        return UserSettings(**settings)
    
    except Exception as e:
        logger.error(f"获取用户设置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户设置失败")
    finally:
        db_config.release_connection(auth_pool, conn)

@router.put("/settings", response_model=Dict[str, str])
async def update_user_settings(
    settings: UserSettings,
    current_user: dict = Depends(get_current_user)
):
    """更新用户设置"""
    conn = db_config.get_connection(auth_pool)
    try:
        # 记录操作
        logger.info(f"用户 {current_user['username']} (ID: {current_user['id']}) 正在更新设置")
        logger.info(f"设置内容: {settings.dict()}")
        
        # 将设置转换为JSON
        settings_json = settings.dict()
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 使用upsert操作保存设置
        cursor.execute("""
            INSERT INTO user_settings (user_id, settings, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                settings = %s,
                updated_at = CURRENT_TIMESTAMP
        """, (current_user["id"], json.dumps(settings_json), json.dumps(settings_json)))
        
        conn.commit()
        logger.info(f"用户 {current_user['username']} 设置已保存")
        return {"message": "设置已保存"}
    
    except Exception as e:
        conn.rollback()
        logger.error(f"更新用户设置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新用户设置失败")
    finally:
        db_config.release_connection(auth_pool, conn)

# 处理头像上传
async def save_avatar(avatar_data: str, username: str) -> str:
    """保存Base64编码的头像图片，返回文件路径"""
    try:
        # 解码Base64数据
        if "," in avatar_data:
            # 如果是完整的data URL，提取实际的Base64编码部分
            avatar_data = avatar_data.split(",", 1)[1]
        
        image_data = base64.b64decode(avatar_data)
        
        # 创建文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{username}_{timestamp}.png"
        
        # 保存路径
        avatar_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "avatars")
        
        # 确保目录存在
        if not os.path.exists(avatar_dir):
            os.makedirs(avatar_dir)
            logger.info(f"创建头像目录: {avatar_dir}")
        
        filepath = os.path.join(avatar_dir, filename)
        
        # 保存文件
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        # 返回相对路径（用于数据库存储）
        return f"/static/avatars/{filename}"
    except Exception as e:
        logger.error(f"保存头像失败: {str(e)}")
        raise HTTPException(status_code=500, detail="保存头像失败")

@router.post("/avatar", response_model=Dict[str, str])
async def update_avatar(
    avatar_data: AvatarUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """更新用户头像"""
    conn = db_config.get_connection(auth_pool)
    try:
        # 保存头像文件
        avatar_path = await save_avatar(avatar_data.avatar_data, current_user["username"])
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 更新数据库
        cursor.execute(
            "UPDATE users SET avatar = %s WHERE id = %s",
            (avatar_path, current_user["id"])
        )
        conn.commit()
        
        logger.info(f"用户 {current_user['username']} 更新了头像")
        return {"message": "头像更新成功", "avatar": avatar_path}
    except Exception as e:
        conn.rollback()
        logger.error(f"更新头像失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新头像失败")
    finally:
        db_config.release_connection(auth_pool, conn)

@router.post("/send-verification-code", response_model=Dict[str, str])
async def send_verification_code(request: VerificationCodeRequest):
    """发送邮箱验证码"""
    try:
        # 发送验证码
        _, verification_manager = get_email_utils()
        success = verification_manager.send_verification_code(
            request.email, 
            request.code_type,
            request.language
        )
        
        if success:
            logger.info(f"验证码已发送到: {request.email}")
            return {"message": "验证码已发送，请查收邮件"}
        else:
            logger.error(f"发送验证码失败: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="发送验证码失败，请稍后重试"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送验证码异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送验证码失败"
        )

@router.post("/verify-code", response_model=Dict[str, Any])
async def verify_verification_code(request: VerificationCodeVerify):
    """验证验证码"""
    try:
        # 验证验证码
        _, verification_manager = get_email_utils()
        is_valid = verification_manager.verify_code(
            request.email,
            request.code,
            request.code_type
        )
        
        if is_valid:
            logger.info(f"验证码验证成功: {request.email}")
            return {
                "valid": True,
                "message": "验证码验证成功"
            }
        else:
            logger.warning(f"验证码验证失败: {request.email}")
            return {
                "valid": False,
                "message": "验证码错误或已过期"
            }
    except Exception as e:
        logger.error(f"验证验证码异常: {str(e)}")
        return {
            "valid": False,
            "message": "验证失败"
        } 