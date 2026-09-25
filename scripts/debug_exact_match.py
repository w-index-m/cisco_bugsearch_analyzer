#!/usr/bin/env python3
"""
一時調査用スクリプト。NVDのkeywordExactMatchパラメータで「Catalyst 9300」の
誤検出（Nexus 9300やASA関連のCVEが混ざる問題）が実際に解消されるか確認する。
調査後は削除する。
"""
import requests

NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def probe(label, keyword, exact_match):
    print(f"=== {label} ===", flush=True)
    params = {"keywordSearch": keyword, "resultsPerPage": 20}
    if exact_match:
        params["keywordExactMatch"] = ""
    r = requests.get(NVD_API_BASE, params=params, timeout=30)
    print(f"final url: {r.url}", flush=True)
    data = r.json()
    print(f"totalResults: {data.get('totalResults')}", flush=True)
    for v in data.get("vulnerabilities", [])[:10]:
        cve = v.get("cve", {})
        descs = cve.get("descriptions", [])
        en = next((d["value"] for d in descs if d.get("lang") == "en"), "")
        print(f"  - {cve.get('id')}: {en[:150]}", flush=True)
    print(flush=True)


if __name__ == "__main__":
    probe("Catalyst 9300 (AND, exact_match=False)", "Catalyst 9300", False)
    probe("Catalyst 9300 (exact_match=True)", "Catalyst 9300", True)
    probe("IOS XE (exact_match=True, sanity check totalResults)", "IOS XE", True)
