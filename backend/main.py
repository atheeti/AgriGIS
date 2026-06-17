from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from database import engine, Base
import models  # noqa: F401 — registers ORM models with Base

http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    Base.metadata.create_all(bind=engine)
    http_client = httpx.AsyncClient(timeout=90.0)
    yield
    await http_client.aclose()


app = FastAPI(
    title="AgriGIS API",
    description="Crop Health Assessment via Satellite Indices",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes.farmer import router as farmer_router
from routes.indices import router as indices_router

app.include_router(farmer_router, prefix="/api/farmers", tags=["Farmers"])
app.include_router(indices_router, prefix="/api/indices", tags=["Indices"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AgriGIS"}


# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
