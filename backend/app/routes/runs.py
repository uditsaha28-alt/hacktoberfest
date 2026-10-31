import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.db import database as db
from app.schemas import CreateRunRequest, CreateRunResponse, Report
from app.services.event_bus import format_sse
from app.services.repo_url import parse_repo_url
from app.services.run_manager import run_manager

router = APIRouter()


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


@router.post("/runs", status_code=201, response_model=CreateRunResponse)
async def create_run(body: CreateRunRequest):
    try:
        parse_repo_url(body.repo_url)
    except ValueError as exc:
        raise _error(400, "invalid_repo_url", str(exc))
    # repo_not_found (404) and rate_limited (429) arrive with the GitHub client in B4
    return {"run_id": run_manager.start_run(body.repo_url)}


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: str):
    channel = run_manager.bus.get(run_id)
    if channel is None:
        raise _error(404, "run_not_found", "Run not found.")

    async def generate():
        async for item in channel.stream():
            yield format_sse(item["event"], item["data"])

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runs/{run_id}/report", response_model=Report)
def get_report(run_id: str):
    run = db.get_run(run_id)
    if run is None:
        raise _error(404, "run_not_found", "Run not found.")
    if run["status"] != "done":
        raise _error(409, "run_not_finished", "The run has not finished yet.")
    return json.loads(run["report_json"])