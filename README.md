# Microservices Backend

This repository contains a collection of microservices that power the backend of the application.

## 🚀 Project Structure

The project consists of the following microservices:

| Service | Description | Port |
|---------|-------------|------|
| messenger-api-service | API for messenger integration | 7999 |
| file-service | Service for file management | 52001 |
| telegram-bot-service | Telegram bot integration | 7998 |
| message-processing-service | Message processing and handling | 8001 |
| whatsapp-service | WhatsApp integration | 52101 |
| data-service | Admin Panel | 3000 |
| mongo-service | MongoDB database | 27017 |
| presentation-service | Data presentation service | 52003 |
| classification-service | Classification service | 52004 |

## 📋 Requirements

- [Docker and Docker Compose](https://docs.docker.com/get-docker/)
- [Node.js](https://nodejs.org/en/download/)
- [uv Python package installer](https://github.com/astral-sh/uv)

## 🔧 Installation & Setup

### Running all services with Docker

To start project:

```bash
docker compose up
```

### Running individual services for development

#### Python microservices

For each Python-based microservice:

1. Navigate to the service directory
2. Start the service (all dependencies will be installed automatically):

```bash
uv run poe start
```

#### Node.js microservices

For Node.js-based services:

1. Navigate to the service directory
2. Install dependencies:

```bash
npm i
```

3. Start the service (e.g., for WhatsApp service):

```bash
node whatsapp.js
```

## 🔐 Environment Variables

Environment variables are loaded from the `.env` file in the root directory.
