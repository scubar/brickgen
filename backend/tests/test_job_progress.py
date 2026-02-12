"""Unit tests for job_progress slot, overlay, and WebSocket subscriber state."""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from backend.core import job_progress


def _release_slot(job_id: str) -> None:
    """Release slot and remove progress for job_id so tests leave no side effects."""
    job_progress.release_job_slot(job_id)
    job_progress.remove_job_progress(job_id)


# Job IDs used in tests that claim the slot; released in teardown so one failing test doesn't block others
_SLOT_TEST_JOB_IDS = [
    "job-stale", "job-new", "job-a-recent", "job-b-recent",
    "job-a-refresh", "job-b-refresh", "job-holder-other", "job-other-other",
    "job-remove-slot", "other-job-slot", "job-set-no-claim",
]


@pytest.fixture(autouse=True)
def _release_slot_after_test():
    """After each test, release any of the known test job IDs so the slot is never left held."""
    yield
    for jid in _SLOT_TEST_JOB_IDS:
        _release_slot(jid)


class TestLastLogLine:
    """Tests for last_log_line (pure function, no shared state)."""

    def test_none_returns_none(self):
        assert job_progress.last_log_line(None) is None

    def test_empty_string_returns_none(self):
        assert job_progress.last_log_line("") is None

    def test_whitespace_only_returns_none(self):
        assert job_progress.last_log_line("   \n\t  ") is None

    def test_single_line_returns_stripped(self):
        assert job_progress.last_log_line("  hello  ") == "hello"

    def test_multiple_lines_returns_last_non_empty(self):
        assert job_progress.last_log_line("a\nb\nc") == "c"
        assert job_progress.last_log_line("line1\n\nline2\n  ") == "line2"

    def test_trailing_empty_lines_ignored(self):
        assert job_progress.last_log_line("only\n\n") == "only"


class TestClaimAndReleaseSlot:
    """Tests for the single-job slot: claim_job_slot, release_job_slot, is_job_running, is_any_job_running."""

    def test_initial_state_nothing_running(self):
        job_id = "job-initial"
        assert job_progress.is_any_job_running() is False
        assert job_progress.is_job_running(job_id) is False
        _release_slot(job_id)

    def test_claim_succeeds_when_slot_free(self):
        job_id = "job-claim-ok"
        assert job_progress.claim_job_slot(job_id) is True
        assert job_progress.is_job_running(job_id) is True
        assert job_progress.is_any_job_running() is True
        _release_slot(job_id)

    def test_claim_fails_when_slot_taken(self):
        job_a = "job-a"
        job_b = "job-b"
        assert job_progress.claim_job_slot(job_a) is True
        assert job_progress.claim_job_slot(job_b) is False
        assert job_progress.is_job_running(job_a) is True
        assert job_progress.is_job_running(job_b) is False
        _release_slot(job_a)
        _release_slot(job_b)

    def test_release_frees_slot_for_same_job(self):
        job_id = "job-release"
        job_progress.claim_job_slot(job_id)
        job_progress.release_job_slot(job_id)
        assert job_progress.is_any_job_running() is False
        assert job_progress.is_job_running(job_id) is False
        _release_slot(job_id)

    def test_release_idempotent(self):
        job_id = "job-idem"
        job_progress.claim_job_slot(job_id)
        job_progress.release_job_slot(job_id)
        job_progress.release_job_slot(job_id)
        assert job_progress.is_any_job_running() is False
        _release_slot(job_id)

    def test_release_wrong_job_does_not_clear_slot(self):
        job_a = "job-a"
        job_b = "job-b"
        job_progress.claim_job_slot(job_a)
        job_progress.release_job_slot(job_b)
        assert job_progress.is_job_running(job_a) is True
        _release_slot(job_a)
        _release_slot(job_b)

    def test_after_release_claim_succeeds_again(self):
        job_id = "job-reclaim"
        job_progress.claim_job_slot(job_id)
        job_progress.release_job_slot(job_id)
        assert job_progress.claim_job_slot(job_id) is True
        _release_slot(job_id)


class TestSetAndGetProgress:
    """Tests for set_job_progress, get_job_progress_overlay, remove_job_progress."""

    def test_get_overlay_missing_job_returns_none(self):
        assert job_progress.get_job_progress_overlay("nonexistent") is None

    def test_set_creates_default_entry(self):
        job_id = "job-set-default"
        job_progress.set_job_progress(job_id)
        overlay = job_progress.get_job_progress_overlay(job_id)
        assert overlay is not None
        assert overlay["status"] == "processing"
        assert overlay["progress"] == 0
        assert overlay["error_message"] is None
        assert overlay["log"] is None
        _release_slot(job_id)

    def test_set_updates_status_progress_error_log(self):
        job_id = "job-set-fields"
        job_progress.set_job_progress(job_id, status="failed", progress=50, error_message="err", log="log line")
        overlay = job_progress.get_job_progress_overlay(job_id)
        assert overlay["status"] == "failed"
        assert overlay["progress"] == 50
        assert overlay["error_message"] == "err"
        assert overlay["log"] == "log line"
        _release_slot(job_id)

    def test_set_partial_updates_preserve_other_fields(self):
        job_id = "job-partial"
        job_progress.set_job_progress(job_id, status="processing", progress=10)
        job_progress.set_job_progress(job_id, progress=20)
        overlay = job_progress.get_job_progress_overlay(job_id)
        assert overlay["status"] == "processing"
        assert overlay["progress"] == 20
        _release_slot(job_id)

    def test_set_job_progress_enqueues_payload_with_last_log_line(self):
        job_id = "job-queue-payload"
        with patch.object(job_progress, "_progress_queue") as mock_queue:
            mock_queue.put_nowait.side_effect = None
            job_progress.set_job_progress(job_id, status="processing", progress=10, log="line1\nline2\nlast")
            assert mock_queue.put_nowait.called
            call_args = mock_queue.put_nowait.call_args[0][0]
            assert call_args[0] == job_id
            payload = call_args[1]
            assert payload["status"] == "processing"
            assert payload["progress"] == 10
            assert payload["log"] == "last"
        _release_slot(job_id)

    def test_set_job_progress_queue_full_still_updates_overlay(self):
        job_id = "job-queue-full"
        with patch.object(job_progress, "_progress_queue") as mock_queue:
            import queue as queue_module
            mock_queue.put_nowait.side_effect = queue_module.Full
            job_progress.set_job_progress(job_id, progress=99)
            overlay = job_progress.get_job_progress_overlay(job_id)
            assert overlay is not None
            assert overlay["progress"] == 99
        _release_slot(job_id)

    def test_remove_job_progress_clears_overlay_and_releases_slot(self):
        job_id = "job-remove"
        job_progress.claim_job_slot(job_id)
        job_progress.set_job_progress(job_id, progress=5)
        job_progress.remove_job_progress(job_id)
        assert job_progress.get_job_progress_overlay(job_id) is None
        assert job_progress.is_any_job_running() is False
        _release_slot(job_id)

    def test_remove_job_progress_idempotent(self):
        job_id = "job-remove-idem"
        job_progress.set_job_progress(job_id)
        job_progress.remove_job_progress(job_id)
        job_progress.remove_job_progress(job_id)
        assert job_progress.get_job_progress_overlay(job_id) is None
        _release_slot(job_id)

class TestStaleSlotAutoClear:
    """Tests for auto-clearing the job slot when no update received in STALE_JOB_SECONDS (5 min)."""

    def test_claim_succeeds_after_stale_slot_auto_cleared(self):
        job_old = "job-stale"
        job_new = "job-new"
        base_time = 1000.0
        try:
            with patch.object(job_progress, "time") as mock_time:
                stale_time = base_time + job_progress.STALE_JOB_SECONDS + 1
                mock_time.time.side_effect = [base_time, stale_time, stale_time]
                assert job_progress.claim_job_slot(job_old) is True
                assert job_progress.claim_job_slot(job_new) is True
                assert job_progress.is_job_running(job_new) is True
                assert job_progress.is_job_running(job_old) is False
        finally:
            _release_slot(job_new)
            _release_slot(job_old)

    def test_claim_fails_when_slot_recently_updated(self):
        job_a = "job-a-recent"
        job_b = "job-b-recent"
        base_time = 1000.0
        try:
            with patch.object(job_progress, "time") as mock_time:
                mock_time.time.return_value = base_time
                assert job_progress.claim_job_slot(job_a) is True
                mock_time.time.return_value = base_time + 60
                assert job_progress.claim_job_slot(job_b) is False
        finally:
            _release_slot(job_a)
            _release_slot(job_b)

    def test_set_job_progress_refreshes_timestamp_so_slot_not_stale(self):
        job_a = "job-a-refresh"
        job_b = "job-b-refresh"
        base_time = 1000.0
        try:
            with patch.object(job_progress, "time") as mock_time:
                mock_time.time.return_value = base_time
                assert job_progress.claim_job_slot(job_a) is True
                job_progress.set_job_progress(job_a, progress=50)
                mock_time.time.return_value = base_time + job_progress.STALE_JOB_SECONDS + 1
                assert job_progress.claim_job_slot(job_b) is True
        finally:
            _release_slot(job_b)
            _release_slot(job_a)

    def test_set_job_progress_for_other_job_does_not_refresh_timestamp(self):
        job_a = "job-holder-other"
        job_b = "job-other-other"
        base_time = 1000.0
        try:
            with patch.object(job_progress, "time") as mock_time:
                mock_time.time.return_value = base_time
                assert job_progress.claim_job_slot(job_a) is True
                job_progress.set_job_progress(job_b, progress=50)
                mock_time.time.return_value = base_time + job_progress.STALE_JOB_SECONDS + 1
                assert job_progress.claim_job_slot(job_b) is True
        finally:
            _release_slot(job_b)
            _release_slot(job_a)

class TestSlotAndOverlayInteraction:
    """Tests that slot and overlay state stay consistent (remove_job_progress releases slot)."""

    def test_remove_job_progress_releases_slot_for_that_job(self):
        job_id = "job-remove-slot"
        other_id = "other-job-slot"
        try:
            job_progress.claim_job_slot(job_id)
            job_progress.set_job_progress(job_id)
            job_progress.remove_job_progress(job_id)
            assert job_progress.is_any_job_running() is False
            assert job_progress.claim_job_slot(other_id) is True
        finally:
            _release_slot(job_id)
            _release_slot(other_id)

    def test_set_progress_does_not_claim_slot(self):
        job_id = "job-set-no-claim"
        try:
            job_progress.set_job_progress(job_id, progress=1)
            assert job_progress.is_any_job_running() is False
            overlay = job_progress.get_job_progress_overlay(job_id)
            assert overlay is not None
        finally:
            _release_slot(job_id)


class TestWebSocketSubscribers:
    """Tests for add_ws_subscriber, remove_ws_subscriber with get_ws_lock."""

    @pytest.mark.asyncio
    async def test_add_and_remove_subscriber(self):
        job_id = "job-ws-1"
        ws = MagicMock()
        async with job_progress.get_ws_lock():
            job_progress.add_ws_subscriber(job_id, ws)
        async with job_progress.get_ws_lock():
            job_progress.remove_ws_subscriber(job_id, ws)
        _release_slot(job_id)

    @pytest.mark.asyncio
    async def test_remove_unknown_job_id_no_error(self):
        job_progress.remove_ws_subscriber("no-such-job", MagicMock())

    @pytest.mark.asyncio
    async def test_remove_unknown_websocket_no_error(self):
        job_id = "job-ws-remove-unknown"
        ws = MagicMock()
        async with job_progress.get_ws_lock():
            job_progress.add_ws_subscriber(job_id, ws)
        async with job_progress.get_ws_lock():
            job_progress.remove_ws_subscriber(job_id, MagicMock())  # different instance, no crash
            job_progress.remove_ws_subscriber(job_id, ws)  # clean up
        _release_slot(job_id)

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_job(self):
        job_id = "job-ws-multi"
        ws1, ws2 = MagicMock(), MagicMock()
        async with job_progress.get_ws_lock():
            job_progress.add_ws_subscriber(job_id, ws1)
            job_progress.add_ws_subscriber(job_id, ws2)
        async with job_progress.get_ws_lock():
            job_progress.remove_ws_subscriber(job_id, ws1)
            job_progress.remove_ws_subscriber(job_id, ws2)
        _release_slot(job_id)


class TestBroadcastProgressTask:
    """Tests for broadcast_progress_task (queue drain, cancel, circuit breaker)."""

    @pytest.mark.asyncio
    async def test_cancelled_terminates_cleanly(self):
        task = asyncio.create_task(job_progress.broadcast_progress_task())
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
