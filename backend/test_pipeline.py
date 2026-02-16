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

if __name__ == "__main__":
    asyncio.run(test_pipeline())
