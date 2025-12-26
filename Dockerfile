# Estágio 1: Builder
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala ferramentas apenas para compilar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock* ./
# Instalamos no diretório /install em vez do sistema para copiar limpo
RUN uv pip install --system --no-cache -r pyproject.toml

# Estágio 2: Final (O mais leve possível)
FROM python:3.11-slim

WORKDIR /app

# Copia apenas o que é estritamente necessário do builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia o código (Filtrado pelo seu .dockerignore)
COPY . .

# Limpa arquivos temporários do Python que podem ter vindo na cópia
RUN find . -type d -name "__pycache__" -exec rm -rf {} +

ENV USE_DB=False
ENV DATABASE_URL=sqlite:///./public.db
ENV PORT=8080
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Instala apenas o gunicorn e limpa o cache do pip imediatamente
RUN pip install --no-cache-dir gunicorn && \
    rm -rf ~/.cache/pip

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "120", "app:app"]