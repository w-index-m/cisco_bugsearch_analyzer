"""
FortiGuard PSIRT RSSフィードの description フィールドに、Solution（修正済み
バージョン）情報が含まれているかを確認するための一時デバッグスクリプト。
確認が終わり次第、対応するworkflowと合わせて削除する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402

FORTIGUARD_RSS_URL = "https://filestore.fortinet.com/fortiguard/rss/ir.xml"


def main():
    response = requests.get(FORTIGUARD_RSS_URL, timeout=20)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = root.findall(".//item")
    print(f"total items: {len(items)}")
    for item in items[:5]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        description_html = item.findtext("description") or ""
        print("=" * 80)
        print("title:", title)
        print("link:", link)
        print("--- raw description (full) ---")
        print(description_html)
        print()


if __name__ == "__main__":
    sys.exit(main())
