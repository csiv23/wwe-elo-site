# src/elo.py

import pandas as pd
from typing import Dict, List, Any, Tuple, Optional

from sqlalchemy import select, insert, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.db import SessionLocal
from src.models import matches, elo_history

DEFAULT_ELO = 1000
K_FACTOR   = 32


def calculate_elo_gain(player_elo: float,
                       opponent_avg_elo: float,
                       k: float = K_FACTOR) -> float:
    """
    Compute the ELO change for a player given their current ELO and
    the average ELO of their opponents. Positive k for winners, negative k for losers.
    """
    expected = 1 / (1 + 10 ** ((opponent_avg_elo - player_elo) / 400))
    return k * (1 - expected)


def update_elos(
    df: pd.DataFrame,
    initial_elos: Optional[Dict[str, float]] = None
) -> Tuple[Dict[str, float], Dict[str, List[Dict[str, Any]]]]:
    """
    Process all matches in df (chronologically), update ELOs and record history.

    Args:
        df: DataFrame must include at least ['id','winners','losers'].
        initial_elos: optional starting ELOs; defaults to 1000 for newcomers.

    Returns:
        elo_ratings: final ELO ratings dict {wrestler: elo}.
        history: per‐wrestler list of match records.
    """
    elo_ratings = initial_elos.copy() if initial_elos else {}
    history: Dict[str, List[Dict[str, Any]]] = {}

    # df is newest→oldest → reverse to oldest first
    for _, row in df.iloc[::-1].iterrows():
        match_id = row['id']
        winners  = [w.strip() for w in str(row['winners']).split(',') if w.strip()]
        losers   = [l.strip() for l in str(row['losers']).split(',')  if l.strip()]

        # losers’ avg elo
        loser_elos = [elo_ratings.get(l, DEFAULT_ELO) for l in losers] or [DEFAULT_ELO]
        avg_loser  = sum(loser_elos) / len(loser_elos)

        # winners gain
        for w in winners:
            before = elo_ratings.get(w, DEFAULT_ELO)
            change = calculate_elo_gain(before, avg_loser, k=K_FACTOR)
            after  = before + change
            elo_ratings[w] = after
            history.setdefault(w, []).append({
                'match_id':   match_id,
                'wrestler':   w,
                'opponents':  ', '.join(losers),
                'elo_before': before,
                'elo_change': change,
                'elo_after':  after,
                'result':     'Win'
            })

        # winners’ new avg
        winner_elos = [elo_ratings.get(w, DEFAULT_ELO) for w in winners] or [DEFAULT_ELO]
        avg_winner  = sum(winner_elos) / len(winner_elos)

        # losers lose
        for l in losers:
            before = elo_ratings.get(l, DEFAULT_ELO)
            change = calculate_elo_gain(before, avg_winner, k=-K_FACTOR)
            after  = before + change
            elo_ratings[l] = after
            history.setdefault(l, []).append({
                'match_id':   match_id,
                'wrestler':   l,
                'opponents':  ', '.join(winners),
                'elo_before': before,
                'elo_change': change,
                'elo_after':  after,
                'result':     'Loss'
            })

    return elo_ratings, history


def refresh_elo_history(records: List[Dict[str, Any]]) -> None:
    """
    Truncate the elo_history table and bulk‐insert the provided records.
    """
    session = SessionLocal()
    try:
        # 1) remove all existing rows
        session.execute(delete(elo_history))

        # 2) insert fresh history
        session.execute(insert(elo_history), records)
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    # 1) load all matches from the DB
    session = SessionLocal()
    rows = session.execute(select(matches)).mappings().all()
    session.close()

    df = pd.DataFrame(rows)

    # 2) compute ELOs & build history
    _, history = update_elos(df)

    # 3) flatten history into a list of dicts
    hist_records: List[Dict[str, Any]] = []
    for recs in history.values():
        hist_records.extend(recs)

    # 4) truncate & reload the elo_history table
    refresh_elo_history(hist_records)

    print(f"[INFO] Replaced elo_history with {len(hist_records)} rows.")
