# src/elo.py

import pandas as pd
from typing import Dict, List, Any, Tuple, Optional

DEFAULT_ELO = 1000
K_FACTOR = 32


def calculate_elo_gain(player_elo: float,
                       opponent_avg_elo: float,
                       k: float = K_FACTOR) -> float:
    """
    Compute the ELO change for a player given their current ELO and the
    average ELO of their opponents. Positive k for winners, negative k for losers.
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
        df: DataFrame with columns ['Match Type','Winners','Losers',...].
        initial_elos: optional starting ELOs; defaults to 1000 for new wrestlers.

    Returns:
        elo_ratings: final ELO ratings dict {wrestler: elo}.
        history: per-wrestler list of match records.
    """
    elo_ratings = initial_elos.copy() if initial_elos else {}
    history: Dict[str, List[Dict[str, Any]]] = {}

    # assume df is newest→oldest, so reverse to process oldest first
    for _, row in df.iloc[::-1].iterrows():
        winners = [w.strip() for w in str(row['Winners']).split(',') if w.strip()]
        losers  = [l.strip() for l in str(row['Losers']).split(',')  if l.strip()]

        # average ELO of losers
        loser_elos = [elo_ratings.get(l, DEFAULT_ELO) for l in losers] or [DEFAULT_ELO]
        avg_loser_elo = sum(loser_elos) / len(loser_elos)

        # winners gain
        for w in winners:
            before = elo_ratings.get(w, DEFAULT_ELO)
            gain = calculate_elo_gain(before, avg_loser_elo, k=K_FACTOR)
            after = before + gain
            elo_ratings[w] = after
            history.setdefault(w, []).append({
                'Match Type': row.get('Match Type'),
                'Opponents':   ', '.join(losers),
                'ELO Before':  before,
                'ELO Change':  gain,
                'ELO After':   after,
                'Result':      'Win'
            })

        # average ELO of winners (after update)
        winner_elos = [elo_ratings.get(w, DEFAULT_ELO) for w in winners] or [DEFAULT_ELO]
        avg_winner_elo = sum(winner_elos) / len(winner_elos)

        # losers lose (negative k)
        for l in losers:
            before = elo_ratings.get(l, DEFAULT_ELO)
            gain = calculate_elo_gain(before, avg_winner_elo, k=-K_FACTOR)
            after = before + gain
            elo_ratings[l] = after
            history.setdefault(l, []).append({
                'Match Type': row.get('Match Type'),
                'Opponents':   ', '.join(winners),
                'ELO Before':  before,
                'ELO Change':  gain,
                'ELO After':   after,
                'Result':      'Loss'
            })

    return elo_ratings, history


def load_matches(path: str = "matches.csv") -> pd.DataFrame:
    """
    Load the scraped matches CSV into a DataFrame.
    """
    return pd.read_csv(path)


def save_current_elos(elos: Dict[str, float], path: str = "elos.csv") -> None:
    """
    Persist the current ELO ratings to a CSV with columns ['Wrestler','ELO'].
    """
    df = pd.DataFrame(list(elos.items()), columns=['Wrestler', 'ELO'])
    df.to_csv(path, index=False)


def save_elo_history(history: Dict[str, List[Dict[str, Any]]],
                     path: str = "elo_history.csv") -> None:
    """
    Persist the full ELO history to CSV with columns:
    ['Wrestler','Match Type','Opponents','ELO Before','ELO Change','ELO After','Result'].
    """
    rows: List[Dict[str, Any]] = []
    for wrestler, recs in history.items():
        for rec in recs:
            row = {'Wrestler': wrestler}
            row.update(rec)
            rows.append(row)
    df_hist = pd.DataFrame(rows)
    df_hist.to_csv(path, index=False)


def get_elo_history(wrestler: str,
                    history: Dict[str, List[Dict[str, Any]]]
                   ) -> pd.DataFrame:
    """
    Return a DataFrame of the ELO history for a given wrestler.
    """
    if wrestler not in history:
        raise KeyError(f"No history found for '{wrestler}'")
    return pd.DataFrame(history[wrestler])


if __name__ == "__main__":
    # 1. Load matches
    df = load_matches("matches.csv")

    # 2. Compute ELOs and history
    elos, history = update_elos(df)

    # 3. Save full history
    save_elo_history(history, "elo_history.csv")
    print(f"[INFO] Saved full ELO history to elo_history.csv")
