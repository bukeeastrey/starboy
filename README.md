# Star Boy ⭐

**Star Boy gets people out of their rooms and onto the pitch.**

Every pickup football pitch becomes a small community: register at your pitch, set up a game, get reminded to show up, then tell Star Boy how it went with a voice note. Open models (Whisper for speech, Gemma for understanding) turn the voice note into stats, your teammates confirm them, and the pitch leaderboards update.

> Work in progress. Built for the DEV Hacktoberfest Open-Source AI Challenge ("Touch Grass").

## How it is built

- **Frontend:** React 18 + Vite, plain CSS (a phone-first PWA).
- **Backend:** FastAPI (Python), which also serves the built React app.
- **Database:** MongoDB Atlas (free M0 cluster), through the Motor async driver.
- **AI:** Gemma via Ollama and faster-whisper, both on CPU. No cloud AI APIs.

## Run it on Windows (PowerShell)

You need Python 3.12+, Node.js 20+ and a MongoDB Atlas connection string.

**1. Settings.** Copy `.env.example` to `.env` and paste your Atlas URI after `MONGODB_URI=`.

```powershell
Copy-Item .env.example .env
```

**2. Backend** (first time only: create the virtual environment and install).

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then start it (every time):

```powershell
.\run.ps1
```

The API is now at http://localhost:8000 (try http://localhost:8000/api/health).

**3. Frontend**, in a second PowerShell window.

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

You also need [Ollama](https://ollama.com) running with the Gemma model: `ollama pull gemma4:e2b-it-qat`.

## Telegram bot (reminders, invites, voice notes)

1. Create a bot with [@BotFather](https://t.me/BotFather) and put its token in `.env` as `TELEGRAM_BOT_TOKEN=`.
2. Start the backend. On a laptop the bot uses **polling**, so nothing needs to be public. The log says `Telegram bot is polling for messages.`
3. In the web app, tap **Connect Telegram 🔔** on the Home screen and press **Start** in Telegram.

Bot commands: `/next`, `/report`, `/leaderboard`, `/help`. After a game, send the bot a voice note.

When the app is deployed, switch the bot to **webhook** mode (only one mode works at a time):

```powershell
cd backend
python scripts/set_webhook.py https://<user>-starboy.hf.space   # deployed app receives messages
python scripts/set_webhook.py --delete                           # back to the laptop
python scripts/set_webhook.py --info                             # what is set now
```

## Reminders and the cron ping

A scheduler inside the app checks every minute and sends: the night-before reminder (8 pm Lagos), a nudge 6 hours before to players who haven't answered, a 2-hours-before reminder, and "How was your game? 🎙️" 15 minutes after the final whistle. If the server was asleep, anything due in the last 2 hours is still sent.

Free servers sleep when nobody visits. To keep reminders going, set `CRON_TOKEN` and let a free cron service (for example cron-job.org) call this every 10 minutes:

```
GET https://<your app>/api/cron/tick?token=<CRON_TOKEN>
```

## Demo data and tests

```powershell
cd backend
python scripts/seed.py        # one demo pitch, 10 players, 3 confirmed games
pip install -r requirements-dev.txt
python -m pytest              # consensus rules, number checks, pipelines, scheduler
```

Demo players sign in with phone `0800 000 0001` to `0800 000 0010`, PIN `1234`. The database tests use a separate database called `starboy_test`.

## How the AI is kept honest

- **Voice note to stats:** Whisper transcribes, Gemma extracts JSON, then code checks it: numbers must be 0 to 20, any number of 2 or more must appear in the transcript, the result and score must agree, and names must match players in that game. The audio file is deleted right after transcription.
- **Settle it and game summaries:** code computes every number from confirmed stats. Gemma only writes the sentences, and every number in its text must exist in the facts it was given. If not, it gets one retry, then a plain template is used.

## Run it with Docker

```powershell
docker build -t starboy .
docker run --rm -p 7860:7860 --env-file .env starboy
```

Open http://localhost:7860.
