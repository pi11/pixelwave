import asyncio

import httpx

from app.config import settings


async def set_webhook() -> None:
    if not settings.telegram_bot_token or not settings.telegram_webhook_secret:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET are required")
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            url,
            json={
                "url": f"{settings.public_base_url.rstrip('/')}/telegram/webhook",
                "secret_token": settings.telegram_webhook_secret,
                "allowed_updates": ["message"],
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(payload.get("description") or "Telegram rejected the webhook")
        print(payload.get("description") or "Webhook configured")


if __name__ == "__main__":
    asyncio.run(set_webhook())
