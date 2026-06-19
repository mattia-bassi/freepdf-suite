"""FIFO render queue with priority support for visible PDF pages."""

from __future__ import annotations

from collections import deque


class PageRenderQueue:
    """Tracks which pages still need rendering and in which order."""

    def __init__(self) -> None:
        self._queue: deque[int] = deque()
        self._pending: set[int] = set()
        self._done: set[int] = set()

    def clear(self) -> None:
        self._queue.clear()
        self._pending.clear()
        self._done.clear()

    def invalidate_all(self) -> None:
        """Drop rendered state so pages will be queued again (e.g. after zoom)."""
        self._done.clear()
        self._pending.clear()
        self._queue.clear()

    def is_rendered(self, page_index: int) -> bool:
        return page_index in self._done

    def enqueue(self, page_indices: list[int], *, front: int | None = None) -> None:
        """Add pages to the queue; ``front`` is processed first if given."""
        if front is not None and front not in self._done and front not in self._pending:
            self._pending.add(front)
            self._queue.appendleft(front)

        for page_index in page_indices:
            if page_index in self._done or page_index in self._pending:
                continue
            self._pending.add(page_index)
            self._queue.append(page_index)

    def pop(self, prefer: set[int] | None = None) -> int | None:
        """Take the next page index, preferring visible pages when possible."""
        if not self._queue:
            return None
        if prefer:
            for index, page_index in enumerate(self._queue):
                if page_index in prefer:
                    del self._queue[index]
                    return page_index
        return self._queue.popleft()

    def mark_done(self, page_index: int) -> None:
        self._done.add(page_index)
        self._pending.discard(page_index)

    def has_work(self) -> bool:
        return bool(self._queue)
