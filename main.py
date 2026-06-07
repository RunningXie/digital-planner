import json
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from database import init_db, get_db
from models import User, Diary
from schemas import (
    UserCreate, UserResponse, UserLogin,
    DiaryCreate, DiaryUpdate, DiaryResponse,
    Token, PhraseSearchRequest, PhraseSearchResponse
)
from auth import (
    get_password_hash, verify_password, 
    create_access_token, get_current_active_user,
    get_current_user
)
from ai_service import ai_service
from config import get_settings

settings = get_settings()

# Lifespan handler for startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

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

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")

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


@app.get("/write", response_class=HTMLResponse)
async def write_page(request: Request):
    return render_template("write.html", request)


@app.get("/diaries", response_class=HTMLResponse)
async def diaries_page(request: Request):
    return render_template("diaries.html", request)


# API Routes - Auth
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


@app.get("/api/auth/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


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
    db_diary = Diary(
        user_id=current_user.id,
        title=diary.title or "",
        content=diary.content,
        diary_date=diary.diary_date or datetime.utcnow()
    )
    db.add(db_diary)
    db.commit()
    db.refresh(db_diary)
    
    all_corrections = []
    optimized_content = ""
    
    async def stream_corrections():
        nonlocal all_corrections, optimized_content
        
        async for item in ai_service.correct_diary_stream(diary.content):
            if item.get("type") == "optimized":
                optimized_content = item.get("optimized_content", "")
                yield f"data: {json.dumps(item)}\n\n"
            else:
                all_corrections.append(item)
                yield f"data: {json.dumps(item)}\n\n"
        
        db_diary.corrections = all_corrections
        db_diary.optimized_content = optimized_content
        db.commit()
        db.refresh(db_diary)
        
        yield f"data: {json.dumps({'type': 'done', 'diary_id': db_diary.id})}\n\n"
    
    return StreamingResponse(stream_corrections(), media_type="text/event-stream")


@app.post("/api/diaries", response_model=DiaryResponse)
async def create_diary(
    diary: DiaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Create diary entry
    db_diary = Diary(
        user_id=current_user.id,
        title=diary.title or "",
        content=diary.content,
        diary_date=diary.diary_date or datetime.utcnow()
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
    
    # Update fields
    if diary_update.title:
        db_diary.title = diary_update.title
    if diary_update.content:
        db_diary.content = diary_update.content
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
@app.post("/api/search-phrase/stream")
async def search_phrase_stream(
    request: PhraseSearchRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Stream phrase search results.
    Returns server-sent events with incremental results.
    """
    async def stream_results():
        async for item in ai_service.search_phrase_stream(
            request.phrase,
            request.source_lang,
            request.target_lang
        ):
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(stream_results(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )
