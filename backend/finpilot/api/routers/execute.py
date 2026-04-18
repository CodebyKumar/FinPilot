from fastapi import APIRouter, BackgroundTasks

from finpilot.schemas.execute import ExecuteRequest, ExecuteResponse, JobStatusResponse
from finpilot.services.execute_service import execute_task, get_job_status

router = APIRouter(tags=["Execute"])


@router.post("/execute", response_model=ExecuteResponse)
def execute_route(payload: ExecuteRequest, background_tasks: BackgroundTasks):
    return execute_task(
        task_name=payload.task_name.value,
        user_id=payload.user_id,
        payload=payload.payload,
        mode=payload.mode.value,
        idempotency_key=payload.idempotency_key,
        background_tasks=background_tasks,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def job_status_route(job_id: str):
    return get_job_status(job_id)
