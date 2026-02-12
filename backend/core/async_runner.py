"""Run async coroutines in a background thread with a dedicated event loop."""
import asyncio
import threading
from typing import Any, Callable, Coroutine


def run_async_in_background_thread(
    coro_fn: Callable[..., Coroutine[Any, Any, Any]],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Run coro_fn(*args, **kwargs) in a daemon thread with its own asyncio event loop.

    The server's main event loop is not blocked, so the request returns immediately.
    """
    def _run() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro_fn(*args, **kwargs))
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
