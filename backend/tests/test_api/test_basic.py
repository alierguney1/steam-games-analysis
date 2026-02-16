"""
Basic API smoke tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test that health endpoint is accessible"""
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_root():
    """Test API root endpoint"""
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
