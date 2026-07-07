#!/usr/bin/env python3
"""
把 ECDict 的雅思词条灌进 PostgreSQL。

执行流程：
  1. 从 GitHub 下载 ECDict CSV（约 65MB），到本地临时目录
  2. 按条件筛选：tags 包含 "ielts"、collins >= min_collins、单词是字母
  3. 清理 translation / pos，去除英文词性前缀噪音
  4. 写入 dictionary_entries 表（ON CONFLICT 覆盖）

使用：
  # 第一次：完整导入
  python scripts/load_ielts_dictionary.py

  # 限定 1500 条最高频
  python scripts/load_ielts_dictionary.py --max-rows 1500

  # 只跑 collins 4-5 的核心词
  python scripts/load_ielts_dictionary.py --min-collins 4

  # 加严到 ielts + toefl
  python scripts/load_ielts_dictionary.py --tags ielts,toefl

  # 不下载，使用本地 csv
  python scripts/load_ielts_dictionary.py --csv-path /tmp/ecdict.csv
"""
import argparse
import csv
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Iterator, Dict, Any, List, Optional

# 让脚本可以独立运行（不依赖 main.py 的导入）
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 设置环境变量，否则 database.py 会拿不到 settings
os.environ.setdefault("DATABASE_URL", os.environ.get("DATABASE_URL", "sqlite:///./diary.db"))

# 确保有 urllib 就可以下载（避免依赖外部库）
try:
    import urllib.request
except ImportError:
    print("需要 Python 3 内置 urllib", file=sys.stderr)
    sys.exit(1)

# SQLAlchemy / 模型
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import get_settings
from database import Base
from models import DictionaryEntry


# 兼容调用方式：先暴露 settings 模块级变量
settings = get_settings()


# ───────────────────────── 配置 ─────────────────────────
DEFAULT_ECDICT_URL = (
    "https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv"
)
CHUNK_SIZE = 1024 * 1024  # 1MB per request chunk
TIMEOUT = 60  # seconds
USER_AGENT = "DearDiary-DictLoader/1.0"


# ───────────────────────── 翻译清理 ─────────────────────────

# ECDict 翻译里常见的英文词性前缀（要剔除）
# 涵盖: n, v, adj, adv, vt, vi, prep, conj, pron, art, num, aux, int, pl, a(形容词缩写)
_NOISE_PREFIX = re.compile(
    r"^(n|v|adj|adv|vt|vi|prep|conj|pron|art|num|aux|int|pl|past|pp|a)\.\s*",
    re.IGNORECASE,
)
# 词性短码的合法集合（保留用）
_VALID_POS = {"n", "v", "adj", "adv", "vt", "vi", "prep", "conj", "pron", "art", "num", "aux", "int", "pl", "a"}


def _extract_pos(translation_field: str) -> List[str]:
    """从 ECDict 翻译字段里提取所有词性短码，例如 'n. 城堡\\nv. 城堡' → ['n.', 'v.']"""
    pos_list = []
    for line in translation_field.split("\\n"):
        m = re.match(r"^\s*([a-z]+)\.\s", line)
        if m and m.group(1).lower() in _VALID_POS:
            pos_list.append(m.group(1).lower() + ".")
    return pos_list


def _clean_translation(text: str) -> str:
    """去掉一行翻译里的词性前缀 + 多余空白 + 末尾标点。

    例：
      'n. 城堡' → '城堡'
      'adj. 疲倦的；厌烦的' → '疲倦的；厌烦的'
      'v. （使）疲倦  ' → '（使）疲倦'
    """
    text = text.strip()
    text = _NOISE_PREFIX.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_translations(raw: str) -> List[str]:
    """把 ECDict 的 translation 字段拆成 干净的中文翻译列表。

    字段用 \\n 分隔多个义项；每个义项可能是 'n. 中文' 或 '中文'。
    """
    if not raw:
        return []

    result = []
    for line in raw.split("\\n"):
        cleaned = _clean_translation(line)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def parse_tags(raw: str) -> List[str]:
    """ECDict tags 用空格分隔：'zk gk cet4 ielts' → ['zk', 'gk', 'cet4', 'ielts']"""
    if not raw:
        return []
    return [t.strip() for t in raw.split() if t.strip()]


# ───────────────────────── 下载 ─────────────────────────

def download_ecdict(output_path: Path, force: bool = False) -> bool:
    """下载 ECDict CSV。已有文件且未 force 时跳过。"""
    if output_path.exists() and not force:
        size = output_path.stat().st_size
        print(f"  ECDict 已存在: {output_path} ({size / 1024 / 1024:.1f} MB)，跳过下载")
        return True

    print(f"  正在从 GitHub 下载 ECDict (约 65MB)...")
    req = urllib.request.Request(
        DEFAULT_ECDICT_URL,
        headers={"User-Agent": USER_AGENT},
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            start = time.time()
            with open(tmp_path, "wb") as f:
                while True:
                    chunk = resp.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        speed = downloaded / 1024 / 1024 / max(time.time() - start, 0.001)
                        print(f"\r  进度: {pct:3d}% ({downloaded / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} MB, {speed:.1f} MB/s)", end="", flush=True)
        print()
        tmp_path.rename(output_path)
        print(f"  下载完成: {output_path}")
        return True
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        print(f"  下载失败: {e}", file=sys.stderr)
        return False


# ───────────────────────── 解析 + 筛选 ─────────────────────────

# ECDict CSV 列：word,phonetic,definition,translation,pos,collins,oxford,tag,bnc,frq,exchange,detail,audio
CSV_FIELDS = [
    "word", "phonetic", "definition", "translation", "pos",
    "collins", "oxford", "tag", "bnc", "frq", "exchange", "detail", "audio"
]


def _is_clean_word(word: str) -> bool:
    """单词必须是纯字母（允许空格连接短语，但太长的短语不要）。"""
    if not word:
        return False
    word = word.strip()
    # 拒绝含非字母字符的（如 "you're", "CD-ROM"）
    if not re.fullmatch(r"[a-zA-Z]+(?:[ '-][a-zA-Z]+)*", word):
        return False
    # 拒绝太长的（>30 字符基本是垃圾）
    if len(word) > 30:
        return False
    return True


def _normalize_word(word: str) -> str:
    """规范化用于去重：小写 + 去掉所有非字母字符。"""
    return re.sub(r"[^a-z]", "", word.lower())


def iter_filtered_rows(
    csv_path: Path,
    required_tags: List[str],
    min_collins: int,
    max_rows: Optional[int],
    frq_threshold: int = 0,
) -> Iterator[Dict[str, Any]]:
    """流式遍历 CSV，按条件筛选。返回清洗后的 dict。

    筛选规则（任一满足即可）：
      1. 标签集合与 required_tags 有交集（默认 {ielts}） — 考试大纲词
      2. collins >= min_collins（默认 1） — 柯林斯星级词
      3. frq <= frq_threshold（默认 0 = 关闭） — 高频词兜底

    说明：用"交集"而不是"包含"是为了让 collins=5 的 love、study 等基础词
    也能进表（它们没有 ielts 标签但是 collins 5）。
    """
    required = set(t.lower() for t in required_tags)
    seen_normalized = set()
    yielded = 0
    total = 0
    matched_tags = 0
    matched_collins = 0
    matched_clean = 0
    matched_frq = 0

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, fieldnames=CSV_FIELDS)
        for row in reader:
            total += 1
            word = (row.get("word") or "").strip()
            if not _is_clean_word(word):
                continue

            tags = parse_tags(row.get("tag") or "")
            tags_lower = set(t.lower() for t in tags)

            try:
                collins = int(row.get("collins") or 0)
            except ValueError:
                collins = 0
            try:
                frq_raw = row.get("frq") or ""
                frq = int(frq_raw) if frq_raw.strip() else 999999
            except ValueError:
                frq = 999999

            # 筛选规则：任一满足即可
            tag_match = bool(required) and bool(required & tags_lower)
            collins_match = collins >= min_collins
            frq_match = frq_threshold and frq <= frq_threshold

            if not (tag_match or collins_match or frq_match):
                continue
            if tag_match:
                matched_tags += 1
            elif collins_match:
                matched_collins += 1
            else:
                matched_frq += 1

            translations = parse_translations(row.get("translation") or "")
            if not translations:
                continue
            matched_clean += 1

            norm = _normalize_word(word)
            if norm in seen_normalized:
                continue
            seen_normalized.add(norm)

            pos = _extract_pos(row.get("translation") or "")
            if not pos and row.get("pos"):
                pos = parse_tags(row.get("pos"))

            yield {
                "word": word.lower(),
                "word_normalized": norm,
                "translation": translations,
                "pos": pos,
                "phonetics": (row.get("phonetic") or "").strip() or None,
                "collins": collins,
                "frq": frq if frq != 999999 else None,
                "tags": tags,
            }
            yielded += 1
            if max_rows and yielded >= max_rows:
                break

    print(f"  统计: 总行数={total:,}, 标签匹配={matched_tags:,}, "
          f"collins>={min_collins}={matched_collins:,}, "
          f"frq<={frq_threshold}={matched_frq:,}, "
          f"翻译非空={matched_clean:,}, 去重后={len(seen_normalized):,}, "
          f"最终入库={yielded:,}")


# ───────────────────────── 写入数据库 ─────────────────────────

def _engine():
    """根据 settings 拿到 SQLAlchemy engine（沿用项目配置）。"""
    return create_engine(settings.database_url, pool_pre_ping=True)


def upsert_entries(entries: Iterator[Dict[str, Any]], batch_size: int = 500) -> int:
    """批量 upsert 到 dictionary_entries。返回总行数。"""
    # PG 才能用 ON CONFLICT；SQLite 走 INSERT OR REPLACE
    is_pg = "postgresql" in settings.database_url
    if is_pg:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(DictionaryEntry).values
        conflict_key = ["word_normalized"]
        do_update = {
            "translation": pg_insert(DictionaryEntry).excluded.translation,
            "pos": pg_insert(DictionaryEntry).excluded.pos,
            "phonetics": pg_insert(DictionaryEntry).excluded.phonetics,
            "collins": pg_insert(DictionaryEntry).excluded.collins,
            "frq": pg_insert(DictionaryEntry).excluded.frq,
            "tags": pg_insert(DictionaryEntry).excluded.tags,
            "source": pg_insert(DictionaryEntry).excluded.source,
        }
    else:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        stmt = sqlite_insert(DictionaryEntry).values
        conflict_key = ["word_normalized"]
        do_update = {
            "translation": sqlite_insert(DictionaryEntry).excluded.translation,
            "pos": sqlite_insert(DictionaryEntry).excluded.pos,
            "phonetics": sqlite_insert(DictionaryEntry).excluded.phonetics,
            "collins": sqlite_insert(DictionaryEntry).excluded.collins,
            "frq": sqlite_insert(DictionaryEntry).excluded.frq,
            "tags": sqlite_insert(DictionaryEntry).excluded.tags,
            "source": sqlite_insert(DictionaryEntry).excluded.source,
        }

    engine = _engine()
    Base.metadata.create_all(engine)  # 安全：只创建不存在的表
    Session = sessionmaker(bind=engine)
    session = Session()

    total = 0
    try:
        batch = []
        for entry in entries:
            entry.setdefault("source", "ielts-ecdict")
            batch.append(entry)
            if len(batch) >= batch_size:
                _flush(session, stmt, conflict_key, do_update, batch)
                total += len(batch)
                print(f"\r  已写入 {total:,} 条...", end="", flush=True)
                batch.clear()
        if batch:
            _flush(session, stmt, conflict_key, do_update, batch)
            total += len(batch)
            print(f"\r  已写入 {total:,} 条...")
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
    return total


def _flush(session, stmt, conflict_key, do_update, batch):
    sql = stmt(batch).on_conflict_do_update(index_elements=conflict_key, set_=do_update)
    session.execute(sql)


# ───────────────────────── main ─────────────────────────

def main():
    parser = argparse.ArgumentParser(description="把 ECDict 雅思词条灌进 PG dictionary_entries")
    parser.add_argument("--csv-path", type=Path, default=None,
                        help="本地 ECDict CSV 路径；不传则下载到临时目录")
    parser.add_argument("--max-rows", type=int, default=0,
                        help="最多入库条数（默认 0 = 不限；筛选后取前 N）")
    parser.add_argument("--min-collins", type=int, default=1,
                        help="collins 星级最低要求（1-5，默认 1）")
    parser.add_argument("--tags", type=str, default="ielts,toefl,cet4,cet6,gre",
                        help="至少匹配一个的标签集合，逗号分隔（默认 ielts,toefl,cet4,cet6,gre）")
    parser.add_argument("--frq-threshold", type=int, default=0,
                        help="frq <= 此值也算命中（默认 0 = 关闭；ECDict 的 frq 字段不唯一，请谨慎使用）")
    parser.add_argument("--source", type=str, default="ielts-ecdict",
                        help="写入 source 字段的值（默认 ielts-ecdict）")
    parser.add_argument("--truncate", action="store_true",
                        help="先清空 dictionary_entries 表再导入")
    parser.add_argument("--no-download", action="store_true",
                        help="不下载，必须配合 --csv-path 使用本地文件")
    args = parser.parse_args()

    print("=" * 60)
    print("ECDict 雅思词条 → PG dictionary_entries")
    print("=" * 60)
    db_disp = settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url
    print(f"  目标数据库: {db_disp}")
    print(f"  筛选条件: tags ∩ {{{args.tags}}} 或 collins>={args.min_collins}" + (" 或 frq<={}".format(args.frq_threshold) if args.frq_threshold else ""))
    print(f"  上限: {args.max_rows or '不限'} 条")
    print()

    # 1. 准备 CSV
    if args.csv_path:
        csv_path = args.csv_path
    else:
        if args.no_download:
            print("错误: --no-download 必须配合 --csv-path", file=sys.stderr)
            sys.exit(2)
        csv_path = Path(tempfile.gettempdir()) / "ecdict.csv"

    if not csv_path.exists():
        if not download_ecdict(csv_path):
            sys.exit(1)
    else:
        size = csv_path.stat().st_size
        print(f"  使用本地 ECDict: {csv_path} ({size / 1024 / 1024:.1f} MB)")

    # 1.5 确保表存在（先创建表，truncate 才有对象可清空）
    engine = _engine()
    Base.metadata.create_all(engine)

    # 2. 可选：先清空
    if args.truncate:
        Session = sessionmaker(bind=engine)
        session = Session()
        deleted = session.query(DictionaryEntry).delete()
        session.commit()
        print(f"  已清空 dictionary_entries（删除 {deleted} 条旧数据）")
        session.close()

    # 3. 筛选 + 写入
    required_tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    entries = iter_filtered_rows(
        csv_path,
        required_tags,
        args.min_collins,
        args.max_rows,
        frq_threshold=args.frq_threshold,
    )
    count = upsert_entries(entries)
    print()
    print(f"✅ 完成：写入/更新 {count:,} 条到 dictionary_entries")


if __name__ == "__main__":
    main()
