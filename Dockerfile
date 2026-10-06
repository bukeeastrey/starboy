# One container: FastAPI serves the API and the built React app.
# (Ollama + the Gemma model are added to this image in the deploy milestone.)

# --- Stage 1: build the React app ---
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: the Python app ---
FROM python:3.12-slim

# ffmpeg converts phone voice notes (webm / mp4) for Whisper.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces run the container as user 1000, not root.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=user backend/ backend/
COPY --chown=user --from=frontend /frontend/dist frontend/dist

# Hugging Face Spaces expect the app on port 7860.
EXPOSE 7860
WORKDIR /home/user/app/backend
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
