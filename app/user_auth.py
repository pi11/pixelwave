from hashlib import sha256

from fastapi import Request

from app.models import User


def hash_login_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


async def current_user(request: Request) -> User | None:
    user_id = request.session.get("user_id")
    if not isinstance(user_id, int):
        return None
    return await User.get_or_none(id=user_id)
