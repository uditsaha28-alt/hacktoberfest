import asyncio
import uuid

from app.agent.fake_run import run_fake as run_agent  # swapped for the real agent in B6
from app.db import database as db
from app.schemas import Report
from app.services.event_bus import EventBus, RunChannel


class RunManager:
    def __init__(self) -> None:
        self.bus = EventBus()
        self._tasks: set[asyncio.Task] = set()

    def start_run(self, repo_url: str) -> str:
        run_id = uuid.uuid4().hex[:12]
        db.create_run(run_id, repo_url)
        channel = self.bus.create(run_id)
        task = asyncio.create_task(self._execute(run_id, repo_url, channel))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return run_id

    async def _execute(self, run_id: str, repo_url: str, channel: RunChannel) -> None:
        try:
            raw = await run_agent(repo_url, channel.publish)
            report = Report.model_validate(raw)
            db.save_report(run_id, report.model_dump_json())
            await channel.publish("done", {})
        except Exception as exc:
            db.update_status(run_id, "error")
            await channel.publish("error", {"message": str(exc) or "Run failed"})


run_manager = RunManager()