#!/usr/bin/env python3
"""
F5 BIG-IP TMM（Traffic Management Microkernel）関連バグ収集スクリプト（CLI）

コアロジックは analyzer.py の search_f5_bigip_tmm_bugs() 等に実装されており、
Streamlit の app.py（「F5 BIG-IP TMM バグ検索」セクション）からも同じロジックを
利用できる。

2つのデータソースから収集し、最近の日付順（新しい順）に並べて表示する:

1. NVD（CVE/CVSSを集約している米国立脆弱性データベース）
2. F5公式バグトラッカー（https://cdn.f5.com/product/bugtracker/ID<番号>.html）
   - 検索ページの実際のHTML構造は開発環境から確認できなかったため、個別の
     Bug IDページを1件ずつ取得する方式。既定では analyzer.KNOWN_TMM_BUG_IDS
     （Web検索で確認済みのTMM関連Bug IDのスナップショット）を使う。
     --bug-ids で任意のBug IDを追加指定できる。

使用例:
    python f5_bigip_tmm_bugs.py
    python f5_bigip_tmm_bugs.py --nvd-keyword "F5 BIG-IP TMM buffer overflow"
    python f5_bigip_tmm_bugs.py --bug-ids 1006509,993921,1000973
    python f5_bigip_tmm_bugs.py --source nvd
    python f5_bigip_tmm_bugs.py --format excel --output f5_tmm_bugs.xlsx
    python f5_bigip_tmm_bugs.py --translate google
"""
import argparse
import json
import sys

import pandas as pd

import analyzer


def build_parser():
    parser = argparse.ArgumentParser(
        prog="f5_bigip_tmm_bugs.py",
        description="F5 BIG-IP TMM関連バグを収集し、対象OS（バージョン）と見出しを新しい順に一覧表示する",
    )
    parser.add_argument(
        "--source", choices=["both", "nvd", "bugtracker"], default="both",
        help="収集元（既定: both = NVD + F5公式バグトラッカー）"
    )
    parser.add_argument(
        "--nvd-keyword", default="BIG-IP",
        help='NVD検索キーワード（既定: "BIG-IP"、スペース区切りでOR検索）'
    )
    parser.add_argument("--nvd-api-key", help="NVD APIキー（任意。指定するとレート制限が緩和される）")
    parser.add_argument("--target-version", help="対象バージョンを指定すると、NVD側の結果に影響有無の判定を付与する（例: 17.1.1）")
    parser.add_argument(
        "--bug-ids",
        help="F5公式バグトラッカーで追加取得したいBug ID（カンマ区切り、例: 1006509,993921）。"
             "省略時は既知のTMM関連Bug ID一覧（analyzer.KNOWN_TMM_BUG_IDS）を使う"
    )
    parser.add_argument("--translate", choices=["google", "deepl", "nvidia"], help="指定すると見出しを日本語訳する（既定: 翻訳しない）")
    parser.add_argument("--deepl-key", help="DeepL APIキー（--translate deepl 使用時）")
    parser.add_argument("--nvidia-key", help="NVIDIA APIキー（--translate nvidia 使用時）")
    parser.add_argument("--format", choices=["table", "json", "csv", "excel"], default="table", help="出力形式（既定: table）")
    parser.add_argument("--output", help="csv/excel形式の出力先ファイルパス")
    return parser


def main():
    args = build_parser().parse_args()

    bug_ids = [b.strip() for b in args.bug_ids.split(",")] if args.bug_ids else None

    print(f"[収集中] source={args.source} nvd_keyword=\"{args.nvd_keyword}\"...", file=sys.stderr)
    all_rows = analyzer.search_f5_bigip_tmm_bugs(
        source=args.source, nvd_keyword=args.nvd_keyword, bug_ids=bug_ids,
        translate_engine=args.translate, deepl_api_key=args.deepl_key, nvidia_api_key=args.nvidia_key,
        nvd_api_key=args.nvd_api_key, target_version=args.target_version,
    )

    if isinstance(all_rows, dict) and "error" in all_rows:
        print(f"エラー: NVDへの問い合わせに失敗しました - {all_rows['error']}", file=sys.stderr)
        sys.exit(1)

    if not all_rows:
        print("該当するバグ/CVEが見つかりませんでした", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame(all_rows)
    display_cols = ["date", "source", "id", "versions", "headline_ja" if args.translate else "headline_en", "url"]
    display_names = ["日付", "出所", "ID", "対象OS(バージョン)", "見出し", "参考リンク"]

    if args.format == "json":
        print(json.dumps(all_rows, ensure_ascii=False, indent=2))

    elif args.format == "csv":
        out_df = df[display_cols].copy()
        out_df.columns = display_names
        out = out_df.to_csv(index=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"✓ CSVを書き出しました: {args.output}", file=sys.stderr)
        else:
            print(out)

    elif args.format == "excel":
        if not args.output:
            print("エラー: --format excel には --output <path> が必要です", file=sys.stderr)
            sys.exit(1)
        headers = ["日付", "出所", "ID", "対象OS(バージョン)", "見出し(日本語)", "見出し(原文)", "参考リンク"]
        rows = [
            [r.get("date") or "不明", r["source"], r["id"], r["versions"], r.get("headline_ja", ""), r["headline_en"], r["url"]]
            for r in all_rows
        ]
        excel_data = analyzer.create_combined_excel_report(
            extra_sheets=[{"name": "F5 BIG-IP TMM", "headers": headers, "rows": rows}]
        )
        with open(args.output, "wb") as f:
            f.write(excel_data)
        print(f"✓ Excelを書き出しました: {args.output} ({len(all_rows)} 件)", file=sys.stderr)

    else:  # table
        out_df = df[display_cols].copy()
        out_df.columns = display_names
        out_df["日付"] = out_df["日付"].fillna("不明")
        pd.set_option("display.max_colwidth", 60)
        print(f"収集結果: {len(all_rows)} 件（新しい順）\n")
        print(out_df.to_string(index=False))


if __name__ == "__main__":
    main()
