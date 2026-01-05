FROM python:3.11-slim

WORKDIR /app

# Set timezone to Europe/Warsaw (UTC+1/+2)
ENV TZ=Europe/Warsaw
RUN apt-get update && apt-get install -y \
    gcc \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Run the bot
CMD ["python", "main.py"]
