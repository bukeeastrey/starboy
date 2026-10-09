"""Runs before every test. It makes the tests safe to run anywhere:

- the database is "starboy_test", never the real one;
- the Telegram bot is off, so no test can message a real person;
- the AI mode is "cloud" with no keys, so nothing tries to load Gemma here.
"""

from app.config import settings

settings.mongodb_db = "starboy_test"
settings.telegram_mode = "off"
settings.ai_mode = "cloud"
settings.gemini_api_key = ""
settings.groq_api_key = ""
settings.public_base_url = ""
