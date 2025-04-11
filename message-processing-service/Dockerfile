FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy pyproject.toml for dependency installation
COPY pyproject.toml .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir aiohttp fastapi openai pydantic python-dotenv uvicorn

# Copy application code
COPY . .

# Expose the port the app runs on
EXPOSE ${API_PORT:-8001}

# Command to run the application with hot reload
CMD uvicorn main:app --host 0.0.0.0 --port ${API_PORT:-8001} --reload 