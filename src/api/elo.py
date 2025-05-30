from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text, select, func, and_
from sqlalchemy.orm import Session
from typing import List, Optional

from src.db import SessionLocal
from src.models import elo_history

router = APIRouter(prefix="/elo", tags=["elo"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/current", response_model=List[dict])
def list_current_elos(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    name:  Optional[str] = Query(None, description="Filter by wrestler name substring"),
):
    """
    Returns each wrestler’s latest ELO (elo_after from their most recent match),
    ordered descending. Supports paging and optional name‐filter.
    """
    # Postgres “DISTINCT ON” subquery to grab latest per wrestler:
    stmt = text("""
    SELECT DISTINCT ON (wrestler) wrestler, elo_after
    FROM elo_history
    /** optional name filter **/
    WHERE (:name IS NULL OR wrestler ILIKE :name_pattern)
    ORDER BY wrestler, match_id DESC
    OFFSET :offset
    LIMIT  :limit
    """)
    params = {
        "name": name,
        "name_pattern": f"%{name}%" if name else None,
        "limit": limit,
        "offset": offset,
    }
    rows = db.execute(stmt, params).all()
    # now order in Python by elo descending
    result = sorted(
        [{"wrestler": r[0], "elo": r[1]} for r in rows],
        key=lambda x: x["elo"], reverse=True
    )
    return result


@router.get("/top", response_model=List[dict])
def top_elos(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
):
    # for each wrestler grab the latest match_id…
    subq = (
        select(
            elo_history.c.wrestler,
            func.max(elo_history.c.match_id).label("latest_mid")
        )
        .group_by(elo_history.c.wrestler)
        .subquery()
    )

    # …join back to get their most recent elo_after, then sort desc
    stmt = (
        select(
            elo_history.c.wrestler,
            elo_history.c.elo_after.label("current_elo")
        )
        .join(
            subq,
            and_(
                elo_history.c.wrestler == subq.c.wrestler,
                elo_history.c.match_id == subq.c.latest_mid
            )
        )
        .order_by(elo_history.c.elo_after.desc())
        .limit(limit)
    )

    rows = db.execute(stmt).all()
    return [{"wrestler": r.wrestler, "elo": r.current_elo} for r in rows]