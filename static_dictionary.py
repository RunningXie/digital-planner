"""
离线词典服务。

加载两个数据源（任一缺失都安全降级）：
  1. data/static_dictionary.json - 手工维护的精选短语（含 examples / alternatives）
  2. data/ecdict.csv             - 开源 ECDict 词典（BSD 许可，~30k 高频词筛选后）

搜索顺序：精选短语 → 通用词典。

通用性：CSV loader 使用 ECDict 字段约定（word, translation, collins, tag...），
       任何同格式的 CSV 都能直接替换 data/ecdict.csv。
"""
import csv
import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
JSON_PATH = DATA_DIR / "static_dictionary.json"
CSV_PATH = DATA_DIR / "ecdict.csv"

# ECDict CSV 字段顺序（无表头时使用）
ECDICT_FIELDS = [
    "word", "phonetic", "definition", "translation", "pos",
    "collins", "oxford", "tag", "bnc", "frq", "exchange", "detail", "audio",
]

# 质量筛选
MIN_COLLINS = 1
USEFUL_TAGS = {"zk", "gk", "cet4", "cet6", "ielts", "toefl", "gre"}
MAX_CSV_ENTRIES = 30000  # 30k 词已可覆盖日常写作；过大会拖慢加载

# 模块级缓存
_phrase_entries: List[Dict[str, Any]] = []
_csv_entries: List[Dict[str, Any]] = []
_csv_index: Dict[str, Dict[str, Any]] = {}  # word.lower() → entry，O(1) 精确查询
_loaded = False
_lock = threading.Lock()

# 词性前缀（用于解析 translation 字段）
_PARTS_OF_SPEECH = {
    "n", "v", "vi", "vt", "adj", "adv", "prep", "conj",
    "pron", "int", "art", "num", "aux", "abbr",
}


# ---------- JSON 加载（精选短语）----------

def _load_json() -> List[Dict[str, Any]]:
    """加载精选短语 JSON。"""
    if not JSON_PATH.exists():
        return []
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("精选短语加载失败 %s: %s", JSON_PATH, e)
        return []


# ---------- CSV 加载（开源词典）----------

def _parse_translation(text: str) -> List[str]:
    """从 ECDict translation 字段提取干净的中文释义列表。

    ECDict 样例：
      "n. 罩；风帽\\nv. 覆盖；用头巾包"
      "[网络] 胡德；兜帽；引擎盖"
      "n. 海牙"
    """
    results: List[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 去词性前缀："n. 罩" → "罩"
        if "." in line[:5]:
            prefix, rest = line.split(".", 1)
            if prefix.strip() in _PARTS_OF_SPEECH:
                line = rest.strip()

        # 去 [网络] / [口语] 等标签
        if line.startswith("["):
            end = line.find("]")
            if end > 0:
                line = line[end + 1:].strip()

        # 按 ； 拆成多条释义
        for meaning in line.split("；"):
            meaning = meaning.strip().rstrip(";.,，")
            if meaning and 1 <= len(meaning) <= 30:
                results.append(meaning)
                if len(results) >= 5:
                    return results
    return results


def _load_csv() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """加载 ECDict CSV，返回 (entries, index)。"""
    if not CSV_PATH.exists():
        return [], {}

    entries: List[Dict[str, Any]] = []
    index: Dict[str, Dict[str, Any]] = {}

    try:
        with open(CSV_PATH, "r", encoding="utf-8", errors="ignore") as f:
            # 检测是否有表头
            first = f.readline()
            f.seek(0)
            has_header = first.startswith("word,")

            reader = csv.DictReader(
                f,
                fieldnames=ECDICT_FIELDS if not has_header else None,
            )

            for row in reader:
                word = (row.get("word") or "").strip()
                translation = (row.get("translation") or "").strip()

                if not word or not translation or len(word) > 50:
                    continue

                # 质量筛选：Collins >= 1 或有常见考试标签
                try:
                    collins = int(row.get("collins") or 0)
                except (ValueError, TypeError):
                    collins = 0
                tag = (row.get("tag") or "").lower()

                if collins < MIN_COLLINS and not any(t in tag for t in USEFUL_TAGS):
                    continue

                translations = _parse_translation(translation)
                if not translations:
                    continue

                entry = {
                    "phrase": word,
                    "translations": translations[:3],
                    "examples": [],
                    "alternatives": [],
                    "_phonetic": (row.get("phonetic") or "").strip(),
                    "_tag": tag,
                    "_collins": collins,
                }

                entries.append(entry)
                # 索引去重：保留第一个（ECDict 中重复的取首次出现）
                key = word.lower()
                if key not in index:
                    index[key] = entry

                if len(entries) >= MAX_CSV_ENTRIES:
                    break
    except OSError as e:
        logger.warning("CSV 词典加载失败 %s: %s", CSV_PATH, e)
        return [], {}

    return entries, index


# ---------- 入口 ----------

def _ensure_loaded() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """惰性加载两个数据源，仅加载一次。"""
    global _phrase_entries, _csv_entries, _csv_index, _loaded
    if _loaded:
        return _phrase_entries, _csv_entries, _csv_index
    with _lock:
        if _loaded:
            return _phrase_entries, _csv_entries, _csv_index
        _phrase_entries = _load_json()
        _csv_entries, _csv_index = _load_csv()
        _loaded = True
        logger.info(
            "离线词典加载完成: %d 条精选短语 + %d 条通用词典（索引 %d）",
            len(_phrase_entries), len(_csv_entries), len(_csv_index),
        )
        return _phrase_entries, _csv_entries, _csv_index


def _format_hit(entry: Dict[str, Any], matched_field: str, source: str) -> Dict[str, Any]:
    """统一返回结构，source 区分 'dictionary'(精选) 或 'ecdict'(通用)。"""
    return {
        "phrase": entry.get("phrase", ""),
        "translations": entry.get("translations") or [],
        "examples": entry.get("examples") or [],
        "alternatives": entry.get("alternatives") or [],
        "matched_field": matched_field,
        "source": source,
    }


def search(phrase: str) -> Optional[Dict[str, Any]]:
    """
    搜索短语/单词。

    搜索顺序：
      1. 精选短语 JSON：phrase / translations / alternatives 字段子串匹配（source='dictionary'）
      2. 通用词典 CSV：精确匹配优先，其次子串匹配（source='ecdict'）

    命中返回 dict，未命中返回 None。
    """
    if not phrase:
        return None

    phrase_lower = phrase.lower().strip()
    if not phrase_lower:
        return None

    phrase_entries, csv_entries, csv_index = _ensure_loaded()

    # 1. 精选短语（JSON）— 子串匹配
    for entry in phrase_entries:
        if phrase_lower in (entry.get("phrase") or "").lower():
            return _format_hit(entry, "phrase", "dictionary")
        for t in entry.get("translations") or []:
            if phrase_lower in (t or "").lower():
                return _format_hit(entry, "translations", "dictionary")
        for a in entry.get("alternatives") or []:
            if phrase_lower in (a or "").lower():
                return _format_hit(entry, "alternatives", "dictionary")

    # 2. 通用词典（CSV）— 精确匹配优先
    if phrase_lower in csv_index:
        return _format_hit(csv_index[phrase_lower], "phrase", "ecdict")

    # 3. 通用词典（CSV）— 子串匹配（用于 'love' 命中 'lovely' 等场景）
    for entry in csv_entries:
        if phrase_lower in (entry.get("phrase") or "").lower():
            return _format_hit(entry, "phrase", "ecdict")

    return None


def size() -> Dict[str, int]:
    """返回词典规模（精选 / 通用 / 索引大小）。"""
    phrase_entries, csv_entries, csv_index = _ensure_loaded()
    return {
        "phrase_count": len(phrase_entries),
        "csv_count": len(csv_entries),
        "csv_index_size": len(csv_index),
    }


def reload() -> Dict[str, int]:
    """强制重新加载（数据文件更新后调用，无需重启服务）。"""
    global _phrase_entries, _csv_entries, _csv_index, _loaded
    with _lock:
        _phrase_entries = []
        _csv_entries = []
        _csv_index = {}
        _loaded = False
    return size()
