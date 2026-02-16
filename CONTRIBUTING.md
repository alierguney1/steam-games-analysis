# Contributing to Steam Games Analysis

## Development Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Poetry (Python package manager)
- Git

### Quick Start

1. **Clone and setup**
```bash
git clone https://github.com/alierguney1/steam-games-analysis.git
cd steam-games-analysis
make setup
```

2. **Start services**
```bash
make up
```

3. **Access applications**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/docs
- Database: localhost:5432

### Development Workflow

#### Backend Development

1. **Install dependencies**
```bash
cd backend
poetry install
```

2. **Run locally (without Docker)**
```bash
poetry run uvicorn app.main:app --reload
```

3. **Run tests**
```bash
poetry run pytest
poetry run pytest --cov=app  # with coverage
```

4. **Code formatting**
```bash
poetry run black app/
poetry run ruff check app/
```

#### Frontend Development

1. **Install dependencies**
```bash
cd frontend
npm install
```

2. **Run locally (without Docker)**
```bash
npm run dev
```

3. **Build**
```bash
npm run build
```

4. **Lint**
```bash
npm run lint
```

### Project Structure

```
steam-games-analysis/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/      # REST endpoints
│   │   ├── db/       # Database models
│   │   ├── ingestion/# Data scrapers
│   │   ├── analysis/ # Statistical models
│   │   └── schemas/  # Pydantic schemas
│   └── tests/
├── frontend/         # React frontend
│   └── src/
├── docker/           # Docker configs
├── configs/          # Config files
├── notebooks/        # Jupyter notebooks
└── scripts/          # Utility scripts
```

### Coding Standards

#### Python (Backend)
- Follow PEP 8
- Use type hints
- Maximum line length: 100
- Format with Black
- Lint with Ruff
- Write docstrings for public functions

#### TypeScript/React (Frontend)
- Use functional components
- Follow React hooks best practices
- Use TypeScript strict mode
- Maximum line length: 100

### Database Migrations

Using Alembic:

```bash
# Create a new migration
cd backend
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Testing Guidelines

#### Backend Tests
- Write tests for all API endpoints
- Mock external API calls
- Use pytest fixtures
- Aim for >80% coverage

#### Test Structure
```python
def test_endpoint_name():
    """Test description"""
    # Arrange
    # Act
    # Assert
```

### Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `style:` Formatting
- `chore:` Maintenance

Example:
```
feat: implement DiD analysis endpoint

- Add statistical model for DiD
- Create API endpoint at /api/analytics/did
- Add unit tests for model validation
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Update documentation
6. Submit PR with clear description

### Environment Variables

Never commit `.env` files. Use `.env.example` as template.

Required variables:
- `DATABASE_URL`: PostgreSQL connection string
- `STEAMSPY_API_URL`: SteamSpy API endpoint
- `STEAM_STORE_API_URL`: Steam Store API endpoint

### Useful Commands

```bash
# View all available commands
make help

# Start services
make up

# Stop services
make down

# View logs
make logs

# Run tests
make test

# Validate schema
make validate

# Clean up
make clean
```

## Questions?

Open an issue or reach out to the maintainer.
