import logging
import smtplib
import secrets
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.config import get_settings

logger = logging.getLogger(__name__)

EMAIL_TOKEN_EXPIRE_HOURS = 24


class EmailService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    def _create_message(self, to_email: str, subject: str, html_content: str) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["From"] = self.settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        return msg

    def _send(self, msg: MIMEMultipart) -> bool:
        if not self.settings.SMTP_HOST:
            logger.warning("SMTP not configured, email not sent")
            return False
        try:
            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
                server.starttls()
                server.login(self.settings.SMTP_USER, self.settings.SMTP_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def generate_token(self, user: User, token_type: str) -> str:
        token = secrets.token_urlsafe(32)
        user_data = {
            "user_id": user.id,
            "type": token_type,
            "exp": (datetime.now(timezone.utc) + timedelta(hours=EMAIL_TOKEN_EXPIRE_HOURS)).isoformat(),
        }
        from app.core.security import create_access_token
        return create_access_token(subject=str(user.id), extra_data=user_data)

    async def send_verification_email(self, user: User) -> bool:
        token = await self.generate_token(user, "email_verify")
        verify_url = f"{self.settings.FRONTEND_URL}/verify-email?token={token}"
        html = f"""
        <h2>欢迎使用 TrendRadar</h2>
        <p>请点击以下链接验证您的邮箱：</p>
        <p><a href="{verify_url}">验证邮箱</a></p>
        <p>此链接 {EMAIL_TOKEN_EXPIRE_HOURS} 小时内有效。</p>
        <p>如果您没有注册 TrendRadar 账号，请忽略此邮件。</p>
        """
        msg = self._create_message(user.email, "TrendRadar - 邮箱验证", html)
        return self._send(msg)

    async def send_password_reset_email(self, user: User) -> str | None:
        token = await self.generate_token(user, "password_reset")
        reset_url = f"{self.settings.FRONTEND_URL}/reset-password?token={token}"
        html = f"""
        <h2>TrendRadar 密码重置</h2>
        <p>请点击以下链接重置您的密码：</p>
        <p><a href="{reset_url}">重置密码</a></p>
        <p>此链接 {EMAIL_TOKEN_EXPIRE_HOURS} 小时内有效。</p>
        <p>如果您没有请求重置密码，请忽略此邮件。</p>
        """
        msg = self._create_message(user.email, "TrendRadar - 密码重置", html)
        if self._send(msg):
            return token
        return None

    async def send_trial_reminder(self, user: User, days_left: int) -> bool:
        purchase_url = f"{self.settings.FRONTEND_URL}/purchase"
        if days_left <= 1:
            subject = "TrendRadar - 试用即将在今天结束"
            html = f"""
            <h2>您的 TrendRadar 试用即将结束</h2>
            <p>您的免费试用将在 <strong>今天</strong> 结束。</p>
            <p>试用结束后，您的账号将降级为免费版，部分功能将受到限制。</p>
            <p><a href="{purchase_url}" style="background:#409eff;color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px;">立即购买专业版</a></p>
            """
        else:
            subject = f"TrendRadar - 试用剩余 {days_left} 天"
            html = f"""
            <h2>您的 TrendRadar 试用还剩 {days_left} 天</h2>
            <p>您的免费试用将在 {days_left} 天后结束。</p>
            <p>试用结束后，您的账号将降级为免费版。</p>
            <p><a href="{purchase_url}" style="background:#409eff;color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px;">立即购买专业版</a></p>
            """
        msg = self._create_message(user.email, subject, html)
        return self._send(msg)

    async def send_subscription_expiry_email(self, user: User) -> bool:
        purchase_url = f"{self.settings.FRONTEND_URL}/purchase"
        html = f"""
        <h2>TrendRadar 专业版已到期</h2>
        <p>您的 TrendRadar 专业版订阅已到期，账号已降级为免费版。</p>
        <p>如需继续使用专业版功能，请重新购买。</p>
        <p><a href="{purchase_url}" style="background:#409eff;color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px;">重新购买</a></p>
        """
        msg = self._create_message(user.email, "TrendRadar - 专业版到期通知", html)
        return self._send(msg)
