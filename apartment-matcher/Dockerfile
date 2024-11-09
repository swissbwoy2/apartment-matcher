FROM python:3.9-slim

# Install Chrome and required dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Chrome options for running in container
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DRIVER=/usr/bin/chromedriver
ENV PYTHONUNBUFFERED=1

# Create volume for database
VOLUME /app/data

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]