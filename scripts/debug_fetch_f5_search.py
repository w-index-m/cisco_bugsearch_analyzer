#!/usr/bin/env python3
"""
一時的な調査用スクリプト。F5公式バグトラッカーの「検索/一覧ページ」および
サイトマップ等、個別Bug IDページ以外に大量のBug IDを見つける手がかりが
無いか確認する（GitHub Actions上で実行し、ジョブログから内容を確認する）。
役目を終えたら削除してよい。
"""
import sys
import requests

CANDIDATE_URLS = [
    "https://my.f5.com/manage/s/bug-tracker",
    "https://cdn.f5.com/sitemap.xml",
    "https://cdn.f5.com/product/bugtracker/sitemap.xml",
    "https://cdn.f5.com/product/bugtracker/",
    "https://cdn.f5.com/product/bugtracker/index.html",
]

for url in CANDIDATE_URLS:
    print(f"\n===== {url} =====", file=sys.stderr)
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        print(f"status_code={response.status_code} length={len(response.text)}", file=sys.stderr)
        print(response.text[:6000])
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
