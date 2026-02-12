# Authentication System Documentation

This document describes the JWT-based authentication system implemented for BrickGen.

## Overview

A comprehensive JWT (JSON Web Token) authentication system has been added to secure all API endpoints. Users must log in with credentials stored in the environment configuration before accessing the application.

## Features

### Backend Authentication
- **JWT Token-based authentication** using python-jose library
- **Password hashing** with bcrypt via passlib
- **Secure token generation** with configurable expiration (default: 24 hours)
- **Protected API routes** - all existing API endpoints require valid JWT tokens
- **Public endpoints** - `/api/login` and `/api/verify` remain public for authentication
- **HTTPBearer security scheme** for standardized token validation

### Frontend Authentication
- **Login page** with modern UI/UX using TailwindCSS
- **Authentication context** for global auth state management
- **Protected routes** - all application routes require authentication
- **Automatic token injection** - JWT tokens automatically added to all API requests
- **Session management** - automatic logout on 401 responses
- **Logout functionality** - users can logout from the header

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Authentication credentials
AUTH_USERNAME=admin
AUTH_PASSWORD=changeme

# JWT Secret Key (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
```

**Important Security Notes:**
1. Change the default username and password
2. Generate a strong, random JWT secret key for production
3. Keep your `.env` file secure and never commit it to version control

## Usage

### First Time Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your credentials:
   ```bash
   AUTH_USERNAME=your_username
   AUTH_PASSWORD=your_secure_password
   JWT_SECRET_KEY=$(openssl rand -hex 32)
   ```

3. Start the application:
   ```bash
   docker-compose up
   ```

### Logging In

1. Navigate to `http://localhost:8000`
2. You will be automatically redirected to the login page
3. Enter your configured username and password
4. Click "Login"

Upon successful authentication:
- A JWT token is generated and stored in your browser's localStorage
- You are redirected to the main application
- All subsequent API calls automatically include your JWT token

### Logging Out

Click the "Logout" button in the header to:
- Clear the JWT token from localStorage
- Reset authentication state
- Redirect to the login page

## API Endpoints

### Public Endpoints

#### POST /api/login
Authenticate and receive a JWT token.

**Request:**
```json
{
  "username": "admin",
  "password": "changeme"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### GET /api/verify
Verify that a JWT token is valid.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "username": "admin",
  "authenticated": true
}
```

### Protected Endpoints

All other API endpoints require authentication:
- `/api/search` - Search LEGO sets
- `/api/generate` - Generate 3D files
- `/api/download` - Download generated files
- `/api/settings` - Application settings
- `/api/projects` - Project management
- `/api/parts` - Part information

**Authentication:**
Include the JWT token in the Authorization header:
```
Authorization: Bearer <token>
```

## Security Considerations

### Current Implementation
- **Single-user authentication** - designed for self-hosted, single-user deployments
- **Plaintext passwords** - passwords are stored in environment variables (not hashed)
- **Environment-based secrets** - credentials stored in `.env` file
- **JWT token expiration** - tokens expire after 24 hours by default

### Production Recommendations

For production or multi-user deployments, consider:

1. **Hash passwords** - Store hashed passwords instead of plaintext
2. **User database** - Implement a proper user management system with database storage
3. **Password requirements** - Enforce strong password policies
4. **Rate limiting** - Add rate limiting to login endpoint to prevent brute force attacks
5. **HTTPS only** - Always use HTTPS in production to prevent token interception
6. **Token refresh** - Implement token refresh mechanism for better user experience
7. **Audit logging** - Log authentication attempts and failures

## Testing

The authentication system includes comprehensive test coverage:

### Unit Tests (11 tests)
- Password hashing and verification
- JWT token creation and validation
- User authentication logic

### Integration Tests (9 tests)
- Login endpoint with valid/invalid credentials
- Token verification
- Protected route access control

**Run tests:**
```bash
cd backend
python -m pytest tests/test_auth.py tests/test_auth_routes.py -v
```

## Troubleshooting

### Can't login - "Incorrect username or password"
- Verify credentials in `.env` file match what you're entering
- Check for extra spaces or special characters
- Ensure `.env` file is in the project root directory

### "Invalid authentication credentials" error
- JWT token may have expired (default: 24 hours)
- Token may be invalid - try logging out and logging in again
- Check that JWT_SECRET_KEY hasn't changed (would invalidate all tokens)

### Automatic logout after each page refresh
- Browser may not be persisting localStorage
- Check browser privacy/security settings
- Try a different browser

### API requests fail with 401 Unauthorized
- Token may have been cleared from localStorage
- Token may have expired
- Log out and log back in to get a new token

## Code Structure

### Backend Files
- `backend/auth.py` - Authentication utilities (JWT, password hashing)
- `backend/api/routes/auth.py` - Login and verification endpoints
- `backend/config.py` - Configuration including auth settings
- `backend/models/schemas.py` - Authentication request/response models

### Frontend Files
- `frontend/src/pages/LoginPage.jsx` - Login UI component
- `frontend/src/contexts/AuthContext.jsx` - Authentication state management
- `frontend/src/api.js` - API client with automatic token injection
- `frontend/src/App.jsx` - Protected route wrapper

## Dependencies

### Backend
- `python-jose[cryptography]` - JWT token handling
- `passlib[bcrypt]` - Password hashing
- `fastapi.security.HTTPBearer` - Token authentication

### Frontend
- `react-router-dom` - Client-side routing
- `localStorage` - Token persistence
- Custom event system - Unauthorized response handling
