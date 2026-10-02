#!/usr/bin/env python3
"""
F5 BIG-IP / Palo Alto (PAN-OS) / FortiGate (FortiOS) / Catalyst 9300 / Cisco IOS XE
のバグ情報をNVD等から収集し、data/vendor_bugs/ 配下にJSONとしてキャッシュするスクリプト。

このプロジェクトの開発・実行環境（サンドボックス）からは NVD (services.nvd.nist.gov)
や F5公式サイト (cdn.f5.com) への通信がネットワークポリシーでブロックされている
ことがあるため、GitHub Actions（.github/workflows/collect-vendor-bugs.yml）上で
定期的にこのスクリプトを実行し、結果をリポジトリにコミットしておく運用にしている。
Streamlit アプリ（app.py）は、まずこのキャッシュを読み込んで即座に表示し、
必要なときだけライブでNVDへ再検索する。

使用例:
    python scripts/collect_vendor_bug_cache.py
    python scripts/collect_vendor_bug_cache.py --nvd-api-key "$NVD_API_KEY"
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analyzer  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "vendor_bugs"

# キャッシュには、ライブ検索の既定件数（20件）より多めに保持しておき、
# 必要に応じて多くの履歴をブラウズできるようにする。翻訳はこの件数分だけ
# 呼び出すため、CACHE_RESULTS_LIMIT を増やすと翻訳API呼び出し回数もほぼ
# 比例して増える（DeepL無料枠は月間約50万文字）。まずは200件（従来の10倍）
# から様子を見る。
CACHE_RESULTS_LIMIT = 200
# NVDのkeywordSearchは日付降順を保証しないため、totalResultsがこの値を
# 超えるキーワード（例: 「IOS XE」で総ヒット数585件）ではCACHE_FETCH_LIMITを
# 超えた分の最新CVEが1件も取得できなくなる不具合があった。NVD側の
# resultsPerPage上限である2000まで引き上げて、この取りこぼしを防ぐ
# （analyzer.py の _fetch_nvd_results_or 参照）。
CACHE_FETCH_LIMIT = 2000

# F5公式バグトラッカーの全件一覧（数千件）から、実際に個別ページを取得する
# 件数の上限。1件ごとにHTTPリクエストが発生する（0.5秒間隔）ため、大きくする
# ほどF5サーバーへの負荷・収集時間が増える。
CACHE_F5_BUGTRACKER_LIMIT = 100

# (session_key, ファイル名, 表示名, 収集関数を呼ぶための設定)
# 翻訳エンジンはGroqを既定にする。Google Translate（無料の非公式エンドポイント）は
# GitHub Actionsランナーの共有IPからはボット対策でブロックされることが多く、
# DeepLも無料枠の月間文字数上限に達しやすいため、実際に安定して動作するGroqを
# 優先エンジンにした（Groq失敗時はGoogle→DeepL→OpenRouterの順にフォールバック、
# analyzer.translate_headline の既存フォールバック機構）。
TARGETS = [
    {
        "key": "f5",
        "label": "F5 BIG-IP",
        "collect": lambda keys: analyzer.search_f5_bigip_tmm_bugs(
            source="both", nvd_keyword="BIG-IP",
            translate_engine="groq", nvd_api_key=keys["nvd"], deepl_api_key=keys["deepl"],
            groq_api_key=keys["groq"], open_router_api_key=keys["openrouter"],
            results_limit=CACHE_RESULTS_LIMIT, fetch_limit=CACHE_FETCH_LIMIT,
            bugtracker_limit=CACHE_F5_BUGTRACKER_LIMIT,
        ),
    },
    {
        "key": "paloalto",
        "label": "Palo Alto (PAN-OS)",
        "collect": lambda keys: analyzer.search_paloalto_bugs(
            nvd_keyword='"Palo Alto" PAN-OS', source="both", translate_engine="groq",
            nvd_api_key=keys["nvd"], deepl_api_key=keys["deepl"],
            groq_api_key=keys["groq"], open_router_api_key=keys["openrouter"],
            results_limit=CACHE_RESULTS_LIMIT, fetch_limit=CACHE_FETCH_LIMIT,
        ),
    },
    {
        "key": "fortigate",
        "label": "FortiGate (FortiOS)",
        "collect": lambda keys: analyzer.search_fortigate_bugs(
            nvd_keyword="FortiOS", source="both", translate_engine="groq",
            nvd_api_key=keys["nvd"], deepl_api_key=keys["deepl"],
            groq_api_key=keys["groq"], open_router_api_key=keys["openrouter"],
            results_limit=CACHE_RESULTS_LIMIT, fetch_limit=CACHE_FETCH_LIMIT,
        ),
    },
    {
        "key": "catalyst9300",
        "label": "Catalyst 9300",
        "collect": lambda keys: analyzer.search_vendor_bugs_with_psirt(
            nvd_keyword='"Catalyst 9300"', translate_engine="groq",
            nvd_api_key=keys["nvd"], deepl_api_key=keys["deepl"],
            groq_api_key=keys["groq"], open_router_api_key=keys["openrouter"],
            results_limit=CACHE_RESULTS_LIMIT, fetch_limit=CACHE_FETCH_LIMIT,
            psirt_product="Cisco Catalyst 9300",
            cisco_psirt_client_id=keys["psirt_client_id"], cisco_psirt_client_secret=keys["psirt_client_secret"],
        ),
    },
    {
        "key": "iosxe",
        "label": "Cisco IOS XE",
        "collect": lambda keys: analyzer.search_vendor_bugs_with_psirt(
            nvd_keyword='"IOS XE"', translate_engine="groq",
            nvd_api_key=keys["nvd"], deepl_api_key=keys["deepl"],
            groq_api_key=keys["groq"], open_router_api_key=keys["openrouter"],
            results_limit=CACHE_RESULTS_LIMIT, fetch_limit=CACHE_FETCH_LIMIT,
            psirt_os_type="iosxe", psirt_product="Cisco IOS XE",
            cisco_psirt_client_id=keys["psirt_client_id"], cisco_psirt_client_secret=keys["psirt_client_secret"],
        ),
    },
]


# NVDの取得に失敗した日に、cvelistV5の日次差分から補完する際のキーワード
# （各TARGETのNVD検索キーワードと同じ指定方法）と、遡る日数の上限
CVELIST_FALLBACK_KEYWORDS = {
    "f5": "BIG-IP",
    "paloalto": '"Palo Alto" PAN-OS',
    "fortigate": "FortiOS",
    "catalyst9300": '"Catalyst 9300"',
    "iosxe": '"IOS XE"',
}
CVELIST_FALLBACK_MAX_DAYS = 14


def _fallback_from_cvelist(target, prev_payload, keys):
    """
    NVDに繋がらず収集に失敗した機種について、前回キャッシュの行を維持したまま、
    前回の収集日以降にcvelistV5で公開・更新されたCVEのうちキーワードに一致し、
    まだキャッシュに無いものを追加する。当日分の差分は日付が変わってから公開
    されるため、前回収集日〜前日までを対象にする。

    Returns:
        (rows, 追加件数)
    """
    prev_rows = prev_payload.get("rows", [])
    try:
        since = datetime.fromisoformat(prev_payload["generated_at"]).date()
    except (KeyError, ValueError):
        since = datetime.now(timezone.utc).date() - timedelta(days=CVELIST_FALLBACK_MAX_DAYS)
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    since = max(since, yesterday - timedelta(days=CVELIST_FALLBACK_MAX_DAYS - 1))

    records_by_id = {}
    day = since
    while day <= yesterday:
        records = analyzer.fetch_cvelist_daily_records(day.isoformat())
        if isinstance(records, dict):
            print(f"  -> cvelistV5 {day} の取得に失敗（スキップ）: {records['error']}", file=sys.stderr)
        else:
            for record in records:
                records_by_id[record.get("cveMetadata", {}).get("cveId")] = record
        day += timedelta(days=1)

    extractor = analyzer._extract_bigip_versions if target["key"] == "f5" else analyzer._extract_generic_versions
    candidates = analyzer.cvelist_records_to_rows(
        list(records_by_id.values()), CVELIST_FALLBACK_KEYWORDS[target["key"]], version_extractor=extractor,
    )
    existing_ids = {i.strip() for r in prev_rows for i in str(r.get("id", "")).split(",")}
    # 差分には「CISAが情報を追記した」等で更新されただけの古いCVEも大量に
    # 含まれるため、前回収集日以降に新規公開されたものだけを追加する
    new_rows = [
        r for r in candidates
        if r["id"] not in existing_ids and r["date"] and r["date"] >= since.isoformat()
    ]

    for i, r in enumerate(new_rows):
        if i > 0:
            time.sleep(0.3)
        r["headline_ja"] = analyzer.translate_headline(
            r["headline_en"], engine="groq", deepl_api_key=keys["deepl"],
            groq_api_key=keys["groq"], open_router_api_key=keys["openrouter"],
        )

    if new_rows:
        kev_ids = analyzer.fetch_cisa_kev_ids()
        epss_scores = analyzer.fetch_epss_scores([r["id"] for r in new_rows])
        for r in new_rows:
            r["kev"] = (r["id"] in kev_ids) if kev_ids is not None else None
            r["epss"] = epss_scores.get(r["id"])

    return analyzer.sort_bug_rows_by_date_desc(prev_rows + new_rows), len(new_rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nvd-api-key", help="NVD APIキー（任意、無くても収集可・レート制限が厳しくなる）")
    parser.add_argument(
        "--deepl-api-key",
        help="DeepL APIキー（任意。指定すると、Google翻訳が失敗した場合のフォールバックとして使われる）"
    )
    parser.add_argument(
        "--groq-api-key",
        help="Groq APIキー（任意。Google翻訳・DeepL両方が失敗した場合のフォールバックとして使われる）"
    )
    parser.add_argument(
        "--openrouter-api-key",
        help="OpenRouter APIキー（任意。他の翻訳手段が全て失敗した場合の最後のフォールバック）"
    )
    parser.add_argument(
        "--cisco-psirt-client-id",
        help="Cisco PSIRT openVuln API の Client ID（任意。Catalyst 9300/IOS XEでCisco公式アドバイザリも合流収集する）"
    )
    parser.add_argument(
        "--cisco-psirt-client-secret",
        help="Cisco PSIRT openVuln API の Client Secret（任意、--cisco-psirt-client-id とセットで使う）"
    )
    parser.add_argument("--only", help="収集対象を絞る（カンマ区切り、例: f5,paloalto）")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    only = set(args.only.split(",")) if args.only else None
    keys = {
        "nvd": args.nvd_api_key, "deepl": args.deepl_api_key,
        "groq": args.groq_api_key, "openrouter": args.openrouter_api_key,
        "psirt_client_id": args.cisco_psirt_client_id, "psirt_client_secret": args.cisco_psirt_client_secret,
    }

    # Groq無料枠の1日あたりトークン上限（TPD）に達すると、その日はそれ以降の
    # 機種を翻訳できずに終わる。TARGETSが常に同じ順序（F5→...→IOS XE）だと、
    # 毎日必ず同じ機種（先頭のF5）が優先され、後方の機種（件数の多いIOS XEなど）
    # が慢性的に割を食う。日替わりで開始位置をローテーションし、どの機種も
    # 順番に「その日の最優先」になれるようにする（UTC日付ベースなので、
    # 1日1回の定期実行と噛み合う）。
    rotation = datetime.now(timezone.utc).date().toordinal() % len(TARGETS)
    ordered_targets = TARGETS[rotation:] + TARGETS[:rotation]
    print(
        f"本日の処理順（{rotation}件ローテーション): "
        + " -> ".join(t["key"] for t in ordered_targets),
        file=sys.stderr,
    )

    exit_code = 0
    for target in ordered_targets:
        if only and target["key"] not in only:
            continue

        print(f"[{target['key']}] {target['label']} を収集中...", file=sys.stderr)

        # 前回このスクリプトが書き出したキャッシュ（今回上書きする前のもの）から
        # 「原文 -> 訳文」対応表を読み込み、既に翻訳済みの行はAPIを呼ばずに
        # 再利用する（Groq等の無料枠の1日あたりトークン上限が、毎日ほぼ同じ
        # 数百件を再翻訳するだけで枯渇してしまう問題への対策）
        prev_path = OUTPUT_DIR / f"{target['key']}.json"
        known_translations = {}
        prev_payload = None
        if prev_path.exists():
            try:
                prev_payload = json.loads(prev_path.read_text(encoding="utf-8"))
                for r in prev_payload.get("rows", []):
                    en, ja = r.get("headline_en"), r.get("headline_ja")
                    if en and ja and ja != en:
                        known_translations[en] = ja
            except Exception as e:
                print(f"  -> 前回キャッシュの読み込みに失敗（無視して続行）: {e}", file=sys.stderr)
        analyzer.set_known_translations(known_translations)
        print(f"  -> 前回訳文の再利用可能件数: {len(known_translations)}", file=sys.stderr)

        try:
            rows = target["collect"](keys)
        except Exception as e:
            rows = {"error": f"収集中に例外が発生しました: {e}"}

        fallback_note = None
        if isinstance(rows, dict) and "error" in rows:
            error_text = rows["error"]
            print(f"  -> 収集に失敗しました: {error_text}", file=sys.stderr)
            if not prev_payload:
                exit_code = 1
                continue
            rows, added = _fallback_from_cvelist(target, prev_payload, keys)
            fallback_note = f"収集失敗（{error_text}）のため前回データを維持し、cvelistV5から新規 {added} 件を補完"
            print(f"  -> 前回キャッシュを維持し、cvelistV5から新規 {added} 件を補完しました", file=sys.stderr)

        out_path = OUTPUT_DIR / f"{target['key']}.json"
        payload = {
            "label": target["label"],
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "count": len(rows),
            "rows": rows,
        }
        if fallback_note:
            payload["fallback"] = fallback_note
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"  -> {len(rows)} 件を {out_path} に保存しました", file=sys.stderr)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
