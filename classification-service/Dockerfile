FROM python:3.12

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY pyproject.toml .
COPY uv.lock .

# Install Python dependencies
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir uv && \
    uv pip install --system -e .

# Copy application code
COPY . .

# Command to run the application
CMD ["python", "main.py"] 