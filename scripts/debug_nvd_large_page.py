#!/usr/bin/env python3
"""
一時調査用スクリプト。fetch_limit=2000(resultsPerPage=2000)で
「Catalyst 9300」「IOS XE」を検索すると0件になる原因を切り分ける。
実際のanalyzer.pyのsearch_cve_by_keyword相当のロジックを直接呼び出して
生レスポンスを確認する。調査後は削除する。
"""
import sys
import time

sys.path.insert(0, "/home/runner/work/cisco_bugsearch_analyzer/cisco_bugsearch_analyzer")
import analyzer  # noqa: E402


def probe(label, keyword, results_per_page):
    print(f"=== {label}: keyword={keyword!r}, resultsPerPage={results_per_page} ===", flush=True)
    result = analyzer.search_cve_by_keyword(keyword, results_limit=results_per_page, timeout=60)
    if isinstance(result, dict) and "error" in result:
        print(f"ERROR: {result['error']}", flush=True)
    else:
        print(f"件数: {len(result)}", flush=True)
        for r in result[:3]:
            print(f"  - {r['cve_id']} {r['published']}", flush=True)
    print(flush=True)


if __name__ == "__main__":
    probe("Catalyst 9300 / rpp=2000", "Catalyst 9300", 2000)
    time.sleep(8)
    probe("IOS XE / rpp=2000", "IOS XE", 2000)
    time.sleep(8)
    probe("Catalyst 9300 / rpp=300 (再現用)", "Catalyst 9300", 300)
    time.sleep(8)
    probe("Catalyst 9300 / rpp=16 (totalResultsちょうど)", "Catalyst 9300", 16)
