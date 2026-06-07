import aiohttp
import json
import re
import time
from typing import List, Dict, Any, AsyncGenerator
from config import get_settings

settings = get_settings()


# Simple in-memory cache for phrase search results
class PhraseCache:
    """Simple memory cache with TTL support."""
    _cache: Dict[str, Dict[str, Any]] = {}
    _ttl: int = 3600  # 1 hour TTL

    @classmethod
    def get(cls, key: str) -> Dict[str, Any] | None:
        """Get cached result if not expired."""
        entry = cls._cache.get(key)
        if entry and time.time() - entry["timestamp"] < cls._ttl:
            return entry["data"]
        return None

    @classmethod
    def set(cls, key: str, data: Dict[str, Any]) -> None:
        """Cache a result with current timestamp."""
        cls._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

    @classmethod
    def clear(cls) -> None:
        """Clear all cached entries."""
        cls._cache.clear()


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences, handling common abbreviations."""
    # Protect common abbreviations
    text = re.sub(r'Mr\.', 'Mr<DOT>', text)
    text = re.sub(r'Mrs\.', 'Mrs<DOT>', text)
    text = re.sub(r'Dr\.', 'Dr<DOT>', text)
    text = re.sub(r'Prof\.', 'Prof<DOT>', text)
    text = re.sub(r'vs\.', 'vs<DOT>', text)
    text = re.sub(r'etc\.', 'etc<DOT>', text)
    text = re.sub(r'\.\.\.', '<ELLIPSIS>', text)

    # Split by sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Restore protected abbreviations
    sentences = [s.replace('<DOT>', '.').replace('<ELLIPSIS>', '...') for s in sentences]

    # Filter empty sentences and strip whitespace
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def _parse_json_response(raw_content: str) -> dict:
    """
    Robust JSON parser with multiple fallback strategies for AI responses.
    Handles: plain JSON, ```json``` blocks, ``` blocks, "json" prefix, and JSON embedded in text.
    """
    # Strategy 1: Direct JSON parse
    try:
        return json.loads(raw_content)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from ```json ... ``` (with flexible whitespace and optional language tag)
    for pattern in [
        r'```json\s*\n(.*?)\n\s*```',
        r'```\s*\n(.*?)\n\s*```',
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
    ]:
        m = re.search(pattern, raw_content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                continue

    # Strategy 3: Response starts with "json" keyword (no backticks), then JSON
    m = re.match(r'^\s*json\s*(\{.*\})\s*$', raw_content, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 4: Extract the outermost { ... } JSON object by matching braces
    brace_start = raw_content.find('{')
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(raw_content)):
            if raw_content[i] == '{':
                depth += 1
            elif raw_content[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw_content[brace_start:i + 1])
                    except json.JSONDecodeError:
                        pass
                    break

    raise Exception(f"Failed to parse AI response. Raw content (first 500 chars): {raw_content[:500]}")


class AIService:
    def __init__(self):
        self.base_url = settings.ai_base_url
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def correct_diary(self, content: str) -> Dict[str, Any]:
        """
        Correct English diary content sentence by sentence.
        Returns corrections and optimized content.
        """
        prompt = f"""You are a strict English teacher. Your job is to find and correct EVERY error in a student's diary. Students make many mistakes — never say a diary is perfect.

Diary content:
{content}

CRITICAL RULES — read carefully before responding:
1. Split the diary into individual sentences. Treat each sentence separately.
2. For EVERY sentence, check ALL of these:
   - Grammar: verb tense, subject-verb agreement, article usage (a/an/the), prepositions, singular/plural
   - Spelling: Are all words spelled correctly? "castal" should be "castle", "tosated" should be "roasted"
   - Expression: Is the phrasing natural? "by everyone self" → "by ourselves", "was worthy" → "was worth it"
   - Punctuation: comma splices, run-on sentences, missing periods
3. You MUST output a correction entry for EVERY sentence — even correct ones. For correct sentences, set corrected=same as original and explanation="No errors found."
4. NEVER return an empty corrections array. If the diary has 7 sentences, you MUST return 7 correction entries.
5. Common mistakes Chinese students make that you MUST catch:
   - Missing articles: "one day trip" → "a one-day trip"
   - Missing prepositions: "signed up the trip" → "signed up for the trip"
   - Wrong word choice: "worthy" → "worth it / worthwhile"
   - Comma splices: joining two independent clauses with just a comma
   - Spelling errors: "castal" → "castle", "tosated" → "roasted"
6. Provide 2-3 alternative/better expressions in the suggestions array for each corrected sentence.
7. Provide a fully rewritten, polished version of the entire diary as optimized_content. When creating the optimized version, use the MORE RECOMMENDED expressions from the suggestions array whenever appropriate, rather than just using the grammatically corrected version.

RESPONSE FORMAT — output ONLY this JSON, nothing else:
{{"corrections": [{{"original": "sentence1", "corrected": "corrected sentence1", "explanation": "what was wrong", "suggestions": ["alt1", "alt2"]}}, {{"original": "sentence2", "corrected": "corrected sentence2", "explanation": "what was wrong", "suggestions": ["alt1", "alt2"]}}], "optimized_content": "full rewritten diary"}}

IMPORTANT: Your response must be ONLY the JSON object. No markdown code blocks, no extra text before or after the JSON."""

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a strict English teacher. You ALWAYS find errors in student writing. Respond ONLY with a valid JSON object. Never use markdown formatting."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                }

                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"AI API error: {response.status} - {error_text}")

                    result = await response.json()
                    raw_content = result["choices"][0]["message"]["content"]

                    parsed = _parse_json_response(raw_content)

                    # Validate that corrections is not empty
                    corrections = parsed.get("corrections", [])
                    if not corrections:
                        print(f"WARNING: AI returned empty corrections for diary: {content[:200]}")

                    return parsed

        except Exception as e:
            return {
                "corrections": [],
                "optimized_content": content,
                "error": str(e)
            }

    async def correct_diary_stream(self, content: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream corrections sentence by sentence.
        Yields each correction as soon as it's ready.
        """
        sentences = _split_into_sentences(content)
        all_corrections = []
        optimized_parts = []

        for sentence in sentences:
            prompt = f"""You are a strict English teacher. Correct this single sentence from a student's diary.

Sentence: "{sentence}"

Check for:
- Grammar errors (verb tense, subject-verb agreement, articles, prepositions)
- Spelling errors
- Expression/naturalness
- Punctuation errors

Provide 2-3 alternative/better expressions in the suggestions array.

RESPONSE FORMAT — output ONLY this JSON, nothing else:
{{"original": "{sentence}", "corrected": "corrected sentence", "explanation": "what was wrong or 'No errors found.'", "suggestions": ["alt1", "alt2"]}}

IMPORTANT: Your response must be ONLY the JSON object. No markdown code blocks, no extra text."""

            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a strict English teacher. Respond ONLY with a valid JSON object. Never use markdown formatting."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1
                    }

                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            correction = {
                                "original": sentence,
                                "corrected": sentence,
                                "explanation": f"AI API error: {response.status}",
                                "suggestions": []
                            }
                        else:
                            result = await response.json()
                            raw_content = result["choices"][0]["message"]["content"]
                            try:
                                parsed = _parse_json_response(raw_content)
                                correction = {
                                    "original": sentence,
                                    "corrected": parsed.get("corrected", sentence),
                                    "explanation": parsed.get("explanation", "No errors found."),
                                    "suggestions": parsed.get("suggestions", [])
                                }
                            except Exception as parse_error:
                                correction = {
                                    "original": sentence,
                                    "corrected": sentence,
                                    "explanation": f"Failed to parse AI response: {str(parse_error)}",
                                    "suggestions": []
                                }

                all_corrections.append(correction)
                optimized_parts.append(correction["corrected"])
                yield correction

            except Exception as e:
                correction = {
                    "original": sentence,
                    "corrected": sentence,
                    "explanation": f"Error: {str(e)}",
                    "suggestions": []
                }
                all_corrections.append(correction)
                optimized_parts.append(sentence)
                yield correction

        # After all sentences are processed, generate optimized content
        optimized_content = " ".join(optimized_parts)
        yield {
            "type": "optimized",
            "optimized_content": optimized_content
        }

    async def search_phrase_stream(self, phrase: str, source_lang: str = "zh", target_lang: str = "en") -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream phrase search results.
        First check cache, then call AI if not found.
        Yields results incrementally for better UX.
        """
        cache_key = f"{source_lang}:{target_lang}:{phrase.lower()}"

        # 1. Check cache first
        cached = PhraseCache.get(cache_key)
        if cached:
            yield {"type": "cached", "source": "cache", **cached}
            return

        # 2. Call AI for new phrases
        prompt = f"""Translate the following phrase and provide usage examples.

Phrase: "{phrase}"

Return a JSON object with exactly these fields:
- "translations": 2-3 natural English translations (short phrases, not full sentences)
- "examples": 2 example sentences in English using the phrase
- "alternatives": 2-3 similar English expressions

Keep all text concise. Return ONLY the JSON, nothing else."""

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a concise bilingual translator. Respond ONLY with valid JSON. Keep translations and examples SHORT. Never use markdown code blocks."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                }

                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield {
                            "type": "error",
                            "phrase": phrase,
                            "error": f"AI API error: {response.status}",
                            "translations": [],
                            "examples": [],
                            "alternatives": []
                        }
                        return

                    result = await response.json()
                    raw_content = result["choices"][0]["message"]["content"]

                    try:
                        parsed = _parse_json_response(raw_content)
                        parsed["phrase"] = phrase
                        parsed["source"] = "ai"

                        # Cache the result
                        PhraseCache.set(cache_key, parsed)

                        # Yield translations first
                        if parsed.get("translations"):
                            yield {
                                "type": "translations",
                                "translations": parsed["translations"]
                            }

                        # Yield examples
                        if parsed.get("examples"):
                            yield {
                                "type": "examples",
                                "examples": parsed["examples"]
                            }

                        # Yield alternatives
                        if parsed.get("alternatives"):
                            yield {
                                "type": "alternatives",
                                "alternatives": parsed["alternatives"]
                            }

                        # Yield complete result
                        yield {"type": "complete", **parsed}

                    except Exception as parse_error:
                        yield {
                            "type": "error",
                            "phrase": phrase,
                            "error": f"Failed to parse AI response: {str(parse_error)}",
                            "translations": [],
                            "examples": [],
                            "alternatives": []
                        }

        except Exception as e:
            yield {
                "type": "error",
                "phrase": phrase,
                "error": str(e),
                "translations": [],
                "examples": [],
                "alternatives": []
            }


# Singleton instance
ai_service = AIService()