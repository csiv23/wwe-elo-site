# pipeline.py

import os
from src import scraper, elo, storage

def main():
    # 1. Scrape every match
    matches = scraper.fetch_all_matches()

    # 2. Load existing ELOs or start fresh
    elos_path = "elos.csv"
    if os.path.exists(elos_path):
        previous_elos = storage.load_elos_from_csv(elos_path)
    else:
        previous_elos = {}

    # 3. Compute new ELOs
    updated_elos = elo.update_elos(matches, previous_elos)

    # 4. Persist back to CSV
    storage.save_elos_to_csv(updated_elos, elos_path)
    print(f"Saved {len(updated_elos)} ratings to {elos_path}")

if __name__ == "__main__":
    main()
