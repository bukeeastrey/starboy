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

## Run it with Docker

```powershell
docker build -t starboy .
docker run --rm -p 7860:7860 --env-file .env starboy
```

Open http://localhost:7860.
