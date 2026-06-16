import logging

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import api, pages


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = FastAPI(
        title="FreeBus Kerala",
        description="Free KSRTC ordinary bus finder for the Priyadarshini scheme.",
        version="1.0.0",
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(api.router)
    app.include_router(pages.router)
    return app


app = create_app()
