"""
Fortinet公式の「推奨リリース(Recommended/Suggested Release)」ページのURLが
実在し、到達可能かを確認する一時デバッグスクリプト。確認が終わり次第、
対応するworkflowと合わせて削除する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests  # noqa: E402

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

CANDIDATE_URLS = [
    "https://docs.fortinet.com/recommended-releases",
    "https://docs.fortinet.com/recommended-releases/fortigate",
    "https://www.fortinet.com/support/product-lifecycle/recommended-release",
    "https://docs.fortinet.com/upgrade-tool",
]


def check(url):
    print("=" * 80)
    print("fetching:", url)
    try:
        resp = requests.get(url, timeout=20, headers=HEADERS, allow_redirects=True)
    except Exception as e:
        print("REQUEST ERROR:", e)
        return
    print("status_code:", resp.status_code)
    print("final url:", resp.url)
    print("content length:", len(resp.text))
    print("contains 'Recommended':", "Recommended" in resp.text)
    print("contains 'Suggested':", "Suggested" in resp.text)
    print("--- body (first 2000 chars) ---")
    print(resp.text[:2000])
    print()


def main():
    for url in CANDIDATE_URLS:
        check(url)


if __name__ == "__main__":
    sys.exit(main())
