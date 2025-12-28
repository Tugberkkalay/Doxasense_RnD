# app/main.py
from fastapi import FastAPI
from app.api import ingest
import os

def create_app() -> FastAPI:
    app = FastAPI(
        title="DoxaSense-MIND Extraction",
        version="0.1.0",
    )

    app.include_router(ingest.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
