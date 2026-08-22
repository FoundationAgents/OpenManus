FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright

RUN apt-get update && apt-get install -y
RUN pip install playwright
RUN playwright install --with-deps chromium

WORKDIR /app/OpenManus

RUN apt-get update && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/* \
    && (command -v uv >/dev/null 2>&1 || pip install --no-cache-dir uv)

COPY requirements.txt .

RUN uv pip install --system -r requirements.txt

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y xvfb
RUN apt-get install -qqy x11-apps

RUN apt-get install -y libnss3 \
    libxss1 \
    libasound2 \
    fonts-noto-color-emoji xauth

COPY . .

ENTRYPOINT ["/bin/sh", "-c", "/usr/bin/xvfb-run -a $@", ""]

CMD ["python3", "/app/OpenManus/main.py"]
