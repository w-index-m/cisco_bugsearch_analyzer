#!/usr/bin/env python3
"""一時調査用。「9300」単体で検索した場合の件数・内容を確認する。調査後に削除する。"""
import requests

NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"

r = requests.get(NVD_API_BASE, params={"keywordSearch": "9300", "resultsPerPage": 20}, timeout=30)
print("final url:", r.url, flush=True)
data = r.json()
print("totalResults:", data.get("totalResults"), flush=True)
for v in data.get("vulnerabilities", [])[:15]:
    cve = v.get("cve", {})
    descs = cve.get("descriptions", [])
    en = next((d["value"] for d in descs if d.get("lang") == "en"), "")
    print(f"  - {cve.get('id')}: {en[:150]}", flush=True)
