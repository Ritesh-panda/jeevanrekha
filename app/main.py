# File: app/main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1 import chat_routes, process_routes, admin_routes

# Ensure static directories exist (critical for Docker containers)
os.makedirs("app/static/audio", exist_ok=True)

app = FastAPI(
    title="JeevanRekha AI",
    description="Intelligent Health Protocol — Centralized Orchestration for Voice & WhatsApp.",
    version="2.0.0"
)

# --- CORS Middleware ---
# Allows the React Voice Frontend to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your deployed frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static Files ---
# Serves the generated audio files for WhatsApp voice notes.
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", tags=["Health Check"])
def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to JeevanRekha AI API v2.0!"}

# --- WhatsApp Channel (Twilio Webhook) ---
app.include_router(chat_routes.router, prefix="/api/v1", tags=["WhatsApp Channel"])

# --- Voice Channel (React Frontend JSON API) ---
app.include_router(process_routes.router, prefix="/api/v1", tags=["Voice Channel"])

# --- System Admin & Security Controls ---
app.include_router(admin_routes.router, prefix="/api/v1", tags=["System Admin & Security"])