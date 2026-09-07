# VERIFAI Backend Dockerfile
# ============================
#
# WHAT IS A DOCKERFILE:
# A recipe that tells Docker how to build a container image.
# Think of it as: "here's how to set up a fresh computer to run our app."
#
# WHY DOCKER:
# - Everyone on the team gets the exact same environment
# - "Works on my machine" problems disappear
# - Easy to deploy anywhere (demo laptop, cloud, etc.)
#
# HOW TO BUILD AND RUN:
#   docker build -t verifai-backend .
#   docker run -p 8000:8000 verifai-backend
#
# But you'll usually use docker-compose instead (see docker-compose.yml)

# ── Base Image ────────────────────────────────────────────────────
# python:3.12-slim is a minimal Python image (smaller = faster builds)
# We use 3.12 instead of 3.14 because some packages don't have
# pre-built wheels for 3.14 yet (would require compiling from source)
FROM python:3.12-slim

# ── Set Working Directory ─────────────────────────────────────────
# All subsequent commands run from /app inside the container
WORKDIR /app

# ── Install Dependencies First ────────────────────────────────────
# We copy requirements.txt BEFORE the rest of the code because:
# Docker caches each layer. If requirements.txt hasn't changed,
# Docker reuses the cached pip install (saves minutes on rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy Application Code ────────────────────────────────────────
COPY . .

# ── Create uploads directory ─────────────────────────────────────
RUN mkdir -p uploads

# ── Expose Port ───────────────────────────────────────────────────
# Documents that the container listens on port 8000
# (doesn't actually open the port — that happens at runtime)
EXPOSE 8000

# ── Start Command ─────────────────────────────────────────────────
# uvicorn runs the FastAPI app
# --host 0.0.0.0 means "listen on all network interfaces" (required in Docker)
# --port 8000 is the standard dev port
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

