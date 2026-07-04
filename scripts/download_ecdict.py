#!/usr/bin/env python3
"""
下载 ECDict 离线词典到 data/ecdict.csv。

为什么不在 git 里提交：
  - 65MB 单文件会撑爆 git 历史和 clone 时间
  - 部署时下载一次即可，数据源是权威的上游仓库

用法：
  python scripts/download_ecdict.py            # 下载到默认路径 data/ecdict.csv
  python scripts/download_ecdict.py --force     # 强制覆盖已存在的文件
  python scripts/download_ecdict.py --check     # 只检查不下载

数据源：https://github.com/skywind3000/ECDICT (BSD 许可)
"""
import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# 配置
DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "ecdict.csv"
URL = "https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv"
# 分块大小：10MB，单次下载 65MB 容易超时
CHUNK_SIZE = 10 * 1024 * 1024
# 单块超时（秒）
CHUNK_TIMEOUT = 120
# 重试次数
MAX_RETRIES = 3


def get_remote_size() -> int | None:
    """HEAD 请求获取远程文件大小。"""
    try:
        req = urllib.request.Request(URL, method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as resp:
            length = resp.headers.get("Content-Length")
            return int(length) if length else None
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"[警告] 无法获取远程文件大小: {e}", file=sys.stderr)
        return None


def download_chunk(start: int, end_inclusive: int, retries: int = MAX_RETRIES) -> bytes:
    """下载 [start, end_inclusive] 字节范围。"""
    range_header = f"bytes={start}-{end_inclusive}"
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(URL, headers={"Range": range_header})
            with urllib.request.urlopen(req, timeout=CHUNK_TIMEOUT) as resp:
                return resp.read()
        except (urllib.error.URLError, OSError) as e:
            print(f"  [重试 {attempt}/{retries}] 区块 {start}-{end_inclusive} 失败: {e}",
                  file=sys.stderr)
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)
    return b""  # unreachable


def download(output_path: Path, force: bool = False) -> bool:
    """主流程：检查、下载、合并。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not force:
        size = output_path.stat().st_size
        print(f"文件已存在: {output_path} ({size / 1024 / 1024:.1f} MB)")
        print("  用 --force 覆盖下载")
        return True

    total_size = get_remote_size()
    if total_size is None:
        print("无法获取远程文件大小，将尝试下载到 EOF", file=sys.stderr)
        total_size = 65 * 1024 * 1024  # 估算 65MB

    print(f"开始下载 ECDict -> {output_path}")
    print(f"  远程大小: {total_size / 1024 / 1024:.1f} MB")

    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    start_time = time.time()

    try:
        with open(tmp_path, "wb") as f:
            downloaded = 0
            while downloaded < total_size:
                end = min(downloaded + CHUNK_SIZE - 1, total_size - 1)
                chunk = download_chunk(downloaded, end)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                pct = downloaded * 100 // total_size
                speed_mb = downloaded / 1024 / 1024 / max(time.time() - start_time, 0.001)
                print(f"\r  进度: {pct:3d}% ({downloaded / 1024 / 1024:.1f}/{total_size / 1024 / 1024:.1f} MB, {speed_mb:.1f} MB/s)",
                      end="", flush=True)

                if len(chunk) < CHUNK_SIZE and downloaded < total_size:
                    # 提前结束（EOF），更新实际大小
                    total_size = downloaded
                    break
    except Exception as e:
        print(f"\n[失败] 下载中断: {e}", file=sys.stderr)
        if tmp_path.exists():
            tmp_path.unlink()
        return False

    elapsed = time.time() - start_time
    size = tmp_path.stat().st_size
    print(f"\n[完成] {size / 1024 / 1024:.1f} MB 用时 {elapsed:.1f}s")

    # 验证：至少要有表头和合理行数
    try:
        with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
            first = f.readline()
            line_count = sum(1 for _ in f)
        if not first.startswith("word,"):
            print(f"[警告] 首行不是预期表头: {first[:60]!r}", file=sys.stderr)
        print(f"  行数: {line_count + 1}")
    except OSError as e:
        print(f"[警告] 验证失败: {e}", file=sys.stderr)

    tmp_path.replace(output_path)
    print(f"[就绪] {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="下载 ECDict 离线词典")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"输出路径（默认: {DEFAULT_OUTPUT}）")
    parser.add_argument("--force", action="store_true", help="覆盖已存在文件")
    parser.add_argument("--check", action="store_true", help="只检查不下载")
    args = parser.parse_args()

    if args.check:
        if args.output.exists():
            size = args.output.stat().st_size
            print(f"OK: {args.output} ({size / 1024 / 1024:.1f} MB)")
            return 0
        else:
            print(f"MISSING: {args.output}")
            return 1

    ok = download(args.output, force=args.force)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
