FROM python:3.13

# Set working directory
WORKDIR /app

# Install locales and set Russian locale
RUN apt-get update && apt-get install -y locales && \
    sed -i -e 's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=ru_RU.UTF-8 \
    LANGUAGE=ru_RU:ru \
    LC_ALL=ru_RU.UTF-8

# Copy pyproject.toml for dependency installation
COPY pyproject.toml .

# Install pip packages
RUN pip install --upgrade pip && \
    pip install --no-cache-dir pip-tools && \
    pip install --no-cache-dir python-dotenv && \
    pip install --no-cache-dir aiohttp fastapi uvicorn pandas openpyxl

# Copy application code
COPY . .

# Expose the port the app runs on
EXPOSE ${API_PORT:-52003}

# Command to run the application with hot reload
CMD uvicorn main:app --host 0.0.0.0 --port ${API_PORT:-52003} --reload 