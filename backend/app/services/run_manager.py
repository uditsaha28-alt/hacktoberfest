import asyncio
import logging
import uuid

from app.agent.fake_run import run_fake
from app.agent.llm.base import LLMError
from app.agent.loop import run_agent
from app.agent.tools.github_client import GitHubError
from app.config import settings
from app.db import database as db
from app.schemas import Report
from app.services.event_bus import EventBus, RunChannel

logger = logging.getLogger(__name__)


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

    async def _fail(self, run_id: str, channel: RunChannel, message: str) -> None:
        db.update_status(run_id, "error")
        await channel.publish("error", {"message": message})

    async def _execute(self, run_id: str, repo_url: str, channel: RunChannel) -> None:
        try:
            runner = run_fake if settings.use_fake_run else run_agent
            raw = await runner(repo_url, channel.publish)
            report = Report.model_validate(raw)
            db.save_report(run_id, report.model_dump_json())
            await channel.publish("done", {})  # report is saved BEFORE done
        except LLMError as exc:
            await self._fail(run_id, channel, str(exc))
        except GitHubError as exc:
            await self._fail(run_id, channel, exc.message)
        except Exception:
            logger.exception("Run %s failed", run_id)
            await self._fail(run_id, channel, "The agent hit an unexpected error. Please try again.")


run_manager = RunManager()