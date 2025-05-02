````markdown
# WWE Elo Tracker

**ETL pipeline** that scrapes WWE match results, computes Elo ratings, and stores data in Postgres. Docker-Compose–ready.

---

## 🚀 Features

- **scraper**: fetches “Quick Results” → normalizes → writes to `matches` table  
- **elo**: reads `matches` → computes per-wrestler Elo → writes to `elo_history` table  
- **Postgres** backend (via Docker Compose)

---

## 🏃 Quickstart

1. **Clone** this repo and create a `.env` in the project root:

   ```env
   DATABASE_URL=postgresql://user:pass@db:5432/wwe
````

2. **Launch services**:

   ```bash
   docker-compose up --build -d db
   docker-compose run --rm scraper
   docker-compose run --rm elo
   ```

3. **Verify** data with any SQL client at `localhost:5432`.

---

## 📂 Project Layout

```
.
├─ docker-compose.yml
├─ requirements.txt
└─ src/
   ├─ Dockerfile.scraper
   ├─ Dockerfile.elo
   ├─ db.py
   ├─ models.py
   ├─ scraper.py
   └─ elo.py
```

---

## 🔜 Next Steps

* Add DB migrations (Alembic)
* Implement service-readiness & retry logic
* Expose a REST API (FastAPI or Flask)
* Set up CI/CD (tests, linting)

```
```
