import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
import logging
from datetime import datetime, timedelta
import psycopg2
from db_utils import decrypt_email, get_db_connection, release_db_connection
import random
import json

logger = logging.getLogger(__name__)

class EmailSender:
    """邮件发送器类"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.163.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_email = os.getenv('SMTP_EMAIL')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        
        # 邮件模板多语言支持
        self.templates = {
            'zh-CN': {
                'task_completion_success': {
                    'crawl': {
                        'subject': '🎉 数据爬取任务完成通知',
                        'body': '''
                        <html>
                        <body>
                            <h2>数据爬取任务完成</h2>
                            <p>您好！</p>
                            <p>您的数据爬取任务已成功完成：</p>
                            <ul>
                                <li><strong>任务ID：</strong>{task_id}</li>
                                <li><strong>完成时间：</strong>{completion_time}</li>
                            </ul>
                            <p>您现在可以在系统中查看爬取到的数据或进行数据分析。</p>
                            <p><a href="{system_url}">访问系统</a></p>
                        </body>
                        </html>
                        '''
                    },
                    'analysis': {
                        'subject': '📊 数据分析任务完成通知',
                        'body': '''
                        <html>
                        <body>
                            <h2>数据分析任务完成</h2>
                            <p>您好！</p>
                            <p>您的数据分析任务已成功完成：</p>
                            <ul>
                                <li><strong>任务ID：</strong>{task_id}</li>
                                <li><strong>完成时间：</strong>{completion_time}</li>
                            </ul>
                            <p>您现在可以在系统中查看分析结果和图表。</p>
                            <p><a href="{system_url}">访问系统</a></p>
                        </body>
                        </html>
                        '''
                    }
                },
                'task_completion_failed': {
                    'crawl': {
                        'subject': '❌ 数据爬取任务失败通知',
                        'body': '''
                        <html>
                        <body>
                            <h2>数据爬取任务失败</h2>
                            <p>您好！</p>
                            <p>很遗憾，您的数据爬取任务执行失败：</p>
                            <ul>
                                <li><strong>任务ID：</strong>{task_id}</li>
                                <li><strong>失败时间：</strong>{completion_time}</li>
                            </ul>
                            <p>请检查任务配置或联系系统管理员。</p>
                            <p><a href="{system_url}">访问系统</a></p>
                        </body>
                        </html>
                        '''
                    },
                    'analysis': {
                        'subject': '❌ 数据分析任务失败通知',
                        'body': '''
                        <html>
                        <body>
                            <h2>数据分析任务失败</h2>
                            <p>您好！</p>
                            <p>很遗憾，您的数据分析任务执行失败：</p>
                            <ul>
                                <li><strong>任务ID：</strong>{task_id}</li>
                                <li><strong>失败时间：</strong>{completion_time}</li>
                            </ul>
                            <p>请检查数据或联系系统管理员。</p>
                            <p><a href="{system_url}">访问系统</a></p>
                        </body>
                        </html>
                        '''
                    }
                },
                'password_reset': {
                    'subject': '🔐 密码重置请求',
                    'body': '''
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
                    '''
                },
                'welcome': {
                    'subject': '🎉 欢迎使用数据分析系统',
                    'body': '''
                    <html>
                    <body>
                        <h2>欢迎使用数据分析系统</h2>
                        <p>亲爱的 {username}，</p>
                        <p>欢迎加入数据分析系统！您的账户已成功创建。</p>
                        
                        <h3>系统功能：</h3>
                        <ul>
                            <li>🕷️ 数据爬取：自动采集房源数据</li>
                            <li>📊 数据分析：多维度分析房源信息</li>
                            <li>📈 图表展示：可视化分析结果</li>
                            <li>📤 数据导出：支持多种格式导出</li>
                        </ul>
                        
                        <p><a href="{system_url}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">立即开始使用</a></p>
                        
                        <p>如有任何问题，请随时联系我们！</p>
                    </body>
                    </html>
                    '''
                },
                'verification_code': {
                    'email_verification': {
                        'subject': '邮箱验证码',
                        'body': '''
                        <html>
                        <body>
                            <h2>邮箱验证码</h2>
                            <p>您的邮箱验证码是：<strong style="font-size: 24px; color: #007bff;">{code}</strong></p>
                            <p><strong>验证码5分钟内有效，请及时使用。</strong></p>
                            <p>如果这不是您的操作，请忽略此邮件。</p>
                        </body>
                        </html>
                        '''
                    },
                    'password_reset': {
                        'subject': '密码重置验证码',
                        'body': '''
                        <html>
                        <body>
                            <h2>密码重置验证码</h2>
                            <p>您的密码重置验证码是：<strong style="font-size: 24px; color: #dc3545;">{code}</strong></p>
                            <p><strong>验证码5分钟内有效，请及时使用。</strong></p>
                            <p>如果这不是您的操作，请忽略此邮件。</p>
                        </body>
                        </html>
                        '''
                    }
                }
            },
            'en-US': {
                'task_completion_success': {
                    'crawl': {
                        'subject': '🎉 Data Crawl Task Completed',
                        'body': '''
                        <html>
                        <body>
                            <h2>Data Crawl Task Completed</h2>
                            <p>Hello!</p>
                            <p>Your data crawl task has been completed successfully:</p>
                            <ul>
                                <li><strong>Task ID:</strong> {task_id}</li>
                                <li><strong>Completion Time:</strong> {completion_time}</li>
                            </ul>
                            <p>You can now view the crawled data or perform data analysis in the system.</p>
                            <p><a href="{system_url}">Access System</a></p>
                        </body>
                        </html>
                        '''
                    },
                    'analysis': {
                        'subject': '📊 Data Analysis Task Completed',
                        'body': '''
                        <html>
                        <body>
                            <h2>Data Analysis Task Completed</h2>
                            <p>Hello!</p>
                            <p>Your data analysis task has been completed successfully:</p>
                            <ul>
                                <li><strong>Task ID:</strong> {task_id}</li>
                                <li><strong>Completion Time:</strong> {completion_time}</li>
                            </ul>
                            <p>You can now view the analysis results and charts in the system.</p>
                            <p><a href="{system_url}">Access System</a></p>
                        </body>
                        </html>
                        '''
                    }
                },
                'task_completion_failed': {
                    'crawl': {
                        'subject': '❌ Data Crawl Task Failed',
                        'body': '''
                        <html>
                        <body>
                            <h2>Data Crawl Task Failed</h2>
                            <p>Hello!</p>
                            <p>Unfortunately, your data crawl task has failed:</p>
                            <ul>
                                <li><strong>Task ID:</strong> {task_id}</li>
                                <li><strong>Failure Time:</strong> {completion_time}</li>
                            </ul>
                            <p>Please check the task configuration or contact the system administrator.</p>
                            <p><a href="{system_url}">Access System</a></p>
                        </body>
                        </html>
                        '''
                    },
                    'analysis': {
                        'subject': '❌ Data Analysis Task Failed',
                        'body': '''
                        <html>
                        <body>
                            <h2>Data Analysis Task Failed</h2>
                            <p>Hello!</p>
                            <p>Unfortunately, your data analysis task has failed:</p>
                            <ul>
                                <li><strong>Task ID:</strong> {task_id}</li>
                                <li><strong>Failure Time:</strong> {completion_time}</li>
                            </ul>
                            <p>Please check the data or contact the system administrator.</p>
                            <p><a href="{system_url}">Access System</a></p>
                        </body>
                        </html>
                        '''
                    }
                },
                'password_reset': {
                    'subject': '🔐 Password Reset Request',
                    'body': '''
                    <html>
                    <body>
                        <h2>Password Reset Request</h2>
                        <p>We received your password reset request. Please click the link below to reset your password:</p>
                        <p><a href="{reset_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
                        <p>If the link is not clickable, please copy the following address to your browser:</p>
                        <p>{reset_link}</p>
                        <p><strong>Note:</strong> This link will expire in 24 hours.</p>
                        <p>If you did not request a password reset, please ignore this email.</p>
                    </body>
                    </html>
                    '''
                },
                'welcome': {
                    'subject': '🎉 Welcome to Data Analysis System',
                    'body': '''
                    <html>
                    <body>
                        <h2>Welcome to Data Analysis System</h2>
                        <p>Dear {username},</p>
                        <p>Welcome to the Data Analysis System! Your account has been successfully created.</p>
                        
                        <h3>System Features:</h3>
                        <ul>
                            <li>🕷️ Data Crawling: Automatic property data collection</li>
                            <li>📊 Data Analysis: Multi-dimensional property information analysis</li>
                            <li>📈 Chart Display: Visualized analysis results</li>
                            <li>📤 Data Export: Support for multiple export formats</li>
                        </ul>
                        
                        <p><a href="{system_url}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Start Using Now</a></p>
                        
                        <p>If you have any questions, please feel free to contact us!</p>
                    </body>
                    </html>
                    '''
                },
                'verification_code': {
                    'email_verification': {
                        'subject': 'Email Verification Code',
                        'body': '''
                        <html>
                        <body>
                            <h2>Email Verification Code</h2>
                            <p>Your email verification code is: <strong style="font-size: 24px; color: #007bff;">{code}</strong></p>
                            <p><strong>The verification code is valid for 5 minutes. Please use it promptly.</strong></p>
                            <p>If this was not your action, please ignore this email.</p>
                        </body>
                        </html>
                        '''
                    },
                    'password_reset': {
                        'subject': 'Password Reset Verification Code',
                        'body': '''
                        <html>
                        <body>
                            <h2>Password Reset Verification Code</h2>
                            <p>Your password reset verification code is: <strong style="font-size: 24px; color: #dc3545;">{code}</strong></p>
                            <p><strong>The verification code is valid for 5 minutes. Please use it promptly.</strong></p>
                            <p>If this was not your action, please ignore this email.</p>
                        </body>
                        </html>
                        '''
                    }
                }
            },
            'zh-TW': {
                'task_completion_success': {
                    'crawl': {
                        'subject': '🎉 數據爬取任務完成通知',
                        'body': '''
                        <html>
                        <body>
                            <h2>數據爬取任務完成</h2>
                            <p>您好！</p>
                            <p>您的數據爬取任務已成功完成：</p>
                            <ul>
                                <li><strong>任務ID：</strong>{task_id}</li>
                                <li><strong>完成時間：</strong>{completion_time}</li>
                            </ul>
                            <p>您現在可以在系統中查看爬取到的數據或進行數據分析。</p>
                            <p><a href="{system_url}">訪問系統</a></p>
                        </body>
                        </html>
                        '''
                    },
                    'analysis': {
                        'subject': '📊 數據分析任務完成通知',
                        'body': '''
                        <html>
                        <body>
                            <h2>數據分析任務完成</h2>
                            <p>您好！</p>
                            <p>您的數據分析任務已成功完成：</p>
                            <ul>
                                <li><strong>任務ID：</strong>{task_id}</li>
                                <li><strong>完成時間：</strong>{completion_time}</li>
                            </ul>
                            <p>您現在可以在系統中查看分析結果和圖表。</p>
                            <p><a href="{system_url}">訪問系統</a></p>
                        </body>
                        </html>
                        '''
                    }
                },
                'task_completion_failed': {
                    'crawl': {
                        'subject': '❌ 數據爬取任務失敗通知',
                        'body': '''
                        <html>
                        <body>
                            <h2>數據爬取任務失敗</h2>
                            <p>您好！</p>
                            <p>很遺憾，您的數據爬取任務執行失敗：</p>
                            <ul>
                                <li><strong>任務ID：</strong>{task_id}</li>
                                <li><strong>失敗時間：</strong>{completion_time}</li>
                            </ul>
                            <p>請檢查任務配置或聯繫系統管理員。</p>
                            <p><a href="{system_url}">訪問系統</a></p>
                        </body>
                        </html>
                        '''
                    },
                    'analysis': {
                        'subject': '❌ 數據分析任務失敗通知',
                        'body': '''
                        <html>
                        <body>
                            <h2>數據分析任務失敗</h2>
                            <p>您好！</p>
                            <p>很遺憾，您的數據分析任務執行失敗：</p>
                            <ul>
                                <li><strong>任務ID：</strong>{task_id}</li>
                                <li><strong>失敗時間：</strong>{completion_time}</li>
                            </ul>
                            <p>請檢查數據或聯繫系統管理員。</p>
                            <p><a href="{system_url}">訪問系統</a></p>
                        </body>
                        </html>
                        '''
                    }
                },
                'password_reset': {
                    'subject': '🔐 密碼重置請求',
                    'body': '''
                    <html>
                    <body>
                        <h2>密碼重置請求</h2>
                        <p>我們收到了您的密碼重置請求。請點擊下面的鏈接重置您的密碼：</p>
                        <p><a href="{reset_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">重置密碼</a></p>
                        <p>如果鏈接無法點擊，請複製以下地址到瀏覽器：</p>
                        <p>{reset_link}</p>
                        <p><strong>注意：</strong>此鏈接將在24小時後失效。</p>
                        <p>如果您沒有請求密碼重置，請忽略此郵件。</p>
                    </body>
                    </html>
                    '''
                },
                'welcome': {
                    'subject': '🎉 歡迎使用數據分析系統',
                    'body': '''
                    <html>
                    <body>
                        <h2>歡迎使用數據分析系統</h2>
                        <p>親愛的 {username}，</p>
                        <p>歡迎加入數據分析系統！您的賬戶已成功創建。</p>
                        
                        <h3>系統功能：</h3>
                        <ul>
                            <li>🕷️ 數據爬取：自動採集房源數據</li>
                            <li>📊 數據分析：多維度分析房源信息</li>
                            <li>📈 圖表展示：可視化分析結果</li>
                            <li>📤 數據匯出：支持多種格式匯出</li>
                        </ul>
                        
                        <p><a href="{system_url}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">立即開始使用</a></p>
                        
                        <p>如有任何問題，請隨時聯繫我們！</p>
                    </body>
                    </html>
                    '''
                },
                'verification_code': {
                    'email_verification': {
                        'subject': '郵箱驗證碼',
                        'body': '''
                        <html>
                        <body>
                            <h2>郵箱驗證碼</h2>
                            <p>您的郵箱驗證碼是：<strong style="font-size: 24px; color: #007bff;">{code}</strong></p>
                            <p><strong>驗證碼5分鐘內有效，請及時使用。</strong></p>
                            <p>如果這不是您的操作，請忽略此郵件。</p>
                        </body>
                        </html>
                        '''
                    },
                    'password_reset': {
                        'subject': '密碼重置驗證碼',
                        'body': '''
                        <html>
                        <body>
                            <h2>密碼重置驗證碼</h2>
                            <p>您的密碼重置驗證碼是：<strong style="font-size: 24px; color: #dc3545;">{code}</strong></p>
                            <p><strong>驗證碼5分鐘內有效，請及時使用。</strong></p>
                            <p>如果這不是您的操作，請忽略此郵件。</p>
                        </body>
                        </html>
                        '''
                    }
                }
            }
        }
        
        if not all([self.smtp_email, self.smtp_password]):
            logger.debug("邮件配置不完整，将使用开发模式（验证码会在日志中显示）")
    
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
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            
            if result:
                encrypted_email = result[0]
                return decrypt_email(encrypted_email)
            
            return None
            
        except Exception as e:
            logger.error(f"获取用户邮箱失败: {e}")
            return None
        finally:
            if conn:
                release_db_connection(conn)
    
    def get_template(self, language: str, template_type: str, task_type: str = None):
        """
        获取指定语言的邮件模板
        
        Args:
            language: 语言代码
            template_type: 模板类型
            task_type: 任务类型（可选）
            
        Returns:
            dict: 包含subject和body的模板
        """
        # 如果指定语言不存在，使用中文作为默认
        if language not in self.templates:
            language = 'zh-CN'
        
        template = self.templates[language].get(template_type, {})
        
        if task_type and isinstance(template, dict):
            return template.get(task_type, template)
        
        return template

    def send_task_completion_notification(self, user_id: int, task_type: str, task_id: int, success: bool = True, language: str = 'zh-CN'):
        """
        发送任务完成通知
        
        Args:
            user_id: 用户ID
            task_type: 任务类型 (crawl/analysis)
            task_id: 任务ID
            success: 任务是否成功
            language: 语言代码 (从前端传递)
        """
        email = self.get_user_email(user_id)
        if not email:
            logger.warning(f"无法获取用户 {user_id} 的邮箱地址")
            return
        
        # 获取模板
        template_type = 'task_completion_success' if success else 'task_completion_failed'
        template = self.get_template(language, template_type, task_type)
        
        if not template:
            logger.error(f"未找到模板: {language}/{template_type}/{task_type}")
            return
        
        # 格式化模板
        system_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')
        completion_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        subject = template['subject']
        body = template['body'].format(
            task_id=task_id,
            completion_time=completion_time,
            system_url=system_url
        )
        
        self.send_email([email], subject, body, is_html=True)
    
    def send_password_reset_email(self, email: str, reset_token: str, language: str = 'zh-CN'):
        """
        发送密码重置邮件
        
        Args:
            email: 用户邮箱
            reset_token: 重置令牌
            language: 语言代码 (从前端传递)
        """
        # 获取模板
        template = self.get_template(language, 'password_reset')
        
        if not template:
            logger.error(f"未找到密码重置模板: {language}")
            return
        
        # 格式化模板
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        subject = template['subject']
        body = template['body'].format(reset_link=reset_link)
        
        self.send_email([email], subject, body, is_html=True)
    
    def send_welcome_email(self, email: str, username: str, language: str = 'zh-CN'):
        """
        发送欢迎邮件
        
        Args:
            email: 用户邮箱
            username: 用户名
            language: 语言代码 (从前端传递)
        """
        # 获取模板
        template = self.get_template(language, 'welcome')
        
        if not template:
            logger.error(f"未找到欢迎邮件模板: {language}")
            return
        
        # 格式化模板
        system_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')
        
        subject = template['subject']
        body = template['body'].format(
            username=username,
            system_url=system_url
        )
        
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
        expires_at = datetime.now() + timedelta(minutes=5)  # 5分钟有效期
        
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
        if datetime.now() > code_info['expires_at']:
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
        now = datetime.now()
        expired_keys = [
            key for key, code_info in self.codes.items()
            if now > code_info['expires_at']
        ]
        
        for key in expired_keys:
            del self.codes[key]
        
        if expired_keys:
            logging.info(f"清理了 {len(expired_keys)} 个过期验证码")
    
    def send_verification_code(self, email: str, code_type: str = 'email_verification', language: str = 'zh-CN') -> bool:
        """
        发送验证码邮件
        
        Args:
            email: 收件人邮箱
            code_type: 验证码类型
            language: 语言代码 (从前端传递)
            
        Returns:
            bool: 发送是否成功
        """
        try:
            self.clean_expired_codes()
            
            # 生成并存储验证码
            code = self.store_code(email, code_type)
            
            # 检查邮件配置
            placeholder_emails = ['your_email@163.com', 'your_email@gmail.com', 'example@email.com']
            placeholder_passwords = ['your_authorization_code', 'your_password', 'your_app_password']
            
            if (not email_sender.smtp_email or not email_sender.smtp_password or 
                email_sender.smtp_email in placeholder_emails or 
                email_sender.smtp_password in placeholder_passwords):
                logger.warning(f"邮件配置不完整或使用占位符，验证码已生成但无法发送邮件")
                logger.info(f"📧 开发模式：{email} 的验证码是: {code} (类型: {code_type})")
                return True
            
            # 获取相应语言的模板
            template = email_sender.get_template(language, 'verification_code', code_type)
            
            if template:
                subject = template['subject']
                body = template['body'].format(code=code)
            else:
                # 后备方案，使用中文模板
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
            
            return email_sender.send_email([email], subject, body, is_html=True)
            
        except Exception as e:
            logging.error(f"发送验证码失败: {e}")
            return False

# 创建全局验证码管理器实例
verification_manager = VerificationCodeManager() 