import streamlit as st
import pandas as pd
import io
import re
from html import unescape

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

            display_cols = ["BUG Id", "BUG headline", "Bug Severity", "Bug Status",
                          "Known Affected Release(s)", "Known Fixed Releases"]

            st.dataframe(
                results[display_cols],
                use_container_width=True,
                hide_index=True
            )

            st.markdown("### 詳細情報")
            selected_idx = st.selectbox(
                "詳細を見るバグを選択",
                range(len(results)),
                format_func=lambda x: f"{results.iloc[x]['BUG Id']} - {results.iloc[x]['BUG headline'][:50]}"
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

                st.write("**タイトル:**", bug["BUG headline"])

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
