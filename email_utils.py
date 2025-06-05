import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
import logging
from datetime import datetime
import psycopg2
from auth_secure import decrypt_email, get_db_connection
import random

logger = logging.getLogger(__name__)

class EmailSender:
    """邮件发送工具类"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.163.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_email = os.getenv("SMTP_EMAIL", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
        if not self.smtp_email or not self.smtp_password:
            logger.warning("邮箱配置不完整，邮件发送功能将无法使用")
    
    def _create_smtp_connection(self):
        """创建SMTP连接"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.login(self.smtp_email, self.smtp_password)
            return server
        except Exception as e:
            logger.error(f"创建SMTP连接失败: {e}")
            raise
    
    def send_email(self, 
                   to_emails: List[str], 
                   subject: str, 
                   body: str, 
                   is_html: bool = False,
                   attachments: Optional[List[str]] = None) -> bool:
        """
        发送邮件
        
        Args:
            to_emails: 收件人邮箱列表
            subject: 邮件主题
            body: 邮件内容
            is_html: 是否为HTML格式
            attachments: 附件文件路径列表
            
        Returns:
            bool: 发送是否成功
        """
        if not self.smtp_email or not self.smtp_password:
            logger.error("邮箱配置不完整，无法发送邮件")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.smtp_email
            msg['To'] = ", ".join(to_emails)
            msg['Subject'] = subject
            
            # 添加邮件正文
            if is_html:
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 添加附件
            if attachments:
                for file_path in attachments:
                    if os.path.isfile(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        msg.attach(part)
            
            # 发送邮件
            with self._create_smtp_connection() as server:
                server.send_message(msg)
            
            logger.info(f"邮件发送成功: {subject} -> {to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def get_user_email(self, user_id: int) -> Optional[str]:
        """
        从数据库获取用户邮箱（解密）
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: 解密后的邮箱地址，如果失败返回None
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            
            if result:
                encrypted_email = result[0]
                return decrypt_email(conn, encrypted_email)
            
            return None
            
        except Exception as e:
            logger.error(f"获取用户邮箱失败: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()
    
    def send_task_completion_notification(self, user_id: int, task_type: str, task_id: int, success: bool = True):
        """
        发送任务完成通知
        
        Args:
            user_id: 用户ID
            task_type: 任务类型 (crawl/analysis)
            task_id: 任务ID
            success: 任务是否成功
        """
        email = self.get_user_email(user_id)
        if not email:
            logger.warning(f"无法获取用户 {user_id} 的邮箱地址")
            return
        
        if task_type == "crawl":
            if success:
                subject = "🎉 数据爬取任务完成通知"
                body = f"""
                <html>
                <body>
                    <h2>数据爬取任务完成</h2>
                    <p>您好！</p>
                    <p>您的数据爬取任务已成功完成：</p>
                    <ul>
                        <li><strong>任务ID：</strong>{task_id}</li>
                        <li><strong>完成时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>您现在可以在系统中查看爬取到的数据或进行数据分析。</p>
                    <p><a href="http://localhost:8000/docs">访问系统</a></p>
                </body>
                </html>
                """
            else:
                subject = "❌ 数据爬取任务失败通知"
                body = f"""
                <html>
                <body>
                    <h2>数据爬取任务失败</h2>
                    <p>您好！</p>
                    <p>很遗憾，您的数据爬取任务执行失败：</p>
                    <ul>
                        <li><strong>任务ID：</strong>{task_id}</li>
                        <li><strong>失败时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>请检查任务配置或联系系统管理员。</p>
                    <p><a href="http://localhost:8000/docs">访问系统</a></p>
                </body>
                </html>
                """
        
        elif task_type == "analysis":
            if success:
                subject = "📊 数据分析任务完成通知"
                body = f"""
                <html>
                <body>
                    <h2>数据分析任务完成</h2>
                    <p>您好！</p>
                    <p>您的数据分析任务已成功完成：</p>
                    <ul>
                        <li><strong>任务ID：</strong>{task_id}</li>
                        <li><strong>完成时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>您现在可以在系统中查看分析结果和图表。</p>
                    <p><a href="http://localhost:8000/docs">访问系统</a></p>
                </body>
                </html>
                """
            else:
                subject = "❌ 数据分析任务失败通知"
                body = f"""
                <html>
                <body>
                    <h2>数据分析任务失败</h2>
                    <p>您好！</p>
                    <p>很遗憾，您的数据分析任务执行失败：</p>
                    <ul>
                        <li><strong>任务ID：</strong>{task_id}</li>
                        <li><strong>失败时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>请检查数据或联系系统管理员。</p>
                    <p><a href="http://localhost:8000/docs">访问系统</a></p>
                </body>
                </html>
                """
        
        self.send_email([email], subject, body, is_html=True)
    
    def send_password_reset_email(self, email: str, reset_token: str):
        """
        发送密码重置邮件
        
        Args:
            email: 用户邮箱
            reset_token: 重置令牌
        """
        subject = "🔐 密码重置请求"
        reset_link = f"http://localhost:8000/reset-password?token={reset_token}"
        
        body = f"""
        <html>
        <body>
            <h2>密码重置请求</h2>
            <p>您好！</p>
            <p>我们收到了您的密码重置请求。请点击下面的链接重置您的密码：</p>
            <p><a href="{reset_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">重置密码</a></p>
            <p>如果链接无法点击，请复制以下地址到浏览器：</p>
            <p>{reset_link}</p>
            <p><strong>注意：</strong>此链接将在24小时后失效。</p>
            <p>如果您没有请求密码重置，请忽略此邮件。</p>
        </body>
        </html>
        """
        
        self.send_email([email], subject, body, is_html=True)
    
    def send_welcome_email(self, email: str, username: str):
        """
        发送欢迎邮件
        
        Args:
            email: 用户邮箱
            username: 用户名
        """
        subject = "🎉 欢迎使用链家数据分析系统"
        
        body = f"""
        <html>
        <body>
            <h2>欢迎使用链家数据分析系统</h2>
            <p>亲爱的 {username}，</p>
            <p>欢迎加入链家数据分析系统！您的账户已成功创建。</p>
            
            <h3>系统功能：</h3>
            <ul>
                <li>🕷️ 数据爬取：自动采集链家房源数据</li>
                <li>📊 数据分析：多维度分析房源信息</li>
                <li>📈 图表展示：可视化分析结果</li>
                <li>📤 数据导出：支持多种格式导出</li>
            </ul>
            
            <p><a href="http://localhost:8000/docs" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">立即开始使用</a></p>
            
            <p>如有任何问题，请随时联系我们！</p>
        </body>
        </html>
        """
        
        self.send_email([email], subject, body, is_html=True)

# 创建全局邮件发送实例
email_sender = EmailSender()

class VerificationCodeManager:
    """内存验证码管理器"""
    
    def __init__(self):
        self.codes = {}  # {email: {'code': '123456', 'expires_at': datetime, 'attempts': 0}}
        
    def generate_code(self) -> str:
        """生成6位数字验证码"""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    def store_code(self, email: str, code_type: str = 'email_verification') -> str:
        """存储验证码，返回生成的验证码"""
        code = self.generate_code()
        expires_at = datetime.datetime.now() + datetime.timedelta(minutes=5)  # 5分钟有效期
        
        key = f"{email}:{code_type}"
        self.codes[key] = {
            'code': code,
            'expires_at': expires_at,
            'attempts': 0,
            'email': email
        }
        
        logging.info(f"验证码已生成: {email} ({code_type})")
        return code
    
    def verify_code(self, email: str, code: str, code_type: str = 'email_verification') -> bool:
        """验证验证码"""
        key = f"{email}:{code_type}"
        
        if key not in self.codes:
            logging.warning(f"验证码不存在: {email}")
            return False
        
        code_info = self.codes[key]
        
        # 检查是否过期
        if datetime.datetime.now() > code_info['expires_at']:
            logging.warning(f"验证码已过期: {email}")
            del self.codes[key]
            return False
        
        # 检查尝试次数
        if code_info['attempts'] >= 3:
            logging.warning(f"验证码尝试次数过多: {email}")
            del self.codes[key]
            return False
        
        # 验证验证码
        if code_info['code'] == code:
            logging.info(f"验证码验证成功: {email}")
            del self.codes[key]  # 验证成功后删除
            return True
        else:
            # 增加尝试次数
            self.codes[key]['attempts'] += 1
            logging.warning(f"验证码错误: {email}, 尝试次数: {code_info['attempts']}")
            return False
    
    def clean_expired_codes(self):
        """清理过期的验证码"""
        now = datetime.datetime.now()
        expired_keys = [
            key for key, code_info in self.codes.items()
            if now > code_info['expires_at']
        ]
        
        for key in expired_keys:
            del self.codes[key]
        
        if expired_keys:
            logging.info(f"清理了 {len(expired_keys)} 个过期验证码")
    
    def send_verification_code(self, email: str, code_type: str = 'email_verification') -> bool:
        """发送验证码邮件"""
        try:
            # 清理过期验证码
            self.clean_expired_codes()
            
            # 生成并存储验证码
            code = self.store_code(email, code_type)
            
            # 发送验证码邮件
            if code_type == 'email_verification':
                subject = "邮箱验证码"
                body = f"""
                您的邮箱验证码是：<strong>{code}</strong>
                <br><br>
                验证码5分钟内有效，请及时使用。
                <br><br>
                如果这不是您的操作，请忽略此邮件。
                """
            elif code_type == 'password_reset':
                subject = "密码重置验证码"
                body = f"""
                您的密码重置验证码是：<strong>{code}</strong>
                <br><br>
                验证码5分钟内有效，请及时使用。
                <br><br>
                如果这不是您的操作，请忽略此邮件。
                """
            else:
                subject = "验证码"
                body = f"""
                您的验证码是：<strong>{code}</strong>
                <br><br>
                验证码5分钟内有效，请及时使用。
                """
            
            return email_sender.send_email(email, subject, body)
            
        except Exception as e:
            logging.error(f"发送验证码失败: {e}")
            return False

# 创建全局验证码管理器实例
verification_manager = VerificationCodeManager() 