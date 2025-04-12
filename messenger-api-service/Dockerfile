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

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

RUN pip install -e .

# Copy the rest of the application
COPY . .
COPY start.sh /start.sh
RUN chmod +x /start.sh
# Expose port
EXPOSE 8005

# Command to run the application using the startup script
CMD ["/start.sh"]
