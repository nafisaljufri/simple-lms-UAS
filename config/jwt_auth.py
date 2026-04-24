from ninja.security import HttpBearer
from .auth import decode_token
from django.contrib.auth import get_user_model

User = get_user_model()


class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        payload = decode_token(token)

        if not payload:
            return None

        user_id = payload.get("user_id")

        try:
            user = User.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            return None