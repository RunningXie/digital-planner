"""
集成测试：内置雅思词条 DB（离线高频词库）搜索功能。
"""
import pytest
from unittest.mock import patch


# ═══════════════════════════════════════════════════════════════════
#  static_dictionary 单元测试（PG 雅思词条）
# ═══════════════════════════════════════════════════════════════════

class TestStaticDictionaryUnit:
    """直接测试 static_dictionary.search 函数。"""

    def test_search_case_insensitive(self):
        """英文搜索大小写不敏感。"""
        from static_dictionary import search
        result = search("LOVE")
        if result is None:
            pytest.skip("PG dictionary_entries 暂无可用数据")
        assert result["phrase"].lower() == "love"

    def test_search_substring_match(self):
        """子串匹配：搜索 love 应能命中 'love'。"""
        from static_dictionary import search
        result = search("love")
        if result is None:
            pytest.skip("PG dictionary_entries 暂无可用数据")
        assert "love" in result["phrase"].lower()

    def test_search_not_found(self):
        """词典里没有的词返回 None。"""
        from static_dictionary import search
        result = search("xyzzz123notarealword")
        assert result is None

    def test_search_empty_phrase(self):
        """空字符串返回 None。"""
        from static_dictionary import search
        assert search("") is None


# ═══════════════════════════════════════════════════════════════════
#  API 集成测试：词典命中短路 AI 调用
# ═══════════════════════════════════════════════════════════════════

class TestSearchPhraseDictHit:
    """雅思词条命中应该短路 AI 调用。"""

    @pytest.fixture
    def mock_ai_should_not_be_called(self):
        """AI 不应该被调用。"""
        async def fail_if_called(phrase, source_lang="zh", target_lang="en"):
            raise AssertionError("AI service should not be called when static dict hits")
            yield  # syntax requirement
        with patch("main.ai_service.search_phrase_stream", new=fail_if_called):
            yield

    def test_dict_hit_skips_ai(self, client, auth_headers, mock_ai_should_not_be_called):
        """命中雅思词条应跳过 AI。"""
        from static_dictionary import _ielts_index
        if not _ielts_index:
            pytest.skip("PG dictionary_entries 暂无可用数据")
        test_word = next(iter(_ielts_index.keys()))
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": test_word},
            headers=auth_headers
        )
        assert response.status_code == 200
        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        assert len(events) >= 1
        assert '"source": "ielts"' in events[0]
        assert '"type": "cached"' in events[0]

    def test_dict_hit_does_not_consume_quota(self, client, db_session, test_user, auth_headers, mock_ai_should_not_be_called):
        """词典命中不消耗 token 配额。"""
        from static_dictionary import _ielts_index
        if not _ielts_index:
            pytest.skip("PG dictionary_entries 暂无可用数据")
        test_word = next(iter(_ielts_index.keys()))
        before = test_user.daily_token_used
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": test_word},
            headers=auth_headers
        )
        for _ in response.iter_lines():
            pass
        db_session.refresh(test_user)
        assert test_user.daily_token_used == before

    def test_dict_not_hit_falls_through_to_ai(self, client, auth_headers):
        """词典里没有的词走 AI 调用（用 mock 验证）。"""
        async def mock_ai(phrase, source_lang="zh", target_lang="en"):
            yield {"type": "translations", "translations": ["ai result"]}
            yield {"type": "complete", "phrase": phrase, "translations": ["ai result"], "examples": [], "alternatives": [], "source": "ai"}

        with patch("main.ai_service.search_phrase_stream", new=mock_ai):
            response = client.post(
                "/api/search-phrase/stream",
                json={"phrase": "xyzabc123notindict"},
                headers=auth_headers
            )
        assert response.status_code == 200
        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        assert any('"ai result"' in e for e in events)
        assert not any('"source": "ielts"' in e for e in events)


# ═══════════════════════════════════════════════════════════════════
#  IELTS 词条测试（PG loader）
# ═══════════════════════════════════════════════════════════════════

class TestIeltsDbLoader:
    """测试 PG dictionary_entries loader 与搜索集成。DB 不可用时跳过。"""

    def test_ielts_db_optional(self):
        """DB 不可用时不应报错（graceful degradation）。"""
        from static_dictionary import size, reload
        reload()
        s = size()
        assert "ielts_count" in s
        if s["ielts_count"] == 0:
            pytest.skip("PG dictionary_entries 暂无可用数据（生产可由 load_ielts_dictionary 灌入）")

    def test_ielts_db_loaded(self):
        """DB 中有数据时应该被加载（>=100 条即视为可用）。"""
        from static_dictionary import size, reload
        reload()
        s = size()
        if s["ielts_count"] == 0:
            pytest.skip("PG dictionary_entries 暂无可用数据")
        assert s["ielts_count"] >= 100, f"IELTS 加载条数过少: {s['ielts_count']}"

    def test_ielts_index_built(self):
        """IELTS 索引应该建立（O(1) 精确查询）。"""
        from static_dictionary import size, reload
        reload()
        s = size()
        if s["ielts_count"] == 0:
            pytest.skip("PG dictionary_entries 暂无可用数据")
        # 索引接近全量（允许少量 word_normalized 冲突去重）
        assert s["ielts_index_size"] >= s["ielts_count"] * 0.9

    def test_ielts_returns_clean_translations(self):
        """翻译应该清理过：去掉 'n. '、'a. ' 等噪音。"""
        from static_dictionary import search
        result = search("ability")
        if result is None or result["source"] != "ielts":
            pytest.skip("PG dictionary_entries 暂无可用数据")
        for t in result["translations"]:
            assert "\n" not in t, f"翻译未清理: {t!r}"
            assert not t.startswith("n."), f"词性前缀未清理: {t!r}"
            assert not t.startswith("a."), f"形容词缩写未清理: {t!r}"
            assert not t.startswith("v."), f"词性前缀未清理: {t!r}"

    def test_ielts_exact_match_priority(self):
        """精确匹配应能命中已存在的词。"""
        from static_dictionary import search
        result = search("ability")
        if result is None or result["source"] != "ielts":
            pytest.skip("PG dictionary_entries 暂无可用数据")
        assert result["phrase"].lower() == "ability"
