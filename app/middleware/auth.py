"""Authentication middleware for API endpoints."""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from typing import Optional
import os
from app.config import API_KEY

# API Key header name
API_KEY_NAME = "X-API-Key"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)


def get_api_key_from_env() -> Optional[str]:
    """Get API key from environment variable."""
    return os.getenv("API_KEY", None)


def verify_api_key(api_key: Optional[str] = None) -> bool:
    """
    Verify API key against configured key.
    
    Args:
        api_key: API key to verify
        
    Returns:
        True if valid, False otherwise
    """
    if not api_key:
        return False
    
    expected_key = get_api_key_from_env()
    
    # If no API key is configured, allow access (for development)
    # In production, this should be required
    if not expected_key:
        return True
    
    return api_key == expected_key


async def get_api_key(
    api_key_header: Optional[str] = Security(API_KEY_HEADER),
    api_key_query: Optional[str] = Security(API_KEY_QUERY),
) -> str:
    """
    Extract and validate API key from header or query parameter.
    
    Args:
        api_key_header: API key from X-API-Key header
        api_key_query: API key from api_key query parameter
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    api_key = api_key_header or api_key_query
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide it via X-API-Key header or api_key query parameter.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )
    
    return api_key


async def get_admin_api_key(
    api_key_header: Optional[str] = Security(API_KEY_HEADER),
    api_key_query: Optional[str] = Security(API_KEY_QUERY),
) -> str:
    """
    Extract and validate admin API key (stricter validation).
    
    Args:
        api_key_header: API key from X-API-Key header
        api_key_query: API key from api_key query parameter
        
    Returns:
        Validated admin API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    api_key = await get_api_key(api_key_header, api_key_query)
    
    # Additional admin checks can be added here
    # For now, same validation but can be extended with role-based checks
    
    return api_key

