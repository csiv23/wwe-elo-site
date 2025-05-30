from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from src.db import SessionLocal
from src.models import matches

router = APIRouter(prefix="/matches", tags=["matches"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[dict])
def list_matches(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    wrestler: Optional[str] = None,
    date_from: Optional[datetime.date] = None,
    date_to: Optional[datetime.date] = None,
):
    stmt = select(matches)
    if wrestler:
        stmt = stmt.where(
            (matches.c.winners.ilike(f"%{wrestler}%")) |
            (matches.c.losers.ilike(f"%{wrestler}%"))
        )
    if date_from:
        stmt = stmt.where(matches.c.date >= date_from)
    if date_to:
        stmt = stmt.where(matches.c.date <= date_to)
    rows = db.execute(stmt.limit(limit).offset(offset)).mappings().all()
    return [dict(r) for r in rows]
