FROM python:3.12

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml ./

# Install setuptools first
RUN pip install --upgrade pip setuptools

RUN pip install -e .

# Copy application code
COPY . .

# Expose the port the app runs on
EXPOSE 8001

# Command to run the application with hot reload
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]