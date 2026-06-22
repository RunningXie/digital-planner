import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import EmailVerificationCode
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def generate_verification_code(length: int = 6) -> str:
    """Generate a numeric verification code."""
    return ''.join(random.choices(string.digits, k=length))


async def send_verification_email(to_email: str, code: str) -> bool:
    """Send verification code email via SMTP."""
    msg = MIMEMultipart()
    msg['From'] = settings.smtp_from_email or settings.smtp_user
    msg['To'] = to_email
    msg['Subject'] = 'Dear Diary - 邮箱验证码'

    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #c4956a;">Dear Diary</h2>
        <p>你好！</p>
        <p>你的邮箱验证码是：</p>
        <div style="background: #f5e6d3; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #c4956a;">{code}</span>
        </div>
        <p>验证码有效期为 <strong>10 分钟</strong>，请尽快使用。</p>
        <p>如果这不是你的操作，请忽略此邮件。</p>
        <hr style="border: none; border-top: 1px solid #e8d5b7; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">此邮件由 Dear Diary 系统自动发送，请勿回复。</p>
    </div>
    """

    msg.attach(MIMEText(body, 'html', 'utf-8'))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=True,
        )
        logger.info(f"Verification email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def create_verification_code(db: Session, email: str) -> str:
    """Create a new verification code for the given email."""
    code = generate_verification_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Invalidate any existing codes for this email
    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == email,
        EmailVerificationCode.used == False,
    ).update({"used": True})

    verification = EmailVerificationCode(
        email=email,
        code=code,
        expires_at=expires_at,
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return code


def verify_code(db: Session, email: str, code: str) -> bool:
    """Verify a verification code. Returns True if valid."""
    verification = db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == email,
        EmailVerificationCode.code == code,
        EmailVerificationCode.used == False,
    ).first()

    if not verification:
        return False

    if verification.expires_at < datetime.utcnow():
        return False

    # Mark as used
    verification.used = True
    db.commit()
    return True
