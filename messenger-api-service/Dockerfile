FROM python:3.12

RUN apt-get update && apt-get install -y build-essential cmake git wget ffmpeg

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

RUN pip install -e .

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 7999

# Command to run the application using the startup script
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7999", "--reload"]
