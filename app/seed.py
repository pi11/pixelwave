import asyncio

from tortoise import Tortoise

from app.db import TORTOISE_ORM
from app.models import Radio

RADIOS = [
    {
        "name": "Night Drive",
        "slug": "night-drive",
        "description": "Neon momentum after dark.",
        "tags": ["synthwave", "retrowave", "electronic"],
        "speeds": ["medium", "high"],
    },
    {
        "name": "Deep Focus",
        "slug": "deep-focus",
        "description": "Quiet patterns for difficult problems.",
        "tags": ["ambient", "idm", "electronic"],
        "speeds": ["low", "medium"],
    },
    {
        "name": "Lo-Fi Terminal",
        "slug": "lo-fi-terminal",
        "description": "Soft beats, clean terminal.",
        "tags": ["lofi", "chillout", "hiphop"],
        "speeds": ["low", "medium"],
    },
]


async def main():
    await Tortoise.init(config=TORTOISE_ORM)
    for data in RADIOS:
        await Radio.get_or_create(slug=data["slug"], defaults=data)
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
