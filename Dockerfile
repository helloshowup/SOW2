FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir \
    fastapi uvicorn sqlmodel psycopg2-binary \
    apscheduler httpx python-dotenv structlog \
    redis rq requests beautifulsoup4 openai pyyaml

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
