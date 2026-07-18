"""
إعداد الاتصال بقاعدة البيانات (SQLite - ملف محلي، لا يحتاج تثبيت سيرفر منفصل)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./email_agent.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency تُستخدم في مسارات FastAPI للحصول على جلسة قاعدة بيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
