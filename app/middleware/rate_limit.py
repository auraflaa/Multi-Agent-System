"""Rate limiting middleware."""
from fastapi import HTTPException, Request, status
from typing import Dict, Tuple
import time
from collections import defaultdict

# Rate limit storage: {endpoint: {identifier: (count, reset_time)}}
rate_limit_store: Dict[str, Dict[str, Tuple[int, float]]] = defaultdict(dict)

# Rate limit configurations
RATE_LIMITS = {
    "/sales-agent": {
        "requests": 30,  # 30 requests
        "window": 60,    # per 60 seconds
    },
    "/admin": {
        "requests": 20,  # 20 requests
        "window": 60,    # per 60 seconds
    },
    "default": {
        "requests": 100,  # 100 requests
        "window": 60,     # per 60 seconds
    },
}


def get_client_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    Uses API key if available, otherwise IP address.
    """
    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key[:8]}"  # Use first 8 chars for privacy
    
    # Fall back to IP address
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


def get_rate_limit_config(path: str) -> Dict[str, int]:
    """Get rate limit configuration for a path."""
    for endpoint, config in RATE_LIMITS.items():
        if endpoint != "default" and path.startswith(endpoint):
            return config
    return RATE_LIMITS["default"]


def check_rate_limit(request: Request) -> None:
    """
    Check if request exceeds rate limit.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    path = request.url.path
    identifier = get_client_identifier(request)
    config = get_rate_limit_config(path)
    
    current_time = time.time()
    key = f"{path}:{identifier}"
    
    # Get or initialize rate limit entry
    if key not in rate_limit_store[path]:
        rate_limit_store[path][key] = (0, current_time + config["window"])
    
    count, reset_time = rate_limit_store[path][key]
    
    # Reset if window expired
    if current_time > reset_time:
        count = 0
        reset_time = current_time + config["window"]
    
    # Check limit
    if count >= config["requests"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded. Maximum {config['requests']} requests "
                f"per {config['window']} seconds. Try again later."
            ),
            headers={
                "X-RateLimit-Limit": str(config["requests"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_time)),
            },
        )
    
    # Increment count
    rate_limit_store[path][key] = (count + 1, reset_time)

