# Uygulamayı Test Etme Rehberi

Bu rehber, Steam Oyuncu Tutundurma Analizi uygulamasını adım adım başlatmanız ve test etmeniz için hazırlanmıştır.

---

## Ön Gereksinimler

Başlamadan önce aşağıdakilerin kurulu olduğundan emin olun:

- **Docker & Docker Compose** — Tüm servisleri ayağa kaldırmak için
- **Git** — Projeyi klonlamak için

> 💡 Bu kadar! Docker sayesinde Python, Node.js veya veritabanı kurmanıza gerek yok.

---

## Adım 1: Projeyi Hazırlayın

```bash
git clone https://github.com/alierguney1/steam-games-analysis.git
cd steam-games-analysis
make setup
```

**Ne olur?** Gerekli dizinler oluşturulur ve örnek `.env` dosyası kopyalanır.

---

## Adım 2: Servisleri Başlatın

```bash
make up
```

**Ne olur?** Aşağıdaki servisler Docker ile ayağa kalkar:

| Servis      | Adres                              | Açıklama                     |
|-------------|------------------------------------|-----------------------------|
| Frontend    | http://localhost:5173              | React arayüz                |
| Backend API | http://localhost:8000              | FastAPI sunucusu             |
| API Docs    | http://localhost:8000/api/docs     | Swagger dökümantasyonu       |
| PostgreSQL  | localhost:5432                     | Veritabanı                  |

> ⏳ İlk çalıştırmada Docker imajları indirileceği için birkaç dakika sürebilir.

**Servislerin ayakta olduğunu doğrulayın:**
```bash
make logs
```
Loglar akmaya başladığında her şey hazır demektir. Çıkmak için `Ctrl+C` basın.

---

## Adım 3: API'yi Test Edin

Tarayıcınızda **http://localhost:8000/api/docs** adresini açın.

Swagger arayüzünde artık **yeni API endpoint'lerini** göreceksiniz:

### Yeni API Endpoint'leri (Phase 4)

**Games API** (`/api/games`):
- `GET /api/games` - Oyunları listele (filtreleme, sıralama, sayfalama)
- `GET /api/games/{game_id}` - Oyun detayları
- `GET /api/games/search` - Oyun ara
- `POST /api/games` - Yeni oyun oluştur
- `PUT /api/games/{game_id}` - Oyun güncelle
- `DELETE /api/games/{game_id}` - Oyun sil

**Analytics API** (`/api/analytics`):
- `POST /api/analytics/did` - DiD analizi çalıştır
- `POST /api/analytics/survival` - Survival analizi çalıştır
- `POST /api/analytics/elasticity` - Fiyat esnekliği analizi çalıştır
- `GET /api/analytics/results` - Analiz sonuçlarını listele
- `GET /api/analytics/results/{result_id}` - Analiz sonucu detayları

**Ingestion API** (`/api/ingestion`):
- `POST /api/ingestion/trigger` - Manuel ETL tetikle
- `GET /api/ingestion/status/{job_id}` - İş durumu sorgula
- `GET /api/ingestion/status` - Genel ETL durumu
- `GET /api/ingestion/data-quality` - Veri kalite metrikleri

**Dashboard API** (`/api/dashboard`):
- `GET /api/dashboard/` - Kapsamlı dashboard verisi
- `GET /api/dashboard/summary` - Özet metrikler
- `GET /api/dashboard/top-games` - En iyi oyunlar
- `GET /api/dashboard/genre-distribution` - Tür dağılımı
- `GET /api/dashboard/time-series/players` - Zaman serisi verileri

Her endpoint'i Swagger'da "Try it out" butonuyla test edebilirsiniz.

**Sağlık kontrolü (terminal'den):**
```bash
curl http://localhost:8000/api/health
```

Beklenen yanıt:
```json
{"status": "healthy"}
```

**Dashboard özeti testi:**
```bash
curl http://localhost:8000/api/dashboard/summary
```

---

## Adım 4: Veri Toplama Pipeline'ını Test Edin

Backend container'ına bağlanıp ETL sürecini manuel tetikleyin:

```bash
docker exec -it steam-backend bash
python3
```

Aşağıdaki kodu Python interpreter'da çalıştırın:

```python
import asyncio
from app.ingestion.steamspy_client import SteamSpyClient
from app.ingestion.steamcharts_scraper import SteamChartsScraper
from app.ingestion.steam_store_client import SteamStoreClient
from app.ingestion.merger import DataMerger
from app.ingestion.loader import DataLoader
from app.db.session import get_session

async def test_pipeline():
    test_appids = [730, 570, 440, 271590, 252490]
    # CS:GO, Dota 2, TF2, GTA V, Rust

    # 1. SteamSpy'dan veri çek
    async with SteamSpyClient() as spy:
        spy_data = await spy.fetch(appids=test_appids)
        spy_parsed = spy.parse(spy_data)
        spy_transformed = spy.transform(spy_parsed)
    print("✅ SteamSpy verisi alındı")

    # 2. SteamCharts'tan oyuncu verileri çek
    async with SteamChartsScraper() as charts:
        charts_data = await charts.fetch(test_appids)
        charts_parsed = charts.parse(charts_data)
        charts_transformed = charts.transform(charts_parsed)
    print("✅ SteamCharts verisi alındı")

    # 3. Steam Store'dan fiyat bilgisi çek
    async with SteamStoreClient() as store:
        store_data = await store.fetch(test_appids)
        store_parsed = store.parse(store_data)
        store_transformed = store.transform(store_parsed)
    print("✅ Steam Store verisi alındı")

    # 4. Verileri birleştir
    merger = DataMerger()
    merged = merger.merge_game_data(
        spy_transformed, charts_transformed, store_transformed
    )
    merged['fact_player_price'] = merger.deduplicate_facts(
        merged['fact_player_price']
    )
    print(f"✅ Veriler birleştirildi:")
    print(f"   Oyunlar: {len(merged['dim_game'])}")
    print(f"   Kayıtlar: {len(merged['fact_player_price'])}")
    print(f"   Etiketler: {len(merged['dim_tag'])}")
    print(f"   Türler: {len(merged['dim_genre'])}")

    # 5. Veritabanına yükle
    session = await get_session()
    loader = DataLoader(session)
    stats = await loader.load_all(merged)
    print(f"✅ Veritabanına yüklendi: {stats}")
    await session.close()

asyncio.run(test_pipeline())
```

Çıkmak için `exit()` yazın, ardından `exit` ile container'dan çıkın.

---

## Adım 5: Veritabanını Kontrol Edin

PostgreSQL'e bağlanın:

```bash
docker exec -it steam-postgres psql -U steam_user -d steam_analytics
```

Aşağıdaki sorguları çalıştırarak verilerin yüklendiğini doğrulayın:

**Tablo sayımları:**
```sql
SELECT 'dim_game' AS tablo, COUNT(*) AS kayit FROM dim_game
UNION ALL
SELECT 'fact_player_price', COUNT(*) FROM fact_player_price
UNION ALL
SELECT 'dim_tag', COUNT(*) FROM dim_tag
UNION ALL
SELECT 'bridge_game_tag', COUNT(*) FROM bridge_game_tag;
```

**En popüler oyunlar:**
```sql
SELECT g.name, MAX(f.concurrent_players_avg) AS max_oyuncu
FROM dim_game g
JOIN fact_player_price f ON g.game_id = f.game_id
GROUP BY g.name
ORDER BY max_oyuncu DESC
LIMIT 10;
```

**Belirli bir oyunun detayı (CS:GO):**
```sql
SELECT g.name, f.concurrent_players_avg, f.current_price, f.discount_pct
FROM dim_game g
JOIN fact_player_price f ON g.game_id = f.game_id
WHERE g.appid = 730
LIMIT 5;
```

Çıkmak için `\q` yazın.

---

## Adım 6: Analitik Modülleri Test Edin (Yeni!)

Backend container'ına bağlanıp analitik modülleri test edin:

```bash
docker exec -it steam-backend bash
python3
```

### DiD (Difference-in-Differences) Analizi

```python
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from app.analysis.did_model import run_did_analysis

# Örnek veri oluştur
def create_sample_data():
    dates = [datetime(2024, 1, 1) + timedelta(days=30*i) for i in range(12)]
    
    # Treatment grubu (indirim alan oyun)
    treatment = []
    for i, date in enumerate(dates):
        treatment.append({
            "game_id": 1,
            "date": date,
            "avg_players": 1000 + (200 if i >= 6 else 0) + (i * 10),
            "current_price": 19.99,
            "discount_pct": 30.0 if i >= 6 else 0.0,
            "is_discount_active": i >= 6,
        })
    
    # Control grubu (indirim almayan oyun)
    control = []
    for i, date in enumerate(dates):
        control.append({
            "game_id": 2,
            "date": date,
            "avg_players": 1000 + (i * 10),
            "current_price": 19.99,
            "discount_pct": 0.0,
            "is_discount_active": False,
        })
    
    return pd.DataFrame(treatment), pd.DataFrame(control)

treatment_df, control_df = create_sample_data()

# DiD analizi çalıştır
results = run_did_analysis(treatment_df, control_df)

print("✅ DiD Analizi Tamamlandı!")
print(f"   ATT (Treatment Effect): {results['main_estimation']['att']:.2f}")
print(f"   P-değeri: {results['main_estimation']['p_value']:.4f}")
print(f"   Paralel trend geçerli mi?: {results['parallel_trends']['parallel_trends_valid']}")
```

### Survival (Hayatta Kalma) Analizi

```python
from app.analysis.survival import run_survival_analysis

# Örnek oyuncu verisi oluştur
player_data = []
for game_id in range(1, 21):
    for month in range(12):
        # Bazı oyunlar zamanla oyuncu kaybeder (churn)
        base = 1000
        decline = month * 100 if game_id <= 10 else 0
        player_data.append({
            "game_id": game_id,
            "date": datetime(2024, 1, 1) + timedelta(days=30*month),
            "avg_players": max(100, base - decline),
            "genre_name": "RPG" if game_id <= 10 else "Indie",
        })

df = pd.DataFrame(player_data)

# Survival analizi çalıştır
results = run_survival_analysis(
    df,
    churn_threshold_pct=0.5,
    groupby_col="genre_name",
)

print("✅ Survival Analizi Tamamlandı!")
print(f"   Churn oranı: {results['retention_metrics']['churn_rate']:.2%}")
print(f"   Retention oranı: {results['retention_metrics']['retention_rate']:.2%}")
print(f"   Medyan churn süresi: {results['retention_metrics']['median_time_to_churn_months']} ay")
```

### Price Elasticity (Fiyat Esnekliği) Analizi

```python
from app.analysis.elasticity import run_elasticity_analysis
import numpy as np

# Örnek fiyat-talep verisi oluştur
np.random.seed(42)
elasticity_data = []

for i in range(50):
    price = np.random.uniform(10, 30)
    # Talep fiyatla ters orantılı
    quantity = 1000 * (price ** -0.8) + np.random.normal(0, 50)
    
    elasticity_data.append({
        "game_id": i,
        "current_price": price,
        "avg_players": max(0, quantity),
        "genre_name": "RPG" if i < 25 else "Action",
    })

df = pd.DataFrame(elasticity_data)

# Elasticity analizi çalıştır
results = run_elasticity_analysis(
    df,
    method="log_log",
    group_by="genre_name",
)

print("✅ Elasticity Analizi Tamamlandı!")
if "overall" in results["elasticity_results"]:
    e = results["elasticity_results"]["overall"]["elasticity"]
    print(f"   Fiyat esnekliği: {e:.2f}")
    print(f"   Elastik mi?: {'Evet' if abs(e) > 1.0 else 'Hayır'}")
```

Çıkmak için `exit()` yazın.

---

## Adım 7: Frontend'i Kontrol Edin

Tarayıcınızda **http://localhost:5173** adresini açın.

### Ana Sayfalar (Phase 5)

Artık tam fonksiyonel bir React arayüzü var! Sol taraftaki navigasyon menüsünü kullanarak şu sayfalara erişebilirsiniz:

#### 1. Dashboard (Ana Sayfa)
- **Adres**: http://localhost:5173/
- **Özellikler**:
  - KPI kartları (toplam oyun, kayıt, ortalama oyuncu, aktif indirim)
  - Genel istatistikler
  - Son güncelleme bilgisi
  - Veri yoksa kullanıcı yönlendirme mesajları

#### 2. Oyunlar Sayfası
- **Adres**: http://localhost:5173/games
- **Özellikler**:
  - Oyun listesi (sayfalama ile)
  - Arama çubuğu
  - Her oyun için detay butonu
  - Geliştirici, yayıncı, çıkış tarihi bilgileri

#### 3. Oyun Detay Sayfası
- **Adres**: http://localhost:5173/games/{game_id}
- **Özellikler**:
  - Oyun bilgileri (geliştirici, yayıncı, çıkış tarihi)
  - İnceleme istatistikleri (olumlu/olumsuz)
  - SteamSpy sahip sayısı tahmini
  - Oyuncu trendi grafiği (Recharts)
  - Fiyat geçmişi grafiği

#### 4. Nedensel Analiz (DiD)
- **Adres**: http://localhost:5173/causal-analysis
- **Özellikler**:
  - Treatment ve control oyun seçimi
  - DiD analizi çalıştırma
  - ATT (Average Treatment Effect) sonuçları
  - P-değeri ve güven aralığı
  - Paralel trend testi
  - Treatment vs Control karşılaştırma grafiği
  - Placebo test sonuçları

#### 5. Survival Analizi
- **Adres**: http://localhost:5173/survival-analysis
- **Özellikler**:
  - Churn eşiği belirleme
  - Gruplama kolonu seçimi (tür, ücretsiz/ücretli, vb.)
  - Retention ve churn metrikleri
  - Kaplan-Meier survival eğrileri (Recharts)
  - Cox Proportional Hazards model sonuçları
  - Grup bazlı karşılaştırmalar

#### 6. Veri Durumu
- **Adres**: http://localhost:5173/data-status
- **Özellikler**:
  - Genel sistem durumu (sağlıklı/uyarı/hata)
  - Veri kalite metrikleri
  - Veri tazeliği bilgisi
  - Son ETL işleri tablosu
  - Pipeline istatistikleri
  - Veritabanı tablo bilgileri

### Test Adımları

1. **Dashboard'u kontrol edin**: Ana sayfada KPI kartlarının yüklendiğini doğrulayın
2. **Navigasyon'u test edin**: Sol menüden tüm sayfalara gidin
3. **Oyun listesini inceleyin**: Oyunlar sayfasında arama ve sayfalama çalıştığını doğrulayın
4. **Grafikleri kontrol edin**: Oyun detay sayfasında Recharts grafiklerinin render olduğunu görün
5. **Analiz sayfalarını test edin**: DiD ve Survival analiz formlarını doldurup çalıştırın

---

## Adım 8: Testleri Çalıştırın

Otomatik testleri çalıştırmak için:

```bash
make test
```

---

## Servisleri Durdurun

İşiniz bittiğinde:

```bash
make down
```

Tüm verileri (veritabanı dahil) sıfırlamak isterseniz:

```bash
make clean
```

---

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| Port çakışması (5173, 8000, 5432) | İlgili portu kullanan başka servisleri durdurun |
| Docker imajı bulunamadı | `make clean && make up` çalıştırın |
| Rate-limit hatası (429) | Birkaç dakika bekleyip tekrar deneyin |
| HTML parse hatası | SteamCharts site yapısı değişmiş olabilir — issue açın |
| Veritabanı bağlantı hatası | `make logs` ile PostgreSQL'in ayakta olduğunu kontrol edin |

---

## Beklenen Sonuçlar

Her şey doğru çalıştığında şunları görmelisiniz:

- ✅ `make up` ile tüm servisler sorunsuz ayağa kalkar
- ✅ API Docs (Swagger) sayfası açılır ve endpoint'ler listelenir
- ✅ Sağlık kontrolü `{"status": "healthy"}` döner
- ✅ ETL pipeline'ı 5 test oyunun verisini başarıyla toplar ve birleştirir
- ✅ Veritabanı tablolarında veri görünür
- ✅ **Analitik modüller (DiD, Survival, Elasticity) başarıyla çalışır**
- ✅ Frontend arayüzü yüklenir
- ✅ `make test` testleri başarıyla geçer

### Yeni Eklenen Analitik Özellikler

**Phase 3** ile birlikte aşağıdaki analitik modüller eklenmiştir:

1. **DiD (Difference-in-Differences)** — İndirimlerin oyuncu sayısına nedensel etkisini ölçer
2. **Survival Analysis** — Kaplan-Meier ve Cox PH ile oyuncu retention analizi
3. **Price Elasticity** — Talep esnekliği ve optimal fiyat önerileri

Bu modüller artık tam fonksiyonel ve test edilmiştir!

### Yeni Eklenen API Katmanı (Phase 4)

**Phase 4** ile birlikte REST API katmanı tamamlanmıştır:

1. **Games API** — CRUD operasyonları, arama, filtreleme, sayfalama
2. **Analytics API** — DiD, Survival ve Elasticity analizlerini tetikleme
3. **Ingestion API** — Manuel ETL tetikleme, durum izleme, veri kalitesi
4. **Dashboard API** — Özet metrikler, top oyunlar, tür dağılımı, zaman serileri

Tüm endpoint'ler Swagger UI'da (`/api/docs`) görülebilir ve test edilebilir!

### Yeni Eklenen Frontend Katmanı (Phase 5)

**Phase 5** ile birlikte tam fonksiyonel React frontend tamamlanmıştır:

1. **Layout Components** — Sidebar navigasyon ve Header ile tutarlı sayfa düzeni
2. **Dashboard Sayfası** — KPI kartları, özet metrikler ve genel bakış
3. **Oyunlar Sayfası** — Arama, filtreleme, sayfalama ile oyun listesi
4. **Oyun Detay Sayfası** — Oyuncu ve fiyat trend grafikleri (Recharts)
5. **Nedensel Analiz Sayfası** — DiD modeli sonuçları ve görselleştirme
6. **Survival Analiz Sayfası** — Kaplan-Meier eğrileri ve Cox PH sonuçları
7. **Veri Durumu Sayfası** — ETL pipeline monitoring ve veri kalitesi metrikleri

Artık uçtan uca çalışan bir analitik platform var!
