import heapq
from typing import Any, Callable

import mesa

from src.uni_async.types import PendingMessage


class UniAsyncNetwork:
    def __init__(
        self,
        model: mesa.Model,
        delay_fcn: Callable[[dict[str, Any]], int],
    ) -> None:
        self.model = model
        self.delay_fcn = delay_fcn

        self._pq: list[PendingMessage] = []
        self._seq = 0

    def send(self, source: int, dest: int, payload: dict[str, Any]) -> None:
        delay = max(1, self.delay_fcn(payload))
        deliver_at = self.model.ticks + delay  # type: ignore

        message = PendingMessage(
            deliver_at=deliver_at,
            seq=self._seq,
            source=source,
            dest=dest,
            payload=payload,
        )
        self._seq += 1
        heapq.heappush(self._pq, message)

    def step(self) -> None:
        while self._pq and self._pq[0].deliver_at <= self.model.ticks:  # type: ignore
            message = heapq.heappop(self._pq)
            agent = self.model.agents[message.dest]
            agent.inbox.append(  # type: ignore
                {
                    "source": message.source,
                    "dest": message.dest,
                    "payload": message.payload,
                }
            )
