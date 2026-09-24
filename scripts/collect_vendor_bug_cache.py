#!/usr/bin/env python3
"""
F5 BIG-IP TMM / Palo Alto (PAN-OS) / FortiGate (FortiOS) のバグ情報を
NVD等から収集し、data/vendor_bugs/ 配下にJSONとしてキャッシュするスクリプト。

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
from datetime import datetime, timezone
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
CACHE_FETCH_LIMIT = 300

# F5公式バグトラッカーの全件一覧（数千件）から、実際に個別ページを取得する
# 件数の上限。1件ごとにHTTPリクエストが発生する（0.5秒間隔）ため、大きくする
# ほどF5サーバーへの負荷・収集時間が増える。
CACHE_F5_BUGTRACKER_LIMIT = 100

# (session_key, ファイル名, 表示名, 収集関数を呼ぶための設定)
# 翻訳は既定でGoogle Translate（無料の非公式エンドポイント）を使うが、
# GitHub Actionsランナーの共有IPからはボット対策でブロックされ翻訳できない
# ことが多いため、キーを渡した場合はGoogle失敗時に
# DeepL → Groq → OpenRouter の順にフォールバックする
# （analyzer.translate_headline の既存フォールバック機構）。
TARGETS = [
    {
        "key": "f5",
        "label": "F5 BIG-IP",
        "collect": lambda keys: analyzer.search_f5_bigip_tmm_bugs(
            source="both", nvd_keyword="BIG-IP",
            translate_engine="google", nvd_api_key=keys["nvd"], deepl_api_key=keys["deepl"],
            groq_api_key=keys["groq"], open_router_api_key=keys["openrouter"],
            results_limit=CACHE_RESULTS_LIMIT, fetch_limit=CACHE_FETCH_LIMIT,
            bugtracker_limit=CACHE_F5_BUGTRACKER_LIMIT,
        ),
    },
    {
        "key": "paloalto",
        "label": "Palo Alto (PAN-OS)",
        "collect": lambda keys: analyzer.search_vendor_bugs(
            nvd_keyword='"Palo Alto" PAN-OS', translate_engine="google",
            nvd_api_key=keys["nvd"], deepl_api_key=keys["deepl"],
            groq_api_key=keys["groq"], open_router_api_key=keys["openrouter"],
            results_limit=CACHE_RESULTS_LIMIT, fetch_limit=CACHE_FETCH_LIMIT,
        ),
    },
    {
        "key": "fortigate",
        "label": "FortiGate (FortiOS)",
        "collect": lambda keys: analyzer.search_vendor_bugs(
            nvd_keyword="Fortinet FortiOS", translate_engine="google",
            nvd_api_key=keys["nvd"], deepl_api_key=keys["deepl"],
            groq_api_key=keys["groq"], open_router_api_key=keys["openrouter"],
            results_limit=CACHE_RESULTS_LIMIT, fetch_limit=CACHE_FETCH_LIMIT,
        ),
    },
]


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
    parser.add_argument("--only", help="収集対象を絞る（カンマ区切り、例: f5,paloalto）")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    only = set(args.only.split(",")) if args.only else None
    keys = {
        "nvd": args.nvd_api_key, "deepl": args.deepl_api_key,
        "groq": args.groq_api_key, "openrouter": args.openrouter_api_key,
    }

    exit_code = 0
    for target in TARGETS:
        if only and target["key"] not in only:
            continue

        print(f"[{target['key']}] {target['label']} を収集中...", file=sys.stderr)
        try:
            rows = target["collect"](keys)
        except Exception as e:
            print(f"  -> 収集中に例外が発生しました: {e}", file=sys.stderr)
            exit_code = 1
            continue

        if isinstance(rows, dict) and "error" in rows:
            print(f"  -> 収集に失敗しました: {rows['error']}", file=sys.stderr)
            exit_code = 1
            continue

        out_path = OUTPUT_DIR / f"{target['key']}.json"
        payload = {
            "label": target["label"],
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "count": len(rows),
            "rows": rows,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"  -> {len(rows)} 件を {out_path} に保存しました", file=sys.stderr)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
