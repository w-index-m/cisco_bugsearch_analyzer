#!/usr/bin/env python3
"""
Cisco Bug Search Analyzer - CLI

Web を介さず、同一マシン/コンテナ内のエージェントやスクリプトから
直接呼び出すためのコマンドラインインターフェース。

使用例:
    # バグを検索して表で表示
    python cli.py search --feature "Catalyst 9300" --version 17.12.4

    # 検索して Excel でエクスポート
    python cli.py search --feature multicast --severity 1 2 3 \\
        --format excel --output result.xlsx

    # JSON で標準出力に出す（他のエージェント/スクリプトへパイプ）
    python cli.py search --version 17.12.4 --format json

    # 見出しを翻訳するだけ
    python cli.py translate "Device may reload unexpectedly"

    # 利用可能な IOS バージョン一覧
    python cli.py versions

    # Cisco 以外のベンダー（Palo Alto / YAMAHA 等）は NVD をキーワード検索
    python cli.py cve-search "PAN-OS 11.1.2"
    python cli.py cve-search "Yamaha RTX830" --translate google --format json
"""
import argparse
import json
import sys

import pandas as pd

import analyzer


def cmd_search(args):
    df = analyzer.load_csv(args.csv)

    results = analyzer.search_bugs(
        df,
        feature=args.feature,
        version=args.version,
        severity=args.severity,
        ios_version=args.ios_version,
        sort_by=args.sort_by,
    )

    if args.limit:
        results = results.head(args.limit)

    if len(results) == 0:
        print("該当するバグが見つかりませんでした", file=sys.stderr)
        sys.exit(1)

    # 分析データ（あれば）を読み込み、突き合わせる
    analysis_data = {}
    if args.analysis_json:
        with open(args.analysis_json, encoding="utf-8") as f:
            analysis_data = analyzer.load_analysis_from_json(f.read())

    # 翻訳（デフォルトは無効。--translate 指定時のみ翻訳して列を追加）
    if args.translate:
        results = results.copy()
        results["BUG headline (日本語)"] = results["BUG headline"].apply(
            lambda x: analyzer.translate_headline(
                x,
                engine=args.translate,
                deepl_api_key=args.deepl_key,
                nvidia_api_key=args.nvidia_key,
            )
        )

    search_params = {
        "feature": args.feature,
        "version": args.version,
        "severity": args.severity or [],
    }

    if args.format == "json":
        records = results.to_dict("records")
        for rec in records:
            bug_id = rec.get("BUG Id")
            rec["analysis"] = analysis_data.get(bug_id, {})
        print(json.dumps(records, ensure_ascii=False, indent=2, default=str))

    elif args.format == "csv":
        out = results.to_csv(index=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"✓ CSV を書き出しました: {args.output}", file=sys.stderr)
        else:
            print(out)

    elif args.format == "excel":
        if not args.output:
            print("エラー: --format excel には --output <path> が必要です", file=sys.stderr)
            sys.exit(1)
        excel_bytes = analyzer.create_excel_report(results, analysis_data, search_params)
        with open(args.output, "wb") as f:
            f.write(excel_bytes)
        print(f"✓ Excel を書き出しました: {args.output} ({len(results)} 件)", file=sys.stderr)

    else:  # table
        display_cols = ["BUG Id", "BUG headline", "Bug Severity", "Bug Status",
                         "Known Affected Release(s)", "Known Fixed Releases"]
        if args.translate:
            display_cols[1] = "BUG headline (日本語)"
        pd.set_option("display.max_colwidth", 60)
        print(f"検索結果: {len(results)} 件\n")
        print(results[display_cols].to_string(index=False))


def cmd_versions(args):
    df = analyzer.load_csv(args.csv)
    versions = analyzer.list_affected_releases(df)
    if args.format == "json":
        print(json.dumps(versions, ensure_ascii=False, indent=2))
    else:
        for v in versions:
            print(v)


def cmd_translate(args):
    result = analyzer.translate_headline(
        args.text,
        engine=args.engine,
        deepl_api_key=args.deepl_key,
        nvidia_api_key=args.nvidia_key,
    )
    print(result)


def cmd_assess(args):
    assessment = analyzer.assess_bug_possibility(
        args.headline,
        args.release_note or "",
        args.comment or "",
        groq_key=args.groq_key,
        gemini_key=args.gemini_key,
        open_router_key=args.open_router_key,
    )
    if assessment:
        print(json.dumps(assessment, ensure_ascii=False, indent=2))
    else:
        print("エラー: どの AI エンジンからも結果を取得できませんでした（API キーを確認してください）", file=sys.stderr)
        sys.exit(1)


def cmd_cve_search(args):
    results = analyzer.search_cve_with_translation(
        args.keyword,
        engine=args.translate,
        deepl_api_key=args.deepl_key,
        nvidia_api_key=args.nvidia_key,
        results_limit=args.limit,
        api_key=args.nvd_api_key,
        target_version=args.target_version,
    )

    if isinstance(results, dict) and "error" in results:
        print(f"エラー: NVD への問い合わせに失敗しました - {results['error']}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print(f"「{args.keyword}」に該当する CVE が見つかりませんでした", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"検索結果: {len(results)} 件（キーワード: {args.keyword}）\n")
        for r in results:
            score = r["cvss_score"] if r["cvss_score"] is not None else "-"
            label = f"[{r['severity_ja']}] {r['cve_id']}  (CVSS {score})"
            if args.target_version:
                label += f"  - {r['affected_ja']}"
            print(label)
            print(f"  {r['description_ja']}")
            print(f"  公開日: {r['published'][:10] if r['published'] else '-'}  参考: {r['url']}")
            print()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Cisco Bug Search Analyzer CLI（Web 不要でエージェント/スクリプトから利用可能）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = subparsers.add_parser("search", help="バグを検索する")
    p_search.add_argument("--csv", default="bugSearch.csv", help="読み込む CSV ファイル（既定: bugSearch.csv）")
    p_search.add_argument("--feature",
                           help="Product / Headline に対する部分一致検索。"
                                "カンマ(, ， 、)またはスペース区切りで複数指定するとOR検索になる "
                                "（例: 'VPN Multicast' や 'VPN,Multicast'）。スペースを含む語を"
                                "1語として検索したい場合はダブルクォートで囲む（例: '\"Catalyst 9300\" VPN'）")
    p_search.add_argument("--version",
                           help="検索バージョン。同トレイン内で旧バージョンから未修正のまま "
                                "続いている可能性があるバグも推測で含む（中間バージョンでの "
                                "発生を保証するものではない）")
    p_search.add_argument("--ios-version", help="特定 IOS バージョンで絞り込み（--version と同じ判定ロジック）")
    p_search.add_argument("--severity", type=int, nargs="+", default=[1, 2, 3],
                           help="対象 Severity（既定: 1 2 3）")
    p_search.add_argument("--sort-by", choices=["severity", "last_modified", "bug_id"],
                           default="severity", help="ソート順（既定: severity）")
    p_search.add_argument("--limit", type=int, help="表示/出力件数の上限")
    p_search.add_argument("--format", choices=["table", "json", "csv", "excel"],
                           default="table", help="出力形式（既定: table）")
    p_search.add_argument("--output", help="csv/excel 形式の出力先ファイルパス")
    p_search.add_argument("--analysis-json", help="既存の分析結果 JSON を読み込んで結果に付与する")
    p_search.add_argument("--translate", choices=["google", "deepl", "nvidia"],
                           help="指定すると headline を翻訳して列を追加する")
    p_search.add_argument("--deepl-key", help="DeepL API キー（--translate deepl 使用時）")
    p_search.add_argument("--nvidia-key", help="NVIDIA API キー（--translate nvidia 使用時）")
    p_search.set_defaults(func=cmd_search)

    # versions
    p_versions = subparsers.add_parser("versions", help="CSV 内の IOS バージョン一覧を表示")
    p_versions.add_argument("--csv", default="bugSearch.csv")
    p_versions.add_argument("--format", choices=["table", "json"], default="table")
    p_versions.set_defaults(func=cmd_versions)

    # translate
    p_translate = subparsers.add_parser("translate", help="テキストを日本語に翻訳")
    p_translate.add_argument("text", help="翻訳するテキスト")
    p_translate.add_argument("--engine", choices=["google", "deepl", "nvidia"], default="google")
    p_translate.add_argument("--deepl-key", help="DeepL API キー")
    p_translate.add_argument("--nvidia-key", help="NVIDIA API キー")
    p_translate.set_defaults(func=cmd_translate)

    # assess
    p_assess = subparsers.add_parser("assess", help="AI でバグの発生可能性を判定")
    p_assess.add_argument("headline", help="バグのタイトル（日本語推奨）")
    p_assess.add_argument("--release-note", help="リリースノート本文")
    p_assess.add_argument("--comment", help="ユーザーコメント")
    p_assess.add_argument("--groq-key", help="Groq API キー")
    p_assess.add_argument("--gemini-key", help="Gemini API キー")
    p_assess.add_argument("--open-router-key", help="Open Router API キー")
    p_assess.set_defaults(func=cmd_assess)

    # cve-search（Cisco 以外のベンダー向け：NVD をキーワード検索）
    p_cve = subparsers.add_parser(
        "cve-search",
        help="NVD（脆弱性データベース）をキーワード検索。Palo Alto / YAMAHA など、"
             "構造化データを持たないベンダーの調査に使う",
    )
    p_cve.add_argument("keyword", help="検索キーワード（例: 'PAN-OS 11.1.2', 'Yamaha RTX830'）")
    p_cve.add_argument("--limit", type=int, default=20, help="取得件数上限（既定: 20）")
    p_cve.add_argument("--format", choices=["table", "json"], default="table")
    p_cve.add_argument("--translate", choices=["google", "deepl", "nvidia"], default="google",
                        help="説明文の翻訳エンジン（既定: google）")
    p_cve.add_argument("--deepl-key", help="DeepL API キー（--translate deepl 使用時）")
    p_cve.add_argument("--nvidia-key", help="NVIDIA API キー（--translate nvidia 使用時）")
    p_cve.add_argument("--nvd-api-key",
                        help="NVD API キー（省略可。指定するとレート制限が緩和される。"
                             "https://nvd.nist.gov/developers/request-an-api-key）")
    p_cve.add_argument("--target-version",
                        help="指定すると、各CVEがこのバージョンに影響するか（NVDのバージョン範囲データから"
                             "判定した Fixed/Affected）を結果に付与する（例: '11.1.2'）")
    p_cve.set_defaults(func=cmd_cve_search)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
