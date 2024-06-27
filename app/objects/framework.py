import asyncio
from datetime import datetime, timedelta
from enum import Enum
import os
from typing import Callable
from databases import Database
from pydantic import BaseModel, Field

from redis import asyncio as aioredis


class JobStatus(str, Enum):
    IDLE = "idle"
    IN_PROGRESS = "in progress"
    DISABLED = "disabled"


class Job(BaseModel):
    name: str
    interval: int
    is_controllable: bool
    # ^^^^ if `is_controllable` is enabled then 
    # the cron won't run it periodically and 
    # requires it to be manually activated 

    callback: Callable = Field(exclude=True)
    status: JobStatus = JobStatus.IDLE
    next_run: datetime = datetime.now()


class JobFramework:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}

        self.database = Database(f"mysql+aiomysql://{os.getenv("DB_NAME")}:{os.getenv("DB_PASSWORD")}@localhost/{os.getenv("DB_DATABASE")}")
        self.redis = aioredis.from_url(f"redis://{os.getenv("REDIS_NAME")}:{os.getenv("REDIS_PASSWORD")}@{os.getenv("REDIS_HOST")}:{os.getenv("REDIS_PORT")}")

    async def start(self) -> None:
        await self.database.connect()
        await self.redis.initialize()
        
        asyncio.create_task(self.watch())

    def register(
        self, name: str, interval: int = 0, is_controllable: bool = False
    ) -> Callable:
        def decorator(cb) -> None:
            self.jobs[name] = Job(
                name=name,
                interval=interval,
                is_controllable=is_controllable,
                callback=cb,
            )

        return decorator

    async def run(self, job: Job) -> None:
        job.status = JobStatus.IN_PROGRESS

        await job.callback(job, self.database, self.redis)

        job.status = JobStatus.IDLE
        job.next_run = datetime.now() + timedelta(seconds=job.interval)

    async def prepare(self, name: str) -> bool:
        if not (job := self.jobs[name]):
            return False

        asyncio.create_task(self.run(job))

        return True

    async def watch(self) -> None:
        while True:
            for name, job in self.jobs.items():
                if (
                    job.status == JobStatus.DISABLED
                    or job.status == JobStatus.IN_PROGRESS
                    or job.is_controllable
                ):
                    continue

                current_time = datetime.now()

                if current_time > job.next_run:
                    await self.prepare(name)

            await asyncio.sleep(1)  # wait a second before checking all jobs again


config = JobFramework()
