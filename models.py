from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Date
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta, date
from database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Token quota for AI usage
    # 用 server_default 是为了在 SQL 层面给已存在的行兜底默认值，
    # 防止 daily_token_used / daily_token_limit 被插入 NULL。
    daily_token_used = Column(Integer, nullable=False, default=0, server_default="0")
    daily_token_date = Column(Date, nullable=True)
    daily_token_limit = Column(Integer, nullable=False, default=20000, server_default="20000")  # 20k tokens per day

    # Last activity timestamp (for admin "today active users" stat)
    last_active = Column(DateTime, nullable=True)

    # Relationship
    diaries = relationship("Diary", back_populates="user", cascade="all, delete-orphan")


class Diary(Base):
    __tablename__ = "diaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=True, default="")
    content = Column(Text, nullable=False)
    diary_date = Column(DateTime, default=datetime.utcnow)  # User-selected diary date
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # AI correction results
    corrections = Column(JSON, default=list)  # Store sentence-by-sentence corrections
    optimized_content = Column(Text, default="")  # Full optimized text
    ai_error = Column(Text, nullable=True, default=None)  # AI error message if correction failed

    # Weather recorded when the diary was written
    weather = Column(String(16), nullable=True, default=None)
    
    # Relationship
    user = relationship("User", back_populates="diaries")


class NotebookEntry(Base):
    __tablename__ = "notebook_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    phrase = Column(String(200), nullable=False, index=True)  # Original phrase searched
    translations = Column(JSON, default=list)  # Translations from AI
    examples = Column(JSON, default=list)  # Example sentences
    alternatives = Column(JSON, default=list)  # Alternative expressions
    note = Column(Text, nullable=True)  # User's personal note
    created_at = Column(DateTime, default=datetime.utcnow)
    last_reviewed_at = Column(DateTime, nullable=True)
    review_count = Column(Integer, default=0)
    
    # Relationship
    user = relationship("User", back_populates="notebook_entries")


# Add relationship to User
User.notebook_entries = relationship("NotebookEntry", back_populates="user", cascade="all, delete-orphan")


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
