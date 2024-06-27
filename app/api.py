from fastapi import APIRouter, Response
from app.objects.framework import JobStatus, config

router = APIRouter()

# TODO: authorization...


@router.get("/")
async def all_jobs() -> Response:
    return config.jobs


@router.get("/job/{job_name}")
async def get_job(job_name: str) -> Response:
    if job_name not in config.jobs:
        return {"error": "job not found"}

    return config.jobs[job_name]


@router.post("/start/{job_name}")
async def start_job(job_name: str) -> Response:
    if job_name not in config.jobs:
        return {"error": "job not found"}

    job = config.jobs[job_name]

    if job.status == JobStatus.IN_PROGRESS:
        return {"error": "job already in progress."}

    await config.prepare(job_name)
    return {"status": "ok"}
