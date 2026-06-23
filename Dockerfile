# ---------------------------------------------------------------------------
# GBT AI Workstation — Docker image
# Runs the headless Web API + unified AI routing on :8765.
# Build:   docker build -t gbt-ai-workstation .
# Run:     docker run -p 8765:8765 --env-file .env gbt-ai-workstation
# ---------------------------------------------------------------------------

FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GBT_DOCKER=1

# Runtime libraries for headless GUI libs (Pillow/pyautogui) and audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libx11-6 \
    libxtst6 \
    libxinerama1 \
    libxcursor1 \
    libxi6 \
    ca-certificates \
    curl \
    ffmpeg \
    xvfb \
    xauth \
    python3-tk \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifest and install
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy full application including vendored submodules
COPY . .

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8765/api/health || exit 1

CMD xvfb-run -a -s "-screen 0 1920x1080x24" python entry.py
