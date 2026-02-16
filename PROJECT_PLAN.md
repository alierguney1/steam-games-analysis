# Steam Oyuncu Tutundurma Analizi — Teknik Proje Planı

## Proje Genel Bakış

**Steam Oyuncu Tutundurma Analizi ve Talep Esnekliğinin Nedensel Modellenmesi**

Oyun sektöründeki anlık rekabet, oyuncu sayısının korunması ve fiyat/indirim stratejilerinin optimize edilmesi etrafında şekillenir. Bu proje, oyun fiyatları ile eşzamanlı oyuncu sayıları arasındaki karmaşık ilişkiyi modelleyerek doğrudan ekonomik iş kararlarına etki edecek bir analitik mimari sunar.

### Temel Değer Önerisi

- **Nedensel Çıkarım (Causal Inference)**: Fiyat değişikliklerinin oyuncu sayısına gerçek etkisini ölçme
- **Hayatta Kalma Analizi (Survival Analysis)**: Oyuncu terk (churn) oranlarının modellenmesi
- **Hibrit Veri Pipeline**: API + Web Scraping entegrasyonu
- **Production-Ready Mimari**: Docker, PostgreSQL Star Schema, FastAPI, React

---

## 1. Project Directory Structure

```
steam-games-analysis/
├── docker/
│   ├── docker-compose.yml          # PostgreSQL + Backend + Frontend + Scheduler
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── postgres/
│       └── init.sql                 # Star schema DDL + seed data
│
├── backend/
│   ├── pyproject.toml               # Dependencies (fastapi, aiohttp, bs4, statsmodels, lifelines, asyncpg, apscheduler)
│   ├── alembic.ini                  # DB migrations config
│   ├── alembic/
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app factory, lifespan events, CORS
│   │   ├── config.py                # Pydantic Settings (DB_URL, API keys, rate limits)
│   │   │
│   │   ├── api/                     # API Layer (REST endpoints)
│   │   │   ├── __init__.py
│   │   │   ├── router.py            # Top-level router aggregator
│   │   │   ├── games.py             # /api/games — CRUD & search
│   │   │   ├── analytics.py         # /api/analytics — DiD results, survival curves
│   │   │   ├── ingestion.py         # /api/ingestion — trigger manual ETL, status
│   │   │   └── dashboard.py         # /api/dashboard — aggregated metrics for frontend
│   │   │
│   │   ├── db/                      # Database Layer
│   │   │   ├── __init__.py
│   │   │   ├── session.py           # AsyncPG connection pool / SQLAlchemy async session
│   │   │   ├── models.py            # SQLAlchemy ORM models (Star Schema)
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       ├── game_repo.py     # dim_game CRUD
│   │   │       ├── price_repo.py    # fact_price_player CRUD
│   │   │       └── analysis_repo.py # Analiz sonuçları CRUD
│   │   │
│   │   ├── ingestion/               # Data Ingestion Layer (ETL)
│   │   │   ├── __init__.py
│   │   │   ├── base_scraper.py      # Abstract BaseScraper (aiohttp, rate-limit, retry)
│   │   │   ├── steamspy_client.py   # SteamSpy API client (extends BaseScraper)
│   │   │   ├── steamcharts_scraper.py  # SteamCharts HTML scraper (extends BaseScraper)
│   │   │   ├── steam_store_client.py   # Steam Store API (fiyat/indirim verisi)
│   │   │   ├── merger.py            # Hybrid merge strategy (API + Scraping birleştirme)
│   │   │   └── loader.py            # PostgreSQL'e bulk upsert (COPY / batch insert)
│   │   │
│   │   ├── analysis/                # Analytical Modeling Layer
│   │   │   ├── __init__.py
│   │   │   ├── did_model.py         # Difference-in-Differences (statsmodels OLS)
│   │   │   ├── survival.py          # Kaplan-Meier + Cox PH (lifelines)
│   │   │   ├── elasticity.py        # Price elasticity of demand hesaplama
│   │   │   └── utils.py             # Ortak yardımcı fonksiyonlar (cohort oluşturma, vb.)
│   │   │
│   │   ├── scheduler/               # APScheduler Jobs
│   │   │   ├── __init__.py
│   │   │   └── jobs.py              # Günlük/saatlik ETL job tanımları
│   │   │
│   │   └── schemas/                 # Pydantic request/response models
│   │       ├── __init__.py
│   │       ├── game.py
│   │       ├── analytics.py
│   │       └── ingestion.py
│   │
│   └── tests/
│       ├── conftest.py              # Fixtures (test DB, mock HTTP responses)
│       ├── test_ingestion/
│       │   ├── test_steamspy.py
│       │   ├── test_steamcharts.py
│       │   └── test_merger.py
│       ├── test_analysis/
│       │   ├── test_did_model.py
│       │   └── test_survival.py
│       └── test_api/
│           └── test_endpoints.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts               # Vite bundler
│   ├── tsconfig.json
│   ├── public/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                     # Axios/fetch wrapper, endpoint tanımları
│   │   │   └── client.ts
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Header.tsx
│   │   │   ├── charts/
│   │   │   │   ├── KaplanMeierChart.tsx    # D3.js ile survival curve
│   │   │   │   ├── DiDChart.tsx            # Treatment vs Control zaman serisi
│   │   │   │   ├── PlayerTrendChart.tsx    # Recharts ile oyuncu trendi
│   │   │   │   └── ElasticityHeatmap.tsx   # Tür bazlı esneklik ısı haritası
│   │   │   ├── tables/
│   │   │   │   └── GameTable.tsx
│   │   │   └── filters/
│   │   │       └── GenreFilter.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx         # Ana dashboard
│   │   │   ├── GameDetail.tsx        # Tekil oyun detay sayfası
│   │   │   ├── SurvivalAnalysis.tsx  # Kaplan-Meier sayfası
│   │   │   ├── CausalAnalysis.tsx    # DiD sonuçları sayfası
│   │   │   └── DataStatus.tsx        # ETL pipeline durumu
│   │   ├── hooks/
│   │   │   └── useAnalytics.ts       # Custom data fetching hooks
│   │   └── styles/
│   │       └── globals.css           # Tailwind CSS
│   └── index.html
│
├── notebooks/                        # Exploratif analiz & prototipleme
│   ├── 01_data_exploration.ipynb
│   ├── 02_did_prototype.ipynb
│   └── 03_survival_prototype.ipynb
│
├── configs/
│   ├── .env.example                  # Environment variables template
│   └── logging.yaml                  # Python logging konfigürasyonu
│
├── scripts/
│   ├── seed_initial_data.py          # İlk veri çekimi (one-time bulk)
│   └── run_analysis.py               # Manuel analiz tetikleme
│
├── .gitignore
├── .env                              # (gitignore'da) Gerçek env değişkenleri
└── README.md
```

---

## 2. Database Architecture — Star Schema (PostgreSQL)

```
                    ┌─────────────────────┐
                    │     dim_game        │
                    │─────────────────────│
                    │ game_id (PK)        │◄──────────────────────┐
                    │ appid (UNIQUE)      │                       │
                    │ name                │                       │
                    │ developer           │                       │
                    │ publisher           │                       │
                    │ release_date        │                       │
                    │ is_free             │                       │
                    │ steamspy_owners_min │                       │
                    │ steamspy_owners_max │                       │
                    │ positive_reviews    │                       │
                    │ negative_reviews    │                       │
                    │ created_at          │                       │
                    │ updated_at          │                       │
                    └─────────────────────┘                       │
                                                                  │
┌──────────────────────┐    ┌───────────────────────────────────┐ │
│    dim_genre          │    │     fact_player_price             │ │
│──────────────────────│    │───────────────────────────────────│ │
│ genre_id (PK)        │    │ fact_id (PK)                      │ │
│ genre_name (UNIQUE)  │◄───│ game_id (FK → dim_game)       ────┘ 
│ created_at           │    │ date_id (FK → dim_date)           │
└──────────────────────┘    │ genre_id (FK → dim_genre)         │
                            │ concurrent_players (avg/peak)     │
┌──────────────────────┐    │ current_price                     │
│    dim_date           │    │ original_price                    │
│──────────────────────│    │ discount_pct                      │
│ date_id (PK)         │◄───│ is_discount_active                │
│ full_date (UNIQUE)   │    │ gain_pct (SteamCharts monthly)    │
│ year                 │    │ avg_players_month                 │
│ quarter              │    │ peak_players_month                │
│ month                │    │ created_at                        │
│ day                  │    └───────────────────────────────────┘
│ day_of_week          │
│ is_weekend           │    ┌───────────────────────────────────┐
│ is_steam_sale_period │    │     dim_tag                       │
└──────────────────────┘    │───────────────────────────────────│
                            │ tag_id (PK)                       │
┌──────────────────────┐    │ tag_name (UNIQUE)                 │
│  bridge_game_tag     │    └───────────────────────────────────┘
│──────────────────────│              ▲
│ game_id (FK)         │──────────────┘
│ tag_id (FK)          │
│ (composite PK)       │
└──────────────────────┘

┌───────────────────────────────────────┐
│     analysis_results                   │
│───────────────────────────────────────│
│ result_id (PK)                        │
│ analysis_type (ENUM: 'did', 'km', 'elasticity') │
│ game_id (FK → dim_game, nullable)     │
│ genre_id (FK → dim_genre, nullable)   │
│ parameters (JSONB)                    │
│ results (JSONB)                       │
│ executed_at                           │
│ model_version                         │
└───────────────────────────────────────┘
```

### Tasarım Kararları

- **`dim_date`**: Steam büyük indirim dönemlerini (`is_steam_sale_period`) flag olarak tutar — DiD analizi için kritik.
- **`bridge_game_tag`**: Bir oyunun birden fazla etiketi olabilir (many-to-many), bu yüzden bridge table kullanılır.
- **`fact_player_price`**: SteamCharts'tan gelen aylık oyuncu verileri (avg/peak) ile Steam Store'dan gelen o andaki fiyat/indirim bilgisi tek bir fact satırında birleştirilir. Granularity: **aylık** (SteamCharts aylık veri sunduğu için).
- **`analysis_results`**: Model çıktılarını JSONB olarak saklar — frontend bu tablodan okur, her analiz çalıştığında yeni satır eklenir (audit trail).
- **Partitioning**: `fact_player_price` tablosu `date_id` üzerinden range partition ile yıllık bölünebilir (veri büyüdüğünde).

---

## 3. ETL Strategy & Data Ingestion

### 3.1 Asenkron Scraper Mimarisi

```
BaseScraper (Abstract)
├── rate_limiter: asyncio.Semaphore(1)  → saniyede 1 istek
├── retry_policy: exponential backoff (3 deneme, 2^n * 1s)
├── session: aiohttp.ClientSession (connection pool)
├── abstract fetch(url, params) → dict/str
├── abstract parse(raw_data) → List[DataModel]
└── abstract transform(parsed) → List[DBRecord]

SteamSpyClient(BaseScraper)
├── fetch_all_games()      → GET ?request=all         (60s rate limit!)
├── fetch_game_detail(appid) → GET ?request=appdetails  (1s rate limit)
├── parse() → SteamSpyGameSchema
└── Özel: "all" endpoint'i için 60 saniye bekleme, detay için 1 saniye

SteamChartsScraper(BaseScraper)
├── fetch_game_history(appid) → GET /app/{appid}
├── parse() → BeautifulSoup ile HTML table parse
├── transform() → aylık avg/peak oyuncu sayıları
└── Özel: robots.txt respected, User-Agent rotation

SteamStoreClient(BaseScraper)
├── fetch_app_details(appid) → Steam Store API
├── parse() → fiyat, indirim, tür bilgisi
└── Özel: 200 appid batch destekli
```

### 3.2 Rate-Limit Yönetimi

```python
# Konsept: Her scraper sınıfının __init__'inde tanımlı
self._semaphore = asyncio.Semaphore(1)         # Concurrent istek limiti
self._min_interval = 1.0                        # SteamSpy detay: 1s
# SteamSpy "all" endpoint için: 60.0

async def _rate_limited_fetch(self, url, params):
    async with self._semaphore:
        result = await self._session.get(url, params=params)
        await asyncio.sleep(self._min_interval)
        return result
```

### 3.3 Hybrid Merge Strategy

```
Pipeline Akışı:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 1: Discovery (Paralel)
├── SteamSpy /all  → Top 1000+ oyun appid listesi
└── Steam Store    → Trend olan oyunların appid listesi

Phase 2: Enrichment (Seri, rate-limited)
├── Her appid için SteamSpy detay çek       (1 req/s)
├── Her appid için SteamCharts history çek  (1 req/s)
└── Her appid için Steam Store price çek    (batch 200)

Phase 3: Merge (In-memory, Pandas)
├── LEFT JOIN: SteamSpy (ana kaynak) + SteamCharts (oyuncu verileri)
├── LEFT JOIN: + Steam Store (fiyat/indirim)
├── Conflict resolution:
│   ├── Fiyat: Steam Store authoritative
│   ├── Oyuncu sayısı: SteamCharts authoritative
│   └── Meta veri: SteamSpy authoritative
└── Deduplicate on (appid, month_year)

Phase 4: Load (PostgreSQL)
├── dim tabloları: UPSERT (ON CONFLICT DO UPDATE)
├── fact tablosu: INSERT + deduplicate check
└── VACUUM ANALYZE sonrası
```

### 3.4 Scheduling (APScheduler)

| Job | Sıklık | Açıklama |
|-----|--------|----------|
| `daily_price_sync` | Her gün 03:00 UTC | Steam Store'dan güncel fiyat/indirim çek |
| `weekly_full_etl` | Her Pazartesi 04:00 UTC | Tam ETL pipeline (SteamSpy + SteamCharts + Store) |
| `monthly_analysis` | Her ayın 1'i 06:00 UTC | DiD + Survival analiz modellerini çalıştır |
| `healthcheck` | Her 5 dakika | Scraper bağlantı testi, DB connection pool durumu |

---

## 4. Analytical Modeling Layer

### 4.1 Difference-in-Differences (DiD) Model

```python
class DifferenceInDifferences:
    """
    İndirim dönemlerinin eşzamanlı oyuncu sayısı üzerindeki
    nedensel etkisini ölçen Farkların Farkı modeli.

    Model Spesifikasyonu (OLS):
        Y_it = β0 + β1 * Treatment_i + β2 * Post_t + β3 * (Treatment_i × Post_t) + ε_it

        - Y_it: Oyun i'nin t zamanındaki log(avg_concurrent_players)
        - Treatment_i: 1 = indirime giren oyun, 0 = kontrol grubu
        - Post_t: 1 = indirim döneminden sonra, 0 = önce
        - β3: DİD tahmincisi (ATT - Average Treatment Effect on Treated)

    Kontrol Grubu Seçimi:
        - Aynı türde (genre), benzer fiyat aralığında, benzer oyuncu tabanına
          sahip ama aynı dönemde indirime GİRMEMİŞ oyunlar.
        - Propensity Score Matching (PSM) ile kontrol grubu eşleştirmesi
          yapılabilir (opsiyonel genişleme).
        - Paralel trend varsayımı (pre-treatment dönemi) grafikle doğrulanır.

    Deney Grubu Seçimi:
        - Belirli bir Steam Sale döneminde (Summer Sale, Winter Sale vb.)
          en az %25 indirime giren oyunlar.
        - Minimum 6 aylık pre-treatment veri gereksinimiyle.
    """

    def __init__(self, pre_periods: int = 6, post_periods: int = 3):
        """
        Args:
            pre_periods: İndirim öncesi kaç aylık veri kullanılacak
            post_periods: İndirim sonrası kaç aylık veri analiz edilecek
        """

    def prepare_panel_data(
        self,
        treatment_appids: List[int],
        control_appids: List[int],
        treatment_date: datetime,
        player_data: pd.DataFrame,    # fact_player_price'dan
    ) -> pd.DataFrame:
        """Panel veri setini oluşturur: (appid, month, players, treatment, post, treatment×post)"""

    def validate_parallel_trends(
        self,
        panel: pd.DataFrame
    ) -> dict:
        """Pre-treatment dönemde paralel trend varsayımını test eder.
        Returns: {is_valid: bool, trend_diff_pvalue: float, plot_data: dict}"""

    def fit(self, panel: pd.DataFrame) -> "DiDResult":
        """statsmodels OLS ile DiD modelini tahmin eder.
        Returns: DiDResult(att=β3, se, pvalue, ci_lower, ci_upper, r_squared, n_obs)"""

    def placebo_test(
        self,
        panel: pd.DataFrame,
        fake_treatment_date: datetime
    ) -> dict:
        """Sahte treatment tarihi ile placebo test — robustness check"""

    def event_study(
        self,
        panel: pd.DataFrame,
        leads: int = 4,
        lags: int = 4
    ) -> pd.DataFrame:
        """Event study design: her dönem için ayrı treatment etkisi.
        Paralel trend varsayımının görsel doğrulaması."""
```

### 4.2 Survival Analysis (Kaplan-Meier + Cox PH)

```python
class PlayerSurvivalAnalyzer:
    """
    Oyun yayınlandıktan sonra oyuncuların oyunu terk etme hızını (churn rate)
    modeller. Kaplan-Meier eğrileri ve Cox Proportional Hazards modeli kullanır.

    Churn Tanımı:
        - Aylık ortalama oyuncu sayısı, lansman ayı peak değerinin
          %10'unun altına düşerse "churned" kabul edilir.
        - Alternatif: Ardışık 2 ay oyuncu kaybı > %50 ise early churn.
    """

    def __init__(
        self,
        churn_threshold: float = 0.10,   # Peak'in %10'u altı = churn
        observation_window: int = 365,    # Gün cinsinden max gözlem süresi
    ): ...

    def prepare_survival_data(
        self,
        player_history: pd.DataFrame,     # fact_player_price JOIN dim_game
        genre_filter: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Returns DataFrame:
            - game_id: int
            - duration: int (gün, lansmandan churn'e veya censoring'e kadar)
            - event_observed: bool (True=churned, False=hâlâ aktif/censored)
            - genre: str
            - initial_price: float
            - is_free: bool
            - release_year: int
        """

    def fit_kaplan_meier(
        self,
        survival_data: pd.DataFrame,
        groupby: str = "genre",            # Gruplama değişkeni
        milestones: List[int] = [30, 60, 90, 180, 365]  # Gün bazlı checkpoint'ler
    ) -> dict:
        """
        Her grup için Kaplan-Meier eğrisi fit eder.
        Returns: {
            group_name: {
                survival_function: pd.Series,    # S(t) değerleri
                median_survival: float,          # Medyan sağkalım süresi (gün)
                milestone_survival: {30: 0.72, 60: 0.55, ...},
                confidence_intervals: pd.DataFrame,
                n_at_risk: pd.Series
            }
        }
        Kullanım: lifelines.KaplanMeierFitter
        """

    def fit_cox_ph(
        self,
        survival_data: pd.DataFrame,
        covariates: List[str] = ["genre", "initial_price", "is_free", "release_year"]
    ) -> dict:
        """
        Cox Proportional Hazards modeli — hangi faktörlerin churn hızına
        etki ettiğini ölçer.
        Returns: {
            hazard_ratios: dict,        # exp(coef) — HR > 1 churn artışı
            p_values: dict,
            concordance_index: float,   # Model uyumu (0.5-1.0)
            summary_df: pd.DataFrame,
            proportionality_test: dict  # PH varsayımı test sonucu
        }
        Kullanım: lifelines.CoxPHFitter
        """

    def compare_groups(
        self,
        survival_data: pd.DataFrame,
        group_col: str = "genre"
    ) -> dict:
        """Log-rank test ile gruplar arası sağkalım farkını test eder.
        Returns: {test_statistic: float, p_value: float, is_significant: bool}
        Kullanım: lifelines.statistics.logrank_test
        """

    def plot_data(
        self,
        km_results: dict,
        output_format: str = "json"       # Frontend için JSON, notebook için matplotlib
    ) -> dict:
        """Kaplan-Meier eğrisi verilerini frontend-ready JSON formatına çevirir."""
```

### 4.3 Price Elasticity

```python
class PriceElasticityAnalyzer:
    """
    Fiyat-talep esnekliğini oyun türüne göre hesaplar.
    Ed = (%ΔQ) / (%ΔP)

    - |Ed| > 1: Elastik (fiyat düşünce oyuncu oransal olarak daha çok artar)
    - |Ed| < 1: İnelastik
    - |Ed| = 1: Birim elastik
    """

    def calculate_arc_elasticity(
        self,
        price_player_data: pd.DataFrame,   # fact tablosundan
        groupby: str = "genre"
    ) -> pd.DataFrame:
        """Her tür için ark esnekliği hesaplar."""

    def regression_elasticity(
        self,
        data: pd.DataFrame
    ) -> dict:
        """Log-log regresyon ile esneklik katsayısı tahmin eder.
        ln(Players) = α + β * ln(Price) + controls + ε
        β = esneklik katsayısı
        """
```

---

## 5. API Endpoints (FastAPI)

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/games` | Oyun listesi (filtreli, paginated) |
| GET | `/api/games/{appid}` | Tekil oyun detayı + tarihsel veriler |
| GET | `/api/analytics/did` | DiD analiz sonuçları (genre/sale dönemi filtreli) |
| GET | `/api/analytics/survival` | Kaplan-Meier eğri verileri |
| GET | `/api/analytics/elasticity` | Tür bazlı esneklik sonuçları |
| POST | `/api/ingestion/trigger` | Manuel ETL tetikleme |
| GET | `/api/ingestion/status` | Pipeline durumu (son çalışma, hata logları) |
| GET | `/api/dashboard/summary` | Toplam oyun, ortalama churn, vb. KPI'lar |
| WS | `/ws/live-players` | Opsiyonel: canlı oyuncu sayısı stream |

---

## 6. Frontend Sayfa Yapısı (React)

| Sayfa | İçerik |
|-------|--------|
| **Dashboard** | KPI kartları (toplam oyun, ort. churn, ort. esneklik), Top 10 trend, genre dağılımı pie chart |
| **Game Detail** | Seçili oyunun fiyat vs oyuncu zaman serisi (dual-axis Recharts), indirim dönemleri overlay |
| **Causal Analysis** | DiD interaktif grafik: treatment vs control (D3.js), β3 katsayısı ve CI gösterimi, event study plot |
| **Survival Analysis** | Kaplan-Meier eğrileri (D3.js), genre dropdown ile filtreleme, milestone tablosu (30/60/90 gün) |
| **Data Status** | ETL job listesi, son çalışma zamanları, hata logları, manuel tetikleme butonu |

---

## 7. Docker Compose Servisleri

| Servis | Image/Build | Port | Açıklama |
|--------|-------------|------|----------|
| `postgres` | `postgres:16-alpine` | 5432 | Star schema + init.sql |
| `backend` | `backend.Dockerfile` | 8000 | FastAPI + APScheduler |
| `frontend` | `frontend.Dockerfile` | 3000 | React (Vite dev server / nginx prod) |

---

## 8. Technology Stack

### Backend
- **Framework**: FastAPI (async, OpenAPI docs)
- **Database**: PostgreSQL 16 (Star Schema, JSONB)
- **ORM**: SQLAlchemy 2.0 (async)
- **Migration**: Alembic
- **HTTP Client**: aiohttp (async scraping)
- **HTML Parser**: BeautifulSoup4
- **Statistical Models**: statsmodels (DiD, OLS)
- **Survival Analysis**: lifelines (Kaplan-Meier, Cox PH)
- **Data Processing**: pandas, numpy
- **Scheduling**: APScheduler
- **Testing**: pytest, pytest-asyncio, aioresponses

### Frontend
- **Framework**: React 18 + TypeScript
- **Bundler**: Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts (standart grafikler) + D3.js (özel grafikler)
- **HTTP Client**: Axios
- **State Management**: React Query (server state)
- **Routing**: React Router

### DevOps
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions (lint, test, build)
- **Environment Management**: python-dotenv

---

## 9. Verification & Testing Strategy

### Unit Tests
- **Scrapers**: Mock HTTP responses (`aioresponses`), rate-limit logic validation
- **DiD Model**: Sentetik veri ile bilinen β3 katsayısının doğrulanması
- **Survival Analysis**: `lifelines` referans değerleriyle output karşılaştırma
- **Repository Layer**: Test DB ile CRUD operasyon doğrulama

### Integration Tests
- **ETL Pipeline**: Mock veri → scraping → merge → DB load → validation queries
- **API Endpoints**: FastAPI TestClient ile endpoint response validation
- **Database**: Star schema constraint'leri, FK integrity check

### Smoke Tests
- `docker-compose up` → tüm servisler healthy
- Frontend dashboard render kontrolü
- PostgreSQL connection pool health check
- En az 1 oyun verisi görünürlük testi

### Analytical Validation
- **DiD**: 
  - Paralel trend varsayımı: p-value > 0.05
  - Placebo test: Sahte treatment tarihinde β3 ≈ 0 (istatistiksel olarak anlamsız)
- **Kaplan-Meier**: 
  - Survival function monotonicity check (azalmayan)
  - Confidence intervals overlap kontrolü
- **Cox PH**: 
  - Proportional hazards varsayımı: Schoenfeld residuals test

---

## 10. Development Roadmap

### Phase 1: Foundation (Hafta 1-2)
- [ ] Docker Compose environment setup
- [ ] PostgreSQL Star Schema DDL oluşturma
- [ ] FastAPI base structure + config management
- [ ] React + Vite + Tailwind boilerplate

### Phase 2: Data Ingestion (Hafta 3-4)
- [ ] BaseScraper abstract class implementation
- [ ] SteamSpyClient + rate-limit logic
- [ ] SteamChartsScraper + BeautifulSoup parser
- [ ] SteamStoreClient + batch API handling
- [ ] Hybrid merge strategy implementation
- [ ] PostgreSQL loader (bulk upsert)

### Phase 3: Analytics (Hafta 5-6)
- [ ] Difference-in-Differences model class
- [ ] Kaplan-Meier survival analysis
- [ ] Cox Proportional Hazards model
- [ ] Price elasticity calculator
- [ ] Analysis results repository

### Phase 4: API Layer (Hafta 7)
- [ ] Games CRUD endpoints
- [ ] Analytics endpoints (DiD, survival, elasticity)
- [ ] Ingestion trigger endpoints
- [ ] Dashboard summary endpoint

### Phase 5: Frontend (Hafta 8-9)
- [ ] Layout components (Sidebar, Header)
- [ ] Dashboard page + KPI cards
- [ ] Game Detail page + trend charts
- [ ] Causal Analysis page + DiD visualization (D3.js)
- [ ] Survival Analysis page + Kaplan-Meier curves (D3.js)
- [ ] Data Status page + ETL monitoring

### Phase 6: Automation & Testing (Hafta 10)
- [ ] APScheduler job definitions
- [ ] Unit tests (scraper, models, API)
- [ ] Integration tests (ETL pipeline)
- [ ] Analytical validation (DiD, KM)

### Phase 7: Documentation & Deployment (Hafta 11-12)
- [ ] API documentation (Swagger/ReDoc)
- [ ] User guide + analytical methodology doc
- [ ] Docker production build optimization
- [ ] README portfolio showcase

---

## 11. Key Design Decisions

| Karar | Seçenek | Gerekçe |
|-------|---------|---------|
| **Frontend Framework** | React + Recharts/D3.js | Komponent bazlı mimari, zengin ekosistem, D3.js ile tam kontrol |
| **Backend Framework** | FastAPI | Async native (scraper'larla uyum), otomatik OpenAPI docs, modern |
| **Scheduling** | APScheduler | Ekstra servis gerektirmez, FastAPI lifespan'a entegre, yeterli |
| **Deployment** | Docker Compose (lokal) | Portfolyo gösterimi için yeterli, cloud-ready extensible |
| **Fact Granularity** | Aylık | SteamCharts aylık veri sunuyor, doğal granularity |
| **Merge Strategy** | LEFT JOIN (SteamSpy ana) | SteamSpy appid discovery için authoritative, diğerleri zenginleştirme |

---

## 12. Expected Challenges & Mitigation

| Challenge | Mitigation |
|-----------|------------|
| **SteamCharts HTML değişikliği** | BeautifulSoup selector'ları esnek tut, version tracking, fallback logic |
| **Rate-limit aşımı** | Semaphore + exponential backoff + IP rotation (proxy pool - opsiyonel) |
| **DiD paralel trend ihlali** | Alternatif kontrol grubu seçimi, PSM ile matching, robustness check |
| **Veri eksikliği (bazı oyunların SteamCharts'ta olmaması)** | LEFT JOIN ile eksik veriyi tolere et, minimum veri threshold filtresi |
| **Frontend performans (binlerce oyun)** | Virtualized list (react-window), server-side pagination, lazy loading |

---

## 13. Portfolio Showcase Points

Bu proje şu yetkinlikleri kanıtlar:

✅ **Nedensel Çıkarım (Causal Inference)**: DiD modeli ile "korelasyon ≠ nedensellik" ilkesine hakim olduğunuzu gösterir — e-ticaret, pricing, product takımları için kritik.

✅ **Survival Analysis**: Churn modeling, customer lifetime value (CLV) hesaplamaları için temel — SaaS ve oyun sektörlerinde doğrudan uygulanabilir.

✅ **Hibrit Veri Pipeline**: API + Web Scraping entegrasyonu — gerçek dünya veri kaynaklarının asimetrik yapısını yönetme.

✅ **Production-Ready Mimari**: Docker, PostgreSQL Star Schema, async Python, REST API, React frontend — end-to-end ownership.

✅ **Statistical Rigor**: Paralel trend testi, placebo test, proportionality test — akademik titizlik + iş dünyası uygulaması.

---

## 14. Next Steps

1. **Environment Setup**: Docker Compose dosyalarını oluştur, PostgreSQL init.sql scriptini yaz
2. **Backend Skeleton**: FastAPI app + config + logging infrastructure
3. **First Scraper**: SteamSpy client ile ilk veri çekimini gerçekleştir
4. **Database Load**: dim_game tablosuna ilk 100 oyunu yükle, doğrula
5. **Frontend Bootstrap**: React + Vite projesi oluştur, dummy dashboard render et

---

**Son Güncelleme**: 16 Şubat 2026  
**Proje Sahibi**: Ali Erguney  
**Repository**: [steam-games-analysis](https://github.com/alierguney1/steam-games-analysis)
