FROM python:3.12

# Install cron
RUN apt-get update && \
    apt-get install -y cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create cron directory with correct permissions
RUN mkdir -p /var/spool/cron/crontabs && \
    chmod -R 0644 /var/spool/cron && \
    chmod -R 1730 /var/spool/cron/crontabs

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using pip
RUN pip install -e .

# Copy the application
COPY . .

# Create a startup script to run both the app and cron service
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Expose port for the FastAPI application
EXPOSE 52001

# Run both cron and the application
CMD ["/start.sh"]
