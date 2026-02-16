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

Swagger arayüzünde mevcut endpoint'leri göreceksiniz. Her birini "Try it out" butonuyla doğrudan test edebilirsiniz.

**Sağlık kontrolü (terminal'den):**
```bash
curl http://localhost:8000/api/health
```

Beklenen yanıt:
```json
{"status": "healthy"}
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

## Adım 6: Frontend'i Kontrol Edin

Tarayıcınızda **http://localhost:5173** adresini açın.

React arayüzünün yüklendiğini ve çalıştığını doğrulayın.

---

## Adım 7: Testleri Çalıştırın

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
- ✅ Frontend arayüzü yüklenir
- ✅ `make test` testleri başarıyla geçer
