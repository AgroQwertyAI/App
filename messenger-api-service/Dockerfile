FROM python:3.12

RUN apt-get update && apt-get install -y build-essential cmake git wget ffmpeg

RUN git clone https://github.com/ggml-org/whisper.cpp.git
WORKDIR /whisper.cpp
RUN cmake -B build
RUN cmake --build build --config Release
RUN sh ./models/download-ggml-model.sh tiny

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
