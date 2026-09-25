#!/usr/bin/env python3
"""
一時調査用スクリプト。Catalyst 9300 / IOS XE のNVD keywordSearch検索が
0件になった原因を切り分けるため、いくつかのキーワードパターンで直接
NVD APIを叩いて totalResults と説明文の一部を確認する。
調査後は削除する。
"""
import sys
import time

import requests

NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def probe(label, params, timeout=30):
    print(f"=== {label} ===", flush=True)
    print(f"params: {params}", flush=True)
    try:
        r = requests.get(NVD_API_BASE, params=params, timeout=timeout)
        print(f"status_code: {r.status_code}", flush=True)
        print(f"final url: {r.url}", flush=True)
        if r.status_code != 200:
            print(f"body: {r.text[:500]}", flush=True)
            return
        data = r.json()
        print(f"totalResults: {data.get('totalResults')}", flush=True)
        vulns = data.get("vulnerabilities", [])
        for v in vulns[:3]:
            cve = v.get("cve", {})
            descs = cve.get("descriptions", [])
            en = next((d["value"] for d in descs if d.get("lang") == "en"), "")
            print(f"  - {cve.get('id')}: {en[:150]}", flush=True)
    except Exception as e:
        print(f"EXCEPTION: {e}", flush=True)
    print(flush=True)


if __name__ == "__main__":
    probe("keywordSearch='IOS XE' (space, requests auto-encode)", {"keywordSearch": "IOS XE", "resultsPerPage": 5})
    time.sleep(7)
    probe("keywordSearch='Catalyst 9300'", {"keywordSearch": "Catalyst 9300", "resultsPerPage": 5})
    time.sleep(7)
    probe("keywordSearch='Cisco IOS XE'", {"keywordSearch": "Cisco IOS XE", "resultsPerPage": 5})
    time.sleep(7)
    probe("keywordSearch='IOS' (sanity, should be huge)", {"keywordSearch": "IOS", "resultsPerPage": 5})
    time.sleep(7)
    probe("keywordSearch='Catalyst' (sanity)", {"keywordSearch": "Catalyst", "resultsPerPage": 5})
    time.sleep(7)
    probe("keywordSearch='Fortinet FortiOS' (known-good pattern, single request)",
          {"keywordSearch": "Fortinet FortiOS", "resultsPerPage": 5})
    sys.exit(0)
