# src/scraper.py

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
from typing import Optional, List, Dict

BASE_URL = "https://www.cagematch.net/?id=8&nr=1&page=8"


def extract_match_time(text: str) -> Optional[str]:
    """
    Extract MM:SS from within parentheses, ignoring TITLE CHANGE markers.
    """
    m = re.search(r'\((\d{1,2}:\d{2})\)(?:\s+-\s+TITLE CHANGE !!!)?', text)
    return m.group(1) if m else None


def determine_finish(text: str) -> str:
    """
    Infer finish type from the text.
    """
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
    """
    Return True if the text contains 'TITLE CHANGE !!!'.
    """
    return 'TITLE CHANGE !!!' in text


def replace_and_symbols(name: str) -> str:
    """
    Normalize team delimiters: replace ' & ' and ' and ' with ', '.
    """
    name = name.replace(" & ", ", ")
    name = name.replace(" and ", ", ")
    return name.strip(", ")


def parse_header(header_text: str) -> Dict[str, str]:
    """
    From the QuickResultsHeader text, extract the date (ISO format).
    """
    date_match = re.search(r'\((\d{2}\.\d{2}\.\d{4})\)', header_text)
    date_iso = None
    if date_match:
        dt = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
        date_iso = dt.isoformat()
    return {'Date': date_iso}


def detect_ple(show: Optional[str]) -> Optional[str]:
    """
    Mark 'Y' if 'Premium Live Event' appears in the show name.
    """
    if not show:
        return None
    return 'Y' if 'premium live event' in show.lower() else None


def scrape_matches() -> pd.DataFrame:
    """
    Crawl cagematch listing pages and return a DataFrame of match data,
    including Date, Show, Premium Live Event flag, and match details.
    """
    records: List[Dict] = []

    for offset in range(0, 300, 100):
        url = f"{BASE_URL}&s={offset}" if offset else BASE_URL
        print(f"Scraping URL: {url}")
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

            # skip house shows / LFG
            if re.search(r'\b(house show|lfg)\b', header_txt, re.IGNORECASE):
                continue

            # extract date
            info = parse_header(header_txt)

            # parse show name
            show_el = header.find('a')
            show = show_el.get_text(strip=True) if show_el else None

            # skip non-PPV brand specials by name
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
                # match type
                mt_el = li.find('span', class_='MatchType')
                mtype = mt_el.get_text(" ", strip=True).rstrip(':') if mt_el else None
                if mtype and re.search(r'\bdark\b', mtype, re.IGNORECASE):
                    continue

                # results
                mr_el = li.find('span', class_='MatchResults')
                if not mr_el:
                    continue
                full = mr_el.get_text(" ", strip=True)

                time = extract_match_time(full)
                finish = determine_finish(full)

                title_change = detect_title_change(full)

                parts = re.split(r' defeat[s]? ', full, maxsplit=1)
                if len(parts) != 2:
                    continue
                win_raw, loss_raw = parts

                # strip flags, times, managers, title-change
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
                    'Title Change':       title_change,
                })

    return pd.DataFrame(records)


def split_tag_teams_from_columns(df: pd.DataFrame,
                                 winners_col: str = 'Winners',
                                 losers_col: str = 'Losers') -> pd.DataFrame:
    """
    Expand any "(A, B)" into "A, B" for tag teams.
    """
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
    """
    Remove bracketed notes like [2:0], [Runde 3], trailing dashes, and extra whitespace.
    """
    if pd.isna(value):
        return value
    value = re.sub(r'\[.*?\]', '', value)
    value = re.sub(r'\s*-\s*$', '', value)
    return value.strip()


def is_multi_man(row: pd.Series) -> Optional[str]:
    """
    Label 'Y' for matches with multi-competitor keywords or uneven sides.
    """
    mt = str(row['Match Type']).lower()
    winners = str(row['Winners']).split(',')
    losers  = str(row['Losers']).split(',')
    if any(kw in mt for kw in ['fatal four way', 'triple threat', 'gauntlet', 'battle royal', 'ten man']):
        return 'Y'
    if len(winners) == 1 and len(losers) > 1:
        return 'Y'
    return None


stipulation_keywords = [
    'hardcore', 'casket', 'ambulance', 'anything goes', 'sudden death',
    'tables', 'devil\'s playground', 'ladder', 'chair', 'chairs', 'bull rope',
    'strap', 'kendo stick', 'singapore cane', 'steel cage', 'no holds barred',
    'hell in a cell', 'street fight', 'falls count anywhere', 'last man standing',
    'i quit', 'submission', 'buried alive', 'inferno', 'punjabi prison',
    'blindfold', 'lumberjack', 'tribal combat', 'second city strap',
    'elimination chamber', 'tower of doom', 'beat the clock', 'three stages of hell',
    'survivors match', 'iron man', 'texas death', 'extreme rules',
    'best two out of three falls', 'death', 'double dog collar', 'pure rules',
    'new japan rambo', 'wargames', 'barbed wire board'
]


def detect_stipulation(mtype: str) -> Optional[str]:
    """
    Label 'Y' if match type contains any stipulation keyword,
    but exclude any that contain 'qualifying'.
    """
    mt = str(mtype).lower()
    if 'qualifying' in mt:
        return None
    return 'Y' if any(kw in mt for kw in stipulation_keywords) else None


def classify_match_type(mtype: str) -> Optional[str]:
    """
    Classify into #1 Contendership, Title, Battle Royal or None.
    """
    mt = str(mtype).lower()
    if ('#1 contendership' in mt and 'final' in mt) or ('#1 contendership' in mt and 'tournament' not in mt):
        return '#1 Contendership'
    if 'title' in mt and not any(kw in mt for kw in ['semi final', 'tournament first round']):
        return 'Title'
    if 'battle royal' in mt:
        return 'Battle Royal'
    return None


if __name__ == "__main__":
    df = scrape_matches()

    # split tag teams into individuals
    df = split_tag_teams_from_columns(df)

    # clean up Winners/Losers text
    df['Winners'] = df['Winners'].apply(clean_column)
    df['Losers']  = df['Losers'].apply(clean_column)

    # add derived columns
    df['Multi-Man']   = df.apply(is_multi_man, axis=1)
    df['Stipulation'] = df['Match Type'].apply(detect_stipulation)
    df['Category']    = df['Match Type'].apply(classify_match_type)

    # exclude tornado tag from Multi-Man
    mask = df['Match Type'].str.contains('tornado tag', case=False, na=False)
    df.loc[mask, 'Multi-Man'] = None

    # save to CSV
    df.to_csv("matches.csv", index=False)
    print(f"[INFO] Saved {len(df)} matches to matches.csv")
