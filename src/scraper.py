# src/scraper.py

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy import select, insert, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.db import engine, SessionLocal, metadata
from src.models import matches_raw as matches

# Ensure schemas exist before creating tables
if engine.dialect.name.startswith("postg"):
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS silver"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold"))


# Now create tables in their schemas
metadata.create_all(engine)

BASE_URL = "https://www.cagematch.net/?id=8&nr=1&page=8"


def extract_match_time(text: str) -> Optional[str]:
    m = re.search(r'\((\d{1,2}:\d{2})\)(?:\s+-\s+TITLE CHANGE !!!)?', text)
    return m.group(1) if m else None


def determine_finish(text: str) -> str:
    low = text.lower()
    if "referee's decision" in low:
        return "Referee's Decision"
    if 'by dq' in low:
        return 'DQ'
    if 'by count out' in low or 'by countout' in low:
        return 'Countout'
    if 'by submission' in low:
        return 'Submission'
    if 'by no contest' in low:
        return 'No Contest'
    if 'double count out' in low:
        return 'Double Count Out'
    return 'Pinfall'


def detect_title_change(text: str) -> bool:
    return 'TITLE CHANGE !!!' in text


def replace_and_symbols(name: str) -> str:
    name = name.replace(" & ", ", ")
    name = name.replace(" and ", ", ")
    return name.strip(", ")


def parse_header(header_text: str) -> Dict[str, Optional[str]]:
    date_match = re.search(r'\((\d{2}\.\d{2}\.\d{4})\)', header_text)
    if date_match:
        # parse into a real date object
        dt: datetime.date = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
        return {'Date': dt}
    return {'Date': None}


def detect_ple(show: Optional[str]) -> bool:
    """
    True if the show name contains 'Premium Live Event', else False.
    """
    return bool(show and 'premium live event' in show.lower())


def scrape_matches() -> pd.DataFrame:
    records: List[Dict] = []

    for offset in range(0, 1000, 100):
        url = f"{BASE_URL}&s={offset}" if offset else BASE_URL
        print(url)
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"  → Failed to fetch: {resp.status_code}")
            continue

        soup = BeautifulSoup(resp.text, 'html.parser')
        for qr in soup.select('div.QuickResults'):
            header = qr.find('div', class_='QuickResultsHeader')
            if not header:
                continue
            header_txt = header.get_text(" ", strip=True)

            # Skip House Shows / LFG
            if re.search(r'\b(house show|lfg)\b', header_txt, re.IGNORECASE):
                continue

            info = parse_header(header_txt)
            show_el = header.find('a')
            show = show_el.get_text(strip=True) if show_el else None

            # Skip “WWE Speed” or “WWE Main Event”
            if show and re.match(r'(?i)^wwe speed\b', show):
                continue
            if show and re.match(r'(?i)^wwe main event\b', show):
                continue

            info['Show'] = show
            info['Premium Live Event'] = detect_ple(show)

            ul = header.find_next_sibling('ul')
            if not ul:
                continue

            for li in ul.find_all('li'):
                mt_el = li.find('span', class_='MatchType')
                mtype = mt_el.get_text(" ", strip=True).rstrip(':') if mt_el else None
                # Skip dark matches
                if mtype and re.search(r'\bdark\b', mtype, re.IGNORECASE):
                    continue

                mr_el = li.find('span', class_='MatchResults')
                if not mr_el:
                    continue
                full = mr_el.get_text(" ", strip=True)

                time    = extract_match_time(full)
                finish  = determine_finish(full)
                tchange = detect_title_change(full)

                parts = re.split(r' defeat[s]? ', full, maxsplit=1)
                if len(parts) != 2:
                    continue
                win_raw, loss_raw = parts
                
                # remove any “ by DQ”, “ by submission”, etc.
                loss_raw = re.sub(r'\s+by\s+\w+.*$', '', loss_raw, flags=re.IGNORECASE)

                # Strip championship flags, match times, managers, title change markers
                for patt in [r'\(c\)', r'\(\d{1,2}:\d{2}\)', r'\(w/.*?\)', r'- TITLE CHANGE !!!']:
                    win_raw  = re.sub(patt, '', win_raw)
                    loss_raw = re.sub(patt, '', loss_raw)

                winners = replace_and_symbols(win_raw).strip()
                losers  = replace_and_symbols(loss_raw).strip()

                records.append({
                    'Date':               info['Date'],
                    'Show':               info['Show'],
                    'Premium Live Event': info['Premium Live Event'],
                    'Match Type':         mtype,
                    'Winners':            winners,
                    'Losers':             losers,
                    'Time':               time,
                    'Finish':             finish,
                    'Title Change':       tchange,
                })

    return pd.DataFrame(records)


def split_tag_teams_from_columns(df: pd.DataFrame,
                                 winners_col: str = 'Winners',
                                 losers_col: str = 'Losers') -> pd.DataFrame:
    def split_tag_teams(value: str) -> str:
        if pd.isna(value):
            return value
        groups = re.findall(r'\(([^)]+)\)', value)
        if not groups:
            return value
        names: List[str] = []
        for grp in groups:
            names += [n.strip() for n in grp.split(',')]
        return ', '.join(names)

    df[winners_col] = df[winners_col].apply(split_tag_teams)
    df[losers_col]  = df[losers_col].apply(split_tag_teams)
    return df


def clean_column(value: str) -> str:
    if pd.isna(value):
        return value
    value = re.sub(r'\[.*?\]', '', value)      # remove [notes]
    value = re.sub(r'\s*-\s*$', '', value)     # trailing dash
    return value.strip()


def is_multi_man(row: pd.Series) -> bool:
    """
    True for multi-man matches (keyword in match type or uneven sides).
    """
    mt      = str(row['Match Type'] or '').lower()
    winners = [w.strip() for w in str(row['Winners']).split(',') if w.strip()]
    losers  = [l.strip() for l in str(row['Losers']).split(',')  if l.strip()]
    if any(kw in mt for kw in ['fatal four way','triple threat','gauntlet','battle royal','ten man']):
        return True
    return len(winners) == 1 and len(losers) > 1


def detect_stipulation(mtype: str) -> bool:
    """
    True if match type contains any stipulation keyword (but not 'qualifying').
    """
    mt = str(mtype or '').lower()
    if 'qualifying' in mt:
        return False
    return any(
        kw in mt for kw in [
            'hardcore','casket','ambulance','anything goes','sudden death',
            'tables','devil\'s playground','ladder','chair','chairs','bull rope',
            'strap','kendo stick','singapore cane','steel cage','no holds barred',
            'hell in a cell','street fight','falls count anywhere','last man standing',
            'i quit','submission','buried alive','inferno','punjabi prison',
            'blindfold','lumberjack','tribal combat','second city strap',
            'elimination chamber','tower of doom','beat the clock','three stages of hell',
            'survivors match','iron man','texas death','extreme rules',
            'best two out of three falls','death','double dog collar','pure rules',
            'new japan rambo','wargames','barbed wire board'
        ]
    )


def classify_match_type(mtype: str) -> Optional[str]:
    mt = str(mtype).lower()
    if ('#1 contendership' in mt and 'final' in mt) or ('#1 contendership' in mt and 'tournament' not in mt):
        return '#1 Contendership'
    if 'title' in mt and not any(kw in mt for kw in ['semi final','tournament first round']):
        return 'Title'
    if 'battle royal' in mt:
        return 'Battle Royal'
    return None

def refresh_matches(records: List[Dict]) -> None:
    """
    Insert only those records whose (date,show,match_type,winners,losers)
    combo is not already present.
    """
    session = SessionLocal()
    try:
        # 1) load existing natural keys
        existing = session.execute(
            select(
                matches.c.date,
                matches.c.show,
                matches.c.match_type,
                matches.c.winners,
                matches.c.losers,
            )
        ).all()

        # debug: show how many existing and a few samples
        print(f"[DEBUG] {len(existing)} existing match keys in DB")
        for ex in existing[:5]:
            print("       EX:", ex)

        if not existing:
            # table is empty → initial load
            session.execute(insert(matches), records)
            session.commit()
            print(f"[INFO] Initial load: inserted {len(records)} matches")
            return

        seen = set(existing)  # set of 5‑tuples
        print(f"[DEBUG] First 5 seen keys: {list(seen)[:5]}")

        # 2) filter out any you’ve already got
        new_recs = []
        for r in records:
            key = (
                r['date'],
                r['show'],
                r['match_type'],
                r['winners'],
                r['losers']
            )
            if key not in seen:
                new_recs.append(r)
            else:
                print("   SKIP:", key)

        # 3) bulk‑insert only the truly new ones
        if new_recs:
            print(
                "[DEBUG] Inserting",
                len(new_recs),
                "new keys; sample:",
                [(r['date'], r['show']) for r in new_recs[:3]]
            )
            session.execute(insert(matches), new_recs)
            session.commit()
            print(f"[INFO] Inserted {len(new_recs)} new matches")
        else:
            print("[INFO] No new matches to insert")

    finally:
        session.close()



if __name__ == "__main__":
    # 1. Scrape into DataFrame
    df = scrape_matches()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date


    # 2. Clean & derive
    df = split_tag_teams_from_columns(df)
    df['Winners']       = df['Winners'].apply(clean_column)
    df['Losers']        = df['Losers'].apply(clean_column)
    df['Multi-Man']     = df.apply(is_multi_man, axis=1)
    df['Stipulation']   = df['Match Type'].apply(detect_stipulation)
    df['Category']      = df['Match Type'].apply(classify_match_type)
    mask = df['Match Type'].str.contains('tornado tag', case=False, na=False)
    df.loc[mask, 'Multi-Man'] = False


    # 3. Rename to match your SQLAlchemy columns
    df_db = df.rename(columns={
        'Date':               'date',
        'Show':               'show',
        'Premium Live Event': 'ple',
        'Match Type':         'match_type',
        'Winners':            'winners',
        'Losers':             'losers',
        'Time':               'time',
        'Finish':             'finish',
        'Title Change':       'title_change',
        'Multi-Man':          'multi_man',
        'Stipulation':        'stipulation',
        'Category':           'category',
    })

    records = df_db.to_dict(orient="records")
    refresh_matches(records)
    



   
