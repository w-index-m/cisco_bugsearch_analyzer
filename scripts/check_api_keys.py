#!/usr/bin/env python3
"""
NVD / DeepL / Groq / OpenRouter / Cisco PSIRT の各APIキーが実際に機能するか、
軽量な呼び出しで素早く確認するスクリプト。

data/vendor_bugs/ の収集ジョブ（数十分かかることがある）を実行してから
「翻訳されていない」「NVDに繋がらない」と分かるのは非効率なため、
ワークフローの先頭でこのスクリプトを実行し、数秒〜十数秒でキーの有効性を
診断できるようにする。

診断のみを目的としており、キーが未設定・無効でもこのスクリプト自体は
常に終了コード0で終わる（後続の収集ステップは既存の翻訳フォールバック
チェーンで自動的に他の手段へフォールバックするため、ここで失敗させる
必要はない）。

使用例:
    python scripts/check_api_keys.py --nvd-api-key "$NVD_API_KEY" --deepl-api-key "$DEEPL_API_KEY"
"""
import argparse

import requests


def check_nvd(api_key):
    if not api_key:
        return None, "未設定（無くても収集は可能。レート制限が厳しくなるだけ）"
    try:
        r = requests.get(
            "https://services.nvd.nist.gov/rest/json/cves/2.0",
            params={"resultsPerPage": 1, "keywordSearch": "test"},
            headers={"apiKey": api_key},
            timeout=15,
        )
        if r.status_code == 200:
            return True, "OK"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def check_deepl(api_key):
    if not api_key:
        return None, "未設定"
    try:
        import deepl
        translator = deepl.Translator(api_key)
        usage = translator.get_usage()
        if usage.character.limit_exceeded:
            return False, f"月間文字数上限に到達済み（{usage.character.count}/{usage.character.limit}）"
        return True, f"OK（今月の使用量: {usage.character.count}/{usage.character.limit}文字）"
    except Exception as e:
        return False, str(e)


def check_groq(api_key):
    if not api_key:
        return None, "未設定"
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        client.chat.completions.create(
            model="openai/gpt-oss-120b",
            max_tokens=5,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "OK"
    except Exception as e:
        return False, str(e)


def check_openrouter(api_key):
    if not api_key:
        return None, "未設定"
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://streamlit.io",
                "X-Title": "Cisco Bug Search Analyzer",
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            },
            timeout=15,
        )
        if r.status_code == 200:
            return True, "OK"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def check_cisco_psirt(client_id, client_secret):
    """Cisco PSIRT openVuln APIはOAuth2のトークン取得のみ確認する
    （アドバイザリ検索自体はクレジット消費が無いためトークン取得成功で十分）"""
    if not client_id or not client_secret:
        return None, "未設定"
    try:
        r = requests.post(
            "https://id.cisco.com/oauth2/default/v1/token",
            data={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        if r.status_code == 200 and r.json().get("access_token"):
            return True, "OK（トークン取得成功）"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nvd-api-key")
    parser.add_argument("--deepl-api-key")
    parser.add_argument("--groq-api-key")
    parser.add_argument("--openrouter-api-key")
    parser.add_argument("--cisco-psirt-client-id")
    parser.add_argument("--cisco-psirt-client-secret")
    args = parser.parse_args()

    checks = [
        ("NVD", check_nvd, args.nvd_api_key),
        ("DeepL", check_deepl, args.deepl_api_key),
        ("Groq", check_groq, args.groq_api_key),
        ("OpenRouter", check_openrouter, args.openrouter_api_key),
    ]

    print("=" * 60)
    print("APIキー疎通チェック（診断のみ、失敗してもジョブは継続します）")
    print("=" * 60)
    for name, fn, key in checks:
        ok, detail = fn(key)
        icon = "⚪" if ok is None else ("✅" if ok else "❌")
        print(f"{icon} {name}: {detail}")

    ok, detail = check_cisco_psirt(args.cisco_psirt_client_id, args.cisco_psirt_client_secret)
    icon = "⚪" if ok is None else ("✅" if ok else "❌")
    print(f"{icon} Cisco PSIRT: {detail}")
    print("=" * 60)


if __name__ == "__main__":
    main()
