"""
本番の翻訳ループ（0.3秒間隔で連続呼び出し）を模倣し、Groq API呼び出しが
実際に失敗する場合の生の例外内容を確認する一時デバッグスクリプト。
analyzer._call_groq_prompt は例外を握りつぶしてNoneを返すだけなので、
実際の失敗理由（レート制限/クォータ超過/その他）が分からないため、
ここでは例外を握りつぶさずそのまま表示する。
確認が終わり次第、対応するworkflowと合わせて削除する。
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from groq import Groq  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--groq-api-key", required=True)
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()

    client = Groq(api_key=args.groq_api_key)
    ok = 0
    fail = 0
    for i in range(args.count):
        if i > 0:
            time.sleep(0.3)
        text = f"Test sentence number {i} for translation bulk test."
        try:
            message = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": (
                        "Translate the following text from English to Japanese. "
                        f"Only return the translated text without any explanation.\n\nText: {text}"
                    ),
                }],
            )
            result = message.choices[0].message.content.strip()
            print(f"[{i}] OK: {result[:50]}")
            ok += 1
        except Exception as e:
            print(f"[{i}] FAIL: {type(e).__name__}: {e}")
            fail += 1

    print()
    print(f"total ok={ok} fail={fail}")


if __name__ == "__main__":
    sys.exit(main())
