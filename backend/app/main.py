from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ecg, patients, predictions, auth
from app.config import settings

app = FastAPI(
    title="CardioAI – Cardiovascular Diagnostics Platform",
    description="Real-time ECG analysis and AI-driven cardiovascular risk prediction for clinicians.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/auth",        tags=["auth"])
app.include_router(patients.router,    prefix="/api/patients",    tags=["patients"])
app.include_router(ecg.router,         prefix="/api/ecg",         tags=["ecg"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])


@app.get("/")
def root():
    return {"service": "CardioAI API", "version": "1.0.0", "status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
