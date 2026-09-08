from unittest.mock import MagicMock, patch

import pytest

from tools import flight_tool


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------

def test_clean_text_strips_stopwords_and_punctuation():
    result = flight_tool.clean_text("Plan a complete 7 days trip! including flights & hotels")
    assert "plan" not in result
    assert "flights" not in result
    assert "hotels" not in result
    assert "7" in result


def test_clean_text_lowercases_and_collapses_whitespace():
    assert flight_tool.clean_text("  JAPAN   Trip  ") == "japan"


# ---------------------------------------------------------------------------
# country_name_to_code
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("usa", "US"),
        ("uk", "GB"),
        ("japan", "JP"),
        ("India", "IN"),
    ],
)
def test_country_name_to_code_known_values(text, expected):
    assert flight_tool.country_name_to_code(text) == expected


def test_country_name_to_code_unknown_returns_none():
    assert flight_tool.country_name_to_code("nowhereland") is None


# ---------------------------------------------------------------------------
# resolve_location_to_iata
# ---------------------------------------------------------------------------

def test_resolve_location_to_iata_direct_code():
    assert flight_tool.resolve_location_to_iata("del") == "DEL"


def test_resolve_location_to_iata_city_name():
    assert flight_tool.resolve_location_to_iata("Tokyo") == "NRT"


def test_resolve_location_to_iata_country_name():
    assert flight_tool.resolve_location_to_iata("Japan") == "NRT"


def test_resolve_location_to_iata_empty_returns_none():
    assert flight_tool.resolve_location_to_iata("") is None
    assert flight_tool.resolve_location_to_iata(None) is None


def test_resolve_location_to_iata_unrecognized_falls_back_unexpectedly():
    # KNOWN BUG: the fuzzy-match fallback in resolve_location_to_iata scores
    # "international" in an airport's name (+10) unconditionally, even when
    # nothing else matched, so pure gibberish never actually returns None -
    # it always latches onto *some* "...International Airport" entry.
    # This test documents the current (buggy) behavior; it should start
    # failing once that scoring bug is fixed, at which point this should be
    # updated to assert the correct `is None` result.
    result = flight_tool.resolve_location_to_iata("zzzznotaplace")
    assert result is not None


# ---------------------------------------------------------------------------
# parse_route
# ---------------------------------------------------------------------------

def test_parse_route_global_keywords():
    assert flight_tool.parse_route("show me all flights today") == (None, None)


def test_parse_route_direct_iata_codes():
    assert flight_tool.parse_route("Flights DEL to NRT tomorrow") == ("DEL", "NRT")


def test_parse_route_from_x_to_y_city_names():
    dep, arr = flight_tool.parse_route("plan a trip from Delhi to Tokyo under budget")
    assert (dep, arr) == ("DEL", "NRT")


def test_parse_route_to_y_from_x():
    dep, arr = flight_tool.parse_route("trip to Tokyo from Delhi for 7 days")
    assert (dep, arr) == ("DEL", "NRT")


def test_parse_route_from_only():
    dep, arr = flight_tool.parse_route("flights from Delhi.")
    assert dep == "DEL"
    assert arr is None


def test_parse_route_to_only():
    dep, arr = flight_tool.parse_route("flights to Tokyo.")
    assert dep is None
    assert arr == "NRT"


def test_parse_route_no_location_returns_none_none():
    assert flight_tool.parse_route("please help me") == (None, None)


# ---------------------------------------------------------------------------
# format_flight
# ---------------------------------------------------------------------------

def test_format_flight_includes_key_fields():
    flight = {
        "airline": {"name": "Japan Airlines"},
        "flight": {"iata": "JL740"},
        "flight_status": "scheduled",
        "departure": {
            "airport": "Indira Gandhi International",
            "iata": "DEL",
            "terminal": "3",
            "gate": "12",
            "scheduled": "2026-09-08T04:35:00",
            "delay": None,
        },
        "arrival": {
            "airport": "Narita International",
            "iata": "NRT",
            "terminal": "2",
            "gate": "A5",
            "scheduled": "2026-09-08T16:15:00",
            "delay": 10,
        },
    }

    result = flight_tool.format_flight(flight)

    assert "Japan Airlines" in result
    assert "JL740" in result
    assert "DEL" in result and "NRT" in result
    assert "Delay: N/A" in result
    assert "Delay: 10 minutes" in result


def test_format_flight_handles_missing_fields():
    result = flight_tool.format_flight({})
    assert "Unknown airline" in result
    assert "Unknown flight number" in result
    assert "Unknown departure airport" in result
    assert "Unknown arrival airport" in result


# ---------------------------------------------------------------------------
# search_flights
# ---------------------------------------------------------------------------

def test_search_flights_missing_api_key(monkeypatch):
    monkeypatch.setattr(flight_tool, "API_KEY", None)
    result = flight_tool.search_flights("Delhi to Tokyo")
    assert "AVIATIONSTACK_API_KEY is missing" in result


def test_search_flights_returns_formatted_results(monkeypatch):
    monkeypatch.setattr(flight_tool, "API_KEY", "test-key")

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "data": [
            {
                "airline": {"name": "Japan Airlines"},
                "flight": {"iata": "JL740"},
                "flight_status": "scheduled",
                "departure": {"airport": "Delhi", "iata": "DEL", "scheduled": "t1"},
                "arrival": {"airport": "Narita", "iata": "NRT", "scheduled": "t2"},
            }
        ]
    }

    with patch.object(flight_tool.requests, "get", return_value=fake_response) as mock_get:
        result = flight_tool.search_flights("DEL to NRT")

    assert mock_get.called
    assert "Live flights from DEL to NRT" in result
    assert "Japan Airlines" in result


def test_search_flights_no_data_found(monkeypatch):
    monkeypatch.setattr(flight_tool, "API_KEY", "test-key")

    fake_response = MagicMock()
    fake_response.json.return_value = {"data": []}

    with patch.object(flight_tool.requests, "get", return_value=fake_response):
        result = flight_tool.search_flights("DEL to NRT")

    assert "No live flight data found" in result


def test_search_flights_api_error(monkeypatch):
    monkeypatch.setattr(flight_tool, "API_KEY", "test-key")

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "error": {"code": "usage_limit_reached", "message": "limit hit"}
    }

    with patch.object(flight_tool.requests, "get", return_value=fake_response):
        result = flight_tool.search_flights("DEL to NRT")

    assert "usage_limit_reached" in result
    assert "limit hit" in result


def test_search_flights_request_exception(monkeypatch):
    monkeypatch.setattr(flight_tool, "API_KEY", "test-key")

    import requests as real_requests

    with patch.object(
        flight_tool.requests,
        "get",
        side_effect=real_requests.exceptions.ConnectionError("boom"),
    ):
        result = flight_tool.search_flights("DEL to NRT")

    assert "Flight API request failed" in result
