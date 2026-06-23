# ---------------------------------------------------------------------------
# GBT AI Workstation — multi-stage Docker build
# Inspired by https://github.com/paysssk-creator/openhuman
# Produces a minimal image running the GBT headless Web API on :8765.
#
# Build:   docker build -t gbt-ai-workstation .
# Run:     docker run -p 8765:8765 --env-file .env gbt-ai-workstation
# ---------------------------------------------------------------------------

# ==========================================================================
# Stage 1: Build Python dependencies
# ==========================================================================
FROM python:3.12-slim-bookworm AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System dependencies required for compilation (screen capture / audio / crypto).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Cache dependencies — copy only manifests first
COPY requirements.txt pyproject.toml setup.py ./
RUN pip install --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# ==========================================================================
# Stage 2: Minimal runtime image
# ==========================================================================
FROM python:3.12-slim-bookworm AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GBT_DOCKER=1 \
    PATH=/root/.local/bin:$PATH

# Runtime libraries for GUI headless operation (Xvfb + display capture)
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY gbt ./gbt
COPY agents ./agents
COPY tools ./tools
COPY desktop ./desktop
COPY entry.py ./entry.py
COPY main.py ./main.py
COPY README.md ./README.md

# Ensure dashboard.html is included
COPY gbt/dashboard.html ./gbt/dashboard.html

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8765/api/health || exit 1

CMD ["python", "-m", "gbt.web_api"]
