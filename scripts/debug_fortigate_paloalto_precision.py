"""
一時デバッグ: Palo Alto PAN-OS の Known / Addressed Issues ページの HTML 構造と、
バージョン別サブページへのリンク構造を確認する（パーサー実装用）。確認後に削除する。
"""
import re
import sys

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

INDEX_URLS = [
    "https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-release-notes",
    "https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-release-notes/pan-os-11-1-0-known-and-addressed-issues",
    "https://docs.paloaltonetworks.com/ngfw/release-notes",
    "https://docs.paloaltonetworks.com/ngfw/release-notes/12-2",
    "https://docs.paloaltonetworks.com/pan-os/10-2/pan-os-release-notes",
]

ISSUE_URLS = [
    "https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-release-notes/"
    "pan-os-11-1-0-known-and-addressed-issues/pan-os-11-1-0-known-issues",
    "https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-release-notes/"
    "pan-os-11-1-0-known-and-addressed-issues/pan-os-11-1-0-h4-addressed-issues",
    "https://docs.paloaltonetworks.com/ngfw/release-notes/12-2/"
    "pan-os-12-2-3-known-and-addressed-issues",
]


def fetch(url):
    try:
        r = requests.get(url, timeout=30, headers=HEADERS)
        print(f"  status={r.status_code} len={len(r.text)} final_url={r.url}")
        return r.text
    except Exception as e:
        print(f"  ERROR {e}")
        return ""


def main():
    for url in INDEX_URLS:
        print("=" * 100)
        print("[INDEX]", url)
        html = fetch(url)
        hrefs = sorted(set(re.findall(r'href="([^"]+)"', html)))
        rel = [h for h in hrefs if "addressed" in h or "known" in h or "release-notes" in h]
        print(f"  release-note related hrefs: {len(rel)}")
        for h in rel[:120]:
            print("   ", h)

    for url in ISSUE_URLS:
        print("=" * 100)
        print("[ISSUES]", url)
        html = fetch(url)
        ids = re.findall(r"PAN-\d{5,7}", html)
        print(f"  PAN-ID occurrences={len(ids)} unique={len(set(ids))}")
        for tag in ("<table", "<tr", "<td", "<dl", "<li", "<h2", "<h3", "<p "):
            print(f"  count {tag!r}: {html.count(tag)}")
        headings = re.findall(r"<h[1-4][^>]*>(.*?)</h[1-4]>", html, re.S)
        print("  headings:", [re.sub(r"<[^>]+>", "", h).strip()[:80] for h in headings[:30]])
        starts = [m.start() for m in re.finditer(r"PAN-\d{5,7}", html)]
        for i in (0, 1, 2, len(starts) // 2, len(starts) - 1):
            if 0 <= i < len(starts):
                s = starts[i]
                print(f"  --- raw snippet around occurrence #{i} ---")
                print(html[max(0, s - 700): s + 1300])


if __name__ == "__main__":
    sys.exit(main())
