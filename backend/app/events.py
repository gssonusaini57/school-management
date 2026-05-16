import asyncio
import json
from typing import AsyncIterator


class Broker:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = {}

    def _qset(self, channel: str) -> set[asyncio.Queue]:
        return self._subs.setdefault(channel, set())

    async def subscribe(self, channel: str) -> AsyncIterator[str]:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._qset(channel).add(q)
        try:
            while True:
                msg = await q.get()
                yield msg
        finally:
            self._qset(channel).discard(q)

    def publish(self, channel: str, event: str, **payload) -> None:
        msg = json.dumps({"event": event, **payload}, default=str)
        for q in list(self._qset(channel)):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass


broker = Broker()
