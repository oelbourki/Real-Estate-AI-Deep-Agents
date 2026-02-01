"""Integration tests for API endpoints."""

from unittest.mock import patch, Mock
from langchain_core.messages import AIMessage


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_check_with_redis(self, client, mock_redis):
        """Test health check with Redis connected."""
        mock_redis.ping.return_value = True
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["redis"] in ["connected", "disconnected"]


class TestMetricsEndpoint:
    """Tests for metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "requests_total" in data
        assert "errors_total" in data


class TestChatEndpoint:
    """Tests for chat endpoint."""

    @patch("api.main.get_main_agent")
    def test_chat_success(self, mock_get_agent, client):
        """Test successful chat request (default LangGraph format)."""
        mock_agent = Mock()
        mock_agent.invoke.return_value = {
            "messages": [AIMessage(content="Test response")]
        }
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/api/v1/chat",
            json={"message": "Find houses in San Francisco", "user_name": "Test User"},
        )

        assert response.status_code == 200
        data = response.json()
        # Default response is LangGraph format (messages + thread_id)
        assert "messages" in data
        assert "thread_id" in data
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) >= 1
        assert data["messages"][-1].get("content") == "Test response"

    def test_chat_missing_message(self, client):
        """Test chat with missing message."""
        response = client.post("/api/v1/chat", json={})
        assert response.status_code == 422  # Validation error


class TestPropertySearchEndpoint:
    """Tests for property search endpoint."""

    @patch("tools.realty_us.realty_us_search_buy")
    def test_property_search_success(self, mock_search, client):
        """Test successful property search."""
        mock_search.invoke.return_value = {
            "results": [{"address": "123 Main St", "price": 500000}],
            "total": 1,
        }
        response = client.post(
            "/api/v1/properties/search",
            json={"location": "San Francisco, CA", "bedrooms": 3},
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_property_search_missing_location(self, client):
        """Test property search with missing location."""
        response = client.post("/api/v1/properties/search", json={})
        assert response.status_code == 422


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_headers(self, client):
        """Test rate limit headers in response."""
        response = client.get("/health")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
