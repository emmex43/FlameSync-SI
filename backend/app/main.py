from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 1. Import your API routers properly (no "backend" prefix)
from app.api.investigations import router as investigations_router
from app.api.predictions import router as predictions_router
from app.api.rankings import router as rankings_router
from app.api.assistant import router as assistant_router

app = FastAPI(
    title="FlameSync API",
    description="SI-powered Fire safety insights from microgravity combustion data",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthResponse(BaseModel):
    status: str
    message: str

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return {"status": "ok", "message": "FlameSync API is running and ready."}

# 2. Register the routers with the main application
app.include_router(investigations_router)
app.include_router(predictions_router)
app.include_router(rankings_router)
app.include_router(assistant_router)