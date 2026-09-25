#!/usr/bin/env python3
"""
一時調査用スクリプト。FortiGuard PSIRT アドバイザリのRSS/XMLフィードに
実際にアクセスできるか、どんなフィールドが含まれるかを確認する。
調査後は削除する。
"""
import xml.etree.ElementTree as ET

import requests

URLS = [
    "https://filestore.fortinet.com/fortiguard/rss/ir.xml",
    "https://www.fortiguard.com/rss/ir.xml",
]


def probe(url, timeout=30):
    print(f"=== {url} ===", flush=True)
    try:
        r = requests.get(url, timeout=timeout)
        print(f"status_code: {r.status_code}", flush=True)
        print(f"content-type: {r.headers.get('Content-Type')}", flush=True)
        print(f"size: {len(r.content)} bytes", flush=True)
        if r.status_code != 200:
            print(f"body(先頭500文字): {r.text[:500]}", flush=True)
            return
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
        print(f"item数: {len(items)}", flush=True)
        for item in items[:5]:
            fields = {child.tag: (child.text or "")[:200] for child in item}
            print(f"  --- item ---", flush=True)
            for k, v in fields.items():
                print(f"    {k}: {v}", flush=True)
    except Exception as e:
        print(f"EXCEPTION: {e}", flush=True)
    print(flush=True)


if __name__ == "__main__":
    for url in URLS:
        probe(url)
