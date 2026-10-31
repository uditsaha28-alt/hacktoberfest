import asyncio
import json
from typing import Any, AsyncIterator

TERMINAL_EVENTS = {"done", "error"}


def format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class RunChannel:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._cond = asyncio.Condition()

    async def publish(self, event: str, data: dict[str, Any]) -> None:
        async with self._cond:
            self.events.append({"event": event, "data": data})
            self._cond.notify_all()

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        index = 0
        while True:
            async with self._cond:
                await self._cond.wait_for(lambda: len(self.events) > index)
                batch = self.events[index:]
                index = len(self.events)
            for item in batch:
                yield item
                if item["event"] in TERMINAL_EVENTS:
                    return


class EventBus:
    def __init__(self) -> None:
        self._channels: dict[str, RunChannel] = {}

    def create(self, run_id: str) -> RunChannel:
        channel = RunChannel()
        self._channels[run_id] = channel
        return channel

    def get(self, run_id: str) -> RunChannel | None:
        return self._channels.get(run_id)