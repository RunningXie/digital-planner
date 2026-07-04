import json
import logging
import aiohttp
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List
from datetime import datetime, timedelta, date
from contextlib import asynccontextmanager

from database import init_db, get_db, engine
from models import User, Diary, NotebookEntry, EmailVerificationCode
from schemas import (
    UserCreate, UserResponse, UserLogin,
    DiaryCreate, DiaryUpdate, DiaryResponse,
    Token, PhraseSearchRequest, PhraseSearchResponse,
    NotebookEntryCreate, NotebookEntryUpdate, NotebookEntryResponse,
    SendVerificationCodeRequest, VerifyCodeRequest, VerifyCodeResponse,
    ResetPasswordRequest, UserQuotaResponse
)
from auth import (
    get_password_hash, verify_password, 
    create_access_token, get_current_active_user,
    get_current_user
)
from ai_service import ai_service
from static_dictionary import search as static_dict_search
from email_service import (
    send_verification_email, create_verification_code, verify_code
)
from config import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ========== Token Quota ==========

def _estimate_tokens(text: str) -> int:
    """估算文本的 token 数。英文约 1 token ≈ 3.5 字符，加 prompt 开销。"""
    if not text:
        return 100
    # 输入 token + 输出 token 估算（输出通常与输入相当）
    return max(100, int(len(text) / 3.5) * 2 + 300)


def _check_and_deduct_quota(user: User, estimated_tokens: int, db: Session) -> None:
    """
    检查用户每日 token 配额，如果超限抛出 429。
    如果日期变更则自动重置计数器。
    """
    today = date.today()
    if user.daily_token_date != today:
        user.daily_token_used = 0
        user.daily_token_date = today
        db.commit()

    if user.daily_token_used + estimated_tokens > user.daily_token_limit:
        smtp_email = settings.smtp_user or "support@example.com"
        raise HTTPException(
            status_code=429,
            detail=(
                f"今日 AI 调用额度已用完（{user.daily_token_limit:,} tokens/天）。"
                f"如需更多配额，请联系我们：{smtp_email}"
            )
        )

    user.daily_token_used += estimated_tokens
    db.commit()


# Lifespan handler for startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时打印数据库连接信息
    import os
    env_db_url = os.environ.get("DATABASE_URL", "未设置")
    db_url = settings.database_url
    
    logger.info("=" * 60)
    logger.info("🚀 Dear Diary 服务启动中...")
    logger.info("=" * 60)
    
    # 调试：打印环境变量和配置
    logger.info(f"🔍 环境变量 DATABASE_URL: {env_db_url}")
    logger.info(f"🔍 Settings.database_url: {db_url}")
    logger.info(f"🔍 两者是否相同: {'是' if env_db_url == db_url else '否 (使用默认值)'}")
    
    is_postgresql = "postgresql" in db_url
    
    # 隐藏密码
    if "@" in db_url:
        parts = db_url.split("@")
        safe_url = parts[0].rsplit(":", 1)[0] + ":***@" + parts[1]
    else:
        safe_url = db_url
    
    logger.info(f"📊 数据库类型: {'PostgreSQL' if is_postgresql else 'SQLite'}")
    logger.info(f"🔗 数据库地址: {safe_url}")
    
    # 测试数据库连接
    try:
        with engine.connect() as conn:
            if is_postgresql:
                result = conn.execute(text("SELECT version();"))
                version = result.fetchone()[0]
                logger.info(f"✅ PostgreSQL 连接成功!")
                logger.info(f"📌 数据库版本: {version[:80]}...")
            else:
                result = conn.execute(text("SELECT sqlite_version();"))
                version = result.fetchone()[0]
                logger.info(f"✅ SQLite 连接成功!")
                logger.info(f"📌 SQLite 版本: {version}")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        logger.error("请检查数据库配置和网络连接!")
    
    logger.info("=" * 60)
    
    # 初始化数据库表
    init_db()
    logger.info("✅ 数据库表初始化完成")
    
    yield
    
    # 关闭时打印
    logger.info("👋 Dear Diary 服务已关闭")

# Initialize FastAPI app
app = FastAPI(
    title="Dear Diary - English Writing Practice",
    description="A warm and private digital planner for English writing practice with AI corrections",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware (admin login uses request.session)
# 注意：必须用 settings.secret_key，否则重启后已签发的 session 全部失效
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="diary_session",
    same_site="lax",
    https_only=False,  # 本地 http 测试；生产部署到 https 时改为 True
)

class NoCacheStaticFiles(StaticFiles):
    """静态资源默认不缓存，避免改了 CSS/JS 浏览器不刷新。"""
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        # dev 时强制每次回源校验；部署到生产可改为 max-age=3600
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response

# Mount static files and templates
app.mount("/static", NoCacheStaticFiles(directory="static"), name="static")

from jinja2 import Environment, FileSystemLoader, select_autoescape
templates_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "htm"])
)

def render_template(template_name: str, request: Request, **context):
    template = templates_env.get_template(template_name)
    return HTMLResponse(template.render(request=request, **context))


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Database debug endpoint
@app.get("/debug/db")
async def debug_database():
    """调试接口：显示当前数据库配置"""
    db_url = settings.database_url
    # 隐藏密码
    if "@" in db_url:
        parts = db_url.split("@")
        safe_url = parts[0].rsplit(":", 1)[0] + ":***@" + parts[1]
    else:
        safe_url = db_url
    
    return {
        "database_type": "PostgreSQL" if "postgresql" in db_url else "SQLite",
        "database_url": safe_url,
        "ai_model": settings.ai_model
    }


# Page routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return render_template("index.html", request)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return render_template("login.html", request)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return render_template("register.html", request)


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return render_template("forgot_password.html", request)


@app.get("/write", response_class=HTMLResponse)
async def write_page(request: Request):
    return render_template("write.html", request)


@app.get("/diaries", response_class=HTMLResponse)
async def diaries_page(request: Request):
    return render_template("diaries.html", request)


@app.get("/notebook", response_class=HTMLResponse)
async def notebook_page(request: Request):
    return render_template("notebook.html", request)


# Admin Routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """后台首页：未登录直接 302 跳到登录页，避免页面闪一下才被踢。"""
    if not request.session.get("admin_logged_in"):
        return RedirectResponse(url="/admin/login", status_code=302)
    return render_template("admin.html", request)


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return render_template("admin_login.html", request)


# Admin API Routes
@app.post("/api/admin/login")
async def admin_login(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    # 管理员账户从环境变量 / .env 读取，避免硬编码到代码里
    if username == settings.admin_username and password == settings.admin_password:
        # 设置登录状态（使用session）
        request.session["admin_logged_in"] = True
        return {"message": "Login successful"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@app.post("/api/admin/logout")
async def admin_logout(request: Request):
    request.session.pop("admin_logged_in", None)
    return {"message": "Logout successful"}


@app.get("/api/admin/check")
async def admin_check(request: Request):
    if request.session.get("admin_logged_in"):
        return {"authenticated": True}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )


@app.get("/api/admin/stats")
async def admin_stats(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("admin_logged_in"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # 总用户数
    total_users = db.query(User).count()
    
    # 总日记数
    total_diaries = db.query(Diary).count()
    
    # 今日活跃用户（过去24小时有活动的用户）
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    today_active_users = db.query(User).filter(
        User.last_active >= yesterday
    ).count()
    
    # 人均日记数
    avg_diaries_per_user = round(total_diaries / max(total_users, 1), 1)
    
    # 总笔记数
    total_notes = db.query(NotebookEntry).count()
    
    # 使用笔记的用户数
    users_with_notes = db.query(NotebookEntry.user_id).distinct().count()
    
    # 近7天每日日记数量
    daily_diaries = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = start_of_day + timedelta(days=1)
        count = db.query(Diary).filter(
            Diary.created_at >= start_of_day,
            Diary.created_at < end_of_day
        ).count()
        daily_diaries.append({
            "date": f"{date.month}/{date.day}",
            "count": count
        })
    
    # 活跃用户排行（按日记数量）
    top_users = db.query(
        User.username,
        User.email,
        User.created_at,
        User.last_active,
        User.daily_token_used,
        User.daily_token_limit,
        func.count(Diary.id).label("diary_count")
    ).outerjoin(Diary, User.id == Diary.user_id).group_by(User.id).order_by(
        func.count(Diary.id).desc()
    ).limit(10).all()
    
    top_users_list = []
    for user in top_users:
        top_users_list.append({
            "username": user.username,
            "email": user.email,
            "diary_count": user.diary_count,
            "daily_token_used": user.daily_token_used or 0,
            "daily_token_limit": user.daily_token_limit or 20000,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_active": user.last_active.isoformat() if user.last_active else None
        })
    
    return {
        "total_users": total_users,
        "total_diaries": total_diaries,
        "today_active_users": today_active_users,
        "avg_diaries_per_user": avg_diaries_per_user,
        "total_notes": total_notes,
        "users_with_notes": users_with_notes,
        "daily_diaries": daily_diaries,
        "top_users": top_users_list
    }


# API Routes - Auth
@app.post("/api/auth/send-verification-code")
async def send_verification_code(req: SendVerificationCodeRequest, db: Session = Depends(get_db)):
    """Send a verification code to the given email."""
    if not settings.smtp_user or not settings.smtp_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SMTP not configured. Please set SMTP environment variables."
        )
    
    # Check if email is already registered
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already registered"
        )
    
    code = create_verification_code(db, req.email)
    success = await send_verification_email(req.email, code)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again later."
        )
    
    return {"message": "Verification code sent", "email": req.email}


@app.post("/api/auth/verify-code", response_model=VerifyCodeResponse)
async def verify_verification_code(req: VerifyCodeRequest, db: Session = Depends(get_db)):
    """Verify the email verification code."""
    is_valid = verify_code(db, req.email, req.code)
    
    if not is_valid:
        return VerifyCodeResponse(verified=False, message="Invalid or expired verification code")
    
    return VerifyCodeResponse(verified=True, message="Verification successful")


@app.post("/api/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/api/auth/login", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/auth/reset-password")
async def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password after email verification."""
    # Find user by email
    db_user = db.query(User).filter(User.email == req.email).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with this email"
        )
    
    # Update password
    db_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    
    return {"message": "Password reset successfully"}


@app.get("/api/auth/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get("/api/user/quota", response_model=UserQuotaResponse)
async def get_user_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户的每日 token 配额信息"""
    today = date.today()
    if current_user.daily_token_date != today:
        current_user.daily_token_used = 0
        current_user.daily_token_date = today
        db.commit()
    return UserQuotaResponse(
        daily_token_used=current_user.daily_token_used,
        daily_token_limit=current_user.daily_token_limit,
        remaining=max(0, current_user.daily_token_limit - current_user.daily_token_used),
        is_exceeded=current_user.daily_token_used >= current_user.daily_token_limit,
    )


# API Routes - Diaries
@app.post("/api/diaries/stream")
async def create_diary_stream(
    diary: DiaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Stream diary corrections sentence by sentence.
    Returns a server-sent event stream with individual correction results.
    """
    # 检查 token 配额
    estimated_tokens = _estimate_tokens(diary.content)
    _check_and_deduct_quota(current_user, estimated_tokens, db)

    db_diary = Diary(
        user_id=current_user.id,
        title=diary.title or "",
        content=diary.content,
        diary_date=diary.diary_date or datetime.utcnow(),
        weather=diary.weather,
        mood=diary.mood,
    )
    db.add(db_diary)
    db.commit()
    db.refresh(db_diary)
    
    all_corrections = []
    optimized_content = ""
    
    async def stream_corrections():
        nonlocal all_corrections, optimized_content
        stream_failed = False
        try:
            async for item in ai_service.correct_diary_stream(diary.content):
                if item.get("type") == "optimized":
                    optimized_content = item.get("optimized_content", "")
                    yield f"data: {json.dumps(item)}\n\n"
                else:
                    all_corrections.append(item)
                    yield f"data: {json.dumps(item)}\n\n"
        except Exception as e:
            # 流式接口中途异常时，把已收到的内容落库，避免前端"已展示的优化版本被错误覆盖"
            stream_failed = True
            logger.error(f"流式批改中途失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        # 无论成功还是异常退出，都把已经收集到的部分结果写回 DB
        try:
            db_diary.corrections = all_corrections
            db_diary.optimized_content = optimized_content
            db.commit()
            db.refresh(db_diary)
        except Exception as e:
            logger.error(f"保存部分批改结果失败: {e}", exc_info=True)

        done_event = {"type": "done", "diary_id": db_diary.id}
        if stream_failed:
            done_event["partial"] = True
        yield f"data: {json.dumps(done_event)}\n\n"
    
    return StreamingResponse(stream_corrections(), media_type="text/event-stream")


@app.post("/api/diaries/draft", response_model=DiaryResponse)
async def save_draft(
    diary: DiaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Save diary draft without AI correction.
    This is used for auto-save feature.
    """
    db_diary = Diary(
        user_id=current_user.id,
        title=diary.title or "",
        content=diary.content,
        diary_date=diary.diary_date or datetime.utcnow(),
        weather=diary.weather,
        mood=diary.mood,
    )
    db.add(db_diary)
    db.commit()
    db.refresh(db_diary)
    
    return DiaryResponse(
        id=db_diary.id,
        user_id=db_diary.user_id,
        title=db_diary.title,
        content=db_diary.content,
        diary_date=db_diary.diary_date,
        created_at=db_diary.created_at,
        updated_at=db_diary.updated_at,
        corrections=[],
        optimized_content="",
        error=None,
        weather=db_diary.weather,
        mood=db_diary.mood,
    )


@app.put("/api/diaries/{diary_id}/draft", response_model=DiaryResponse)
async def update_draft(
    diary_id: int,
    diary_update: DiaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update existing diary draft without AI correction.
    This is used for auto-save feature.
    """
    db_diary = db.query(Diary).filter(
        Diary.id == diary_id,
        Diary.user_id == current_user.id
    ).first()
    if not db_diary:
        raise HTTPException(status_code=404, detail="Diary not found")
    
    if diary_update.title is not None:
        db_diary.title = diary_update.title
    if diary_update.content is not None:
        db_diary.content = diary_update.content
    if diary_update.diary_date is not None:
        db_diary.diary_date = diary_update.diary_date
    if diary_update.weather is not None:
        db_diary.weather = diary_update.weather
    if diary_update.mood is not None:
        db_diary.mood = diary_update.mood

    db.commit()
    db.refresh(db_diary)

    return DiaryResponse(
        id=db_diary.id,
        user_id=db_diary.user_id,
        title=db_diary.title,
        content=db_diary.content,
        diary_date=db_diary.diary_date,
        created_at=db_diary.created_at,
        updated_at=db_diary.updated_at,
        corrections=db_diary.corrections or [],
        optimized_content=db_diary.optimized_content or "",
        error=db_diary.ai_error,
        weather=db_diary.weather,
        mood=db_diary.mood,
    )


@app.post("/api/diaries", response_model=DiaryResponse)
async def create_diary(
    diary: DiaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # 检查 token 配额
    estimated_tokens = _estimate_tokens(diary.content)
    _check_and_deduct_quota(current_user, estimated_tokens, db)

    # Create diary entry
    db_diary = Diary(
        user_id=current_user.id,
        title=diary.title or "",
        content=diary.content,
        diary_date=diary.diary_date or datetime.utcnow(),
        weather=diary.weather,
        mood=diary.mood,
    )
    db.add(db_diary)
    db.commit()
    db.refresh(db_diary)
    
    # Get AI corrections
    corrections_result = await ai_service.correct_diary(diary.content)
    
    # Update diary with corrections (always store original content if AI fails)
    db_diary.corrections = corrections_result.get("corrections", [])
    db_diary.optimized_content = corrections_result.get("optimized_content", diary.content)
    db_diary.ai_error = corrections_result.get("error")  # Store error message
    db.commit()
    db.refresh(db_diary)
    
    # Build response - include error if present
    response = DiaryResponse(
        id=db_diary.id,
        user_id=db_diary.user_id,
        title=db_diary.title,
        content=db_diary.content,
        diary_date=db_diary.diary_date,
        created_at=db_diary.created_at,
        updated_at=db_diary.updated_at,
        corrections=db_diary.corrections or [],
        optimized_content=db_diary.optimized_content or "",
        error=db_diary.ai_error,  # Pass through AI error
        weather=db_diary.weather,
        mood=db_diary.mood,
    )
    return response


@app.get("/api/diaries", response_model=List[DiaryResponse])
async def get_diaries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    diaries = db.query(Diary).filter(
        Diary.user_id == current_user.id
    ).order_by(Diary.diary_date.desc()).offset(skip).limit(limit).all()
    return diaries


@app.get("/api/diaries/{diary_id}", response_model=DiaryResponse)
async def get_diary(
    diary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    diary = db.query(Diary).filter(
        Diary.id == diary_id,
        Diary.user_id == current_user.id
    ).first()
    if not diary:
        raise HTTPException(status_code=404, detail="Diary not found")
    return diary


@app.put("/api/diaries/{diary_id}", response_model=DiaryResponse)
async def update_diary(
    diary_id: int,
    diary_update: DiaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_diary = db.query(Diary).filter(
        Diary.id == diary_id,
        Diary.user_id == current_user.id
    ).first()
    if not db_diary:
        raise HTTPException(status_code=404, detail="Diary not found")

    # Track whether content changed (to decide whether to re-run AI)
    content_changed = (
        diary_update.content is not None
        and diary_update.content != db_diary.content
    )

    # Update fields
    if diary_update.title is not None:
        db_diary.title = diary_update.title
    if diary_update.diary_date is not None:
        db_diary.diary_date = diary_update.diary_date
    if diary_update.weather is not None:
        db_diary.weather = diary_update.weather
    if diary_update.mood is not None:
        db_diary.mood = diary_update.mood
    if content_changed:
        db_diary.content = diary_update.content
        # 检查 token 配额
        estimated_tokens = _estimate_tokens(diary_update.content)
        _check_and_deduct_quota(current_user, estimated_tokens, db)
        # Re-run AI corrections
        corrections_result = await ai_service.correct_diary(diary_update.content)
        db_diary.corrections = corrections_result.get("corrections", [])
        db_diary.optimized_content = corrections_result.get("optimized_content", diary_update.content)
        db_diary.ai_error = corrections_result.get("error")

    db.commit()
    db.refresh(db_diary)
    
    # Build response with error if present
    response = DiaryResponse(
        id=db_diary.id,
        user_id=db_diary.user_id,
        title=db_diary.title,
        content=db_diary.content,
        diary_date=db_diary.diary_date,
        created_at=db_diary.created_at,
        updated_at=db_diary.updated_at,
        corrections=db_diary.corrections or [],
        optimized_content=db_diary.optimized_content or "",
        error=db_diary.ai_error,
        weather=db_diary.weather,
        mood=db_diary.mood,
    )
    return response


@app.delete("/api/diaries/{diary_id}")
async def delete_diary(
    diary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_diary = db.query(Diary).filter(
        Diary.id == diary_id,
        Diary.user_id == current_user.id
    ).first()
    if not db_diary:
        raise HTTPException(status_code=404, detail="Diary not found")
    
    db.delete(db_diary)
    db.commit()
    return {"message": "Diary deleted successfully"}


# API Routes - Phrase Search
def _check_notebook_for_phrase(db: Session, user: User, phrase: str) -> dict | None:
    """
    先查用户的笔记本是否有匹配的词条。
    匹配规则：phrase 字段、translations 列表、alternatives 列表任一大小写不敏感包含。
    命中则返回与 AI 返回结构一致的 dict（type=cached, source=notebook）。
    """
    if not phrase:
        return None
    phrase_lower = phrase.lower()
    entries = db.query(NotebookEntry).filter(
        NotebookEntry.user_id == user.id
    ).all()
    for entry in entries:
        if phrase_lower in (entry.phrase or "").lower():
            return _build_notebook_hit(entry, "phrase")
        if any(phrase_lower in (t or "").lower() for t in (entry.translations or [])):
            return _build_notebook_hit(entry, "translations")
        if any(phrase_lower in (a or "").lower() for a in (entry.alternatives or [])):
            return _build_notebook_hit(entry, "alternatives")
    return None


def _build_notebook_hit(entry: "NotebookEntry", matched_field: str) -> dict:
    """把 NotebookEntry 构造成前端能识别的 cached 事件。"""
    return {
        "type": "cached",
        "source": "notebook",
        "phrase": entry.phrase,
        "translations": entry.translations or [],
        "examples": entry.examples or [],
        "alternatives": entry.alternatives or [],
        "matched_field": matched_field,
        "entry_id": entry.id,
    }


@app.post("/api/search-phrase/stream")
async def search_phrase_stream(
    request: PhraseSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Stream phrase search results.
    Returns server-sent events with incremental results.
    命中顺序：用户笔记本 → 内置静态词典 → 内存缓存 → AI 调用。
    笔记本和词典命中都不消耗 token 配额。
    """
    # 1. 查笔记本（用户私有，命中即返回，不消耗配额）
    notebook_hit = _check_notebook_for_phrase(db, current_user, request.phrase)
    if notebook_hit:
        async def stream_notebook():
            yield f"data: {json.dumps(notebook_hit, ensure_ascii=False)}\n\n"
        return StreamingResponse(stream_notebook(), media_type="text/event-stream")

    # 2. 查内置静态词典（精选短语 + ECDict 通用词库，离线即查，不消耗配额）
    dict_hit = static_dict_search(request.phrase)
    if dict_hit:
        # dict_hit 已包含 source（'dictionary' 精选 / 'ecdict' 通用）
        dict_event = {
            "type": "cached",
            **dict_hit,
        }
        async def stream_dict():
            yield f"data: {json.dumps(dict_event, ensure_ascii=False)}\n\n"
        return StreamingResponse(stream_dict(), media_type="text/event-stream")

    # 3. 检查 token 配额（短语搜索 token 消耗较小）
    estimated_tokens = _estimate_tokens(request.phrase)
    _check_and_deduct_quota(current_user, estimated_tokens, db)

    async def stream_results():
        async for item in ai_service.search_phrase_stream(
            request.phrase,
            request.source_lang,
            request.target_lang
        ):
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(stream_results(), media_type="text/event-stream")


# ========== Notebook API ==========

@app.get("/api/notebook", response_model=list[NotebookEntryResponse])
async def get_notebook_entries(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all notebook entries for the current user"""
    entries = db.query(NotebookEntry)\
        .filter(NotebookEntry.user_id == current_user.id)\
        .order_by(NotebookEntry.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return entries


@app.post("/api/notebook", response_model=NotebookEntryResponse)
async def create_notebook_entry(
    entry: NotebookEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new notebook entry"""
    # Check if phrase already exists
    existing = db.query(NotebookEntry)\
        .filter(NotebookEntry.user_id == current_user.id)\
        .filter(NotebookEntry.phrase == entry.phrase)\
        .first()
    
    if existing:
        # Update existing entry instead
        existing.translations = entry.translations or existing.translations
        existing.examples = entry.examples or existing.examples
        existing.alternatives = entry.alternatives or existing.alternatives
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new entry
    db_entry = NotebookEntry(
        user_id=current_user.id,
        phrase=entry.phrase,
        translations=entry.translations or [],
        examples=entry.examples or [],
        alternatives=entry.alternatives or [],
        note=entry.note or ""
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


@app.get("/api/notebook/{entry_id}", response_model=NotebookEntryResponse)
async def get_notebook_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single notebook entry"""
    entry = db.query(NotebookEntry)\
        .filter(NotebookEntry.id == entry_id)\
        .filter(NotebookEntry.user_id == current_user.id)\
        .first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Notebook entry not found")
    
    return entry


@app.put("/api/notebook/{entry_id}", response_model=NotebookEntryResponse)
async def update_notebook_entry(
    entry_id: int,
    entry_update: NotebookEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a notebook entry"""
    db_entry = db.query(NotebookEntry)\
        .filter(NotebookEntry.id == entry_id)\
        .filter(NotebookEntry.user_id == current_user.id)\
        .first()
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Notebook entry not found")
    
    if entry_update.note is not None:
        db_entry.note = entry_update.note
    if entry_update.translations is not None:
        db_entry.translations = entry_update.translations
    if entry_update.examples is not None:
        db_entry.examples = entry_update.examples
    if entry_update.alternatives is not None:
        db_entry.alternatives = entry_update.alternatives
    
    db.commit()
    db.refresh(db_entry)
    return db_entry


@app.delete("/api/notebook/{entry_id}")
async def delete_notebook_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a notebook entry"""
    db_entry = db.query(NotebookEntry)\
        .filter(NotebookEntry.id == entry_id)\
        .filter(NotebookEntry.user_id == current_user.id)\
        .first()
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Notebook entry not found")
    
    db.delete(db_entry)
    db.commit()
    
    return {"message": "Notebook entry deleted successfully"}


@app.put("/api/notebook/{entry_id}/review", response_model=NotebookEntryResponse)
async def mark_as_reviewed(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark a notebook entry as reviewed"""
    db_entry = db.query(NotebookEntry)\
        .filter(NotebookEntry.id == entry_id)\
        .filter(NotebookEntry.user_id == current_user.id)\
        .first()
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Notebook entry not found")
    
    db_entry.last_reviewed_at = datetime.utcnow()
    db_entry.review_count = (db_entry.review_count or 0) + 1
    db.commit()
    db.refresh(db_entry)
    
    return db_entry


@app.get("/api/notebook/search/{phrase}")
async def search_notebook(
    phrase: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search notebook entries by phrase (for caching purposes)"""
    entries = db.query(NotebookEntry)\
        .filter(NotebookEntry.user_id == current_user.id)\
        .filter(NotebookEntry.phrase.ilike(f"%{phrase}%"))\
        .all()
    
    if entries:
        return {
            "found": True,
            "entries": [
                {
                    "id": e.id,
                    "phrase": e.phrase,
                    "translations": e.translations,
                    "examples": e.examples,
                    "alternatives": e.alternatives,
                    "note": e.note
                } for e in entries
            ]
        }
    
    return {"found": False, "entries": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )
