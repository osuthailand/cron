import os
import jwt
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from app.constants import Privileges
from app.context import CRequest
from app.objects.framework import JobStatus, config

router = APIRouter()


async def get_current_user(
    request: CRequest, authorization: str | None = Header(None)
) -> None:
    if not authorization:
        raise HTTPException(401, {"error": "no token"})

    type, token = authorization.split()

    if type.lower() != "bearer":
        raise HTTPException(401, {"error": "could not validate jwt token"})

    try:
        payload: dict[str, Any] = jwt.decode(
            token, os.getenv("SECRET_KEY"), algorithms=["HS256"]
        )
    except jwt.InvalidTokenError:
        raise HTTPException(401, {"error": "could not validate jwt token"})

    user_id = payload.get("sub")
    assert user_id is not None

    data = await request.state.database.fetch_one(
        "SELECT username, privileges FROM users WHERE id = :user_id LIMIT 1",
        {"user_id": user_id},
    )

    if not data:
        raise HTTPException(401, {"error": "could not validate jwt token"})

    if not data["privileges"] & Privileges.ADMIN:
        raise HTTPException(401, {"error": "not authorized"})

    return


@router.get("/")
async def all_jobs(_=Depends(get_current_user)) -> Response:
    return config.jobs


@router.get("/job/{job_name}")
async def get_job(job_name: str, _=Depends(get_current_user)) -> Response:
    if job_name not in config.jobs:
        return {"error": "job not found"}

    return config.jobs[job_name]


@router.post("/start/{job_name}")
async def start_job(job_name: str, _=Depends(get_current_user)) -> Response:
    if job_name not in config.jobs:
        return {"error": "job not found"}

    job = config.jobs[job_name]

    if job.status == JobStatus.IN_PROGRESS:
        return {"error": "job already in progress."}

    await config.prepare(job_name)
    return {"status": "ok"}
