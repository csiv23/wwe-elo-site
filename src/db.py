import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

# pick up DATABASE_URL like: postgresql://user:pass@db:5432/wwe
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./wwe.db"         # fallback for quick local runs
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
metadata = MetaData()
