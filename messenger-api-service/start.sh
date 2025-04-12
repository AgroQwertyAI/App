#!/bin/bash

# Start cron service
service cron start

# Initialize crontab if needed
touch /var/spool/cron/crontabs/root
chmod 600 /var/spool/cron/crontabs/root

# Start the FastAPI application
python -m uvicorn main:app --host 0.0.0.0 --port 8005 --reload 