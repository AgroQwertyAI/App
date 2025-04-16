FROM python:3.12

RUN apt-get update

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

RUN pip install -e .

# Copy the rest of the application
COPY . .

EXPOSE 7998

# Command to run the application using the startup script with auto-reload
CMD ["python", "main.py"]
