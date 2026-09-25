"""
Palo Alto / FortiGate のNVD検索キーワードについて、Catalyst 9300で見つかった
ような「AND検索/OR検索による誤検出」がないかをざっと確認するための一時
デバッグスクリプト。確認が終わり次第、対応するworkflowと合わせて削除する。

確認内容:
  - Palo Alto: 既定キーワード '"Palo Alto" PAN-OS' の各語（"Palo Alto" は
    exact_match、"PAN-OS" はそのまま）の単独ヒット件数とタイトル例
  - FortiGate: 既定キーワード "Fortinet FortiOS" の各語（OR検索、どちらも
    exact_matchなし）の単独ヒット件数とタイトル例
    -> "Fortinet" は同社の全製品を指すブランド名のため、FortiGate/FortiOS
       と無関係な他製品（FortiMail等）のCVEまで拾っていないかを確認する
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analyzer  # noqa: E402


def check(label, term, api_key, exact_match):
    result = analyzer.search_cve_by_keyword(
        term, results_limit=2000, api_key=api_key, exact_match=exact_match,
    )
    print(f"\n=== {label}: term={term!r} exact_match={exact_match} ===")
    if isinstance(result, dict) and "error" in result:
        print(f"ERROR: {result['error']}")
        return
    print(f"total hits: {len(result)}")
    for r in result[:8]:
        print(f"  - {r['cve_id']}: {r['description_en'][:120]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nvd-api-key", default=None)
    args = parser.parse_args()

    check("Palo Alto (exact phrase)", "Palo Alto", args.nvd_api_key, True)
    check("PAN-OS (single word)", "PAN-OS", args.nvd_api_key, False)
    check("Fortinet (single word, brand)", "Fortinet", args.nvd_api_key, False)
    check("FortiOS (single word, product)", "FortiOS", args.nvd_api_key, False)


if __name__ == "__main__":
    sys.exit(main())
