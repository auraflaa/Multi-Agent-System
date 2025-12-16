# Security Configuration Guide

## Overview

This application includes security features to protect API endpoints:

1. **API Key Authentication** - Optional authentication via API keys
2. **Rate Limiting** - Prevents abuse with request rate limits
3. **CORS Restrictions** - Controls which origins can access the API
4. **Admin Endpoint Protection** - Stricter authentication for admin operations

## Configuration

### 1. API Key Authentication (Optional)

Set an API key via environment variable:

```bash
# Linux/Mac
export API_KEY=your-secret-api-key-here

# Windows (PowerShell)
$env:API_KEY="your-secret-api-key-here"

# Windows (CMD)
set API_KEY=your-secret-api-key-here
```

**Note:** If `API_KEY` is not set, authentication is disabled (development mode). In production, always set an API key.

### 2. CORS Configuration

Set allowed origins (comma-separated):

```bash
export ALLOWED_ORIGINS="http://localhost:8000,https://yourdomain.com"
```

If not set, defaults to `http://localhost:8000,http://127.0.0.1:8000`.

### 3. Rate Limits

Default rate limits:
- `/sales-agent`: 30 requests per 60 seconds
- `/admin/*`: 20 requests per 60 seconds
- Other endpoints: 100 requests per 60 seconds

Rate limits are applied per client (identified by API key or IP address).

## Using API Keys

### Frontend (JavaScript)

Include API key in requests:

```javascript
const apiKey = localStorage.getItem('api_key') || '';
const headers = { 'Content-Type': 'application/json' };
if (apiKey) {
    headers['X-API-Key'] = apiKey;
}

fetch('/sales-agent', {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({...})
});
```

### cURL

```bash
curl -X POST 'http://127.0.0.1:8000/sales-agent' \
  -H 'X-API-Key: your-api-key-here' \
  -H 'Content-Type: application/json' \
  -d '{...}'
```

Or via query parameter:

```bash
curl -X POST 'http://127.0.0.1:8000/sales-agent?api_key=your-api-key-here' \
  -H 'Content-Type: application/json' \
  -d '{...}'
```

## Security Best Practices

1. **Always set API_KEY in production**
2. **Use HTTPS in production** (configure at deployment level)
3. **Restrict ALLOWED_ORIGINS** to your actual domains
4. **Rotate API keys regularly**
5. **Never commit API keys to version control**
6. **Use environment variables** for sensitive configuration

## Development vs Production

### Development (No API Key)
- Authentication is optional
- CORS allows localhost
- Rate limiting is still active

### Production (With API Key)
- Authentication is required
- CORS restricted to specified origins
- Rate limiting prevents abuse
- Admin endpoints require authentication

## Troubleshooting

### 401 Unauthorized
- Check if API key is set in environment
- Verify API key is included in request headers
- Ensure API key matches configured value

### 403 Forbidden
- API key is invalid
- Check API key value matches `API_KEY` environment variable

### 429 Too Many Requests
- Rate limit exceeded
- Wait for rate limit window to reset
- Check `X-RateLimit-Reset` header for reset time

