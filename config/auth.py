from datetime import datetime, timedelta
from jose import jwt, JWTError
from django.contrib.auth import get_user_model
import os

User = get_user_model()

SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-dev-key")
ALGORITHM = "HS256"

def create_refresh_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=60)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None