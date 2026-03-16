# Semantic Classifier Microservice Setup

## Overview

Run the semantic classifier as a separate service to avoid Django/gunicorn timeout issues.

## Architecture

```
┌─────────────────┐         HTTP          ┌──────────────────────┐
│                 │  ────────────────────> │                      │
│  Django/        │                        │  Classifier          │
│  Gunicorn       │  <────────────────────  │  Service             │
│  (Port 8000)    │      JSON Response     │  (Port 8001)         │
│                 │                        │  - Loads model once  │
└─────────────────┘                        │  - Stays in memory   │
                                           │  - Fast responses    │
                                           └──────────────────────┘
```

## Setup

### 1. Install Dependencies

```bash
pip install fastapi uvicorn requests
```

### 2. Copy Prototypes to Service Directory

```bash
# The classifier service needs access to the prototypes
cp -r progress_tracker/protos/ .
```

### 3. Test Locally

```bash
# Start the classifier service
python classifier_service.py

# In another terminal, test it
curl http://localhost:8001/health
curl -X POST http://localhost:8001/classify \
  -H "Content-Type: application/json" \
  -d '{"text":"gym workout"}'
```

### 4. Configure Django to Use Remote Classifier

Add to your Django `settings.py`:

```python
# Semantic Classifier Service Configuration
CLASSIFIER_SERVICE_URL = os.environ.get('CLASSIFIER_SERVICE_URL', 'http://localhost:8001')
CLASSIFIER_TIMEOUT = 5  # seconds
```

Then update your code to use the remote client:

```python
# Option A: Change the import (recommended)
# from tracker.services.semantic_classifier import classify_text
from tracker.services.semantic_classifier_remote import classify_text

# Option B: Or conditionally use remote if available
USE_REMOTE_CLASSIFIER = os.environ.get('USE_REMOTE_CLASSIFIER', 'false').lower() == 'true'

if USE_REMOTE_CLASSIFIER:
    from tracker.services.semantic_classifier_remote import classify_text
else:
    from tracker.services.semantic_classifier import classify_text
```

## Production Deployment (AWS/Linux)

### Option 1: Systemd Service (Recommended)

Create `/etc/systemd/system/classifier-service.service`:

```ini
[Unit]
Description=Semantic Classifier Microservice
After=network.target

[Service]
Type=notify
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/vismatrix
Environment="PATH=/home/ubuntu/myenv/bin"
ExecStart=/home/ubuntu/myenv/bin/gunicorn classifier_service:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8001 \
    --timeout 300 \
    --log-level info \
    --access-logfile /var/log/classifier-service/access.log \
    --error-logfile /var/log/classifier-service/error.log

# Give it time to load the model
TimeoutStartSec=300

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create log directory:
```bash
sudo mkdir -p /var/log/classifier-service
sudo chown ubuntu:ubuntu /var/log/classifier-service
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable classifier-service
sudo systemctl start classifier-service
sudo systemctl status classifier-service
```

### Option 2: Docker Container

Create `Dockerfile.classifier`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn gensim numpy gunicorn

# Copy classifier service and prototypes
COPY classifier_service.py .
COPY protos/ ./protos/

# Expose port
EXPOSE 8001

# Start service
CMD ["uvicorn", "classifier_service:app", "--host", "0.0.0.0", "--port", "8001"]
```

Build and run:
```bash
docker build -f Dockerfile.classifier -t classifier-service .
docker run -d -p 8001:8001 --name classifier classifier-service
```

### Option 3: PM2 (Node.js Process Manager)

```bash
# Install PM2
npm install -g pm2

# Create ecosystem.config.js
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'classifier-service',
    script: '/home/ubuntu/myenv/bin/uvicorn',
    args: 'classifier_service:app --host 0.0.0.0 --port 8001',
    cwd: '/home/ubuntu/vismatrix',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '2G',
    env: {
      NODE_ENV: 'production'
    }
  }]
};
EOF

# Start
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## Firewall Configuration

If running on same server, keep it local-only:

```bash
# Allow only local connections to 8001
sudo ufw allow from 127.0.0.1 to any port 8001
```

If on different servers:

```bash
# Allow from Django server IP
sudo ufw allow from <django-server-ip> to any port 8001
```

## Monitoring

Check service health:
```bash
curl http://localhost:8001/health
```

View logs:
```bash
# Systemd
sudo journalctl -u classifier-service -f

# Docker
docker logs -f classifier

# PM2
pm2 logs classifier-service
```

## Performance

- **Startup time**: 30-180 seconds (model loading)
- **Memory usage**: ~1.5GB
- **Response time**: <10ms per classification (after loaded)
- **Workers**: 2 recommended (model is thread-safe but Python GIL limits concurrency)

## Advantages

✅ **No Django timeout issues** - Model loads independently  
✅ **Fast classification** - Model stays warm in memory  
✅ **Scalable** - Can run on different server, scale independently  
✅ **Resilient** - Django works even if classifier is down  
✅ **Easy monitoring** - Separate health checks and logs  

## Disadvantages

❌ **Extra complexity** - One more service to manage  
❌ **Network overhead** - HTTP calls vs in-process (but negligible ~1-2ms)  
❌ **Extra resources** - Needs dedicated memory/CPU  

## Troubleshooting

**Service won't start:**
- Check logs: `sudo journalctl -u classifier-service -n 50`
- Verify prototypes exist: `ls -la protos/`
- Check port availability: `sudo lsof -i :8001`

**Django can't connect:**
- Test from Django server: `curl http://localhost:8001/health`
- Check firewall: `sudo ufw status`
- Verify URL in settings: `CLASSIFIER_SERVICE_URL`

**Slow responses:**
- Check service health: `curl http://localhost:8001/health`
- Monitor logs for errors
- Increase timeout in settings if needed
