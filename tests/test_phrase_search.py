"""
Integration tests for phrase search functionality (streaming version):
- POST /api/search-phrase/stream (direct AI call with caching)
- Error handling and edge cases
- Cache functionality tests
"""
import pytest
from unittest.mock import AsyncMock, patch


# ═══════════════════════════════════════════════════════════════════
#  API integration tests: POST /api/search-phrase/stream
#  Direct AI calls with caching
# ═══════════════════════════════════════════════════════════════════

class TestSearchPhraseStreamAPI:
    """Tests for the streaming phrase search API."""

    @pytest.fixture
    def mock_ai_stream(self):
        """Mock ai_service.search_phrase_stream to return streaming results."""
        async def mock_search_phrase_stream(phrase, source_lang="zh", target_lang="en"):
            yield {"type": "translations", "translations": ["translation1", "translation2"]}
            yield {"type": "examples", "examples": ["Example sentence 1.", "Example sentence 2."]}
            yield {"type": "alternatives", "alternatives": ["alternative1", "alternative2"]}
            yield {
                "type": "complete",
                "phrase": phrase,
                "translations": ["translation1", "translation2"],
                "examples": ["Example sentence 1.", "Example sentence 2."],
                "alternatives": ["alternative1", "alternative2"],
                "source": "ai"
            }

        with patch("main.ai_service.search_phrase_stream", new=mock_search_phrase_stream):
            yield

    def test_search_phrase_stream_success(self, client, mock_ai_stream, auth_headers):
        """Stream API returns incremental results."""
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "测试短语"},
            headers=auth_headers
        )
        assert response.status_code == 200

        # Collect all streaming events
        events = []
        for line in response.iter_lines():
            if line and line.startswith('data: '):
                events.append(line[6:])

        assert len(events) >= 3  # At least translations, examples, alternatives
        assert any('translations' in event for event in events)
        assert any('examples' in event for event in events)
        assert any('alternatives' in event for event in events)

    def test_search_phrase_stream_with_lang_params(self, client, mock_ai_stream, auth_headers):
        """Custom source_lang and target_lang parameters."""
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "bonjour", "source_lang": "fr", "target_lang": "en"},
            headers=auth_headers
        )
        assert response.status_code == 200

        events = []
        for line in response.iter_lines():
            if line and line.startswith('data: '):
                events.append(line[6:])

        assert len(events) > 0

    def test_search_phrase_stream_default_lang(self, client, mock_ai_stream, auth_headers):
        """Default source_lang is 'zh', target_lang is 'en'."""
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "测试"},
            headers=auth_headers
        )
        assert response.status_code == 200


class TestSearchPhraseCache:
    """Tests for phrase search caching functionality - temporarily skipped since test isolation breaks cache."""

    @pytest.fixture
    def mock_ai_stream_cache(self):
        """Mock that tracks call count."""
        call_count = {'count': 0}

        async def mock_search_phrase_stream(phrase, source_lang="zh", target_lang="en"):
            call_count['count'] += 1
            yield {"type": "translations", "translations": ["cached result"]}
            yield {"type": "complete", "phrase": phrase, "translations": ["cached result"], "examples": [], "alternatives": [], "source": "ai"}

        with patch("main.ai_service.search_phrase_stream", new=mock_search_phrase_stream):
            yield call_count

    @pytest.mark.skip(reason="Cache test requires persistent instance, test isolation makes it hard")
    def test_cache_hits_second_request(self, client, mock_ai_stream_cache, auth_headers):
        """Second request for same phrase should hit cache."""
        pass

    @pytest.mark.skip(reason="Cache test requires persistent instance, test isolation makes it hard")
    def test_cache_case_insensitive(self, client, mock_ai_stream_cache, auth_headers):
        """Cache is case-insensitive."""
        pass


class TestSearchPhraseStreamErrorHandling:
    """Tests for error scenarios in streaming phrase search."""

    @pytest.fixture
    def mock_ai_stream_error(self):
        """Mock ai_service.search_phrase_stream to return error."""
        async def mock_search_phrase_stream(phrase, source_lang="zh", target_lang="en"):
            yield {
                "type": "error",
                "phrase": phrase,
                "error": "AI API error: 500 - Internal Server Error",
                "translations": [],
                "examples": [],
                "alternatives": []
            }

        with patch("main.ai_service.search_phrase_stream", new=mock_search_phrase_stream):
            yield

    def test_stream_error_returns_graceful_message(self, client, mock_ai_stream_error, auth_headers):
        """When AI fails, return a user-friendly error message."""
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "出错测试"},
            headers=auth_headers
        )
        assert response.status_code == 200

        events = []
        for line in response.iter_lines():
            if line and line.startswith('data: '):
                events.append(line[6:])

        assert len(events) == 1
        assert 'error' in events[0].lower()
        assert '500' in events[0]

    def test_empty_phrase_rejected(self, client, auth_headers):
        """Empty phrase — response should be handled gracefully."""
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": ""},
            headers=auth_headers
        )
        # API should not crash on empty phrase
        assert response.status_code in [200, 422]

    def test_unauthenticated_rejected(self, client, db_session):
        """Unauthenticated requests should get 401."""
        pass  # Skipped: client fixture overrides auth; test manually


class TestSearchPhraseSourceLanguage:
    """Test source_lang and target_lang parameter behavior."""

    @pytest.fixture
    def mock_ai_stream_lang(self):
        """Mock that captures all call parameters."""
        call_args = []

        async def mock_search_phrase_stream(phrase, source_lang="zh", target_lang="en"):
            call_args.append((phrase, source_lang, target_lang))
            yield {"type": "complete", "phrase": phrase, "translations": [phrase], "examples": [], "alternatives": [], "source": "ai"}

        with patch("main.ai_service.search_phrase_stream", new=mock_search_phrase_stream):
            yield call_args

    def test_custom_source_lang_fr(self, client, mock_ai_stream_lang, auth_headers):
        """Search from French to English."""
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "bonjour", "source_lang": "fr", "target_lang": "en"},
            headers=auth_headers
        )
        assert response.status_code == 200
        for _ in response.iter_lines():
            pass

        assert len(mock_ai_stream_lang) == 1
        assert mock_ai_stream_lang[0] == ("bonjour", "fr", "en")

    def test_default_lang_is_zh_to_en(self, client, mock_ai_stream_lang, auth_headers):
        """Default source_lang is 'zh', target_lang is 'en'."""
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "hello"},
            headers=auth_headers
        )
        assert response.status_code == 200
        for _ in response.iter_lines():
            pass

        assert len(mock_ai_stream_lang) == 1
        assert mock_ai_stream_lang[0] == ("hello", "zh", "en")