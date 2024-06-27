import pkgutil
from fastapi import FastAPI

from app import jobs
from app.objects.framework import config
from app.api import router


def initialize_jobs() -> None:
    all_jobs = jobs.__path__
    job_info = pkgutil.walk_packages(all_jobs, f"{jobs.__name__}.")

    for _, name, _ in job_info:
        __import__(name)


def initialize_framework(api: FastAPI) -> None:
    @api.on_event("startup")
    async def startup() -> None:
        await config.start()


def initialize_router(api: FastAPI) -> None:
    api.include_router(router)


def boot_api() -> FastAPI:
    api = FastAPI()

    initialize_jobs()
    initialize_router(api)
    initialize_framework(api)

    return api


api = boot_api()
