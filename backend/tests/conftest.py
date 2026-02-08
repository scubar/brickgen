"""Pytest configuration and shared fixtures."""
import os
import tempfile
import pytest

# Set app paths to a temp dir before any backend import so config doesn't use /app
_TEST_ROOT = tempfile.mkdtemp(prefix="brickgen_test_")
os.environ["CACHE_DIR"] = os.path.join(_TEST_ROOT, "cache")
os.environ["LDRAW_LIBRARY_PATH"] = os.path.join(_TEST_ROOT, "data", "ldraw")
os.environ["DATABASE_PATH"] = os.path.join(_TEST_ROOT, "database", "brickgen.db")
os.environ["OUTPUT_DIR"] = os.path.join(_TEST_ROOT, "outputs")
for _d in (os.environ["CACHE_DIR"], os.environ["LDRAW_LIBRARY_PATH"],
           os.path.dirname(os.environ["DATABASE_PATH"]), os.environ["OUTPUT_DIR"]):
    os.makedirs(_d, exist_ok=True)


@pytest.fixture
def tmp_ldraw_parts(tmp_path):
    """Create a temporary parts dir (e.g. for LDViewConverter._find_part_file)."""
    parts = tmp_path / "parts"
    parts.mkdir()
    return parts
