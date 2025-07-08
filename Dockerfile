FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --default-timeout=500 --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
