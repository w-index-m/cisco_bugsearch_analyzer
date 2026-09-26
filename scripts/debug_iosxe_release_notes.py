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
# ユーザー提示の具体例（Catalyst 9200 / IOS XE 17.18 リリースノート）
EXAMPLE_URL = (
    "https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9200/software/release/"
    "17-18/release_notes/ol-17-18-9200.html"
)
# Palo Alto PAN-OS リリースノート（Known and Addressed Issues）一覧
PALOALTO_URL = "https://docs.paloaltonetworks.com/ngfw/release-notes"


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

    print()
    print("=" * 80)
    print("fetching user-provided example page:", EXAMPLE_URL)
    example = requests.get(EXAMPLE_URL, timeout=20, headers=headers)
    print("status_code:", example.status_code)
    print("content length:", len(example.text))
    print("contains 'caveat':", "caveat" in example.text.lower())
    print("contains 'CSC':", "CSC" in example.text)
    csc_ids = sorted(set(re.findall(r"CSC[a-z]{2}\d{5}", example.text)))
    print(f"CSC bug IDs found: {len(csc_ids)}")
    print(csc_ids[:20])
    print("--- example page HTML around first CSC id (if any) ---")
    if csc_ids:
        idx = example.text.find(csc_ids[0])
        print(example.text[max(0, idx - 500):idx + 1000])
    else:
        print(example.text[:5000])

    print()
    print("=" * 80)
    print("fetching Palo Alto PAN-OS release notes page:", PALOALTO_URL)
    pa = requests.get(PALOALTO_URL, timeout=20, headers=headers)
    print("status_code:", pa.status_code)
    print("content length:", len(pa.text))
    print("contains 'Addressed Issues':", "Addressed Issues" in pa.text)
    print("contains 'known-issues' or 'addressed-issues' link:", bool(
        re.search(r'href="[^"]*(known-issues|addressed-issues)[^"]*"', pa.text, re.IGNORECASE)
    ))
    print("--- Palo Alto page HTML (first 5000 chars) ---")
    print(pa.text[:5000])


if __name__ == "__main__":
    sys.exit(main())
