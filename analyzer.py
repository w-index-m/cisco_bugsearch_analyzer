"""
Cisco Bug Search Analyzer - コアロジック

Streamlit (app.py) と CLI (cli.py) の両方から利用する共通処理。
Streamlit に依存しないため、エージェントやスクリプトから直接 import して使える。
"""
import io
import re
import json
from html import unescape
from datetime import datetime
from functools import lru_cache

import pandas as pd
import requests
from deep_translator import GoogleTranslator
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

try:
    import deepl
    DEEPL_AVAILABLE = True
except Exception:
    DEEPL_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except Exception:
    GROQ_AVAILABLE = False


# ==================== データ読み込み ====================

def load_csv(file_path):
    """CSV ファイルを読み込み、カラム名の前後空白を除去"""
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    return df


# ==================== リリースノート処理 ====================

def clean_html_tags(text):
    """HTML タグを削除して日本語対応テキストに変換"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_release_note(note_text):
    """リリースノートをセクション別に解析"""
    if not note_text:
        return {}

    text = clean_html_tags(note_text)
    sections = {}

    section_mapping = {
        'Symptom': '症状',
        'Symptôme': '症状',
        'Conditions': '条件',
        'Conditions d\'activation': '条件',
        'Workaround': '回避策',
        'Contournement': '回避策',
        'Further Problem Description': '詳細説明',
        'Description additionnelle du problème': '詳細説明'
    }

    for eng_key, jp_key in section_mapping.items():
        pattern = f'{eng_key}[:\s]*'
        if re.search(pattern, text, re.IGNORECASE):
            parts = re.split(pattern, text, flags=re.IGNORECASE, maxsplit=1)
            if len(parts) > 1:
                content = parts[1].split('\n')[0][:200]
                sections[jp_key] = content

    return sections


def get_cisco_release_notes_url(product, version):
    """Cisco 公式リリースノート URL を生成"""
    product_lower = product.lower()
    if 'catalyst 9200' in product_lower or '9200' in product_lower:
        version_short = version.replace('.', '-')
        return f"https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9200/software/release/{version_short}/release_notes/ol-{version_short}-9200.html"
    elif 'catalyst 9300' in product_lower or '9300' in product_lower:
        version_short = version.replace('.', '-')
        return f"https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/{version_short}/release_notes/ol-{version_short}-9300.html"
    elif 'catalyst 9400' in product_lower or '9400' in product_lower:
        version_short = version.replace('.', '-')
        return f"https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9400/software/release/{version_short}/release_notes/ol-{version_short}-9400.html"
    else:
        return None


# ==================== 翻訳 ====================

@lru_cache(maxsize=4096)
def translate_headline_deepl(text, api_key):
    """DeepL API を使用して日本語に翻訳"""
    if not text or len(text) < 3:
        return text
    try:
        translator = deepl.Translator(api_key)
        result = translator.translate_text(text, source_lang="EN", target_lang="JA")
        return result.text
    except Exception:
        return None


@lru_cache(maxsize=4096)
def translate_headline_google(text):
    """Google Translate を使用して日本語に翻訳"""
    if not text or len(text) < 3:
        return text
    try:
        translator = GoogleTranslator(source_language='en', target_language='ja')
        return translator.translate(text)
    except Exception:
        return None


def translate_headline_nvidia(text, api_key):
    """NVIDIA Riva Translation を使用して日本語に翻訳"""
    if not text or len(text) < 3:
        return None
    if not api_key:
        return None

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "nvidia/riva-translate-4b-instruct-v2",
            "messages": [
                {
                    "role": "user",
                    "content": f"Translate the following text from English to Japanese. Only return the translated text without any explanation.\n\nText: {text}"
                }
            ],
            "temperature": 0.5,
            "top_p": 0.9,
            "max_tokens": 512
        }

        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
        return None

    except Exception:
        return None


def translate_headline(text, engine='google', deepl_api_key=None, nvidia_api_key=None):
    """翻訳エンジンを指定してヘッドラインを翻訳（フォールバック: 指定エンジン → Google）"""
    if not text or len(text) < 3:
        return text

    if engine == 'nvidia' and nvidia_api_key:
        result = translate_headline_nvidia(text, nvidia_api_key)
        if result:
            return result

    if engine == 'deepl' and deepl_api_key and DEEPL_AVAILABLE:
        result = translate_headline_deepl(text, deepl_api_key)
        if result:
            return result

    result = translate_headline_google(text)
    if result:
        return result

    return text


# ==================== 分析データの永続化 ====================

def save_analysis_to_json(analysis_data):
    """分析結果を JSON 文字列に変換"""
    output = {
        "timestamp": datetime.now().isoformat(),
        "analysis_count": len(analysis_data),
        "bugs": []
    }

    for bug_id, data in analysis_data.items():
        output["bugs"].append({
            "bug_id": bug_id,
            "possibility": data.get("possibility", "-"),
            "tags": data.get("tags", []),
            "comment": data.get("comment", "")
        })

    return json.dumps(output, ensure_ascii=False, indent=2)


def load_analysis_from_json(json_str):
    """JSON 文字列から分析結果を読み込み。失敗時は空 dict を返す"""
    try:
        data = json.loads(json_str)
        analysis = {}
        for bug in data.get("bugs", []):
            analysis[bug["bug_id"]] = {
                "possibility": bug.get("possibility", "Medium"),
                "tags": bug.get("tags", []),
                "comment": bug.get("comment", "")
            }
        return analysis
    except Exception:
        return {}


# ==================== AI による発生可能性判定 ====================

def _build_assessment_prompt(headline, release_note, user_comment):
    return f"""以下のバグ情報から、発生の可能性を High/Medium/Low で判定してください。

【バグタイトル（日本語）】
{headline}

【リリースノート】
{release_note[:500] if release_note else ""}

【ユーザーコメント】
{user_comment if user_comment else "（コメントなし）"}

【判定フォーマット】
可能性: [High/Medium/Low]
理由: [簡潔な理由]

日本語で回答してください。"""


def assess_bug_with_groq(headline, release_note, user_comment, api_key):
    """Groq API を使用して発生可能性を判定"""
    if not api_key or not GROQ_AVAILABLE:
        return None

    try:
        client = Groq(api_key=api_key)
        prompt = _build_assessment_prompt(headline, release_note, user_comment)

        message = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.choices[0].message.content
    except Exception:
        return None


def assess_bug_with_gemini(headline, release_note, user_comment, api_key):
    """Gemini API を使用して発生可能性を判定"""
    if not api_key or not GEMINI_AVAILABLE:
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        prompt = _build_assessment_prompt(headline, release_note, user_comment)

        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return None


def assess_bug_with_open_router(headline, release_note, user_comment, api_key):
    """Open Router API を使用して発生可能性を判定"""
    if not api_key:
        return None

    try:
        prompt = _build_assessment_prompt(headline, release_note, user_comment)

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://streamlit.io",
                "X-Title": "Cisco Bug Search Analyzer"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200
            },
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
        return None
    except Exception:
        return None


def assess_bug_possibility(headline_ja, release_note, user_comment, groq_key=None, gemini_key=None, open_router_key=None):
    """
    複数の AI を試してバグの発生可能性を判定

    フォールバック順: Groq → Gemini → Open Router
    """
    assessments = [
        ("Groq", assess_bug_with_groq(headline_ja, release_note, user_comment, groq_key)),
        ("Gemini", assess_bug_with_gemini(headline_ja, release_note, user_comment, gemini_key)),
        ("Open Router", assess_bug_with_open_router(headline_ja, release_note, user_comment, open_router_key))
    ]

    for engine_name, result in assessments:
        if result:
            return {"engine": engine_name, "result": result}

    return None


# ==================== バージョン比較 ====================

_VERSION_DIGITS_RE = re.compile(r'\d+')


def _parse_version_tuple(token):
    """
    バージョン文字列から (major, minor, patch) の整数タプルを抽出する。

    コードネーム接頭辞（Dublin-17.12.5）、括弧表記（17.12(4.2)）、
    末尾の英字サフィックス（17.12.4a）、旧 IOS 表記（3.10.1E_ngwc）などを許容する。
    数値が2つ未満しか取れない場合（sdk-master など）は None を返す。
    """
    digits = _VERSION_DIGITS_RE.findall(str(token))
    if len(digits) < 2:
        return None
    nums = [int(d) for d in digits[:3]]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def version_affects_bug(affected_str, fixed_str, target_version):
    """
    target_version 時点でバグが「影響あり（未修正）」かどうかを判定する。

    ロジック:
    1. target と同じトレイン（major.minor）の Known Affected Release(s) の中に
       target 以前（同じか古い）のバージョンがあれば、そのトレインで「影響が始まっている」とみなす
    2. 同じトレインの Known Fixed Releases の中に target 以前（同じか古い）の修正版が
       無ければ「まだ直っていない」と判定し True を返す
    3. target_version が数値として解析できない場合（例: "master" 等）は、
       従来通り Known Affected Release(s) への部分文字列一致にフォールバックする
    """
    target = _parse_version_tuple(target_version)

    if target is None:
        return str(target_version).lower() in str(affected_str).lower()

    train = target[:2]

    affected_tokens = str(affected_str).split() if pd.notna(affected_str) else []
    affected_versions = [
        v for v in (_parse_version_tuple(t) for t in affected_tokens)
        if v is not None and v[:2] == train
    ]

    if not affected_versions:
        return False

    if not any(v <= target for v in affected_versions):
        # 同トレインの影響開始バージョンが target より後 → まだそのバージョンに到達していない
        return False

    fixed_tokens = str(fixed_str).split() if pd.notna(fixed_str) else []
    fixed_versions = [
        v for v in (_parse_version_tuple(t) for t in fixed_tokens)
        if v is not None and v[:2] == train
    ]

    if any(v <= target for v in fixed_versions):
        # 同トレインで target 以前に修正版がリリース済み → 既に直っている
        return False

    return True


# ==================== バグ検索 ====================

def search_bugs(df, feature=None, version=None, severity=None, ios_version=None, sort_by=None):
    """
    条件に応じて df をフィルタリングする

    Args:
        df: バグデータ全体
        feature: Product - Series / BUG headline に対する部分一致
        version: 検索バージョン。同トレイン内で「これ以前のバージョンから影響していて、
            まだ修正版が出ていない」バグも含めてマッチする（version_affects_bug 参照）。
            数値として解釈できない文字列を渡した場合は部分一致にフォールバックする。
        severity: 対象とする Severity のリスト（例: [1, 2, 3]）
        ios_version: 特定 IOS バージョンでの絞り込み（version と併用可、判定ロジックは同じ）
        sort_by: "severity" | "last_modified" | "bug_id"

    Returns:
        絞り込み・ソート済みの DataFrame
    """
    results = df.copy()

    if severity:
        results = results[results["Bug Severity"].astype(int).isin(severity)]

    if feature:
        mask = (
            results["Product - Series"].str.contains(feature, case=False, na=False) |
            results["BUG headline"].str.contains(feature, case=False, na=False)
        )
        results = results[mask]

    if version:
        mask = results.apply(
            lambda row: version_affects_bug(
                row["Known Affected Release(s)"], row.get("Known Fixed Releases"), version
            ),
            axis=1,
        )
        results = results[mask]

    if ios_version:
        mask = results.apply(
            lambda row: version_affects_bug(
                row["Known Affected Release(s)"], row.get("Known Fixed Releases"), ios_version
            ),
            axis=1,
        )
        results = results[mask]

    if sort_by == "severity":
        results = results.sort_values("Bug Severity", ascending=True)
    elif sort_by == "last_modified":
        results = results.sort_values("Last Modified", ascending=False)
    elif sort_by == "bug_id":
        results = results.sort_values("BUG Id")

    return results


def list_affected_releases(df):
    """CSV 内に登場する全 Known Affected Release(s) のユニーク一覧（降順ソート）"""
    all_releases = set()
    for releases in df["Known Affected Release(s)"].dropna():
        for release in str(releases).split():
            all_releases.add(release.strip())
    return sorted([r for r in all_releases if r], reverse=True)


# ==================== Excel レポート生成 ====================

def create_excel_report(results, analysis_data, search_params):
    """
    Excel 形式のレポートを生成

    複数シート構成:
    - Sheet1 検索結果: バグ情報 + 分析結果
    - Sheet2 分析詳細: 分析結果のみ
    - Sheet3 検索パラメータ: 検索条件とメタデータ
    """
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "検索結果"
    ws2 = wb.create_sheet("分析詳細")
    ws3 = wb.create_sheet("検索パラメータ")

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Sheet1: 検索結果
    headers = ["Bug ID", "Headline (日本語)", "Severity", "Status",
               "Affected Releases", "Fixed Releases", "発生可能性", "関連機能", "コメント"]

    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    for row, (idx, bug_row) in enumerate(results.iterrows(), 2):
        bug_id = bug_row["BUG Id"]
        analysis = analysis_data.get(bug_id, {})
        headline = bug_row.get("BUG headline (日本語)")
        if headline is None or (isinstance(headline, float) and pd.isna(headline)):
            headline = bug_row.get("BUG headline", "")

        row_data = [
            bug_id,
            headline,
            bug_row["Bug Severity"],
            bug_row["Bug Status"],
            bug_row["Known Affected Release(s)"],
            bug_row["Known Fixed Releases"],
            analysis.get("possibility", "-"),
            ", ".join(analysis.get("tags", [])),
            analysis.get("comment", "")
        ]

        for col, value in enumerate(row_data, 1):
            cell = ws1.cell(row=row, column=col)
            cell.value = value
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border

    ws1.column_dimensions['A'].width = 15
    ws1.column_dimensions['B'].width = 40
    ws1.column_dimensions['C'].width = 10
    ws1.column_dimensions['D'].width = 12
    ws1.column_dimensions['E'].width = 25
    ws1.column_dimensions['F'].width = 25
    ws1.column_dimensions['G'].width = 12
    ws1.column_dimensions['H'].width = 20
    ws1.column_dimensions['I'].width = 30

    # Sheet2: 分析詳細
    analysis_headers = ["Bug ID", "発生可能性", "関連機能", "コメント"]

    for col, header in enumerate(analysis_headers, 1):
        cell = ws2.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border

    for row, (bug_id, data) in enumerate(analysis_data.items(), 2):
        row_data = [
            bug_id,
            data.get("possibility", "-"),
            ", ".join(data.get("tags", [])),
            data.get("comment", "")
        ]

        for col, value in enumerate(row_data, 1):
            cell = ws2.cell(row=row, column=col)
            cell.value = value
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border

    ws2.column_dimensions['A'].width = 15
    ws2.column_dimensions['B'].width = 15
    ws2.column_dimensions['C'].width = 25
    ws2.column_dimensions['D'].width = 40

    # Sheet3: 検索パラメータ
    params_data = [
        ["検索パラメータ", ""],
        ["", ""],
        ["タイムスタンプ", datetime.now().isoformat()],
        ["機能", search_params.get("feature") or "（なし）"],
        ["バージョン", search_params.get("version") or "（なし）"],
        ["Severity フィルタ", ", ".join(map(str, search_params.get("severity", [])))],
        ["", ""],
        ["分析情報", ""],
        ["分析済みバグ数", len(analysis_data)],
    ]

    for row, (key, value) in enumerate(params_data, 1):
        cell_key = ws3.cell(row=row, column=1)
        cell_value = ws3.cell(row=row, column=2)

        cell_key.value = key
        cell_value.value = value

        if key in ["検索パラメータ", "分析情報"]:
            cell_key.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            cell_key.font = Font(bold=True)

        cell_key.border = border
        cell_value.border = border

    ws3.column_dimensions['A'].width = 20
    ws3.column_dimensions['B'].width = 40

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)

    return excel_buffer.getvalue()
