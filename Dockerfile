FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libopus0 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
