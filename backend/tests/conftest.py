"""Pytest configuration and fixtures."""
import pytest
import os
import sys
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch('utils.cache.get_redis_client') as mock:
        mock_redis_client = Mock()
        mock_redis_client.get.return_value = None
        mock_redis_client.setex.return_value = True
        mock_redis_client.delete.return_value = True
        mock_redis_client.ping.return_value = True
        mock.return_value = mock_redis_client
        yield mock_redis_client


@pytest.fixture
def mock_agent():
    """Mock main agent."""
    with patch('agents.main_agent.get_main_agent') as mock:
        mock_agent = Mock()
        mock_agent.invoke.return_value = {
            "messages": [Mock(content="Test response")]
        }
        mock.return_value = mock_agent
        yield mock_agent


@pytest.fixture
def sample_property_data():
    """Sample property data for testing."""
    return {
        "address": "123 Main St, San Francisco, CA 94102",
        "price": 1500000,
        "beds": 3,
        "baths": 2,
        "coordinates": {"lat": 37.7749, "lon": -122.4194},
        "listing_url": "https://example.com/property/123",
        "main_photo": "https://example.com/photo.jpg"
    }
