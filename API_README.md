# Marz Limiter - API and Redis Integration

This documentation explains the new API and Redis functionality added to Marz Limiter.

## Overview

The following features have been added:

1. **Redis Integration**: Store connected IP addresses per service with timestamps
2. **REST API**: Access IP information through a secure API
3. **Bearer Token Authentication**: Secure your API with token-based authentication
4. **Swagger UI**: Interactive API documentation
5. **Telegram Bot Commands**: Generate and retrieve API tokens
6. **NGINX Configuration**: Production-ready web server setup

## Redis Integration

Redis is used to efficiently store and retrieve IP address information for each service. The implementation uses:

- Hash data structures for fast lookup
- Sets to store unique IP addresses
- Timestamps to track when IPs were last updated

## API Endpoints

### Authentication

All requests to the API must include an authorization token in the request header:

```
Authorization: Bearer YOUR_API_TOKEN
```

### Available Endpoints

#### Status Check

- **GET /api/status**
  - Description: Get API status
  - Authentication: None (public)
  - Response: `{"status": "active", "version": "1.0.0"}`

#### Connected IPs

- **GET /api/connected-ips**
  - Description: Get all connected IPs for all services
  - Authentication: Required
  - Response: 
    ```json
    {
      "services": {
        "service1": ["1.2.3.4", "5.6.7.8"],
        "service2": ["9.10.11.12"]
      },
      "last_update": 1642348800,
      "check_interval": 240
    }
    ```

#### Special Limits

- **GET /api/special-limits**
  - Description: Get all special limits
  - Authentication: Required
  - Response:
    ```json
    {
      "limits": {
        "username1": 5,
        "username2": 2
      }
    }
    ```

- **POST /api/special-limits**
  - Description: Add or update a special limit for a user
  - Authentication: Required
  - Request Body:
    ```json
    {
      "username": "username1",
      "limit": 5
    }
    ```
  - Response:
    ```json
    {
      "status": "success",
      "message": "Special limit for username1 set to 5"
    }
    ```

- **DELETE /api/special-limits**
  - Description: Remove a special limit for a user
  - Authentication: Required
  - Request Body:
    ```json
    {
      "username": "username1"
    }
    ```
  - Response:
    ```json
    {
      "status": "success",
      "message": "Special limit for username1 removed"
    }
    ```

#### Except Users

- **GET /api/except-users**
  - Description: Get all except users
  - Authentication: Required
  - Response:
    ```json
    {
      "users": ["username1", "username2"]
    }
    ```

- **POST /api/except-users**
  - Description: Add a user to the exception list
  - Authentication: Required
  - Request Body:
    ```json
    {
      "username": "username1"
    }
    ```
  - Response:
    ```json
    {
      "status": "success",
      "message": "User username1 added to exceptions"
    }
    ```

- **DELETE /api/except-users**
  - Description: Remove a user from the exception list
  - Authentication: Required
  - Request Body:
    ```json
    {
      "username": "username1"
    }
    ```
  - Response:
    ```json
    {
      "status": "success",
      "message": "User username1 removed from exceptions"
    }
    ```

## Error Handling

All API errors are returned with appropriate HTTP status codes and a JSON response with the following format:

```json
{
  "detail": "Error message"
}
```

Common error codes:
- 400: Bad Request (invalid parameters)
- 401: Unauthorized (invalid or missing token)
- 404: Not Found (resource not found)
- 500: Internal Server Error

## Configuration

New configuration options in `config.json`:

```json
{
  "API_TOKEN": "your-api-token",
  "API_PORT": 8080,
  "SWAGGER_PORT": 8080,
  "API_DOMAIN": "your-domain.com",
  "REDIS_HOST": "localhost",
  "REDIS_PORT": 6379,
  "REDIS_DB": 0,
  "REDIS_PASSWORD": null
}
```

## Setup Instructions

### 1. Install Redis

On Ubuntu:
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 2. Configure Marz Limiter

Update your `config.json` with the new settings or use the sample config as a template.

### 3. Setup NGINX (for production)

```bash
sudo cp nginx/marz-limiter-api.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/marz-limiter-api.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Or use the provided setup script:
```bash
sudo ./setup_api.sh
```

## Telegram Bot Commands

Two new commands have been added to the Telegram bot:

- `/get_api_token`: View the current API token

## Using the API

1. Get your token using the Telegram bot
2. Use the token in your API requests:
   ```
   Authorization: Bearer your-token-here
   ```
3. Access the Swagger UI documentation at:
   ```
   http://your-domain-or-ip/docs
   ```

## Files Added

- `api/`: Main API package
  - `__init__.py`: Package initialization
  - `auth.py`: Authentication functionality
  - `main.py`: FastAPI application
  - `server.py`: API server runner
  - `token_utils.py`: Token generation utilities
  - `static/`: Swagger UI files (downloaded at runtime)
  - `README.md`: API documentation
- `utils/redis_utils.py`: Redis client implementation
- `nginx/marz-limiter-api.conf`: NGINX configuration
- `setup_api.sh`: Setup script for Redis and NGINX

## Additional Notes

- The API server starts automatically when you run the main application (`python run.py`)
- The API can be accessed via the configured domain or IP address
- SSL can be set up later using Certbot (follow the commented instructions in the NGINX config) 