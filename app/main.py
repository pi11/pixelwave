from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from tortoise.contrib.fastapi import RegisterTortoise

from app.config import settings
from app.db import TORTOISE_ORM
from app.routes import router
from app.user_routes import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with RegisterTortoise(app, config=TORTOISE_ORM):
        yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=settings.public_base_url.startswith("https://"),
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)
app.include_router(user_router)
