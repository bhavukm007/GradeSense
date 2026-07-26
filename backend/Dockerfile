FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PIP_RESUME_RETRIES=10

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends --yes libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system gradesense && adduser --system --ingroup gradesense gradesense

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --upgrade pip && pip install .

RUN mkdir -p /app/runtime/data /app/runtime/models && chown -R gradesense:gradesense /app/runtime

USER gradesense

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
