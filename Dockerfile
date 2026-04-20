# =============================================================================
# Dockerfile
# =============================================================================
# Multi-stage build for the Telegram bot.
#
# Stages:
#   builder  — installs Python dependencies into a virtual environment.
#   runtime  — copies only the venv and application code; no build tools.
#
# Why multi-stage?
#   The builder stage needs pip and potentially gcc (for packages with C
#   extensions). The runtime stage needs neither. Keeping them separate
#   produces a significantly smaller final image with a reduced attack surface.
#
# Usage:
#   Build:  docker build -t tg-bot .
#   Run:    docker compose up -d          (recommended — handles env vars)
#           docker run --env-file .env tg-bot   (manual alternative)
# =============================================================================


# -----------------------------------------------------------------------------
# Stage 1 — builder
# Installs all Python dependencies into /opt/venv.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# PYTHONDONTWRITEBYTECODE: prevents Python from writing .pyc files to disk.
# PYTHONUNBUFFERED: forces stdout/stderr to be unbuffered so log lines appear
#   in `docker logs` immediately instead of being held in a buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Copy dependency specification first.
# Docker caches each layer separately. Copying requirements before the source
# code means the dependency installation layer is only re-run when the
# requirements file changes — not on every code change. This makes rebuilds
# after small code edits very fast.
COPY requirements.txt .

# Create an isolated virtual environment inside the image.
# Installing into a venv (rather than the system Python) makes it trivial
# to copy just the dependencies to the runtime stage.
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip --no-cache-dir && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# -----------------------------------------------------------------------------
# Stage 2 — runtime
# Lean final image: only the venv and application code.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Add the venv to PATH so `python` and all installed commands resolve
# to the venv without needing to activate it explicitly.
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Create a non-root user and group.
# Running as root inside a container is unnecessary and increases risk.
# If the application were compromised, an attacker would have root access
# inside the container. A dedicated user limits that exposure.
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy the virtual environment from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Copy the application source code.
# Only the files needed at runtime are copied — see .dockerignore for what
# is excluded (tests, .git, .env, __pycache__, etc.).
COPY --chown=appuser:appgroup . .

# Switch to the non-root user for all subsequent commands, including the
# process started by CMD.
USER appuser

# The bot runs as a long-lived process started by main.py.
# Using `python -u` in addition to PYTHONUNBUFFERED=1 is belt-and-suspenders
# for ensuring unbuffered output.
CMD ["python", "-u", "main.py"]