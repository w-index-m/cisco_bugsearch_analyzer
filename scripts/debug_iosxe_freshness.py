"""
Cisco IOS XE の最新CVEが約1ヶ月以上出てきていないように見える件を調査する
一時デバッグスクリプト。NVDの"IOS XE"検索(exact match)の総件数と、実際に
取得できた中で最も新しいpublished日付を確認する。確認が終わり次第、
対応するworkflowと合わせて削除する。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analyzer  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nvd-api-key", default=None)
    args = parser.parse_args()

    result = analyzer.search_cve_by_keyword(
        "IOS XE", results_limit=2000, api_key=args.nvd_api_key, exact_match=True,
    )
    if isinstance(result, dict) and "error" in result:
        print("ERROR:", result["error"])
        return

    print(f"total hits (fetched): {len(result)}")
    result.sort(key=lambda r: r.get("published") or "", reverse=True)
    print("--- most recent 10 by published date ---")
    for r in result[:10]:
        print(r["published"], r["cve_id"], r["description_en"][:100])

    print()
    print("--- Cisco PSIRT (iosxe OS type) advisories, most recent 10 ---")
    keys_client_id = None
    keys_client_secret = None
    import os
    keys_client_id = os.environ.get("PSIRT_CLIENT_ID")
    keys_client_secret = os.environ.get("PSIRT_CLIENT_SECRET")
    advisories = analyzer.fetch_cisco_psirt_by_os_version(
        "iosxe", "17.12.4", keys_client_id, keys_client_secret,
    )
    if isinstance(advisories, dict) and "error" in advisories:
        print("PSIRT ERROR:", advisories["error"])
    else:
        print(f"PSIRT advisories count: {len(advisories)}")
        advisories.sort(key=lambda a: a.get("firstPublished") or "", reverse=True)
        for a in advisories[:10]:
            print(a.get("firstPublished"), a.get("advisoryId"), a.get("advisoryTitle"))


if __name__ == "__main__":
    sys.exit(main())
