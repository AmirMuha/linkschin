"""Centralized adaptive priority queue for crawl and search tasks (User Story 6)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import time
from typing import Any, Callable, Coroutine

from crawler.throttle import GLOBAL_THROTTLE

logger = logging.getLogger("crawler.queue")

PRIORITY_SEARCH = 0      # High priority: on-demand live user query
PRIORITY_BACKGROUND = 1  # Standard priority: scheduled periodic crawl


@dataclass(order=True)
class QueuedTask:
    priority: int
    timestamp: float
    task_id: str = field(compare=False)
    handler: Any = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    future: asyncio.Future = field(default_factory=asyncio.Future, compare=False)


class AdaptiveCrawlQueue:
    """Centralized priority queue scheduling user queries ahead of background crawl jobs."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._queue: asyncio.PriorityQueue[QueuedTask] = asyncio.PriorityQueue()
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        """Start worker consumer loop."""
        if self._running:
            return
        self._running = True
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)
        logger.info("AdaptiveCrawlQueue started with %d workers", self.max_workers)

    async def stop(self) -> None:
        """Gracefully stop queue workers."""
        self._running = False
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def enqueue(
        self,
        task_id: str,
        handler: Callable[..., Coroutine],
        *args: Any,
        priority: int = PRIORITY_BACKGROUND,
        **kwargs: Any,
    ) -> Any:
        """Enqueue task and return its awaited result."""
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        queued = QueuedTask(
            priority=priority,
            timestamp=time.time(),
            task_id=task_id,
            handler=handler,
            args=args,
            kwargs=kwargs,
            future=fut,
        )
        await self._queue.put(queued)
        return await fut

    async def _worker_loop(self, worker_id: int) -> None:
        while self._running:
            try:
                task = await self._queue.get()
                try:
                    result = await task.handler(*task.args, **task.kwargs)
                    if not task.future.done():
                        task.future.set_result(result)
                except Exception as exc:
                    logger.exception("Queue worker %d failed processing task %s: %s", worker_id, task.task_id, exc)
                    if not task.future.done():
                        task.future.set_exception(exc)
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in queue worker loop %d: %s", worker_id, e)
                await asyncio.sleep(0.5)


# Global singleton crawl queue
GLOBAL_QUEUE = AdaptiveCrawlQueue()
