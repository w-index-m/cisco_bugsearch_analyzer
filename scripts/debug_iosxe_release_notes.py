"""
Cisco IOS XE 17 リリースノート一覧ページと、そこからリンクされる個別の
リリースノートページ（Resolved/Open Caveats を含むことが多い）が、
契約無しで自動取得できる形式かどうかを確認する一時デバッグスクリプト。
確認が終わり次第、対応するworkflowと合わせて削除する。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests  # noqa: E402

LIST_URL = "https://www.cisco.com/c/en/us/support/ios-nx-os-software/ios-xe-17/products-release-notes-list.html"


def main():
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(LIST_URL, timeout=20, headers=headers)
    print("list page status_code:", resp.status_code)
    print("list page content length:", len(resp.text))

    links = re.findall(r'href="([^"]+release-notes[^"]*)"', resp.text, re.IGNORECASE)
    unique_links = sorted(set(links))
    print(f"found {len(unique_links)} release-notes-like links")
    for link in unique_links[:15]:
        print(" -", link)

    if not unique_links:
        print("--- list page HTML (first 5000 chars) ---")
        print(resp.text[:5000])
        return

    # 個別リリースノートページを1つ試しに取得する
    candidate = unique_links[0]
    if candidate.startswith("/"):
        candidate = "https://www.cisco.com" + candidate
    print()
    print("fetching individual release note page:", candidate)
    page = requests.get(candidate, timeout=20, headers=headers)
    print("status_code:", page.status_code)
    print("content length:", len(page.text))
    has_caveat_word = "caveat" in page.text.lower()
    print("contains 'caveat':", has_caveat_word)
    print("--- page HTML (first 5000 chars) ---")
    print(page.text[:5000])


if __name__ == "__main__":
    sys.exit(main())
