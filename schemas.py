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
    daily_token_used: int = 0
    daily_token_limit: int = 20000
    
    class Config:
        from_attributes = True


class UserQuotaResponse(BaseModel):
    """每日 token 配额信息"""
    daily_token_used: int
    daily_token_limit: int
    remaining: int
    is_exceeded: bool


# Diary schemas
class DiaryBase(BaseModel):
    title: Optional[str] = ""
    content: str
    diary_date: Optional[datetime] = None
    weather: Optional[str] = None


class DiaryCreate(DiaryBase):
    pass


class DiaryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    diary_date: Optional[datetime] = None
    weather: Optional[str] = None


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
    weather: Optional[str] = None

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


# Notebook schemas
class NotebookEntryCreate(BaseModel):
    phrase: str
    translations: Optional[List[str]] = []
    examples: Optional[List[str]] = []
    alternatives: Optional[List[str]] = []
    note: Optional[str] = ""


class NotebookEntryUpdate(BaseModel):
    note: Optional[str] = None
    translations: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None


class NotebookEntryResponse(BaseModel):
    id: int
    user_id: int
    phrase: str
    translations: List[str] = []
    examples: List[str] = []
    alternatives: List[str] = []
    note: Optional[str] = ""
    created_at: datetime
    last_reviewed_at: Optional[datetime] = None
    review_count: int = 0
    
    class Config:
        from_attributes = True


# Email verification schemas
class SendVerificationCodeRequest(BaseModel):
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str


class VerifyCodeResponse(BaseModel):
    verified: bool
    message: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str
