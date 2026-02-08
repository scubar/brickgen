# Contributing to BrickGen

Thank you for your interest in contributing to BrickGen! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Docker and Docker Compose (for containerized development)

### Quick Setup

Run the development setup script:

```bash
chmod +x dev-setup.sh
./dev-setup.sh
```

Or manually:

**Backend:**
```bash
# Install pipenv if not already installed
pip install --user pipenv

cd backend
pipenv install --dev
pipenv shell
```

**Frontend:**
```bash
cd frontend
npm install
```

### Running Locally

**Terminal 1 - Backend:**
```bash
cd backend
pipenv shell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or without activating the shell:
```bash
cd backend
pipenv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Access the app at http://localhost:3000 (proxies API to localhost:8000)

## Project Structure

```
brickgen/
├── backend/                 # FastAPI backend
│   ├── api/
│   │   ├── integrations/   # External API clients
│   │   └── routes/         # API endpoints
│   ├── core/               # Core processing logic
│   ├── models/             # Pydantic schemas
│   ├── config.py           # Configuration management
│   ├── database.py         # Database models
│   └── main.py             # FastAPI application
├── frontend/               # React frontend
│   └── src/
│       ├── components/     # Reusable components
│       └── pages/          # Page components
└── README.md
```

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints where applicable
- Add docstrings to functions and classes
- Keep functions focused and small

Example:
```python
async def get_set_parts(self, set_num: str) -> List[Dict]:
    """Get parts inventory for a specific set.
    
    Args:
        set_num: Set number (e.g., "75192-1")
    
    Returns:
        List of parts with quantity, part number, color, etc.
    """
```

### JavaScript/React

- Use functional components with hooks
- Follow React best practices
- Use meaningful variable names
- Keep components focused and reusable

### General

- Write clear commit messages
- Add comments for complex logic
- Update documentation as needed

## Making Changes

### Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Test thoroughly
5. Commit with clear messages: `git commit -m "Add feature: description"`
6. Push to your fork: `git push origin feature/your-feature-name`
7. Open a Pull Request

### Commit Messages

Format: `type: description`

Types:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks

Example: `feat: add multi-plate support for large sets`

## Testing

### Backend Tests

From project root (using backend's Pipfile):

```bash
pipenv run --path backend python -m pytest backend/tests -v
```

### Frontend Tests

```bash
cd frontend
npm test
```

### Integration Tests

```bash
docker-compose up -d
# Run integration tests
docker-compose down
```

## Areas for Contribution

### High Priority

- [ ] Improve LDraw parser for better STL quality
- [ ] Optimize build plate arrangement algorithm
- [ ] Add comprehensive error handling
- [ ] Unit tests for core functionality
- [ ] Integration tests for API endpoints

### Medium Priority

- [ ] 3D preview using Three.js
- [ ] Multi-plate support for large sets
- [ ] Part color information in UI
- [ ] Print settings recommendations
- [ ] Progress indicators with detailed steps

### Future Enhancements

- [ ] Support for custom MOCs
- [ ] Part substitution suggestions
- [ ] Print time estimation
- [ ] Material usage calculation
- [ ] User accounts and history
- [ ] Kubernetes deployment manifests

## Reporting Issues

When reporting bugs, please include:

1. Description of the issue
2. Steps to reproduce
3. Expected behavior
4. Actual behavior
5. Environment details (OS, Python version, etc.)
6. Relevant logs or error messages

## Feature Requests

We welcome feature requests! Please:

1. Check if the feature already exists or is planned
2. Describe the feature clearly
3. Explain the use case
4. Consider implementation complexity

## Questions?

Feel free to open an issue for questions or join discussions in existing issues.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
