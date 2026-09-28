"""
一時デバッグ: analyzer.fetch_panos_known_issue_rows() を全トレインで実行し、
件数・所要時間・サンプルを確認する（翻訳APIは呼ばない）。確認後に削除する。
"""
import collections
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analyzer  # noqa: E402


def main():
    t0 = time.time()
    rows = analyzer.fetch_panos_known_issue_rows()
    print(f"elapsed: {time.time() - t0:.1f}s  total rows: {len(rows)}")
    for src, n in sorted(collections.Counter(r["source"] for r in rows).items()):
        open_n = sum(1 for r in rows if r["source"] == src and "未修正" in r["versions"])
        pages = sorted({r["url"].rsplit("/", 1)[-1] for r in rows if r["source"] == src})
        print(f"  {src}: {n} rows (未修正 {open_n}) pages={pages}")
    for train in ("11-2", "12-1"):
        sample = [r for r in rows if r["source"].endswith(f"({train.replace('-', '.')})")][:2]
        for r in sample:
            print("-" * 60)
            print(r["id"], "|", r["versions"], "|", r["url"])
            print(r["headline_en"][:250])
    t0 = time.time()
    one = analyzer.collect_panos_known_issue_rows(target_version="11.2.4")
    print(f"target_version=11.2.4 -> {len(one)} rows in {time.time() - t0:.1f}s, "
          f"sources={set(r['source'] for r in one)}")


if __name__ == "__main__":
    sys.exit(main())
