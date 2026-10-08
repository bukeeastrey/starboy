# One small container: FastAPI serves the API and the built React app.
# No AI model is inside it. With AI_MODE=cloud, Gemma 4 answers through the
# Gemini API and Whisper through Groq, so it fits a 512 MB free server.

# --- Stage 1: build the React app ---
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: the Python app ---
FROM python:3.12-slim

# Don't run as root.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=user backend/ backend/
COPY --chown=user --from=frontend /frontend/dist frontend/dist

ENV AI_MODE=cloud PYTHONUNBUFFERED=1

# Render tells the app which port to use through $PORT (10000 by default).
EXPOSE 10000
WORKDIR /home/user/app/backend
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
