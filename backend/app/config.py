"""Settings for Star Boy. Every value comes from an environment variable,
or from the ".env" file in the project root (which is never committed)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> the project root is two folders up from "app".
ROOT_DIR = Path(__file__).resolve().parents[2]

# Where "npm run build" puts the finished React app.
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

# Voice notes wait here for a few seconds, until they are transcribed and deleted.
AUDIO_DIR = ROOT_DIR / "backend" / "data" / "audio"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    # MongoDB Atlas connection string. Empty = the app still starts, but the
    # health check reports that the database is not set up yet.
    mongodb_uri: str = ""
    mongodb_db: str = "starboy"

    # Optional: DNS servers for finding the Atlas cluster, e.g. "8.8.8.8,1.1.1.1".
    # Some phone hotspots and routers can't answer the lookup that a
    # "mongodb+srv://" address needs. Leave empty to use the computer's own DNS.
    dns_servers: str = ""

    # Signs the sign-in cookie. Empty = a random one is made at every start,
    # which signs everybody out whenever the server restarts.
    session_secret: str = ""

    # The public address of the app, e.g. "https://<user>-starboy.hf.space".
    # Empty while developing on the laptop.
    public_base_url: str = ""

    # The open models (both run on this machine's CPU).
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma4:e2b-it-qat"
    whisper_model: str = "small"


settings = Settings()
