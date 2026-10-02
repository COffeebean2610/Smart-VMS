# Deployment Guide

This guide details how to deploy the Smart VMS prototype for the A-1 Launchpad 2026 Hackathon.

## Prerequisites
- A cloud VPS (Ubuntu 22.04 recommended) or a local high-performance edge device.
- Docker & Docker Compose (Optional but recommended).
- MongoDB Atlas account.

## Option 1: Standard Deployment

### 1. Backend (FastAPI)
Deploy the backend using Gunicorn with Uvicorn workers.

```bash
cd backend
pip install -r requirements.txt
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```
*Note: Depending on CPU limits, you may want to restrict the number of workers, as each worker loads a separate YOLO model into memory.*

### 2. Frontend (React/Vite)
Build the frontend for production and serve it using Nginx.

```bash
cd frontend
npm install
npm run build
```
Copy the contents of `frontend/dist/` to `/var/www/html/` on your Nginx server.

Configure Nginx to proxy API requests to the FastAPI backend:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        root /var/www/html;
        try_files $uri /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Required for MJPEG streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;
    }
}
```

## Option 2: Localhost Demo (Hackathon Mode)
If presenting from a laptop:
1. Terminal 1: `cd backend && uvicorn main:app --reload`
2. Terminal 2: `cd frontend && npm run dev`
3. Connect your laptop to the venue Wi-Fi and use `localhost` or your local IP address.
