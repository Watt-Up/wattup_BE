from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
import stations
import reservations

app = FastAPI(title="WattUp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stations.router, prefix="/api/wattup")
app.include_router(reservations.router, prefix="/api/wattup")


@app.get("/health")
def health():
    return {"status": "ok"}