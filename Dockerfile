FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install -U pip \
 && pip config set global.default-timeout 300 \
 && pip install --retries 10 --timeout 300 --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["python", "-m", "app.main"]