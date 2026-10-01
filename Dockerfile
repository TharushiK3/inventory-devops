FROM python:3.13-slim

# Configure Python and the application inside the container.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=5000 \
    DATABASE_PATH=/app/instance/inventory.db

WORKDIR /app

# Install application dependencies without testing packages.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create an unprivileged application user and writable database folder.
RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid appuser --create-home appuser \
    && mkdir -p /app/instance \
    && chown appuser:appuser /app/instance

COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser run.py .

USER appuser

EXPOSE 5000

# A failed HTTP request makes the health check fail.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3).close()"]

CMD ["python", "run.py"]