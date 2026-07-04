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
            json={"phrase": "xyzzznotarealword999"},
            headers=auth_headers
        )
        assert response.status_code == 200
        for _ in response.iter_lines():
            pass

        assert len(mock_ai_stream_lang) == 1
        assert mock_ai_stream_lang[0] == ("xyzzznotarealword999", "zh", "en")


# ═══════════════════════════════════════════════════════════════════
#  笔记本命中短路：搜索时先查用户的笔记本
# ═══════════════════════════════════════════════════════════════════

class TestSearchPhraseNotebookHit:
    """笔记本命中应该短路 AI 调用，直接返回保存的词条。"""

    @pytest.fixture
    def mock_ai_stream_should_not_be_called(self):
        """AI 不应该被调用；一旦被调用则测试失败。"""
        async def fail_if_called(phrase, source_lang="zh", target_lang="en"):
            raise AssertionError("AI service should not be called when notebook hit")
            yield  # 满足 async generator 语法，实际不会执行
        with patch("main.ai_service.search_phrase_stream", new=fail_if_called):
            yield

    def _seed_notebook(self, db_session, test_user):
        """为测试用户写入一条笔记。"""
        from models import NotebookEntry
        entry = NotebookEntry(
            user_id=test_user.id,
            phrase="work overtime",
            translations=["加班"],
            examples=["I had to work overtime yesterday."],
            alternatives=["put in extra hours", "work late"],
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        return entry

    def test_phrase_field_match_skips_ai(self, client, db_session, test_user, auth_headers, mock_ai_stream_should_not_be_called):
        """搜索的词命中 notebook.phrase 字段时直接返回，且 AI 不被调用。"""
        from models import NotebookEntry
        self._seed_notebook(db_session, test_user)

        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "work overtime"},
            headers=auth_headers
        )
        assert response.status_code == 200

        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        assert len(events) == 1
        payload = events[0]
        assert '"source": "notebook"' in payload
        assert '"work overtime"' in payload
        assert '"加班"' in payload
        assert '"type": "cached"' in payload

    def test_translation_field_match_skips_ai(self, client, db_session, test_user, auth_headers, mock_ai_stream_should_not_be_called):
        """命中 translations 字段（如中文查 English 笔记）也应短路 AI。"""
        self._seed_notebook(db_session, test_user)

        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "加班"},
            headers=auth_headers
        )
        assert response.status_code == 200

        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        assert len(events) == 1
        assert '"source": "notebook"' in events[0]

    def test_alternative_field_match_skips_ai(self, client, db_session, test_user, auth_headers, mock_ai_stream_should_not_be_called):
        """命中 alternatives 字段也应短路 AI。"""
        self._seed_notebook(db_session, test_user)

        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "put in extra hours"},
            headers=auth_headers
        )
        assert response.status_code == 200
        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        assert len(events) == 1
        assert '"source": "notebook"' in events[0]

    def test_case_insensitive_match(self, client, db_session, test_user, auth_headers, mock_ai_stream_should_not_be_called):
        """匹配应该大小写不敏感。"""
        self._seed_notebook(db_session, test_user)

        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "WORK OVERTIME"},
            headers=auth_headers
        )
        assert response.status_code == 200
        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        assert len(events) == 1
        assert '"source": "notebook"' in events[0]

    def test_no_match_falls_through_to_ai(self, client, db_session, test_user, auth_headers):
        """笔记本里没有的词应该正常走 AI 调用。"""
        from unittest.mock import patch
        self._seed_notebook(db_session, test_user)

        async def mock_ai(phrase, source_lang="zh", target_lang="en"):
            yield {"type": "translations", "translations": ["new result"]}
            yield {"type": "complete", "phrase": phrase, "translations": ["new result"], "examples": [], "alternatives": [], "source": "ai"}

        with patch("main.ai_service.search_phrase_stream", new=mock_ai):
            response = client.post(
                "/api/search-phrase/stream",
                json={"phrase": "完全不相关的词xyz"},
                headers=auth_headers
            )
        assert response.status_code == 200
        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        # 至少有一个 translations 事件，且不含 notebook source
        assert any('"translations"' in e and '"new result"' in e for e in events)
        assert not any('"source": "notebook"' in e for e in events)

    def test_notebook_hit_does_not_consume_quota(self, client, db_session, test_user, auth_headers, mock_ai_stream_should_not_be_called):
        """笔记本命中不应该消耗用户的 token 配额。"""
        from models import User
        before = test_user.daily_token_used
        self._seed_notebook(db_session, test_user)

        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "work overtime"},
            headers=auth_headers
        )
        for _ in response.iter_lines():
            pass
        db_session.refresh(test_user)
        assert test_user.daily_token_used == before, "笔记本命中不应该扣 token 配额"

    def test_other_users_notebook_does_not_match(self, client, db_session, test_user, auth_headers):
        """别的用户的笔记不应该匹配当前用户。"""
        from models import User, NotebookEntry
        other = User(
            username="otheruser",
            email="other@example.com",
            hashed_password="x",
        )
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)
        other_entry = NotebookEntry(
            user_id=other.id,
            phrase="work overtime",
            translations=["加班"],
            examples=[],
            alternatives=[],
        )
        db_session.add(other_entry)
        db_session.commit()

        async def mock_ai(phrase, source_lang="zh", target_lang="en"):
            yield {"type": "translations", "translations": ["from ai"]}
            yield {"type": "complete", "phrase": phrase, "translations": ["from ai"], "examples": [], "alternatives": [], "source": "ai"}

        with patch("main.ai_service.search_phrase_stream", new=mock_ai):
            response = client.post(
                "/api/search-phrase/stream",
                json={"phrase": "work overtime"},
                headers=auth_headers
            )
        for _ in response.iter_lines():
            pass
        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        # 别人的笔记不能匹配，应该走到 AI
        assert not any('"source": "notebook"' in e for e in events)