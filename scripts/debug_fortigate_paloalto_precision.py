"""
一時デバッグ: analyzer.fetch_panos_known_issue_rows() を実際に動かし、
トレインごとの取得件数・サンプル行・取得したページを確認する。確認後に削除する。
"""
import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests  # noqa: E402

import analyzer  # noqa: E402


def main():
    for train in analyzer.PANOS_TRACKED_TRAINS:
        url = analyzer._panos_train_landing_url(train)
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            paths = [p for p in dict.fromkeys(analyzer._PANOS_KNOWN_ISSUES_HREF_RE.findall(r.text)) if f"/{train}/" in p]
            print(f"[{train}] landing status={r.status_code} final={r.url} known-issues pages={paths}")
        except Exception as e:
            print(f"[{train}] landing ERROR {e}")

    rows = analyzer.fetch_panos_known_issue_rows()
    print()
    print("total rows:", len(rows))
    by_source = collections.Counter(r["source"] for r in rows)
    for k, v in by_source.items():
        open_count = sum(1 for r in rows if r["source"] == k and "未修正" in r["versions"])
        print(f"  {k}: {v} rows (未修正 {open_count})")
    by_url = collections.Counter(r["url"] for r in rows)
    for k, v in by_url.items():
        print(f"  page {k}: {v}")
    for r in rows[:3] + rows[-3:]:
        print("-" * 80)
        print(r["id"], "|", r["versions"])
        print(r["headline_en"][:300])
    lengths = sorted(len(r["headline_en"]) for r in rows)
    if lengths:
        print("headline length min/median/max:", lengths[0], lengths[len(lengths) // 2], lengths[-1])
    odd = [r for r in rows if re.search(r"<|&[a-z]+;", r["headline_en"])]
    print("rows with leftover markup:", len(odd))


if __name__ == "__main__":
    sys.exit(main())
