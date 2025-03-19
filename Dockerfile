FROM python:3.9-bullseye

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libwoff1 \
    libopus0 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libenchant-2-2 \
    libsecret-1-0 \
    libhyphen0 \
    libgles2 \
    libegl1 \
    libevent-2.1-7 \
    libvpx6 \
    libxcomposite1 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libnotify4 \
    libnspr4 \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    && rm -rf /var/lib/apt/lists/*

# Continue with your application setup...

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install  # Install Playwright browsers

# Copy application code
COPY . /app
WORKDIR /app

# Run the API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
