from unittest.mock import patch

from tools import travily_tool


def test_tavily_search_formats_numbered_results():
    fake_response = {
        "results": [
            {"title": "Best Hotels in Tokyo", "url": "https://a.example", "content": "Great stay."},
            {"title": "Top Ryokans", "url": "https://b.example", "content": "Onsen views."},
        ]
    }

    with patch.object(travily_tool.client, "search", return_value=fake_response) as mock_search:
        result = travily_tool.tavily_search("best hotels in tokyo")

    mock_search.assert_called_once_with(query="best hotels in tokyo", max_results=5)
    assert result.startswith("1. **Best Hotels in Tokyo**")
    assert "2. **Top Ryokans**" in result
    assert "https://a.example" in result
    assert "https://b.example" in result


def test_tavily_search_truncates_long_snippet():
    long_content = "word " * 100  # 500 chars, well over the 300-char cutoff
    fake_response = {
        "results": [{"title": "Long Article", "url": "https://c.example", "content": long_content}]
    }

    with patch.object(travily_tool.client, "search", return_value=fake_response):
        result = travily_tool.tavily_search("query")

    snippet_line = result.splitlines()[2]
    expected_snippet = long_content[:300].rsplit(" ", 1)[0] + "..."
    assert snippet_line == f"   {expected_snippet}"


def test_tavily_search_handles_missing_fields():
    fake_response = {"results": [{}]}

    with patch.object(travily_tool.client, "search", return_value=fake_response):
        result = travily_tool.tavily_search("query")

    assert "Unknown" in result


def test_tavily_search_empty_results_returns_empty_string():
    with patch.object(travily_tool.client, "search", return_value={"results": []}):
        result = travily_tool.tavily_search("query")

    assert result == ""
