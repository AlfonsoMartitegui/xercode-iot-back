FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY mqtt_router ./mqtt_router

CMD ["python", "-m", "mqtt_router.main"]