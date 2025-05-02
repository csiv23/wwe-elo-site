# src/db.py
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

# where your on-disk DB will live
DATABASE_URL = "sqlite:///./wwe.db"

# 1) the engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # sqlite-specific
    echo=False
)

# 2) a session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 3) global metadata for your Table™ objects
metadata = MetaData()
