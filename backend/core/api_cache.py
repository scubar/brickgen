"""Generic API cache service for external integrations (e.g. Rebrickable).

Integrations use this to cache responses by key, avoiding repeated API calls
and rate limits. The backend can be DB-backed (persistent) or a no-op.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Iterable, List, Optional, Protocol

logger = logging.getLogger(__name__)


class ApiCacheBackend(Protocol):
    """Protocol for cache backends (get/set by string key, JSON-serializable value)."""

    def get(self, key: str) -> Optional[Any]:
        """Return cached value for key, or None if miss or expired."""
        ...

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store value for key. Optional ttl_seconds for expiration."""
        ...


class DbApiCache:
    """Database-backed API cache. Use with a request-scoped session."""

    def __init__(self, session: Any):
        self._session = session
        self._model = None  # Lazy import to avoid circular deps

    def _get_model(self):
        if self._model is None:
            from backend.database import ApiCache
            self._model = ApiCache
        return self._model

    def get(self, key: str) -> Optional[Any]:
        ApiCache = self._get_model()
        row = self._session.query(ApiCache).filter(ApiCache.key == key).first()
        if not row:
            return None
        if row.expires_at and datetime.utcnow() >= row.expires_at:
            self._session.delete(row)
            self._session.commit()
            return None
        try:
            return json.loads(row.value)
        except (TypeError, ValueError):
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        import json as _json
        ApiCache = self._get_model()
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        payload = _json.dumps(value)
        row = self._session.query(ApiCache).filter(ApiCache.key == key).first()
        if row:
            row.value = payload
            row.expires_at = expires_at
        else:
            row = ApiCache(key=key, value=payload, expires_at=expires_at)
            self._session.add(row)
        self._session.commit()

    @staticmethod
    def delete_by_prefix(session: Any, prefix: str) -> int:
        """Delete all api_cache rows whose key starts with prefix. Returns count deleted."""
        from backend.database import ApiCache
        deleted = session.query(ApiCache).filter(ApiCache.key.like(f"{prefix}%")).delete()
        session.commit()
        return deleted

    @staticmethod
    def delete_keys(session: Any, keys: Iterable[str]) -> int:
        """Delete api_cache rows whose key is in the given set. Returns count deleted."""
        key_list = list(keys)
        if not key_list:
            return 0
        from backend.database import ApiCache
        deleted = session.query(ApiCache).filter(ApiCache.key.in_(key_list)).delete(synchronize_session=False)
        session.commit()
        return deleted

    @staticmethod
    def count_by_prefix(session: Any, prefix: str) -> int:
        """Return number of api_cache rows whose key starts with prefix."""
        from backend.database import ApiCache
        return session.query(ApiCache).filter(ApiCache.key.like(f"{prefix}%")).count()

    @staticmethod
    def list_keys(session: Any, prefix: str, limit: Optional[int] = None, offset: int = 0) -> List[str]:
        """Return api_cache keys that start with prefix, ordered by key. Optional limit/offset."""
        from backend.database import ApiCache
        q = session.query(ApiCache.key).filter(ApiCache.key.like(f"{prefix}%")).order_by(ApiCache.key)
        if offset:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)
        return [row[0] for row in q.all()]
