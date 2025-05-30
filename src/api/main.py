from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.matches import router as matches_router
from src.api.elo     import router as elo_router

app = FastAPI(title="WWE Elo Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_methods=["GET", "POST"],   
    allow_headers=["*"],
)

# mount routers
app.include_router(matches_router)
app.include_router(elo_router)