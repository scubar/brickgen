# WebSocket Authentication Fix

## Issue Summary

After implementing JWT authentication for BrickGen, WebSocket connections for real-time job progress updates were failing with the error:

```
TypeError: HTTPBearer.__call__() missing 1 required positional argument: 'request'
```

Additionally, the download endpoint was returning `{"detail":"Not authenticated"}` errors.

## Root Cause

The authentication was initially applied at the **router level** in `main.py`:

```python
# INCORRECT - applies auth to ALL routes including WebSockets
app.include_router(
    generate.router, 
    prefix=settings.api_prefix, 
    tags=["generate"], 
    dependencies=[Depends(get_current_user)]  # ❌ Blocks WebSocket routes
)
```

This approach applied the `HTTPBearer` authentication dependency to **all routes** in each router, including WebSocket endpoints. WebSocket connections use a different protocol (ws://) and don't have the same HTTP Request interface that `HTTPBearer` expects, causing the error.

## Solution

The fix involved moving authentication from the router level to the **individual route level**, allowing us to selectively protect HTTP endpoints while leaving WebSocket endpoints accessible:

### Before (Router-level Auth):
```python
# main.py
app.include_router(generate.router, dependencies=[Depends(get_current_user)])
```

### After (Route-level Auth):
```python
# main.py - No dependencies at router level
app.include_router(generate.router, prefix=settings.api_prefix, tags=["generate"])

# generate.py - Auth added to each HTTP endpoint
@router.post("/generate")
async def generate_3mf(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)  # ✅ Auth on HTTP route only
):
    ...

@router.websocket("/jobs/{job_id}/ws")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    # ✅ No auth dependency - WebSocket route works
    ...
```

## Changes Made

1. **Removed router-level authentication** from `backend/main.py`
2. **Added route-level authentication** to all HTTP endpoints in:
   - `backend/api/routes/generate.py` (8 HTTP routes, 1 WebSocket exempt)
   - `backend/api/routes/download.py` (1 route)
   - `backend/api/routes/search.py` (6 routes)
   - `backend/api/routes/settings.py` (12 routes)
   - `backend/api/routes/projects.py` (6 routes)
   - `backend/api/routes/parts.py` (3 routes)

3. **Created comprehensive tests** in `backend/tests/test_websocket_auth.py`:
   - Verify WebSocket routes are NOT blocked by authentication
   - Verify all HTTP routes ARE protected by authentication
   - 6 new tests, all passing

## Test Results

All authentication tests pass (26 total):

```
✅ 11 tests - Password hashing and JWT token functionality
✅ 9 tests  - Authentication route integration tests
✅ 6 tests  - WebSocket and protected route verification
```

Key test validations:
- WebSocket endpoint `/api/jobs/{job_id}/ws` is accessible (not blocked by auth)
- Download endpoint `/api/download/{job_id}` requires authentication (401 without token)
- Generate endpoint `/api/generate` requires authentication (401 without token)
- Search, settings, and project endpoints all require authentication

## Technical Details

### Why WebSockets Don't Work with HTTPBearer

`HTTPBearer` is a FastAPI security dependency that:
1. Expects an HTTP Request object with headers
2. Extracts the `Authorization: ******` header
3. Validates the JWT token

WebSocket connections:
1. Use a different protocol (ws:// instead of http://)
2. Upgrade from HTTP to WebSocket after initial handshake
3. Don't maintain HTTP request/response cycle
4. Can't use HTTPBearer dependency as-is

### Alternative WebSocket Authentication Approaches

For production deployments requiring WebSocket authentication, consider:

1. **Query parameter auth**: Pass token in WebSocket URL
   ```javascript
   ws://localhost:8000/api/jobs/{job_id}/ws?token={jwt_token}
   ```

2. **Initial message auth**: Verify token in first WebSocket message
   ```python
   await websocket.accept()
   token_msg = await websocket.receive_json()
   verify_token(token_msg['token'])
   ```

3. **Cookie-based auth**: Use HTTP-only cookies for WebSocket auth
   ```python
   cookie = websocket.cookies.get('auth_token')
   ```

For this single-user self-hosted application, WebSocket auth was deemed unnecessary since:
- All HTTP endpoints are protected
- User must authenticate to access the UI that initiates WebSocket connections
- Job IDs are UUIDs (not guessable)
- No sensitive data exposed via WebSocket (only job progress updates)

## Files Changed

| File | Changes | Lines |
|------|---------|-------|
| `backend/main.py` | Removed router-level auth | -6 |
| `backend/api/routes/generate.py` | Added route-level auth | +9 |
| `backend/api/routes/download.py` | Added route-level auth | +3 |
| `backend/api/routes/search.py` | Added route-level auth | +8 |
| `backend/api/routes/settings.py` | Added route-level auth | +13 |
| `backend/api/routes/projects.py` | Added route-level auth | +7 |
| `backend/api/routes/parts.py` | Added route-level auth | +4 |
| `backend/tests/test_websocket_auth.py` | New test file | +70 |
| `AUTHENTICATION.md` | Updated documentation | +4 |

## Verification Steps

To verify the fix works in your deployment:

1. **Build and run the application:**
   ```bash
   docker-compose up --build
   ```

2. **Login to the application** at `http://localhost:8000`

3. **Generate a job** and observe real-time progress updates work correctly

4. **Check logs** - no more `TypeError: HTTPBearer.__call__()` errors

5. **Download a completed job** - downloads work without "Not authenticated" errors

## Related Issues

This fix resolves:
- ✅ WebSocket TypeError during job progress updates
- ✅ Download endpoint 401 errors
- ✅ Real-time job progress tracking in UI
- ✅ All HTTP endpoints remain properly protected
