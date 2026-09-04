from hashlib import sha256

from fastapi import Request

from app.models import Radio, User


def hash_login_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


async def current_user(request: Request) -> User | None:
    user_id = request.session.get("user_id")
    if not isinstance(user_id, int):
        return None
    return await User.get_or_none(id=user_id)


async def favorites_radio(user: User) -> Radio:
    radio, _ = await Radio.get_or_create(
        slug=f"favorites-{user.id}",
        defaults={
            "owner": user,
            "name": "Favorites",
            "description": "Tracks you liked on Pixelwave Radio.",
            "tags": ["favorites"],
            "speeds": [],
            "instrumental": False,
            "visibility": "hidden",
        },
    )
    return radio
