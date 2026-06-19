"""Tests for lazy page render queue."""

from __future__ import annotations

from ui.page_render_queue import PageRenderQueue


def test_queue_priority_pop() -> None:
    queue = PageRenderQueue()
    queue.enqueue([0, 1, 2, 3])
    assert queue.pop({3, 1}) == 1
    assert queue.pop({3, 1}) == 3
    assert queue.pop({3, 1}) == 0


def test_queue_mark_done_skips_reenqueue() -> None:
    queue = PageRenderQueue()
    queue.enqueue([5])
    page = queue.pop(set())
    assert page == 5
    queue.mark_done(5)
    queue.enqueue([5, 6])
    assert queue.pop(set()) == 6
