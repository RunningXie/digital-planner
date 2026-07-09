"""
离线词典服务。

唯一数据源：PG dictionary_entries 表（来自 scripts/load_ielts_dictionary.py）。
DB 不可用时安全降级（搜索不命中，调用 AI），不抛异常。
"""
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 搜索结果里 source 字段的可能取值
SOURCE_IELTS = "ielts"

# 模块级缓存
_ielts_entries: List[Dict[str, Any]] = []   # 雅思词条（PG 拉入内存）
_ielts_index: Dict[str, Dict[str, Any]] = {}  # word_normalized → entry，O(1) 精确查询
_loaded = False
_lock = threading.Lock()
_db_load_error: Optional[str] = None  # 上次 DB 加载错误


def _load_ielts_from_db() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """从 PG dictionary_entries 拉雅思词条到内存。

    缺失表/连接失败/字段缺失都返回 ([], {}) 不抛异常（搜索服务必须能跑）。
    """
    try:
        # 延迟导入避免循环依赖（database / models / config）
        from database import SessionLocal
        from models import DictionaryEntry
        from sqlalchemy import select
    except ImportError as e:
        logger.debug("DB 模块不可用：%s", e)
        return [], {}

    try:
        with SessionLocal() as session:
            stmt = select(DictionaryEntry)
            rows = session.execute(stmt).scalars().all()
    except Exception as e:
        # 表不存在 / 连不上 PG / 权限问题 等
        global _db_load_error
        _db_load_error = str(e)
        logger.info("雅思词条暂不可用（DB 加载跳过）：%s", e)
        return [], {}

    entries: List[Dict[str, Any]] = []
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        # 防御：翻译必须是 list
        translations = row.translation if isinstance(row.translation, list) else []
        if not translations:
            continue

        entry = {
            "phrase": row.word,
            "translations": translations[:3],
            "_phonetic": row.phonetics,
            "_tag": " ".join(row.tags or []),
            "_collins": row.collins or 0,
            "_frq": row.frq,
        }
        entries.append(entry)
        # 索引：word_normalized 已经小写并去标点，用于精确匹配
        norm = (row.word_normalized or "").lower()
        if norm and norm not in index:
            index[norm] = entry

    return entries, index


def _ensure_loaded() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """惰性加载，仅加载一次。"""
    global _ielts_entries, _ielts_index, _loaded
    if _loaded:
        return _ielts_entries, _ielts_index
    with _lock:
        if _loaded:
            return _ielts_entries, _ielts_index
        _ielts_entries, _ielts_index = _load_ielts_from_db()
        _loaded = True
        logger.info(
            "离线词典加载完成: %d 条雅思词条（索引 %d）",
            len(_ielts_entries), len(_ielts_index),
        )
        return _ielts_entries, _ielts_index


def _format_hit(entry: Dict[str, Any], matched_field: str) -> Dict[str, Any]:
    """统一返回结构。"""
    return {
        "phrase": entry.get("phrase", ""),
        "translations": entry.get("translations") or [],
        "matched_field": matched_field,
        "source": SOURCE_IELTS,
    }


def search(phrase: str) -> Optional[Dict[str, Any]]:
    """
    搜索短语/单词。

    搜索顺序：
      1. 雅思词条 DB 索引：精确匹配优先（O(1)）
      2. 雅思词条 DB 列表：子串匹配兜底

    命中返回 dict，未命中返回 None。
    """
    if not phrase:
        return None

    phrase_lower = phrase.lower().strip()
    if not phrase_lower:
        return None

    ielts_entries, ielts_index = _ensure_loaded()

    # 1. 雅思词条 — 精确匹配（O(1)）
    if phrase_lower in ielts_index:
        return _format_hit(ielts_index[phrase_lower], "phrase")

    # 2. 雅思词条 — 子串匹配兜底
    for entry in ielts_entries:
        if phrase_lower in (entry.get("phrase") or "").lower():
            return _format_hit(entry, "phrase")

    return None


def size() -> Dict[str, Any]:
    """返回词典规模。"""
    ielts_entries, ielts_index = _ensure_loaded()
    return {
        "ielts_count": len(ielts_entries),
        "ielts_index_size": len(ielts_index),
        "db_error": _db_load_error,
    }


def reload() -> Dict[str, Any]:
    """强制重新加载（数据更新后调用，无需重启服务）。"""
    global _ielts_entries, _ielts_index, _loaded, _db_load_error
    with _lock:
        _ielts_entries = []
        _ielts_index = {}
        _loaded = False
        _db_load_error = None
    return size()
