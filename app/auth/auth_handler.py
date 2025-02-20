import hashlib
import jwt
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Get secret key from environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

def hash_pin(pin: str) -> str:
    """Hash a PIN using SHA-256"""
    return hashlib.sha256(pin.encode()).hexdigest()

def verify_pin(pin: str, hashed_pin: str) -> bool:
    """Verify a PIN against its hash"""
    return hash_pin(pin) == hashed_pin

def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = {"user_id": str(user_id)}  # Ensure UUID is converted to string
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()  # Add issued at time
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the user_id if valid"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id:
            return str(user_id)  # Ensure UUID is returned as string
        return None
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None 