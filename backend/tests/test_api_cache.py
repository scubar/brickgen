"""Tests for DbApiCache (mocked DB session)."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.core.api_cache import DbApiCache


def _make_row(key: str, value: str, expires_at=None):
    row = MagicMock()
    row.key = key
    row.value = value
    row.expires_at = expires_at
    return row


def _chainable_query(mock_session, first_result=None, delete_result=0, count_result=0, all_result=None):
    """Make session.query(X).filter(X.key == ...).first() / .delete() / .count() / .all() work."""
    first_result = first_result if all_result is None else None
    chain = MagicMock()
    chain.first.return_value = first_result
    chain.delete.return_value = delete_result
    chain.count.return_value = count_result
    if all_result is not None:
        chain.order_by.return_value = chain
        chain.offset.return_value = chain
        chain.limit.return_value = chain
        chain.all.return_value = [(k,) for k in all_result]
    mock_session.query.return_value.filter.return_value = chain
    return chain


class TestDbApiCacheGet:
    """Tests for DbApiCache.get."""

    def test_get_miss_returns_none(self):
        session = MagicMock()
        _chainable_query(session, first_result=None)
        cache = DbApiCache(session)
        with patch("backend.core.api_cache.datetime") as mdt:
            mdt.utcnow.return_value = datetime(2025, 2, 10, 12, 0, 0)
            assert cache.get("missing") is None
        session.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_hit_returns_parsed_value(self):
        session = MagicMock()
        row = _make_row("k", '{"a": 1}', expires_at=None)
        _chainable_query(session, first_result=row)
        cache = DbApiCache(session)
        assert cache.get("k") == {"a": 1}
        session.commit.assert_not_called()

    def test_get_expired_deletes_and_returns_none(self):
        session = MagicMock()
        row = _make_row("k", "{}", expires_at=datetime(2020, 1, 1))
        _chainable_query(session, first_result=row)
        cache = DbApiCache(session)
        with patch("backend.core.api_cache.datetime") as mdt:
            mdt.utcnow.return_value = datetime(2025, 2, 10)
            assert cache.get("k") is None
        session.delete.assert_called_once_with(row)
        session.commit.assert_called_once()

    def test_get_invalid_json_returns_none(self):
        session = MagicMock()
        row = _make_row("k", "not json", expires_at=None)
        _chainable_query(session, first_result=row)
        cache = DbApiCache(session)
        assert cache.get("k") is None


class TestDbApiCacheSet:
    """Tests for DbApiCache.set."""

    def test_set_new_key_adds_row_and_commits(self):
        session = MagicMock()
        _chainable_query(session, first_result=None)
        cache = DbApiCache(session)
        with patch("backend.core.api_cache.datetime") as mdt:
            mdt.utcnow.return_value = datetime(2025, 2, 10, 12, 0, 0)
            cache.set("newkey", {"x": 1})
        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert added.key == "newkey"
        assert added.value == '{"x": 1}'
        assert added.expires_at is None
        session.commit.assert_called_once()

    def test_set_existing_key_updates_row_and_commits(self):
        session = MagicMock()
        row = _make_row("k", "old")
        _chainable_query(session, first_result=row)
        cache = DbApiCache(session)
        cache.set("k", ["a", "b"])
        assert row.value == '["a", "b"]'
        assert row.expires_at is None
        session.add.assert_not_called()
        session.commit.assert_called_once()

    def test_set_with_ttl_sets_expires_at(self):
        session = MagicMock()
        _chainable_query(session, first_result=None)
        cache = DbApiCache(session)
        with patch("backend.core.api_cache.datetime") as mdt:
            mdt.utcnow.return_value = datetime(2025, 2, 10, 12, 0, 0)
            with patch("backend.core.api_cache.timedelta") as mtd:
                mtd.return_value = MagicMock()
                cache.set("k", 42, ttl_seconds=60)
        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert added.expires_at is not None
        mtd.assert_called_once_with(seconds=60)


class TestDbApiCacheDeleteByPrefix:
    """Tests for DbApiCache.delete_by_prefix."""

    def test_delete_by_prefix_returns_deleted_count(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.delete.return_value = 3
        deleted = DbApiCache.delete_by_prefix(session, "rebrickable:")
        assert deleted == 3
        session.query.return_value.filter.assert_called_once()
        # Filter uses key LIKE prefix% (SQLAlchemy stringifies as e.g. api_cache.key LIKE :key_1)
        assert "LIKE" in str(session.query.return_value.filter.call_args[0][0])
        session.commit.assert_called_once()


class TestDbApiCacheDeleteKeys:
    """Tests for DbApiCache.delete_keys."""

    def test_delete_keys_empty_returns_zero(self):
        session = MagicMock()
        deleted = DbApiCache.delete_keys(session, [])
        assert deleted == 0
        session.query.assert_not_called()

    def test_delete_keys_deletes_and_returns_count(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.delete.return_value = 2
        deleted = DbApiCache.delete_keys(session, ["a", "b", "c"])
        assert deleted == 2
        session.query.return_value.filter.assert_called_once()
        session.commit.assert_called_once()


class TestDbApiCacheCountByPrefix:
    """Tests for DbApiCache.count_by_prefix."""

    def test_count_by_prefix_returns_count(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.count.return_value = 5
        n = DbApiCache.count_by_prefix(session, "rebrickable:set:")
        assert n == 5
        session.query.return_value.filter.assert_called_once()


class TestDbApiCacheListKeys:
    """Tests for DbApiCache.list_keys."""

    def test_list_keys_returns_keys_ordered(self):
        session = MagicMock()
        _chainable_query(session, all_result=["rebrickable:set:1", "rebrickable:set:2"])
        keys = DbApiCache.list_keys(session, "rebrickable:set:")
        assert keys == ["rebrickable:set:1", "rebrickable:set:2"]
        q = session.query.return_value.filter.return_value
        q.order_by.assert_called_once()

    def test_list_keys_respects_limit_and_offset(self):
        session = MagicMock()
        _chainable_query(session, all_result=["rebrickable:set:2"])
        keys = DbApiCache.list_keys(session, "rebrickable:set:", limit=1, offset=1)
        assert keys == ["rebrickable:set:2"]
        q = session.query.return_value.filter.return_value
        q.offset.assert_called_once_with(1)
        q.limit.assert_called_once_with(1)
