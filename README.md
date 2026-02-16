# Steam Games Analysis Platform

**Steam Oyuncu Tutundurma Analizi ve Talep Esnekliğinin Nedensel Modellenmesi**

A comprehensive analytical platform for analyzing Steam game player retention and causal pricing effects using advanced statistical methods including Difference-in-Differences (DiD), Survival Analysis, and Price Elasticity modeling.

## 🎯 Project Overview

This platform combines data engineering, causal inference, and modern web development to provide actionable insights into:

- **Causal Impact Analysis**: Measure the true effect of pricing changes on player counts using DiD methodology
- **Player Retention Modeling**: Predict churn rates using Kaplan-Meier and Cox Proportional Hazards models
- **Price Elasticity**: Calculate demand elasticity across different game genres
- **Real-time Data Pipeline**: Automated ETL from SteamSpy API, SteamCharts, and Steam Store

## 🏗️ Architecture

### Technology Stack

**Backend**:
- FastAPI (Python 3.11+)
- PostgreSQL 15 with Star Schema
- SQLAlchemy (async ORM)
- APScheduler (automated jobs)
- Statistical libraries: statsmodels, lifelines, scipy

**Frontend**:
- React 18 + TypeScript
- Vite (build tool)
- TailwindCSS
- Recharts + D3.js (visualizations)
- React Query (data fetching)

**Infrastructure**:
- Docker Compose
- PostgreSQL with optimized indexes
- Async Python for concurrent scraping

### Database Schema

```
Star Schema Design:
- dim_game: Game metadata
- dim_date: Calendar with Steam sale periods
- dim_genre: Game genres
- dim_tag: Game tags (many-to-many)
- fact_player_price: Monthly player counts + pricing
- analysis_results: Model outputs (JSONB)
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/alierguney1/steam-games-analysis.git
cd steam-games-analysis
```

2. **Configure environment variables**
```bash
cp configs/.env.example .env
# Edit .env with your configuration
```

3. **Start the services**
```bash
cd docker
docker-compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Backend API (port 8000)
- Frontend application (port 5173)

4. **Access the application**
- Frontend: http://localhost:5173
- API Documentation: http://localhost:8000/api/docs
- Health Check: http://localhost:8000/health

### Development Setup

**Backend Development**:
```bash
cd backend
pip install poetry
poetry install
poetry run uvicorn app.main:app --reload
```

**Frontend Development**:
```bash
cd frontend
npm install
npm run dev
```

## 📊 Features

### 1. Difference-in-Differences (DiD) Analysis
- Measures causal effect of discount events on player counts
- Parallel trends validation
- Placebo testing for robustness
- Event study design

### 2. Survival Analysis
- Kaplan-Meier survival curves
- Cox Proportional Hazards modeling
- Churn rate predictions
- Genre-based comparisons

### 3. Price Elasticity
- Demand elasticity calculations
- Genre-specific elasticity heatmaps
- Optimal pricing recommendations

### 4. Data Pipeline
- Automated daily price updates
- Weekly full ETL from SteamSpy + SteamCharts
- Monthly analytical model runs
- Rate-limited, async scraping

## 📁 Project Structure

```
steam-games-analysis/
├── docker/                    # Docker configuration
│   ├── docker-compose.yml
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── postgres/
│       └── init.sql          # Star schema DDL
│
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── api/              # REST endpoints
│   │   ├── db/               # Database models & session
│   │   ├── ingestion/        # ETL scrapers
│   │   ├── analysis/         # Statistical models
│   │   ├── scheduler/        # APScheduler jobs
│   │   └── schemas/          # Pydantic models
│   └── tests/
│
├── frontend/                  # React frontend
│   └── src/
│       ├── components/       # React components
│       ├── pages/            # Page components
│       ├── api/              # API client
│       └── hooks/            # Custom hooks
│
├── notebooks/                 # Jupyter notebooks for analysis
├── scripts/                   # Utility scripts
└── configs/                   # Configuration files
```

## 🔬 Analytical Methods

### Difference-in-Differences (DiD)
```
Y_it = β0 + β1*Treatment_i + β2*Post_t + β3*(Treatment_i × Post_t) + ε_it

β3 = Average Treatment Effect on Treated (ATT)
```

### Kaplan-Meier Estimator
Survival function estimation for player retention:
- Time to churn analysis
- Confidence intervals
- Log-rank tests for group comparisons

### Cox Proportional Hazards
```
h(t|X) = h0(t) × exp(β1*X1 + β2*X2 + ... + βp*Xp)
```

## 📈 API Endpoints

### Games
- `GET /api/games` - List games with filters
- `GET /api/games/{id}` - Get game details
- `GET /api/games/search` - Search games

### Analytics
- `GET /api/analytics/did` - DiD analysis results
- `GET /api/analytics/survival` - Survival curves
- `GET /api/analytics/elasticity` - Price elasticity

### Ingestion
- `POST /api/ingestion/trigger` - Manual ETL trigger
- `GET /api/ingestion/status` - Pipeline status

### Dashboard
- `GET /api/dashboard/summary` - Summary metrics
- `GET /api/dashboard/metrics` - Time-series metrics

## 🧪 Testing

```bash
# Backend tests
cd backend
poetry run pytest

# Frontend tests
cd frontend
npm run test
```

## 📊 Portfolio Showcase

This project demonstrates:

✅ **Causal Inference**: DiD methodology for answering "what caused what"  
✅ **Survival Analysis**: Industry-standard churn modeling  
✅ **Data Engineering**: Hybrid API + web scraping pipeline  
✅ **Full-Stack Development**: End-to-end ownership (DB → API → UI)  
✅ **Statistical Rigor**: Hypothesis testing, validation, robustness checks  
✅ **Production Architecture**: Docker, async Python, PostgreSQL, React

## 📝 Development Roadmap

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for detailed development phases:

- ✅ **Phase 1**: Foundation (Docker, DB, FastAPI, React)
- ✅ **Phase 2**: Data Ingestion (Scrapers, ETL)
- ✅ **Phase 3**: Analytics (DiD, Survival, Elasticity)
- ⏳ **Phase 4**: API Layer
- ⏳ **Phase 5**: Frontend UI
- ⏳ **Phase 6**: Testing & Automation
- ⏳ **Phase 7**: Documentation & Deployment

## 🤝 Contributing

This is a portfolio project. Feel free to fork and adapt for your own use.

## 📄 License

MIT License - see LICENSE file for details

## 👤 Author

**Ali Erguney**
- GitHub: [@alierguney1](https://github.com/alierguney1)

---

**Last Updated**: February 16, 2026