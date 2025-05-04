# Marz Limiter API

This module provides a REST API for Marz Limiter, allowing you to retrieve information about connected IP addresses per service.

## Features

- **Bearer Token Authentication**: All API endpoints are secured with Bearer token authentication
- **Swagger UI Documentation**: Interactive API documentation available at `/docs`
- **Redis Integration**: Uses Redis for efficient storage and retrieval of IP data
- **Configuration Options**: Configurable API port, Swagger UI port, and domain

## Setup

### Prerequisites

- Redis server installed and running
- Nginx (optional, but recommended for production)

### Installation

1. Make sure all requirements are installed:
   ```
   pip install -r requirements.txt
   ```

2. Configure Redis and API settings in `config.json`:
   ```json
   {
     "API_TOKEN": "your-secure-token",
     "API_PORT": 8080,
     "SWAGGER_PORT": 8080,
     "API_DOMAIN": "your-domain.com",
     "REDIS_HOST": "localhost",
     "REDIS_PORT": 6379,
     "REDIS_DB": 0,
     "REDIS_PASSWORD": null
   }
   ```

3. For production deployment, use the provided Nginx configuration:
   ```
   sudo cp nginx/marz-limiter-api.conf /etc/nginx/sites-available/
   sudo ln -s /etc/nginx/sites-available/marz-limiter-api.conf /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. Or use the setup script (on Ubuntu):
   ```
   sudo ./setup_api.sh
   ```

## API Endpoints

### GET /api/status

Returns the current status of the API.

**Response:**
```json
{
  "status": "active",
  "version": "1.0.0"
}
```

### GET /api/connected-ips

Returns all connected IPs for all services.

**Authentication:**
- Bearer Token required in the Authorization header

**Response:**
```json
{
  "services": {
    "service1": [
      {
        "ip": "192.168.1.1",
        "last_updated": 1625097600
      }
    ],
    "service2": [
      {
        "ip": "192.168.1.2",
        "last_updated": 1625097650
      },
      {
        "ip": "192.168.1.3",
        "last_updated": 1625097700
      }
    ]
  }
}
```

## Authentication

To generate an API token, use the Telegram bot command:


To view the current API token:

```
/get_api_token
```

Use the token in your API requests:

```
Authorization: Bearer your-token-here
```

## Swagger UI

Access the Swagger UI documentation at:

```
http://your-domain-or-ip/docs
```

## Running the API Server

The API server is automatically started when you run the main application:

```
python run.py
``` 