"""Tests for RebrickableClient response shaping (mocked HTTP, no real requests)."""
import pytest
from unittest.mock import AsyncMock, patch

from backend.api.integrations.rebrickable import RebrickableClient


class TestRebrickableSearchSets:
    """Test search_sets response shaping from API payload."""

    @pytest.mark.asyncio
    async def test_search_sets_shapes_response(self):
        mock_response = {
            "results": [
                {
                    "set_num": "1234-1",
                    "name": "Test Set",
                    "year": 2020,
                    "theme_id": 1,
                    "num_parts": 100,
                    "set_img_url": "https://example.com/img.png",
                }
            ],
            "count": 1,
            "next": None,
            "previous": None,
        }
        with patch.object(RebrickableClient, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            client = RebrickableClient(api_key="test-key")
            out = await client.search_sets("test", page=1, page_size=20)
        assert out["count"] == 1
        assert out["page"] == 1
        assert out["page_size"] == 20
        assert out["next"] is None
        assert len(out["results"]) == 1
        r = out["results"][0]
        assert r["set_num"] == "1234-1"
        assert r["name"] == "Test Set"
        assert r["year"] == 2020
        assert r["pieces"] == 100
        assert r["image_url"] == "https://example.com/img.png"

    @pytest.mark.asyncio
    async def test_search_sets_next_previous_pages(self):
        mock_response = {
            "results": [],
            "count": 50,
            "next": "https://rebrickable.com/next",
            "previous": None,
        }
        with patch.object(RebrickableClient, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            client = RebrickableClient(api_key="test-key")
            out = await client.search_sets("x", page=1, page_size=20)
        assert out["next"] == 2
        assert out["previous"] is None

        mock_response["next"] = None
        mock_response["previous"] = "https://rebrickable.com/prev"
        with patch.object(RebrickableClient, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            out2 = await client.search_sets("x", page=2, page_size=20)
        assert out2["next"] is None
        assert out2["previous"] == 1


class TestRebrickableGetSetParts:
    """Test get_set_parts response shaping and set_num normalization."""

    @pytest.mark.asyncio
    async def test_get_set_parts_adds_version_suffix(self):
        mock_response = {
            "results": [
                {
                    "part": {"part_num": "3005", "external_ids": {"LDraw": ["3005"]}},
                    "color": {"name": "Red", "rgb": "CC0000"},
                    "quantity": 2,
                    "is_spare": False,
                }
            ],
            "next": None,
        }
        with patch.object(RebrickableClient, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            client = RebrickableClient(api_key="test-key")
            out = await client.get_set_parts("1234")
        # set_num "1234" becomes "1234-1" for the request
        assert len(out) == 1
        assert out[0]["part_num"] == "3005"
        assert out[0]["quantity"] == 2
        assert out[0]["ldraw_id"] == "3005"
        assert out[0]["color_rgb"] == "CC0000"
        assert out[0]["is_spare"] is False

    @pytest.mark.asyncio
    async def test_get_set_parts_ldraw_id_missing(self):
        mock_response = {
            "results": [
                {
                    "part": {"part_num": "x", "external_ids": {}},
                    "color": {"name": "", "rgb": ""},
                    "quantity": 1,
                    "is_spare": False,
                }
            ],
            "next": None,
        }
        with patch.object(RebrickableClient, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            client = RebrickableClient(api_key="test-key")
            out = await client.get_set_parts("1234-1")
        assert out[0]["ldraw_id"] is None

    @pytest.mark.asyncio
    async def test_get_set_parts_uses_cache_when_provided(self):
        """When cache returns a value, no API call is made."""
        cached_parts = [{"part_num": "3005", "quantity": 3, "color": "Red"}]
        mock_cache = type("Cache", (), {
            "get": lambda self, k: cached_parts if "set_parts" in k else None,
            "set": lambda self, k, v, ttl=None: None,
        })()
        with patch.object(RebrickableClient, "_make_request", new_callable=AsyncMock) as mock_req:
            client = RebrickableClient(api_key="test-key", cache=mock_cache)
            out = await client.get_set_parts("75192-1")
        assert out == cached_parts
        mock_req.assert_not_called()
