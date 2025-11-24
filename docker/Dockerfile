# ============================================
# AIVideoMaker Professional - Dockerfile
# ============================================
# Multi-stage build per ottimizzare dimensione immagine

FROM python:3.11-slim as base

# Installa dipendenze sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Copia requirements e installa dipendenze Python
COPY requirements_new.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia codice applicazione
COPY . .

# Crea directory necessarie
RUN mkdir -p uploads outputs temp logs

# Esponi porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Command default
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
