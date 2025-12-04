"""
Auth Module - JWT Token Management
Handles user authentication and token generation
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configuration
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

security = HTTPBearer()

class TokenManager:
    """Manages JWT tokens for authentication"""
    
    @staticmethod
    def create_access_token(user_id: str, email: str) -> str:
        """
        Creates a new access token
        
        Args:
            user_id: Unique user identifier
            email: User email
            
        Returns:
            JWT token string
        """
        payload = {
            "user_id": user_id,
            "email": email,
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Creates a new refresh token"""
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """
        Verifies and decodes a JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    @staticmethod
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> dict:
        """
        Dependency to get current authenticated user
        
        Returns:
            User data from token
        """
        token = credentials.credentials
        payload = TokenManager.verify_token(token)
        
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        return {
            "user_id": payload["user_id"],
            "email": payload.get("email")
        }

# BUG: TASK-101
# Problem: When user changes password, old tokens remain valid
# This causes 401 errors because token is not invalidated in Redis
# 
# TODO: Add token invalidation:
# 1. Store active tokens in Redis with user_id as key
# 2. On password change, delete all tokens for that user
# 3. Add check in verify_token to see if token is in blacklist
#
# Example fix:
# redis_client.delete(f"user:{user_id}:tokens")
# redis_client.sadd(f"blacklist", token)

def invalidate_user_tokens(user_id: str, redis_client):
    """
    Invalidates all tokens for a user
    Should be called on password change, logout, etc.
    """
    # Get all active tokens
    tokens = redis_client.smembers(f"user:{user_id}:tokens")
    
    # Add to blacklist
    for token in tokens:
        redis_client.sadd("token:blacklist", token)
        redis_client.expire("token:blacklist", REFRESH_TOKEN_EXPIRE_DAYS * 86400)
    
    # Clear user tokens
    redis_client.delete(f"user:{user_id}:tokens")
