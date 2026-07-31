import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Cisco Bug Search Analyzer", layout="wide")

st.title("🔍 Cisco Bug Search Analyzer")
st.markdown("Cisco バグ検索システム - 機能とバージョンから該当するバグを検索")

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

    # 検索フォーム
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

    # 検索実行
    if search_button or (feature or version):
        results = df.copy()

        # 機能で絞り込み
        if feature:
            mask = (
                results["Product - Series"].str.contains(feature, case=False, na=False) |
                results["BUG headline"].str.contains(feature, case=False, na=False)
            )
            results = results[mask]

        # バージョンで絞り込み
        if version:
            mask = results["Known Affected Release(s)"].str.contains(version, case=False, na=False)
            results = results[mask]

        # 結果表示
        st.subheader(f"検索結果: {len(results)} 件")

        if len(results) > 0:
            # ソート
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

            # 結果をテーブルで表示
            display_cols = ["BUG Id", "BUG headline", "Bug Severity", "Bug Status",
                          "Known Affected Release(s)", "Known Fixed Releases"]

            st.dataframe(
                results[display_cols],
                use_container_width=True,
                hide_index=True
            )

            # 詳細表示
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
                    st.metric("Severity", bug["Bug Severity"])
                with col3:
                    st.metric("Status", bug["Bug Status"])

                st.write("**Headline:**", bug["BUG headline"])
                st.write("**URL:**", f"[バグを開く]({bug['URL']})")
                st.write("**Product Series:**", bug["Product - Series"])
                st.write("**Affected Releases:**", bug["Known Affected Release(s)"])
                st.write("**Fixed Releases:**", bug["Known Fixed Releases"])
                st.write("**Last Modified:**", bug["Last Modified"])

                with st.expander("詳細説明"):
                    st.write(bug["Release Note Enclosure"])

            # CSV ダウンロード
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
