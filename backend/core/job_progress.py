"""In-memory job progress state and WebSocket broadcast for generation jobs.

Single-process only; multi-worker deployments would not share this store.
Progress updates are pushed to WebSocket subscribers via a queue drained by
broadcast_progress_task (started in main.py).
"""
import asyncio
import logging
import queue
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# In-memory job progress. Key: job_id. Value: status, progress, error_message, log.
_job_progress: Dict[str, Dict[str, Any]] = {}
_job_progress_lock = threading.Lock()

# Only one generation job may run at a time. Set when a job is started, cleared when it ends.
_running_job_id: Optional[str] = None
_running_job_last_update_time: Optional[float] = None

# WebSocket: job_id -> list of connected WebSockets. Progress updates are pushed via _progress_queue.
# All access to _ws_subscribers is protected by the asyncio lock returned by _get_ws_lock().
_ws_subscribers: Dict[str, List[Any]] = {}
_ws_subscribers_lock: Optional[asyncio.Lock] = None
_ws_subscribers_lock_guard = threading.Lock()
_progress_queue: queue.Queue = queue.Queue(maxsize=1000)

# Circuit breaker for broadcast task: max consecutive errors before terminating
_BROADCAST_MAX_CONSECUTIVE_ERRORS = 10
_BROADCAST_ERROR_DELAY_SECONDS = 1.0

# Auto-clear slot if the running job has not received a progress update in this many seconds
STALE_JOB_SECONDS = 300  # 5 minutes


def _get_ws_lock() -> asyncio.Lock:
    """Return the shared asyncio lock for _ws_subscribers. Uses a threading.Lock so that
    concurrent first access from multiple coroutines creates only one asyncio.Lock."""
    global _ws_subscribers_lock
    with _ws_subscribers_lock_guard:
        if _ws_subscribers_lock is None:
            _ws_subscribers_lock = asyncio.Lock()
        return _ws_subscribers_lock


def is_any_job_running() -> bool:
    """Return True if a generation job is currently running (slot claimed)."""
    with _job_progress_lock:
        return _running_job_id is not None


def is_job_running(job_id: str) -> bool:
    """Return True if the given job is currently running."""
    with _job_progress_lock:
        return _running_job_id == job_id


def claim_job_slot(job_id: str) -> bool:
    """If no job is running (or the current one is stale after STALE_JOB_SECONDS), claim for job_id and return True. Otherwise return False."""
    global _running_job_id, _running_job_last_update_time
    with _job_progress_lock:
        if _running_job_id is not None:
            if _running_job_last_update_time is not None and (time.time() - _running_job_last_update_time) > STALE_JOB_SECONDS:
                logger.warning(
                    "Job slot held by %s with no update for %s seconds; auto-clearing slot.",
                    _running_job_id,
                    STALE_JOB_SECONDS,
                )
                _running_job_id = None
                _running_job_last_update_time = None
            else:
                return False
        _running_job_id = job_id
        _running_job_last_update_time = time.time()
        return True


def release_job_slot(job_id: str) -> None:
    """Release the single-job slot if it is currently held by this job_id. Idempotent."""
    global _running_job_id, _running_job_last_update_time
    with _job_progress_lock:
        if _running_job_id == job_id:
            _running_job_id = None
            _running_job_last_update_time = None


def get_job_progress_overlay(job_id: str) -> Optional[Dict[str, Any]]:
    """Return overlay dict (status, progress, error_message, log) for a running job, or None."""
    with _job_progress_lock:
        entry = _job_progress.get(job_id)
        if not entry:
            return None
        return {
            "status": entry["status"],
            "progress": entry["progress"],
            "error_message": entry.get("error_message"),
            "log": entry.get("log"),
        }


def last_log_line(full_log: Optional[str]) -> Optional[str]:
    """Return only the latest log line for API responses (smaller poll payload)."""
    if not full_log or not full_log.strip():
        return None
    lines = [ln.strip() for ln in full_log.splitlines() if ln.strip()]
    return lines[-1] if lines else full_log.strip()


def set_job_progress(
    job_id: str,
    *,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    error_message: Optional[str] = None,
    log: Optional[str] = None,
) -> None:
    """Update in-memory progress (no DB commit). Also enqueues payload for WebSocket broadcast."""
    global _running_job_last_update_time
    with _job_progress_lock:
        if job_id not in _job_progress:
            _job_progress[job_id] = {
                "status": "processing",
                "progress": 0,
                "error_message": None,
                "log": None,
            }
        entry = _job_progress[job_id]
        if status is not None:
            entry["status"] = status
        if progress is not None:
            entry["progress"] = progress
        if error_message is not None:
            entry["error_message"] = error_message
        if log is not None:
            entry["log"] = log
        if _running_job_id == job_id:
            _running_job_last_update_time = time.time()
        payload = {
            "status": entry["status"],
            "progress": entry["progress"],
            "error_message": entry.get("error_message"),
            "log": last_log_line(entry.get("log")),
        }
    try:
        _progress_queue.put_nowait((job_id, payload))
    except queue.Full:
        logger.warning(
            f"Progress queue is full (maxsize={_progress_queue.maxsize}), dropping update for job {job_id}. "
            "This may indicate broadcast_progress_task has fallen behind."
        )


def remove_job_progress(job_id: str) -> None:
    """Remove job from in-memory store and release the single-job slot (call when job completes or fails)."""
    global _running_job_id, _running_job_last_update_time
    with _job_progress_lock:
        _job_progress.pop(job_id, None)
        if _running_job_id == job_id:
            _running_job_id = None
            _running_job_last_update_time = None


def get_ws_lock() -> asyncio.Lock:
    """Return the shared asyncio lock for _ws_subscribers. Use when adding/removing subscribers."""
    return _get_ws_lock()


def add_ws_subscriber(job_id: str, websocket: Any) -> None:
    """Register a WebSocket as a subscriber for progress updates for job_id. Call with get_ws_lock() held."""
    if job_id not in _ws_subscribers:
        _ws_subscribers[job_id] = []
    _ws_subscribers[job_id].append(websocket)


def remove_ws_subscriber(job_id: str, websocket: Any) -> None:
    """Unregister a WebSocket for job_id. Call with get_ws_lock() held."""
    if job_id in _ws_subscribers:
        try:
            _ws_subscribers[job_id].remove(websocket)
        except ValueError:
            pass
        if not _ws_subscribers[job_id]:
            del _ws_subscribers[job_id]


async def broadcast_progress_task() -> None:
    """Background task: drain _progress_queue and send payload to all WebSocket subscribers for that job.

    Implements a circuit breaker pattern: after _BROADCAST_MAX_CONSECUTIVE_ERRORS consecutive
    exceptions in message processing, the task terminates. The error counter resets after each
    successful message broadcast (i.e., after queue.get_nowait() succeeds and all WebSocket
    sends complete without raising to the outer except block).
    """
    consecutive_errors = 0

    while True:
        try:
            try:
                job_id, payload = _progress_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
            async with _get_ws_lock():
                subscribers = list(_ws_subscribers.get(job_id, []))
            for ws in subscribers:
                try:
                    await ws.send_json(payload)
                except Exception:
                    async with _get_ws_lock():
                        try:
                            if job_id in _ws_subscribers:
                                _ws_subscribers[job_id].remove(ws)
                        except (KeyError, ValueError):
                            pass
            await asyncio.sleep(0)
            consecutive_errors = 0
        except asyncio.CancelledError:
            logger.debug("WebSocket broadcast task received cancellation")
            raise
        except Exception as e:
            consecutive_errors += 1
            logger.error(
                f"Unexpected error in WebSocket broadcast task (error {consecutive_errors}/{_BROADCAST_MAX_CONSECUTIVE_ERRORS}): {e}",
                exc_info=True,
            )
            if consecutive_errors >= _BROADCAST_MAX_CONSECUTIVE_ERRORS:
                logger.critical(
                    f"WebSocket broadcast task encountered {_BROADCAST_MAX_CONSECUTIVE_ERRORS} consecutive errors. Terminating task."
                )
                raise
            await asyncio.sleep(_BROADCAST_ERROR_DELAY_SECONDS)
