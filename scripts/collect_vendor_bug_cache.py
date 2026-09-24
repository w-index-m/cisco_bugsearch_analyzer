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

# (session_key, ファイル名, 表示名, 収集関数を呼ぶための設定)
TARGETS = [
    {
        "key": "f5",
        "label": "F5 BIG-IP TMM",
        "collect": lambda nvd_api_key: analyzer.search_f5_bigip_tmm_bugs(
            source="both", nvd_keyword='"BIG-IP LTM"',
            translate_engine="google", nvd_api_key=nvd_api_key,
        ),
    },
    {
        "key": "paloalto",
        "label": "Palo Alto (PAN-OS)",
        "collect": lambda nvd_api_key: analyzer.search_vendor_bugs(
            nvd_keyword="Palo Alto PAN-OS", translate_engine="google", nvd_api_key=nvd_api_key,
        ),
    },
    {
        "key": "fortigate",
        "label": "FortiGate (FortiOS)",
        "collect": lambda nvd_api_key: analyzer.search_vendor_bugs(
            nvd_keyword="Fortinet FortiOS", translate_engine="google", nvd_api_key=nvd_api_key,
        ),
    },
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nvd-api-key", help="NVD APIキー（任意、無くても収集可・レート制限が厳しくなる）")
    parser.add_argument("--only", help="収集対象を絞る（カンマ区切り、例: f5,paloalto）")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    only = set(args.only.split(",")) if args.only else None

    exit_code = 0
    for target in TARGETS:
        if only and target["key"] not in only:
            continue

        print(f"[{target['key']}] {target['label']} を収集中...", file=sys.stderr)
        try:
            rows = target["collect"](args.nvd_api_key)
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
