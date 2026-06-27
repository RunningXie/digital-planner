from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./diary.db"
    
    # AI Configuration
    ai_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    ai_api_key: str = ""
    ai_model: str = "glm-4.5-air"
    daily_token_limit: int = 20000  # 每日每用户 token 配额上限
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # SMTP Email Configuration
    smtp_host: str = "smtp.126.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""

    # Admin Account
    admin_username: str = "admin"
    admin_password: str = "admin123"
    
    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
