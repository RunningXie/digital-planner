from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_settings

settings = get_settings()

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables, then patch missing columns on existing tables.

    SQLAlchemy 的 create_all 只会创建缺失的表，不会给已有表加新列。
    每次 model 加新字段，老库的列就缺失，访问时直接报 no such column。
    这里用 SQL 反射现有列，对比 model 定义的列，把缺失的 ALTER 上去。
    """
    # 1) 先确保表都建好
    Base.metadata.create_all(bind=engine)

    # 2) 轻量迁移：补齐已有表的缺失列
    try:
        inspector = inspect(engine)
        with engine.begin() as conn:
            for table_name, table in Base.metadata.tables.items():
                if not inspector.has_table(table_name):
                    continue
                existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
                for col in table.columns:
                    if col.name in existing_cols:
                        continue
                    # 构造 ALTER TABLE ADD COLUMN
                    col_type = col.type.compile(engine.dialect)
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    server_default = ""
                    if col.server_default is not None and col.server_default.arg is not None:
                        sd = str(col.server_default.arg).strip("'")
                        server_default = f" DEFAULT '{sd}'"
                    elif not col.nullable and col.default is not None and hasattr(col.default, "arg"):
                        server_default = f" DEFAULT {col.default.arg}"
                    stmt = f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type} {nullable}{server_default}'
                    try:
                        conn.execute(text(stmt))
                        print(f"  [migrate] {table_name}.{col.name} -> {col_type}")
                    except Exception as e:
                        # 不让迁移失败阻塞整个启动
                        print(f"  [migrate] skip {table_name}.{col.name}: {e}")
    except Exception as e:
        print(f"[migrate] 检查/补列失败（非致命）: {e}")

    # 3) 轻量回填：把所有带 default 值的列里仍是 NULL 的记录补成模型里的 default。
    #    包含 nullable=True 但有默认值的列（如 daily_token_used / daily_token_limit），
    #    这些列历史上可能因为缺 server_default 被插入 NULL，导致配额检查异常。
    try:
        from datetime import date
        with engine.begin() as conn:
            for table_name, table in Base.metadata.tables.items():
                if not inspector.has_table(table_name):
                    continue
                for col in table.columns:
                    if col.default is None or not hasattr(col.default, "arg"):
                        continue
                    default_val = col.default.arg
                    if default_val is None:
                        continue
                    # 仅当列存在时才回填
                    existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
                    if col.name not in existing_cols:
                        continue
                    # 简单回填（不区分类型，调用方负责 default 简单值）
                    try:
                        result = conn.execute(
                            text(f'UPDATE "{table_name}" SET "{col.name}" = :v WHERE "{col.name}" IS NULL'),
                            {"v": default_val}
                        )
                        if result.rowcount:
                            print(f"  [backfill] {table_name}.{col.name} <- {default_val} ({result.rowcount} rows)")
                    except Exception as e:
                        print(f"  [backfill] skip {table_name}.{col.name}: {e}")
    except Exception as e:
        print(f"[backfill] 回填失败（非致命）: {e}")
