"""
Unit tests for _parse_json_response() — the multi-strategy JSON parser.
Covers all 4 parsing strategies plus edge cases.
"""
import pytest
import json
from ai_service import _parse_json_response

VALID_DATA = {
    "corrections": [
        {
            "original": "I go to school yesterday.",
            "corrected": "I went to school yesterday.",
            "explanation": "Wrong tense: 'go' should be 'went' for past tense.",
            "suggestions": ["I attended school yesterday.", "I was at school yesterday."],
        }
    ],
    "optimized_content": "I went to school yesterday.",
}


# ── Strategy 1: Plain JSON ──────────────────────────────────────────
class TestPlainJSON:
    def test_valid_plain_json(self):
        result = _parse_json_response(json.dumps(VALID_DATA))
        assert result["corrections"][0]["original"] == "I go to school yesterday."
        assert result["optimized_content"] == "I went to school yesterday."

    def test_empty_corrections_json(self):
        """Even empty corrections should parse successfully."""
        data = {"corrections": [], "optimized_content": ""}
        result = _parse_json_response(json.dumps(data))
        assert result["corrections"] == []

    def test_minimal_json(self):
        result = _parse_json_response('{"corrections":[],"optimized_content":""}')
        assert result == {"corrections": [], "optimized_content": ""}


# ── Strategy 2: Markdown code blocks ────────────────────────────────
class TestMarkdownCodeBlock:
    def test_json_in_code_block(self):
        raw = f'```json\n{json.dumps(VALID_DATA)}\n```'
        result = _parse_json_response(raw)
        assert result["corrections"][0]["corrected"] == "I went to school yesterday."

    def test_code_block_no_language_tag(self):
        raw = f'```\n{json.dumps(VALID_DATA)}\n```'
        result = _parse_json_response(raw)
        assert result["optimized_content"] == "I went to school yesterday."

    def test_code_block_with_extra_text(self):
        """AI often adds text before/after the code block."""
        raw = f'Here is the result:\n```json\n{json.dumps(VALID_DATA)}\n```\nHope this helps!'
        result = _parse_json_response(raw)
        assert len(result["corrections"]) == 1

    def test_code_block_inline_no_newlines(self):
        raw = f'```json{json.dumps(VALID_DATA)}```'
        result = _parse_json_response(raw)
        assert result["corrections"][0]["explanation"] == "Wrong tense: 'go' should be 'went' for past tense."

    def test_code_block_extra_whitespace(self):
        raw = f'```json  \n  {json.dumps(VALID_DATA)}  \n  ```'
        result = _parse_json_response(raw)
        assert result["optimized_content"] == "I went to school yesterday."


# ── Strategy 3: "json" prefix without backticks ─────────────────────
class TestJsonPrefix:
    def test_json_prefix_format(self):
        raw = f'json {json.dumps(VALID_DATA)}'
        result = _parse_json_response(raw)
        assert len(result["corrections"]) == 1

    def test_json_prefix_with_leading_whitespace(self):
        raw = f'   json   {json.dumps(VALID_DATA)}  '
        result = _parse_json_response(raw)
        assert result["optimized_content"] == "I went to school yesterday."


# ── Strategy 4: Brace matching (JSON embedded in text) ──────────────
class TestBraceMatching:
    def test_json_embedded_in_text(self):
        raw = f'Some preamble text... {json.dumps(VALID_DATA)} and some trailing text.'
        result = _parse_json_response(raw)
        assert len(result["corrections"]) == 1

    def test_json_with_nested_braces(self):
        """Brace matching must handle nested braces in JSON strings."""
        data = {
            "corrections": [
                {"original": "He said {hello}", "corrected": "He said hello.", "explanation": "Remove braces.", "suggestions": []}
            ],
            "optimized_content": "He said hello.",
        }
        raw = f'Some text {json.dumps(data)} more text'
        result = _parse_json_response(raw)
        assert result["corrections"][0]["original"] == "He said {hello}"

    def test_multiple_json_candidates(self):
        """Should pick the first valid JSON object."""
        data1 = {"corrections": [], "optimized_content": "first"}
        data2 = {"corrections": [], "optimized_content": "second"}
        raw = f'{json.dumps(data1)} some text {json.dumps(data2)}'
        result = _parse_json_response(raw)
        assert result["optimized_content"] == "first"


# ── Error cases ─────────────────────────────────────────────────────
class TestErrorCases:
    def test_completely_invalid_string(self):
        with pytest.raises(Exception) as exc:
            _parse_json_response("This is not JSON at all.")
        assert "Failed to parse AI response" in str(exc.value)

    def test_empty_string(self):
        with pytest.raises(Exception) as exc:
            _parse_json_response("")
        assert "Failed to parse AI response" in str(exc.value)

    def test_malformed_json_in_code_block(self):
        raw = '```json\n{"corrections": [\n```'
        with pytest.raises(Exception):
            _parse_json_response(raw)

    def test_truncated_json(self):
        raw = '{"corrections": [{"original": "text", "corrected":'
        with pytest.raises(Exception):
            _parse_json_response(raw)


# ── Real-world AI response formats ──────────────────────────────────
class TestRealWorldFormats:
    """Test formats that the Zhipu/GLM API actually returns."""

    def test_glm_plain_json(self):
        """GLM sometimes returns plain JSON on the first line."""
        raw = (
            '{"corrections":[{"original":"I go school.","corrected":"I go to school.",'
            '"explanation":"Missing preposition \\"to\\".","suggestions":["I attend school."]}],'
            '"optimized_content":"I go to school."}'
        )
        result = _parse_json_response(raw)
        assert result["corrections"][0]["explanation"] == 'Missing preposition "to".'

    def test_glm_with_explanation_then_json(self):
        """GLM may add a brief note before the code block."""
        raw = (
            'Here is the corrected version:\n'
            '```json\n'
            '{"corrections":[{"original":"test","corrected":"test","explanation":"OK","suggestions":[]}],'
            '"optimized_content":"test"}\n'
            '```'
        )
        result = _parse_json_response(raw)
        assert result["corrections"][0]["corrected"] == "test"

    def test_segovia_diary_scenario(self):
        """Simulate the exact Segovia diary scenario: AI returns corrections for all sentences."""
        raw = json.dumps({
            "corrections": [
                {
                    "original": "This ticket is for Segovia Cathedral.",
                    "corrected": "This ticket is for Segovia Cathedral.",
                    "explanation": "No errors found.",
                    "suggestions": ["This is a ticket for Segovia Cathedral."],
                },
                {
                    "original": "It was one day trip by everyone self.",
                    "corrected": "It was a one-day trip we took by ourselves.",
                    "explanation": "Missing article 'a', 'one-day' needs hyphen, 'by everyone self' → 'by ourselves'.",
                    "suggestions": ["It was a one-day trip we went on our own.", "We took a one-day trip by ourselves."],
                },
                {
                    "original": "I signed up the trip to Segovia.",
                    "corrected": "I signed up for the trip to Segovia.",
                    "explanation": "Missing preposition 'for' after 'signed up'.",
                    "suggestions": ["I registered for the Segovia trip.", "I booked the trip to Segovia."],
                },
                {
                    "original": "It was worthy.",
                    "corrected": "It was worth it.",
                    "explanation": "'Worthy' means deserving respect; 'worth it' means good value.",
                    "suggestions": ["It was worthwhile.", "It was definitely worth it."],
                },
                {
                    "original": "It was another old castal in Spain.",
                    "corrected": "It was another old castle in Spain.",
                    "explanation": "Spelling error: 'castal' → 'castle'.",
                    "suggestions": ["It was yet another historic castle in Spain.", "It was one more ancient Spanish castle."],
                },
                {
                    "original": "We had tosated pig for lunch, it was a famous local food.",
                    "corrected": "We had roasted pig for lunch; it is a famous local dish.",
                    "explanation": "Spelling: 'tosated' → 'roasted'; comma splice fixed; 'food' → 'dish' for cuisine context.",
                    "suggestions": ["We had roast suckling pig, a famous local specialty.", "We ate cochinillo asado, a well-known local dish."],
                },
                {
                    "original": "I wanted to go to the tower of the cathedral.",
                    "corrected": "I wanted to go up to the tower of the cathedral.",
                    "explanation": "Add 'up' for clarity (climbing the tower).",
                    "suggestions": ["I wanted to climb the cathedral tower.", "I wanted to visit the cathedral's tower."],
                },
            ],
            "optimized_content": "This ticket is for Segovia Cathedral. It was a one-day trip we took by ourselves. I signed up for the trip to Segovia. It was definitely worth it. It was another old castle in Spain. We had roasted pig for lunch; it is a famous local dish. I wanted to go up to the tower of the cathedral.",
        })
        result = _parse_json_response(raw)
        assert len(result["corrections"]) == 7
        # Verify all key errors are caught
        explanations = [c["explanation"] for c in result["corrections"]]
        assert any("article" in e.lower() for e in explanations)
        assert any("spelling" in e.lower() or "castal" in e.lower() for e in explanations)
        assert any("preposition" in e.lower() or "signed up" in e.lower() for e in explanations)