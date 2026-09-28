"""
一時デバッグ: PAN-OS Known Issues 収集で取りこぼしているページ（11.2 / 12.1 の
入口が見つからない件、12.2.3 Known Issues が0件の件）とタグ残りの行を調べる。
確認後に削除する。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests  # noqa: E402

import analyzer  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
BASE = analyzer.PANOS_DOCS_BASE


def get(url):
    try:
        r = requests.get(url, timeout=30, headers=UA)
        return r.status_code, r.url, r.text
    except Exception as e:
        return None, url, str(e)


def main():
    probes = []
    for n in range(0, 6):
        probes.append(f"{BASE}/pan-os/11-2/pan-os-release-notes/pan-os-11-2-{n}-known-and-addressed-issues")
        probes.append(f"{BASE}/ngfw/release-notes/12-1/pan-os-12-1-{n}-known-and-addressed-issues")
    for url in probes:
        status, final, text = get(url)
        links = sorted(set(re.findall(r'href="(/content/techdocs/en_US/[^"#]*?known-issues)\.html', text or "")))
        print(f"[probe] {status} {url} -> {final} known-issues links={links}")

    status, final, text = get(
        f"{BASE}/ngfw/release-notes/12-2/pan-os-12-2-3-known-and-addressed-issues/pan-os-12-2-3-known-issues"
    )
    print()
    print(f"[12.2.3 known] status={status} final={final} len={len(text)}")
    for tag in ("<table", "<tr", "<td", "<th"):
        print(f"  count {tag!r}: {text.count(tag)}")
    ids = re.findall(r"PAN-\d{5,7}", text)
    print("  PAN ids:", len(ids), len(set(ids)))
    body = text.find("PAN-OS 12.2.3 Known Issues")
    m = re.search(r"PAN-\d{5,7}", text)
    s = m.start() if m else body
    print("  --- snippet ---")
    print(text[max(0, s - 1500): s + 1500])

    rows = analyzer.fetch_panos_known_issue_rows(trains=("10-2", "11-1", "12-2"))
    odd = [r for r in rows if re.search(r"<|&[a-z]+;", r["headline_en"])]
    print()
    print("odd rows:", len(odd))
    for r in odd:
        print("  ", r["id"], "|", r["headline_en"][:400])


if __name__ == "__main__":
    sys.exit(main())
