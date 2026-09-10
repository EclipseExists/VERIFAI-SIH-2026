# VERIFAI Backend Dockerfile
# ============================

# ── Base Image ────────────────────────────────────────────────────
FROM python:3.12-slim

# ── Install System Libraries ─────────────────────────────────────
# Required by OpenCV / DeepFace
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Set Working Directory ─────────────────────────────────────────
WORKDIR /app
ENV PYTHONPATH=/app/backend

# ── Install Python Dependencies ───────────────────────────────────
COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --no-cache-dir -r backend/requirements.txt

# ── Copy Entire Project ────────────────────────────────────────────
# This includes backend/, ai/, data/, etc.
COPY . .

# ── Create Uploads Directory ──────────────────────────────────────
RUN mkdir -p backend/uploads

# ── Expose Port ───────────────────────────────────────────────────
EXPOSE 8000

# ── Start FastAPI Server ──────────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]