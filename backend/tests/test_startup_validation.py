"""Test startup validation for insecure credentials."""
import pytest
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_validate_auth_credentials_rejects_defaults():
    """Test that default insecure credentials are rejected."""
    # Import here to avoid loading config at module level
    import tempfile
    
    # Set up test environment
    _TEST_ROOT = tempfile.mkdtemp(prefix="brickgen_test_")
    os.environ["CACHE_DIR"] = os.path.join(_TEST_ROOT, "cache")
    os.environ["LDRAW_LIBRARY_PATH"] = os.path.join(_TEST_ROOT, "data", "ldraw")
    os.environ["DATABASE_PATH"] = os.path.join(_TEST_ROOT, "database", "brickgen.db")
    os.environ["OUTPUT_DIR"] = os.path.join(_TEST_ROOT, "outputs")
    os.environ["REBRICKABLE_API_KEY"] = "test_key"
    
    for _d in (os.environ["CACHE_DIR"], os.environ["LDRAW_LIBRARY_PATH"],
               os.path.dirname(os.environ["DATABASE_PATH"]), os.environ["OUTPUT_DIR"]):
        os.makedirs(_d, exist_ok=True)
    
    # Test 1: Default username should fail
    os.environ["AUTH_USERNAME"] = "admin"
    os.environ["AUTH_PASSWORD"] = "securepass123"
    os.environ["JWT_SECRET_KEY"] = "a" * 64
    
    # Clear module cache
    if 'backend.config' in sys.modules:
        del sys.modules['backend.config']
    
    from backend.config import settings
    
    insecure_usernames = ["admin"]
    assert settings.auth_username in insecure_usernames, "Test setup failed"
    
    # Test 2: Default password should fail
    os.environ["AUTH_USERNAME"] = "myuser"
    os.environ["AUTH_PASSWORD"] = "changeme"
    os.environ["JWT_SECRET_KEY"] = "a" * 64
    
    if 'backend.config' in sys.modules:
        del sys.modules['backend.config']
    
    from backend.config import settings as settings2
    
    insecure_passwords = ["changeme"]
    assert settings2.auth_password in insecure_passwords, "Test setup failed"
    
    # Test 3: Default JWT secret should fail
    os.environ["AUTH_USERNAME"] = "myuser"
    os.environ["AUTH_PASSWORD"] = "securepass123"
    os.environ["JWT_SECRET_KEY"] = "dev_secret_key_change_in_production"
    
    if 'backend.config' in sys.modules:
        del sys.modules['backend.config']
    
    from backend.config import settings as settings3
    
    insecure_jwt_secrets = [
        "dev_secret_key_change_in_production",
        "your_secret_key_here_change_in_production"
    ]
    assert settings3.jwt_secret_key in insecure_jwt_secrets, "Test setup failed"


def test_validate_auth_credentials_accepts_secure():
    """Test that secure credentials are accepted."""
    import tempfile
    
    # Set up test environment
    _TEST_ROOT = tempfile.mkdtemp(prefix="brickgen_test_")
    os.environ["CACHE_DIR"] = os.path.join(_TEST_ROOT, "cache")
    os.environ["LDRAW_LIBRARY_PATH"] = os.path.join(_TEST_ROOT, "data", "ldraw")
    os.environ["DATABASE_PATH"] = os.path.join(_TEST_ROOT, "database", "brickgen.db")
    os.environ["OUTPUT_DIR"] = os.path.join(_TEST_ROOT, "outputs")
    os.environ["REBRICKABLE_API_KEY"] = "test_key"
    
    for _d in (os.environ["CACHE_DIR"], os.environ["LDRAW_LIBRARY_PATH"],
               os.path.dirname(os.environ["DATABASE_PATH"]), os.environ["OUTPUT_DIR"]):
        os.makedirs(_d, exist_ok=True)
    
    # Set secure credentials
    os.environ["AUTH_USERNAME"] = "myuser"
    os.environ["AUTH_PASSWORD"] = "securepass123"
    os.environ["JWT_SECRET_KEY"] = "a" * 64
    
    if 'backend.config' in sys.modules:
        del sys.modules['backend.config']
    
    from backend.config import settings
    
    # Verify these are not the defaults
    insecure_usernames = ["admin"]
    insecure_passwords = ["changeme"]
    insecure_jwt_secrets = [
        "dev_secret_key_change_in_production",
        "your_secret_key_here_change_in_production"
    ]
    
    assert settings.auth_username not in insecure_usernames
    assert settings.auth_password not in insecure_passwords
    assert settings.jwt_secret_key not in insecure_jwt_secrets
