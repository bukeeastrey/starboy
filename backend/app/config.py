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
    # How long Ollama keeps Gemma in memory after an answer: "30m", or "-1"
    # for always (used on the server, which has enough RAM: no cold starts).
    ollama_keep_alive: str = "30m"

    # Telegram bot (reminders, invites, voice notes). Empty token = bot is off.
    telegram_bot_token: str = ""
    # "polling" (laptop: the app asks Telegram for news), "webhook" (deployed:
    # Telegram calls us) or "off". Empty = webhook when PUBLIC_BASE_URL is set,
    # otherwise polling.
    telegram_mode: str = ""
    # Telegram sends this back with every webhook call, so we know it's Telegram.
    telegram_webhook_secret: str = ""

    # Protects /api/cron/tick (the free cron ping that keeps reminders going).
    cron_token: str = ""

    @property
    def bot_mode(self) -> str:
        """Which way the bot runs: "polling", "webhook" or "off"."""
        if not self.telegram_bot_token:
            return "off"
        if self.telegram_mode:
            return self.telegram_mode
        return "webhook" if self.public_base_url else "polling"


settings = Settings()
