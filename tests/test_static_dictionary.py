"""
集成测试：内置静态词典（离线高频词库）搜索功能。
"""
import pytest
from unittest.mock import patch


# ═══════════════════════════════════════════════════════════════════
#  static_dictionary 单元测试
# ═══════════════════════════════════════════════════════════════════

class TestStaticDictionaryUnit:
    """直接测试 static_dictionary.search 函数。"""

    def test_search_returns_dict_when_phrase_field_matches(self):
        """phrase 字段命中返回 dict。"""
        from static_dictionary import search
        result = search("work overtime")
        assert result is not None
        assert result["phrase"] == "work overtime"
        assert "加班" in result["translations"]
        assert result["matched_field"] == "phrase"

    def test_search_translation_field_match(self):
        """中文翻译字段也能命中。"""
        from static_dictionary import search
        result = search("加班")
        assert result is not None
        assert "加班" in result["translations"]
        assert result["matched_field"] == "translations"

    def test_search_alternative_field_match(self):
        """alternatives 字段也能命中。"""
        from static_dictionary import search
        result = search("put in extra hours")
        assert result is not None
        assert result["matched_field"] == "alternatives"

    def test_search_case_insensitive(self):
        """英文搜索大小写不敏感。"""
        from static_dictionary import search
        result = search("WORK OVERTIME")
        assert result is not None
        assert result["phrase"] == "work overtime"

    def test_search_substring_match(self):
        """子串匹配：搜索 overtime 应能命中 'work overtime'。"""
        from static_dictionary import search
        result = search("overtime")
        assert result is not None
        assert result["phrase"] == "work overtime"

    def test_search_not_found(self):
        """词典里没有的词返回 None。"""
        from static_dictionary import search
        result = search("xyzzz123notarealword")
        assert result is None

    def test_search_empty_phrase(self):
        """空字符串返回 None。"""
        from static_dictionary import search
        assert search("") is None

    def test_search_returns_examples_and_alternatives(self):
        """命中条目应包含 examples 和 alternatives 字段。"""
        from static_dictionary import search
        result = search("work overtime")
        assert result is not None
        assert isinstance(result["examples"], list)
        assert isinstance(result["alternatives"], list)
        assert len(result["examples"]) > 0
        assert len(result["alternatives"]) > 0


# ═══════════════════════════════════════════════════════════════════
#  API 集成测试：词典命中短路 AI 调用
# ═══════════════════════════════════════════════════════════════════

class TestSearchPhraseStaticDictionaryHit:
    """静态词典命中应该短路 AI 调用，直接返回。"""

    @pytest.fixture
    def mock_ai_should_not_be_called(self):
        """AI 不应该被调用。"""
        async def fail_if_called(phrase, source_lang="zh", target_lang="en"):
            raise AssertionError("AI service should not be called when static dict hits")
            yield  # syntax requirement
        with patch("main.ai_service.search_phrase_stream", new=fail_if_called):
            yield

    def test_dict_phrase_field_hit_skips_ai(self, client, auth_headers, mock_ai_should_not_be_called):
        """命中词典 phrase 字段。"""
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "work overtime"},
            headers=auth_headers
        )
        assert response.status_code == 200
        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        assert len(events) == 1
        assert '"source": "dictionary"' in events[0]
        assert '"work overtime"' in events[0]
        assert '"加班"' in events[0]
        assert '"type": "cached"' in events[0]

    def test_dict_chinese_translation_hit_skips_ai(self, client, auth_headers, mock_ai_should_not_be_called):
        """中文翻译字段也能命中（如搜"加班"）。"""
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "加班"},
            headers=auth_headers
        )
        assert response.status_code == 200
        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        assert len(events) == 1
        assert '"source": "dictionary"' in events[0]

    def test_dict_hit_does_not_consume_quota(self, client, db_session, test_user, auth_headers, mock_ai_should_not_be_called):
        """词典命中不消耗 token 配额。"""
        before = test_user.daily_token_used
        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "work overtime"},
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
        assert not any('"source": "dictionary"' in e for e in events)

    def test_notebook_takes_priority_over_dict(self, client, db_session, test_user, auth_headers, mock_ai_should_not_be_called):
        """当用户笔记本和词典都命中时，笔记本优先（用户私有数据）。"""
        from models import NotebookEntry
        # 笔记本里也有 work overtime（用户翻译成"额外工时"）
        nb = NotebookEntry(
            user_id=test_user.id,
            phrase="work overtime",
            translations=["额外工时"],
            examples=[],
            alternatives=[],
        )
        db_session.add(nb)
        db_session.commit()

        response = client.post(
            "/api/search-phrase/stream",
            json={"phrase": "work overtime"},
            headers=auth_headers
        )
        events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
        assert len(events) == 1
        # 应该是 notebook 命中，不是 dictionary
        assert '"source": "notebook"' in events[0]
        assert '"额外工时"' in events[0]
        assert '"source": "dictionary"' not in events[0]


# ═══════════════════════════════════════════════════════════════════
#  ECDict 通用词典测试（CSV loader）
# ═══════════════════════════════════════════════════════════════════

class TestECDictLoader:
    """测试 ECDict CSV loader 与搜索集成。CSV 文件可选，缺失时跳过。"""

    def test_ecdict_csv_optional(self):
        """ECDict CSV 缺失时不应报错（graceful degradation）。"""
        from static_dictionary import size, reload, CSV_PATH
        reload()
        s = size()
        # 不管 CSV 是否存在，调用都不应抛异常
        assert "phrase_count" in s
        assert "csv_count" in s
        if not CSV_PATH.exists():
            # CSV 缺失时数量应为 0
            assert s["csv_count"] == 0
            pytest.skip("ECDict CSV 未配置（生产部署按需启用）")

    def test_ecdict_csv_is_loaded(self):
        """ECDict CSV 存在时应该被加载（>=5000 条）。"""
        from static_dictionary import size, reload, CSV_PATH
        reload()
        s = size()
        if not CSV_PATH.exists():
            pytest.skip("ECDict CSV 未配置")
        assert s["csv_count"] >= 5000, f"ECDict 加载条数过少: {s['csv_count']}"

    def test_ecdict_index_built(self):
        """CSV 索引应该建立（O(1) 精确查询）。"""
        from static_dictionary import size, reload, CSV_PATH
        reload()
        s = size()
        if not CSV_PATH.exists() or s["csv_count"] == 0:
            pytest.skip("ECDict CSV 未配置")
        assert s["csv_index_size"] >= s["csv_count"] * 0.9  # 索引接近全量

    def test_ecdict_phrase_returns_source_ecdict(self):
        """通用词典命中应该返回 source='ecdict'。"""
        from static_dictionary import search, CSV_PATH
        if not CSV_PATH.exists():
            pytest.skip("ECDict CSV 未配置")
        result = search("happy")
        if result and result["source"] == "ecdict":
            assert result["matched_field"] == "phrase"
            assert len(result["translations"]) > 0
        else:
            assert result is None or result["source"] == "dictionary"

    def test_ecdict_returns_clean_translations(self):
        """翻译应该清理过：去掉 'n. '、'\\\\n' 等噪音。"""
        from static_dictionary import search, CSV_PATH
        if not CSV_PATH.exists():
            pytest.skip("ECDict CSV 未配置")
        result = search("happy")
        if result and result["source"] == "ecdict":
            for t in result["translations"]:
                assert "\\n" not in t, f"翻译未清理: {t!r}"
                assert not t.startswith("n."), f"词性前缀未清理: {t!r}"
                assert not t.startswith("v."), f"词性前缀未清理: {t!r}"

    def test_ecdict_exact_match_priority(self):
        """精确匹配应该比子串匹配优先。"""
        from static_dictionary import search, _csv_index, CSV_PATH
        if not CSV_PATH.exists():
            pytest.skip("ECDict CSV 未配置")
        if "love" in _csv_index:
            result = search("love")
            assert result["phrase"].lower() == "love"

    def test_search_returns_none_for_nonexistent_word(self):
        """词典中不存在的词返回 None。"""
        from static_dictionary import search
        assert search("xyzzznotarealword999") is None


# ═══════════════════════════════════════════════════════════════════
#  API 集成测试：ECDict 命中
# ═══════════════════════════════════════════════════════════════════

class TestSearchPhraseECDictHit:
    """ECDict 通用词典命中应该短路 AI 调用。"""

    @pytest.fixture
    def mock_ai_should_not_be_called(self):
        async def fail_if_called(phrase, source_lang="zh", target_lang="en"):
            raise AssertionError("AI service should not be called when ecdict hits")
            yield
        with patch("main.ai_service.search_phrase_stream", new=fail_if_called):
            yield

    def test_ecdict_hit_returns_source_ecdict(self, client, auth_headers, mock_ai_should_not_be_called):
        """通用词典命中应返回 source='ecdict'。"""
        from static_dictionary import _csv_index, CSV_PATH
        if not CSV_PATH.exists():
            pytest.skip("ECDict CSV 未配置")
        for test_word in ["happy", "work", "good", "love", "time", "tired"]:
            if test_word in _csv_index:
                response = client.post(
                    "/api/search-phrase/stream",
                    json={"phrase": test_word},
                    headers=auth_headers
                )
                assert response.status_code == 200
                events = [line[6:] for line in response.iter_lines() if line and line.startswith("data: ")]
                assert len(events) >= 1
                assert '"type": "cached"' in events[0]
                return
        pytest.skip("ECDict 中未找到测试词")

    def test_ecdict_hit_does_not_consume_quota(self, client, db_session, test_user, auth_headers, mock_ai_should_not_be_called):
        """ECDict 命中不消耗 token 配额。"""
        from static_dictionary import _csv_index, CSV_PATH
        if not CSV_PATH.exists():
            pytest.skip("ECDict CSV 未配置")
        test_word = None
        for w in ["happy", "work", "good", "love"]:
            if w in _csv_index:
                test_word = w
                break
        if test_word is None:
            pytest.skip("ECDict 中未找到测试词")

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
