#!/usr/bin/env python3
"""
一時的な調査用スクリプト。F5公式バグトラッカーの個別ページの実際のHTML構造を
確認するため、生のHTMLをそのまま標準出力に出す（GitHub Actions上で実行し、
ジョブログから内容を確認する）。役目を終えたら削除してよい。
"""
import sys
import requests

BUG_ID = sys.argv[1] if len(sys.argv) > 1 else "1000973"
url = f"https://cdn.f5.com/product/bugtracker/ID{BUG_ID}.html"

response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
print(f"status_code={response.status_code} length={len(response.text)}", file=sys.stderr)
print(response.text)
