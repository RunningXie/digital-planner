from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Diary schemas
class DiaryBase(BaseModel):
    title: Optional[str] = ""
    content: str
    diary_date: Optional[datetime] = None


class DiaryCreate(DiaryBase):
    pass


class DiaryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    diary_date: Optional[datetime] = None


class CorrectionItem(BaseModel):
    original: str
    corrected: str
    explanation: str
    suggestions: List[str]


class DiaryResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = ""
    content: str
    diary_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    corrections: List[CorrectionItem] = []
    optimized_content: str = ""
    error: Optional[str] = None  # AI error message, None if successful

    class Config:
        from_attributes = True


# Auth schemas - login only needs username and password
class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Phrase search schema
class PhraseSearchRequest(BaseModel):
    phrase: str
    source_lang: str = "zh"
    target_lang: str = "en"


class PhraseSearchResponse(BaseModel):
    phrase: str
    translations: List[str]
    examples: List[str]
    alternatives: List[str]
    source: Optional[str] = None  # "local" or "ai" or "error"
    error: Optional[str] = None
