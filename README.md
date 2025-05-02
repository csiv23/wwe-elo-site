```markdown
# WWE Elo Tracker

Simple ETL that scrapes WWE matches from Cagematch, computes Elo ratings, and stores both in Postgres. Docker-Compose–ready.

## 🚀 Features
- **scraper**: fetches “Quick Results” → normalizes → loads into `matches`  
- **elo**: reads `matches` → computes per-wrestler Elo → loads into `elo_history`  
- **Postgres** backend (via Docker Compose)

## 🏃 Quickstart
1. **Clone** & add a `.env`:
```

DATABASE\_URL=postgresql://user\:pass\@db:5432/wwe

````
2. **Launch**:
```bash
docker-compose up --build -d db
docker-compose run --rm scraper
docker-compose run --rm elo
````

3. **Inspect** with any SQL client on `localhost:5432`.

## 📂 Layout

```
docker-compose.yml
requirements.txt
src/
  ├─ Dockerfile.scraper
  ├─ Dockerfile.elo
  ├─ db.py
  ├─ models.py
  ├─ scraper.py
  └─ elo.py
```

## 🔜 Next

* Add migrations (Alembic)
* Handle DB readiness & retries
* Build API (FastAPI/Flask)
* CI/CD for tests & linting

```
```
