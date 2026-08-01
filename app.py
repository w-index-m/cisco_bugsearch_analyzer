import streamlit as st
import pandas as pd
import io
import re
from html import unescape
from deep_translator import GoogleTranslator

try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False

import requests
import os

st.set_page_config(page_title="Cisco Bug Search Analyzer", layout="wide")

st.title("🔍 Cisco Bug Search Analyzer")
st.markdown("Cisco バグ検索システム - 機能とバージョンから該当するバグを検索")

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

@st.cache_data
def translate_headline_deepl(text, api_key):
    """DeepL API を使用して日本語に翻訳"""
    if not text or len(text) < 3:
        return text
    try:
        translator = deepl.Translator(api_key)
        result = translator.translate_text(text, source_lang="EN", target_lang="JA")
        return result.text
    except Exception as e:
        return None

@st.cache_data
def translate_headline_google(text):
    """Google Translate を使用して日本語に翻訳"""
    if not text or len(text) < 3:
        return text
    try:
        translator = GoogleTranslator(source_language='en', target_language='ja')
        return translator.translate(text)
    except Exception as e:
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

    except Exception as e:
        return None

def translate_headline(text, engine='google', deepl_api_key=None, nvidia_api_key=None):
    """翻訳エンジンを指定してヘッドラインを翻訳"""
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

@st.cache_data
def load_csv(file_path):
    """CSV ファイルを読み込み"""
    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
        return None

# CSV ファイル読み込み（デフォルト）
default_csv = "bugSearch.csv"

# ファイルアップロード or デフォルトを使用
uploaded_file = st.file_uploader("CSV ファイルをアップロード（オプション）", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()
else:
    df = load_csv(default_csv)

if df is not None:
    st.success(f"✓ {len(df)} 件のバグ情報を読み込みました")

    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("IOS バージョンから検索")
    with col2:
        st.subheader("翻訳設定")

    col1, col2 = st.columns([2, 1])
    with col2:
        translation_engine = st.radio(
            "翻訳エンジン",
            ["Google", "DeepL", "NVIDIA Riva"],
            horizontal=False,
            index=0
        )

        deepl_api_key = None
        nvidia_api_key = None

        if translation_engine == "DeepL":
            if DEEPL_AVAILABLE:
                deepl_api_key = st.text_input(
                    "DeepL API キー",
                    type="password",
                    placeholder="API キーを入力"
                )
                if not deepl_api_key:
                    st.warning("DeepL API キーを入力してください")
            else:
                st.warning("deepl ライブラリがインストールされていません")
                translation_engine = "Google"

        elif translation_engine == "NVIDIA Riva":
            nvidia_api_key = st.text_input(
                "NVIDIA API キー",
                type="password",
                placeholder="API キーを入力"
            )
            if not nvidia_api_key:
                st.warning("NVIDIA API キーを入力してください")

    st.markdown("---")
    st.subheader("IOS バージョンから検索")

    all_affected_releases = set()
    for releases in df["Known Affected Release(s)"].dropna():
        for release in str(releases).split():
            all_affected_releases.add(release.strip())

    sorted_releases = sorted([r for r in all_affected_releases if r], reverse=True)

    selected_ios_version = st.selectbox(
        "IOS バージョンを選択",
        [""] + sorted_releases,
        format_func=lambda x: "バージョンを選択..." if x == "" else x
    )

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        feature = st.text_input(
            "機能を入力（Product / Headline）",
            placeholder="例：Catalyst 9300, multicast, etc."
        )

    with col2:
        version = st.text_input(
            "バージョンを入力（Known Affected Release）",
            placeholder="例：17.12.4, 17.15.2, etc."
        )

    search_button = st.button("🔎 バグを検索", type="primary")

    st.markdown("---")

    if selected_ios_version:
        st.info(f"📋 **IOS {selected_ios_version} のリリースノート情報**")

        ios_bugs = df[
            df["Known Affected Release(s)"].str.contains(selected_ios_version, case=False, na=False)
        ].copy()

        if len(ios_bugs) > 0:
            st.write(f"**このバージョンに影響するバグ: {len(ios_bugs)} 件**")

            with st.expander("🔍 このバージョンのリリースノート内のバグ情報"):
                for idx, bug in ios_bugs.head(10).iterrows():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{bug['BUG Id']}** - {bug['BUG headline'][:60]}")
                    with col2:
                        severity = bug['Bug Severity']
                        st.write(f"Severity: {severity}")
                    with col3:
                        st.write(f"Status: {bug['Bug Status']}")

                if len(ios_bugs) > 10:
                    st.caption(f"... 他 {len(ios_bugs) - 10} 件")
        else:
            st.write("このバージョンのバグ情報がありません")

        st.markdown("---")

    if search_button or (feature or version):
        results = df.copy()

        if feature:
            mask = (
                results["Product - Series"].str.contains(feature, case=False, na=False) |
                results["BUG headline"].str.contains(feature, case=False, na=False)
            )
            results = results[mask]

        if version:
            mask = results["Known Affected Release(s)"].str.contains(version, case=False, na=False)
            results = results[mask]

        if selected_ios_version:
            mask = results["Known Affected Release(s)"].str.contains(selected_ios_version, case=False, na=False)
            results = results[mask]

        st.subheader(f"検索結果: {len(results)} 件")

        if len(results) > 0:
            sort_by = st.selectbox(
                "ソート順",
                ["Bug Severity (高い順)", "Last Modified (新しい順)", "Bug ID"]
            )

            if sort_by == "Bug Severity (高い順)":
                results = results.sort_values("Bug Severity", ascending=True)
            elif sort_by == "Last Modified (新しい順)":
                results = results.sort_values("Last Modified", ascending=False)
            else:
                results = results.sort_values("BUG Id")

            display_results = results.copy()
            display_results["BUG headline (日本語)"] = display_results["BUG headline"].apply(
                lambda x: translate_headline(x, engine=translation_engine, deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key)
            )

            display_cols = ["BUG Id", "BUG headline (日本語)", "Bug Severity", "Bug Status",
                          "Known Affected Release(s)", "Known Fixed Releases"]

            st.dataframe(
                display_results[display_cols],
                use_container_width=True,
                hide_index=True
            )

            st.markdown("### 詳細情報")
            selected_idx = st.selectbox(
                "詳細を見るバグを選択",
                range(len(results)),
                format_func=lambda x: f"{results.iloc[x]['BUG Id']} - {translate_headline(results.iloc[x]['BUG headline'], engine=translation_engine, deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key)}"
            )

            if selected_idx is not None:
                bug = results.iloc[selected_idx]

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Bug ID", bug["BUG Id"])
                with col2:
                    severity = int(bug["Bug Severity"]) if pd.notna(bug["Bug Severity"]) else 0
                    st.metric("重要度", severity)
                with col3:
                    st.metric("ステータス", bug["Bug Status"])

                headline_en = bug["BUG headline"]
                headline_ja = translate_headline(headline_en, engine=translation_engine, deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key)

                st.write("**タイトル（日本語）:**", headline_ja)
                st.caption(f"英語: {headline_en}")
                if translation_engine != "Google":
                    st.caption(f"翻訳エンジン: {translation_engine}")

                release_note = bug["Release Note Enclosure"]
                sections = parse_release_note(release_note)

                if sections:
                    st.markdown("### 📋 リリースノート情報")

                    for section_name, content in sections.items():
                        st.write(f"**{section_name}:**")
                        st.caption(content)

                    # Cisco 公式ドキュメントへのリンク
                    affected_releases = str(bug["Known Affected Release(s)"]).split()
                    if affected_releases:
                        first_version = affected_releases[0]
                        product = bug["Product - Series"].split(',')[0].strip()
                        release_url = get_cisco_release_notes_url(product, first_version)

                        if release_url:
                            st.info(
                                f"📚 **参考資料**: "
                                f"[Cisco 公式リリースノート - {product} {first_version}]({release_url})"
                            )

                st.markdown("---")
                st.write("**製品:**", bug["Product - Series"])
                st.write("**影響を受けるバージョン:**", bug["Known Affected Release(s)"])
                st.write("**修正バージョン:**", bug["Known Fixed Releases"])
                st.write("**最終更新:**", bug["Last Modified"])

                col1, col2 = st.columns(2)
                with col1:
                    st.write("**参照リンク:**")
                    st.write(f"[Cisco Bug Search で詳細を確認]({bug['URL']})")

                with st.expander("📄 リリースノート全体"):
                    clean_note = clean_html_tags(release_note)
                    st.text(clean_note)

            st.markdown("---")
            csv_buffer = io.StringIO()
            results[display_cols].to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()

            st.download_button(
                label="📥 検索結果を CSV でダウンロード",
                data=csv_data,
                file_name="bug_search_results.csv",
                mime="text/csv"
            )
        else:
            st.warning("該当するバグが見つかりませんでした")
else:
    st.error("CSV ファイルを読み込めません")
