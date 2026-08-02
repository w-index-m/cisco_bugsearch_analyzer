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

    # バージョン系統ごとのEOL（サポート終了日）と関連リンクを取得
    python cli.py eol-info pan-os

    # OS名+バージョンで検証済みのCisco EOL情報を直接取得（貼り付け不要）
    python cli.py eol-lookup cisco-ios-xe 17.17
    python cli.py eol-lookup nxos 10.6

    # Cisco公式EOL通知ページのテキストを貼り付けて解析（IOS XE/NX-OS自動判定）
    python cli.py cisco-eol-parse --file eol_notice.txt
    pbpaste | python cli.py cisco-eol-parse --format json

    # Palo Alto / YAMAHA 等の「既知の問題」ページを貼り付けて解析
    python cli.py parse-issues --file known_issues.txt --translate google
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
        excel_bytes = analyzer.create_excel_report(
            results, analysis_data, search_params,
            include_release_notes=args.with_release_notes,
            translation_engine=args.translate or "google",
            deepl_api_key=args.deepl_key, nvidia_api_key=args.nvidia_key,
        )
        with open(args.output, "wb") as f:
            f.write(excel_bytes)
        note = "（症状/条件/回避策の日本語訳つき）" if args.with_release_notes else ""
        print(f"✓ Excel を書き出しました: {args.output} ({len(results)} 件){note}", file=sys.stderr)

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


def cmd_eol_info(args):
    results = analyzer.get_eol_info(args.product)

    if isinstance(results, dict) and "error" in results:
        print(f"エラー: EOL情報の取得に失敗しました - {results['error']}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print(f"「{args.product}」のEOL情報が見つかりませんでした", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"EOL情報: {args.product}（{len(results)} 系統）\n")
        for r in results:
            status = "🔴 EOL済み" if r["is_eol"] else "🟢 サポート中"
            eol_display = r["eol"] or "未定（現役）"
            print(f"[{status}] {r['release_cycle']} 系統  最新: {r['latest']}")
            print(f"  リリース日: {r['release_date']}　EOL: {eol_display}")
            if r["link"]:
                print(f"  参考: {r['link']}")
            print()


_OS_FAMILY_ALIASES = {
    "cisco-ios-xe": "cisco-ios-xe", "ios-xe": "cisco-ios-xe", "iosxe": "cisco-ios-xe",
    "cisco-nx-os": "cisco-nx-os", "nx-os": "cisco-nx-os", "nxos": "cisco-nx-os",
}


def _read_text_input(args):
    """--file 指定時はファイルから、無指定時は標準入力から貼り付けテキストを読み込む"""
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            return f.read()
    if sys.stdin.isatty():
        print(
            "エラー: --file でファイルを指定するか、標準入力からテキストを渡してください"
            "（例: pbpaste | python cli.py cisco-eol-parse）",
            file=sys.stderr,
        )
        sys.exit(1)
    return sys.stdin.read()


def cmd_eol_lookup(args):
    os_family = _OS_FAMILY_ALIASES[args.os_family]
    result = analyzer.lookup_cisco_eol(os_family, args.version)

    if result is None:
        print(
            f"エラー: {args.os_family} {args.version} の検証済みEOLデータは収録されていません。"
            "cisco-eol-parse で公式ページのテキストを貼り付けて解析してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"EOL情報: {os_family} {result['version']}\n")
        if os_family == "cisco-ios-xe":
            if result.get("note"):
                print(f"  ※ {result['note']}\n")
            for m in result["milestones"]:
                print(f"  {m['milestone']}: {m['date']}")
        else:
            print(f"  EoSWM（ソフトウェアメンテナンス終了日）: {result['eoswm']}")
            print(f"  EoVSS/LDoS（脆弱性サポート/最終サポート終了日）: {result['eovss_ldos']}")


def cmd_cisco_eol_parse(args):
    raw_text = _read_text_input(args)

    # IOS XE形式（1バージョン=1ページのマイルストーン表）を先に試し、
    # 該当しなければ NX-OS形式（全メジャーリリースをまとめた一覧表）を試す
    rows = analyzer.parse_cisco_eol_milestones(raw_text)
    fmt = "iosxe"
    if not rows:
        rows = analyzer.parse_cisco_nxos_eol_table(raw_text)
        fmt = "nxos"

    if not rows:
        print(
            "エラー: マイルストーンを検出できませんでした。"
            "\"End-of-Life Announcement Date\" 等の項目名を含むIOS XE形式、"
            "または \"NX-OS Major Release\" の一覧表（NX-OS形式）を貼り付けてください。",
            file=sys.stderr,
        )
        sys.exit(1)

    if fmt == "iosxe":
        headers, display_headers = ["milestone", "date"], ["マイルストーン", "日付"]
    else:
        headers = ["release", "eoswm", "eovss_ldos"]
        display_headers = ["NX-OSメジャーリリース", "EoSWM", "EoVSS/LDoS"]

    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif args.format == "csv":
        out = pd.DataFrame(rows)[headers].set_axis(display_headers, axis=1).to_csv(index=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"✓ CSV を書き出しました: {args.output}", file=sys.stderr)
        else:
            print(out)
    else:
        label = "IOS XE形式" if fmt == "iosxe" else "NX-OS形式"
        print(f"{label}で {len(rows)} 件検出しました\n")
        for r in rows:
            if fmt == "iosxe":
                print(f"  {r['milestone']}: {r['date']}")
            else:
                print(f"  {r['release']}: EoSWM={r['eoswm']}  EoVSS/LDoS={r['eovss_ldos']}")


def cmd_parse_issues(args):
    raw_text = _read_text_input(args)
    issues = analyzer.parse_vendor_known_issues(raw_text)

    if not issues:
        print(
            "エラー: ID（例: PAN-332943, [12]）を検出できませんでした。"
            "各IDが単独の行になっているか、行頭が角括弧の連番になっているか確認してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    has_sections = any(issue["section"] for issue in issues)
    rows = []
    for issue in issues:
        if has_sections:
            category = issue["section"] or "（見出し無し）"
        else:
            category = " / ".join(analyzer.categorize_vendor_issue(issue["description"]))

        description, workaround = issue["description"], issue["workaround"]
        if args.translate:
            description = analyzer.translate_headline(
                description, engine=args.translate,
                deepl_api_key=args.deepl_key, nvidia_api_key=args.nvidia_key,
            )
            if workaround:
                workaround = analyzer.translate_headline(
                    workaround, engine=args.translate,
                    deepl_api_key=args.deepl_key, nvidia_api_key=args.nvidia_key,
                )

        rows.append({"id": issue["id"], "category": category, "description": description, "workaround": workaround})

    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif args.format == "csv":
        df = pd.DataFrame(rows).set_axis(["ID", "カテゴリ", "説明", "回避策"], axis=1)
        out = df.to_csv(index=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"✓ CSV を書き出しました: {args.output}", file=sys.stderr)
        else:
            print(out)
    else:
        print(f"検出件数: {len(rows)} 件\n")
        for r in rows:
            print(f"[{r['category']}] {r['id']}")
            print(f"  {r['description']}")
            if r["workaround"]:
                print(f"  Workaround: {r['workaround']}")
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
    p_search.add_argument("--with-release-notes", action="store_true",
                           help="--format excel 使用時、検索結果全件の症状/条件/回避策/詳細説明を"
                                "日本語訳して列に追加する（件数が多いと生成に時間がかかる）")
    p_search.add_argument("--translate", choices=["google", "deepl", "nvidia"],
                           help="指定すると headline を翻訳して列を追加する"
                                "（--with-release-notes 使用時はリリースノートの翻訳エンジンにもなる）")
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

    # eol-info（バージョン系統ごとのEOL情報）
    p_eol = subparsers.add_parser(
        "eol-info",
        help="endoflife.date からバージョン系統ごとのリリース日・EOL日・関連リンクを取得",
    )
    p_eol.add_argument("product", help="プロダクトスラッグ（例: 'pan-os'。一覧は https://endoflife.date/ 参照）")
    p_eol.add_argument("--format", choices=["table", "json"], default="table")
    p_eol.set_defaults(func=cmd_eol_info)

    # eol-lookup（OS名+バージョンで検証済みのCisco EOL情報を直接取得、貼り付け不要）
    p_eol_lookup = subparsers.add_parser(
        "eol-lookup",
        help="OS名+バージョンで検証済みのCisco EOL情報を直接取得（貼り付け不要。未収録の場合は cisco-eol-parse を使う）",
    )
    p_eol_lookup.add_argument("os_family", choices=sorted(_OS_FAMILY_ALIASES.keys()),
                               help="OS名（cisco-ios-xe / cisco-nx-os、またはその略称）")
    p_eol_lookup.add_argument("version", help="バージョン（例: 17.17, 10.6(x)）")
    p_eol_lookup.add_argument("--format", choices=["table", "json"], default="table")
    p_eol_lookup.set_defaults(func=cmd_eol_lookup)

    # cisco-eol-parse（Cisco公式EOL通知ページのテキストを貼り付けて解析。IOS XE/NX-OS自動判定）
    p_cisco_eol_parse = subparsers.add_parser(
        "cisco-eol-parse",
        help="Cisco公式EOL通知ページのテキストを貼り付けて解析（IOS XE形式/NX-OS形式を自動判定）",
    )
    p_cisco_eol_parse.add_argument("--file", help="貼り付けテキストのファイルパス（省略時は標準入力から読み込み）")
    p_cisco_eol_parse.add_argument("--format", choices=["table", "json", "csv"], default="table")
    p_cisco_eol_parse.add_argument("--output", help="csv形式の出力先ファイルパス")
    p_cisco_eol_parse.set_defaults(func=cmd_cisco_eol_parse)

    # parse-issues（Palo Alto / YAMAHA 等の既知の問題ページを貼り付けて解析）
    p_parse_issues = subparsers.add_parser(
        "parse-issues",
        help="Palo Alto（Known and Addressed Issues）/ YAMAHA（リリースノート）等、"
             "構造化データを持たないベンダーの既知の問題ページを貼り付けて解析",
    )
    p_parse_issues.add_argument("--file", help="貼り付けテキストのファイルパス（省略時は標準入力から読み込み）")
    p_parse_issues.add_argument("--format", choices=["table", "json", "csv"], default="table")
    p_parse_issues.add_argument("--output", help="csv形式の出力先ファイルパス")
    p_parse_issues.add_argument("--translate", choices=["google", "deepl", "nvidia"],
                                 help="指定すると説明文・回避策を翻訳する（既定: 翻訳しない）")
    p_parse_issues.add_argument("--deepl-key", help="DeepL API キー（--translate deepl 使用時）")
    p_parse_issues.add_argument("--nvidia-key", help="NVIDIA API キー（--translate nvidia 使用時）")
    p_parse_issues.set_defaults(func=cmd_parse_issues)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
