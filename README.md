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

## � Veri Pipeline'ı: Teknik Dokümantasyon

> Bu bölüm, projenin veri kaynaklarını, veri formatlarını, birleştirme stratejisini ve veritabanı yapısını
> giriş seviyesindeki bir data scientist'in anlayabileceği düzeyde açıklar.

### 1. Veri Kaynakları

Bu proje, Steam oyun ekosisteminden veri toplamak için **üç farklı kaynak** kullanır. Her kaynak farklı türde bilgi sağlar ve farklı teknik yöntemlerle erişilir.

#### 1.1. SteamSpy API (`steamspy_client.py`)

| Özellik | Detay |
|---------|-------|
| **URL** | `https://steamspy.com/api.php` |
| **Erişim Yöntemi** | REST API (JSON) |
| **Rate Limit** | `/all` endpoint'i: 60 sn bekleme; `/appdetails`: 1 sn/istek |
| **Rol** | Oyun metadata'sı ve keşif için **birincil kaynak** |

**Ne veri gelir?** SteamSpy, Steam'deki oyunların topluluk istatistiklerini toplar. API'den gelen ham JSON şuna benzer:

```json
{
  "appid": 730,
  "name": "Counter-Strike 2",
  "developer": "Valve",
  "publisher": "Valve",
  "positive": 7200000,
  "negative": 1100000,
  "owners": "50,000,000 .. 100,000,000",
  "average_forever": 32000,
  "average_2weeks": 1200,
  "ccu": 850000,
  "price": 0,
  "initialprice": 0,
  "discount": 0,
  "tags": {"FPS": 9500, "Shooter": 8700, "Competitive": 7200},
  "genre": "Action, Free to Play",
  "languages": "English, Turkish, ..."
}
```

**Parse işlemi sırasında neler yapılır:**
- `owners` alanı ("50,000,000 .. 100,000,000") parse edilerek `owners_min` ve `owners_max` olarak ayrılır
- `tags` dict'inden benzersiz tag listesi çıkarılır → `dim_tag` tablosuna yazılır
- `genre` virgülle ayrılmış string'den genre listesi çıkarılır → `dim_genre` tablosuna yazılır

**Transform çıktısı:** SteamSpy client'ın `transform()` metodu dört ayrı liste döndürür:

```python
{
    "games": [...],       # dim_game tablosuna gidecek oyun bilgileri
    "tags": [...],        # dim_tag tablosuna gidecek tag'ler
    "genres": [...],      # dim_genre tablosuna gidecek genre'ler
    "raw_games": [...]    # Bridge tablo oluşturmak için ham veri (tag-oyun ilişkisi)
}
```

#### 1.2. SteamCharts Scraper (`steamcharts_scraper.py`)

| Özellik | Detay |
|---------|-------|
| **URL** | `https://steamcharts.com/app/{appid}` |
| **Erişim Yöntemi** | Web Scraping (HTML → BeautifulSoup ile parse) |
| **Rate Limit** | 2 sn/istek (robots.txt'e saygılı) |
| **Rol** | Oyuncu sayıları için **birincil kaynak** |

**Ne veri gelir?** SteamCharts bir API sunmaz, bunun yerine HTML sayfaları scrape edilir. Sayfadaki tablo şu sütunları içerir:

```
| Month         | Avg. Players | Gain    | % Gain  | Peak Players |
|---------------|------------- |---------|---------|-------------- |
| January 2024  | 32,456       | +1,234  | +3.95%  | 65,789       |
| December 2023 | 31,222       | -500    | -1.58%  | 60,123       |
```

**Parse işlemi sırasında neler yapılır:**

1. HTML, `BeautifulSoup` ile DOM ağacına dönüştürülür
2. `<table class="common-table">` bulunur
3. Her satırdan ay/yıl, ortalama oyuncu, peak oyuncu, değişim yüzdesi parse edilir
4. Sayısal değerlerdeki virgüller temizlenir (ör. "32,456" → 32456)
5. Yüzde değerleri float'a çevrilir (ör. "+3.95%" → 3.95)
6. Ay isimleri datetime objelerine dönüştürülür (ör. "January 2024" → month=1, year=2024)

**Transform çıktısı:** Her kayıt bir "fact record" olur:

```python
{
    "appid": 730,
    "month": 1,
    "year": 2024,
    "concurrent_players_avg": 32456,
    "concurrent_players_peak": 65789,
    "gain_pct": 3.95
}
```

#### 1.3. Steam Store API (`steam_store_client.py`)

| Özellik | Detay |
|---------|-------|
| **URL** | `https://store.steampowered.com/api/appdetails?appids={id}` |
| **Erişim Yöntemi** | REST API (JSON) |
| **Rate Limit** | 1.5 sn/istek, batch desteği (200 appid/batch) |
| **Rol** | Fiyat ve indirim bilgisi için **birincil kaynak** |

**Ne veri gelir?** Steam'in resmi API'sinden gelen JSON iç içe geçmiş (nested) bir yapıdadır:

```json
{
  "730": {
    "success": true,
    "data": {
      "name": "Counter-Strike 2",
      "is_free": true,
      "type": "game",
      "release_date": {"date": "Aug 21, 2012"},
      "developers": ["Valve"],
      "publishers": ["Valve"],
      "price_overview": {
        "currency": "USD",
        "initial": 1499,
        "final": 749,
        "discount_percent": 50
      }
    }
  }
}
```

**Dikkat edilmesi gereken noktalar:**
- Fiyatlar **cent** cinsinden gelir → 100'e bölünerek dolara çevrilir: `1499 → 14.99`
- `release_date` formatı "Aug 21, 2012" → `datetime.strptime` ile parse edilir
- Ücretsiz oyunlarda `price_overview` alanı boş gelir

**Transform çıktısı:** İki ayrı liste üretilir:

```python
{
    "pricing_facts": [     # fact tablosuna gidecek fiyat metrikleri
        {
            "appid": 730,
            "current_price": 7.49,
            "original_price": 14.99,
            "discount_pct": 50,
            "is_discount_active": True
        }
    ],
    "game_updates": [      # dim_game tablosundaki bilgileri güncellemek için
        {
            "appid": 730,
            "is_free": False,
            "release_date": "2012-08-21",
            "developer": "Valve",
            "publisher": "Valve"
        }
    ]
}
```

### 2. Her Kaynaktaki Ortak Altyapı: BaseScraper

Üç client da `BaseScraper` soyut sınıfından türer. Bu sınıf şunları sağlar:

- **Rate Limiting**: `asyncio.Semaphore` ile eş zamanlı istek sayısı kontrolü
- **Retry Logic**: Başarısız istekler üstel geri çekilme (exponential backoff) ile yeniden denenir
- **Async HTTP**: `aiohttp.ClientSession` ile non-blocking I/O
- **User-Agent**: Gerçek tarayıcı gibi gözükmek için özel header

```
Her client şu lifecycle'ı izler:
  fetch()  →  ham veriyi indir (JSON veya HTML)
  parse()  →  ham veriyi yapılandırılmış dict listesine dönüştür
  transform()  →  veritabanına yazılmaya hazır formata getir
```

### 3. Veri Birleştirme (Merge) Stratejisi

`DataMerger` sınıfı üç kaynağı **hybrid merge** stratejisiyle birleştirir. Her kaynak belirli alanlar için **otorite** kabul edilir:

```
┌────────────────────────────────────────────────────────────┐
│                    MERGE STRATEJİSİ                        │
├────────────────┬───────────────────────────────────────────┤
│   Kaynak       │  Otoritesi (Birincil olduğu alanlar)     │
├────────────────┼───────────────────────────────────────────┤
│   SteamSpy     │  Oyun keşfi, tag'ler, genre'ler,         │
│                │  sahip sayısı tahmini, review'ler         │
├────────────────┼───────────────────────────────────────────┤
│   SteamCharts  │  Aylık ortalama/peak oyuncu sayıları,    │
│                │  oyuncu trendleri (gain_pct)              │
├────────────────┼───────────────────────────────────────────┤
│   Steam Store  │  Güncel fiyat, indirim oranı, çıkış      │
│                │  tarihi, geliştirici/yayıncı bilgisi      │
└────────────────┴───────────────────────────────────────────┘
```

#### Birleştirme Adımları

**Adım 1 — Oyun Metadata Birleştirme (`_merge_game_metadata`):**

SteamSpy ve Steam Store'dan gelen oyun bilgileri `pandas.DataFrame.merge()` ile birleştirilir:
- Yöntem: **LEFT JOIN** (SteamSpy'daki tüm oyunlar korunur)
- Birleştirme anahtarı: `appid`
- `is_free`, `release_date`, `developer`, `publisher` alanlarında **Steam Store** verisi önceliklidir
- Steam Store'da bulunmayan oyunlar için SteamSpy değerleri korunur (`.combine_first()`)

**Adım 2 — Fact Kayıtları Birleştirme (`_merge_fact_records`):**

SteamCharts'tan gelen aylık oyuncu metrikleri + Steam Store'dan gelen fiyat bilgileri birleştirilir:
- Yöntem: **LEFT JOIN** on `appid`
- SteamCharts'tan: `concurrent_players_avg`, `concurrent_players_peak`, `gain_pct`
- Steam Store'dan: `current_price`, `original_price`, `discount_pct`, `is_discount_active`

**Adım 3 — Bridge Kayıtları (`_create_bridge_records`):**

SteamSpy'ın ham verisindeki `tags` dict'inden oyun-tag ilişkileri oluşturulur:
- Her oyun için tüm tag isimleri `(appid, tag_name)` çiftlerine dönüştürülür

**Son çıktı (merge sonrası):**

```python
{
    "dim_game":           [...],   # Oyun bilgileri (SteamSpy + Store)
    "dim_tag":            [...],   # Benzersiz tag listesi
    "dim_genre":          [...],   # Benzersiz genre listesi
    "fact_player_price":  [...],   # Aylık oyuncu + fiyat metrikleri
    "bridge_game_tag":    [...],   # Oyun-tag ilişki kayıtları
}
```

### 4. Veritabanı Yapısı: Star Schema

Veriler PostgreSQL'de **star schema** (yıldız şeması) ile tutulur. Bu yapı analitik sorgular için optimize edilmiştir.

```
                        ┌──────────────┐
                        │   dim_date   │
                        │──────────────│
                        │ date_id (PK) │
                        │ full_date    │
                        │ year         │
                        │ quarter      │
                        │ month        │
                        │ day_of_week  │
                        │ is_weekend   │
                        │ is_steam_    │
                        │  sale_period │
                        └──────┬───────┘
                               │
┌──────────────┐    ┌──────────┴──────────┐    ┌──────────────┐
│   dim_game   │    │  fact_player_price   │    │  dim_genre   │
│──────────────│    │─────────────────────│    │──────────────│
│ game_id (PK) │◄──│ game_id (FK)        │    │ genre_id(PK) │
│ appid (UQ)   │    │ date_id (FK)        │──►│ genre_name   │
│ name         │    │ genre_id (FK)       │    └──────────────┘
│ developer    │    │ concurrent_players_ │
│ publisher    │    │  avg               │
│ release_date │    │ concurrent_players_ │
│ is_free      │    │  peak              │
│ owners_min   │    │ gain_pct           │
│ owners_max   │    │ current_price      │
│ positive_rev │    │ original_price     │
│ negative_rev │    │ discount_pct       │
└──────┬───────┘    │ is_discount_active │
       │            └────────────────────┘
       │
       │
┌──────┴────────────┐    ┌──────────────┐
│ bridge_game_tag   │    │   dim_tag     │
│───────────────────│    │──────────────│
│ game_id (FK, PK)  │──►│ tag_id (PK)  │
│ tag_id  (FK, PK)  │    │ tag_name     │
└───────────────────┘    └──────────────┘
```

#### Neden Star Schema?

- **Basit JOIN'ler**: Fact tablosu merkezde, dimension tabloları etrafında → karmaşık sorgular bile 1-2 JOIN ile yazılabilir
- **Analitik Uygunluk**: "X ayında Y oyununun fiyatı neydi, oyuncu sayısı kaçtı?" gibi sorular doğal olarak modellenir
- **Esneklik**: Yeni bir dimension eklemek (ör. `dim_region`) mevcut yapıyı bozmadan mümkündür

#### Tablolar ve Rolleri

| Tablo | Tip | Açıklama |
|-------|-----|----------|
| `dim_game` | Dimension | Oyun bilgileri (isim, geliştirici, sahip sayısı, review'ler) |
| `dim_date` | Dimension | Takvim bilgileri (yıl, çeyrek, ay, Steam indirim dönemi) |
| `dim_genre` | Dimension | Oyun türleri (Action, RPG, Strategy vb.) |
| `dim_tag` | Dimension | Kullanıcı etiketleri (FPS, Multiplayer, Open World vb.) |
| `bridge_game_tag` | Bridge | Oyun-tag çoktan-çoğa ilişkisi |
| `fact_player_price` | Fact | Aylık oyuncu metrikleri + fiyat bilgisi (ölçüm verileri) |
| `analysis_results` | Sonuç | Analitik model çıktıları (JSONB formatında) |

### 5. Yükleme (Load) Süreci

`DataLoader` sınıfı, birleştirilmiş verileri PostgreSQL'e **upsert** (insert or update) mantığıyla yazar:

```
Yükleme sırası (foreign key bağımlılıkları nedeniyle):
  1. dim_genre   → Önce genre'ler (bağımsız)
  2. dim_tag     → Sonra tag'ler (bağımsız)
  3. dim_game    → Oyunlar (bağımsız ama genre/tag'den sonra güvenli)
  4. dim_date    → Tarihler (otomatik oluşturulur)
  5. fact_player_price → Fact kayıtları (game_id ve date_id gerektirir)
  6. bridge_game_tag   → Bridge kayıtları (game_id ve tag_id gerektirir)
```

- PostgreSQL'in `INSERT ... ON CONFLICT DO UPDATE` özelliği kullanılır
- Aynı `appid`'li oyun tekrar geldiğinde güncellenir, duplicate oluşmaz
- Bridge tabloda `ON CONFLICT DO NOTHING` ile gereksiz tekrar engellenir

### 6. Pipeline Akış Özeti

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  SteamSpy   │     │ SteamCharts │     │ Steam Store  │
│   (API)     │     │  (Scraping) │     │   (API)      │
└──────┬──────┘     └──────┬──────┘     └──────┬───────┘
       │ JSON              │ HTML              │ JSON
       ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐    ┌──────────────┐
│   fetch()    │   │   fetch()    │    │   fetch()    │
│   parse()    │   │   parse()    │    │   parse()    │
│  transform() │   │  transform() │    │  transform() │
└──────┬───────┘   └──────┬───────┘    └──────┬───────┘
       │                  │                    │
       └──────────────────┼────────────────────┘
                          ▼
                 ┌─────────────────┐
                 │   DataMerger    │
                 │  (Hybrid Join)  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │   DataLoader    │
                 │ (Upsert → PG)  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │   PostgreSQL    │
                 │  (Star Schema)  │
                 └─────────────────┘
```

## �📁 Project Structure

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
- ✅ **Phase 4**: API Layer
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