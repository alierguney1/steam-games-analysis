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

## Test Scenarios

### Phase 2: Data Ingestion (Tamamlandı)

Bu aşamada veri toplama altyapısı tamamlandı. Test senaryoları:

#### 1. SteamSpy Client Testi
```python
# backend/tests/test_ingestion/test_steamspy.py örneği
import asyncio
from app.ingestion.steamspy_client import SteamSpyClient

async def test_steamspy_fetch():
    async with SteamSpyClient() as client:
        # Belirli appid'ler için veri çek
        data = await client.fetch(appids=[730, 570, 440])  # CS:GO, Dota 2, TF2
        assert len(data) == 3
        assert data[0]['appid'] == 730

# Çalıştırmak için:
# pytest backend/tests/test_ingestion/test_steamspy.py -v
```

#### 2. SteamCharts Scraper Testi
```python
# backend/tests/test_ingestion/test_steamcharts.py örneği
async def test_steamcharts_scraper():
    async with SteamChartsScraper() as scraper:
        data = await scraper.fetch([730])  # CS:GO
        parsed = scraper.parse(data)
        assert len(parsed) > 0
        assert 'avg_players' in parsed[0]
```

#### 3. Steam Store Client Testi
```python
# backend/tests/test_ingestion/test_steam_store.py örneği
async def test_steam_store_pricing():
    async with SteamStoreClient() as client:
        data = await client.fetch([730])
        parsed = client.parse(data)
        assert 'current_price' in parsed[0]
```

#### 4. Manual ETL Pipeline Test
```bash
# Backend container'a gir
docker exec -it steam-backend bash

# Python interpreter aç ve çalıştır:
python3
```

```python
import asyncio
from app.ingestion.steamspy_client import SteamSpyClient
from app.ingestion.steamcharts_scraper import SteamChartsScraper
from app.ingestion.steam_store_client import SteamStoreClient
from app.ingestion.merger import DataMerger
from app.ingestion.loader import DataLoader
from app.db.session import get_session

async def test_full_pipeline():
    # 1. Veri toplama (test için sadece 5 oyun)
    test_appids = [730, 570, 440, 271590, 252490]  # Popüler oyunlar
    
    # SteamSpy
    async with SteamSpyClient() as spy:
        spy_data = await spy.fetch(appids=test_appids)
        spy_parsed = spy.parse(spy_data)
        spy_transformed = spy.transform(spy_parsed)
    
    # SteamCharts
    async with SteamChartsScraper() as charts:
        charts_data = await charts.fetch(test_appids)
        charts_parsed = charts.parse(charts_data)
        charts_transformed = charts.transform(charts_parsed)
    
    # Steam Store
    async with SteamStoreClient() as store:
        store_data = await store.fetch(test_appids)
        store_parsed = store.parse(store_data)
        store_transformed = store.transform(store_parsed)
    
    # 2. Veri birleştirme
    merger = DataMerger()
    merged = merger.merge_game_data(
        spy_transformed,
        charts_transformed,
        store_transformed
    )
    
    # Deduplication
    merged['fact_player_price'] = merger.deduplicate_facts(
        merged['fact_player_price']
    )
    
    print(f"Merged data:")
    print(f"  - Games: {len(merged['dim_game'])}")
    print(f"  - Facts: {len(merged['fact_player_price'])}")
    print(f"  - Tags: {len(merged['dim_tag'])}")
    print(f"  - Genres: {len(merged['dim_genre'])}")
    
    # 3. Veritabanına yükleme
    session = await get_session()
    loader = DataLoader(session)
    stats = await loader.load_all(merged)
    
    print(f"Load stats: {stats}")
    
    await session.close()

# Çalıştır
asyncio.run(test_full_pipeline())
```

#### 5. Veritabanı Doğrulama
```bash
# PostgreSQL container'a bağlan
docker exec -it steam-postgres psql -U steam_user -d steam_analytics

# Veri kontrolü
SELECT COUNT(*) FROM dim_game;
SELECT COUNT(*) FROM fact_player_price;
SELECT COUNT(*) FROM dim_tag;
SELECT COUNT(*) FROM bridge_game_tag;

# Örnek oyun detayı
SELECT g.name, f.concurrent_players_avg, f.current_price, f.discount_pct
FROM dim_game g
JOIN fact_player_price f ON g.game_id = f.game_id
WHERE g.appid = 730
LIMIT 10;

# En yüksek oyuncu sayılarına sahip oyunlar
SELECT g.name, MAX(f.concurrent_players_avg) as max_players
FROM dim_game g
JOIN fact_player_price f ON g.game_id = f.game_id
GROUP BY g.name
ORDER BY max_players DESC
LIMIT 10;
```

### Beklenen Sonuçlar

Phase 2 tamamlandıktan sonra:

✅ **Başarılı Test Göstergeleri:**
- SteamSpy'dan oyun metadatası çekilebildi
- SteamCharts'tan aylık oyuncu verileri parse edilebildi
- Steam Store'dan fiyat bilgileri alınabildi
- Üç veri kaynağı başarıyla birleştirildi
- Veritabanına bulk upsert işlemleri çalıştı
- dim_game, dim_tag, fact_player_price tablolarında veri var

❌ **Sorun Göstergeleri:**
- Rate-limit hatası (429 Too Many Requests) → Rate limit ayarlarını kontrol et
- HTML parse hatası → SteamCharts HTML yapısı değişmiş olabilir
- Database constraint error → Veri tiplerini ve NULL değerlerini kontrol et

## Questions?

Open an issue or reach out to the maintainer.
