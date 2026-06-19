from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
