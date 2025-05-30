from fastapi import FastAPI
from src.api.matches import router as matches_router

app = FastAPI(title="WWE Elo Tracker API")

# mount routers
app.include_router(matches_router)
