# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import ingest
import os

def create_app() -> FastAPI:
    app = FastAPI(
        title="DoxaSense-MIND Extraction",
        version="0.1.0",
    )

    # CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify your frontend domain
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ingest.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
