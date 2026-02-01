"""Unit tests for tools."""

import requests
from tools.realty_us import realty_us_search_buy
from tools.location import geocode_address
from tools.financial import calculate_roi, estimate_mortgage
from unittest.mock import patch, Mock


class TestRealtyUSTools:
    """Tests for RealtyUS tools."""

    @patch("tools.realty_us.settings")
    @patch("tools.realty_us.requests.get")
    def test_realty_us_search_buy_success(self, mock_get, mock_settings):
        """Test successful property search."""
        mock_settings.rapidapi_key = "test-key"
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "results": [
                    {
                        "location": {"address": {"line": "123 Main St"}},
                        "list_price": 500000,
                        "description": {"beds": 3, "baths": 2},
                        "primary_photo": {"href": "https://example.com/photo.jpg"},
                        "photos": [],
                        "href": "https://example.com/listing",
                        "list_date": "2025-01-01",
                    }
                ]
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = realty_us_search_buy.invoke({"location": "city:San Francisco, CA"})

        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["address"] == "123 Main St"

    @patch("tools.realty_us.requests.get")
    def test_realty_us_search_buy_error(self, mock_get):
        """Test property search error handling."""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.RequestException("API Error")
        )
        mock_get.return_value = mock_response

        result = realty_us_search_buy.invoke({"location": "city:San Francisco, CA"})

        assert "error" in result
        assert result["results"] == []
        assert result["total"] == 0


class TestLocationTools:
    """Tests for location tools."""

    @patch("tools.location.requests.get")
    def test_geocode_address_success(self, mock_get):
        """Test successful geocoding."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"lat": "37.7749", "lon": "-122.4194", "display_name": "San Francisco, CA"}
        ]
        mock_get.return_value = mock_response

        result = geocode_address.invoke({"address": "San Francisco, CA"})

        assert "lat" in result
        assert "lon" in result
        assert result["lat"] == 37.7749

    @patch("tools.location.requests.get")
    def test_geocode_address_not_found(self, mock_get):
        """Test geocoding with no results."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = geocode_address.invoke({"address": "Invalid Address 12345"})

        assert "error" in result


class TestFinancialTools:
    """Tests for financial tools."""

    def test_calculate_roi_success(self):
        """Test ROI calculation."""
        result = calculate_roi.invoke(
            {
                "purchase_price": 500000,
                "monthly_rent": 3000,
                "down_payment": 0.2,
                "interest_rate": 0.065,
            }
        )

        assert "roi_percent" in result or "cash_on_cash_roi_percent" in result
        assert "monthly_cash_flow" in result
        assert "net_annual_income" in result

    def test_estimate_mortgage_success(self):
        """Test mortgage estimation."""
        result = estimate_mortgage.invoke(
            {"loan_amount": 400000, "interest_rate": 0.065, "loan_term_years": 30}
        )

        assert "monthly_payment" in result
        assert "total_interest" in result
        assert result["monthly_payment"] > 0
