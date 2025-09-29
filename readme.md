# Instagram Stories → Discord Webhook

A small Python service (with Docker support) that fetches Instagram stories and sends them into a Discord channel via a webhook.

## ✨ Features

- Periodically check Instagram for new stories  
- Send story content (images, videos, text) into a Discord channel via webhook  
- Configurable via environment variables  
- Docker + Docker Compose support for easy deployment  

## 🚀 Setup & Usage

### 1. Clone the repo

```bash
git clone https://github.com/vicente-higino/instagram-stories-discord-webhook.git
cd instagram-stories-discord-webhook
cp .env.exemple .env
docker compose up --build
```
